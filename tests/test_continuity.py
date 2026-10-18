"""Real local HTTP fixtures; no production graph or user state is accessed."""

import copy
import http.server
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import engram_continuity as core


CHECKPOINT = {"objective": "Deliver the client film", "progress": "Rough cut approved",
              "next_action": "Mix dialogue and export the review cut", "decisions": ["Keep the quiet opening"],
              "references": ["D:/Відео/Client Film/edit.project"], "blockers": [], "verification": ""}


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="engram continuity ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.notes = {}
        self.deleted = 0
        self.writes = 0
        self.mode = "ok"
        self.sse = False
        self.shape = "structured"
        self.on_read = None
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                method = payload["method"]
                if outer.mode == "offline":
                    self.send_error(503)
                    return
                if method == "notifications/initialized":
                    self.send_response(202)
                    self.end_headers()
                    return
                error = None
                if method == "initialize":
                    result = {"protocolVersion": "2025-06-18", "serverInfo": {"name": "test", "version": "1"}}
                else:
                    name = payload["params"]["name"]
                    args = payload["params"]["arguments"]
                    if name == "list_memory_projects":
                        result = {"structuredContent": {"result": {"constrained_project": "other" if outer.mode == "wrong_project" else "engram"}}}
                    elif name == "write_note":
                        outer.writes += 1
                        if outer.mode == "write_error":
                            result = {"isError": True, "content": [{"type": "text", "text": "Write failed"}]}
                        elif outer.mode == "rpc_error":
                            result = {}
                            error = {"code": -32603, "message": "Write RPC failed"}
                        else:
                            if args["project"] != "engram" or not args["overwrite"]:
                                raise AssertionError("Checkpoint write must target engram and update the same chat note")
                            outer.notes[args["title"]] = {"content": args["content"], "directory": args["directory"]}
                            result = {"structuredContent": {"result": {"title": args["title"]}}}
                    elif name == "read_note":
                        if outer.on_read:
                            callback, outer.on_read = outer.on_read, None
                            callback()
                        if outer.mode == "read_error":
                            result = {"isError": True}
                        else:
                            stored = outer.notes.get(args["identifier"])
                            if stored is None:
                                result = {"structuredContent": {"result": {"title": None, "content": None, "file_path": None}}}
                                body = json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": result})
                                self.send_response(200)
                                self.send_header("Content-Type", "application/json")
                                self.end_headers()
                                self.wfile.write(body.encode("utf-8"))
                                return
                            content = stored["content"]
                            if outer.mode == "mismatch":
                                content += "\nUnexpected extra text\n"
                            if outer.mode == "wrong_chat":
                                content = content.replace(core.session_key("chat-one"), core.session_key("chat-two"))
                            note = {"title": args["identifier"], "content": content,
                                    "file_path": stored["directory"] + "/checkpoint.md"}
                            if outer.shape == "structured":
                                result = {"structuredContent": {"result": note}}
                            elif outer.shape == "json_text":
                                result = {"content": [{"type": "text", "text": json.dumps({"result": note})}]}
                            else:
                                result = {"content": [{"type": "text", "text": content}]}
                    else:
                        raise AssertionError(name)
                response = {"jsonrpc": "2.0", "id": payload["id"]}
                response["error" if error else "result"] = error or result
                body = json.dumps(response)
                if outer.sse:
                    body = "event: message\ndata: " + body + "\n\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream" if outer.sse else "application/json")
                self.send_header("Mcp-Session-Id", "fixture-session")
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))

            def do_DELETE(self):
                outer.deleted += 1
                self.send_response(200)
                self.end_headers()

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.env = {"CODEX_HOME": str(self.root / "codex"),
                    "ENGRAM_MCP_URL": f"http://127.0.0.1:{self.server.server_port}/mcp"}
        self.chat = core.Continuity("chat-one", self.env)

    def test_status_is_read_only_and_turn_generation_is_monotonic(self):
        status = self.chat.status()
        self.assertEqual(status["generation"], 1)
        self.assertEqual(status["verified_generation"], 0)
        self.assertTrue(status["needs_checkpoint"])
        self.assertFalse(self.chat.directory.exists())
        self.assertEqual(self.chat.begin_turn()["generation"], 2)
        self.assertEqual(self.chat.begin_turn()["generation"], 3)
        self.assertEqual(self.chat.session_id, "chat-one")

    def test_json_sse_and_readback_shapes_commit_only_verified_receipts(self):
        for sse, shape in ((False, "structured"), (True, "structured"), (True, "json_text"), (False, "raw")):
            with self.subTest(sse=sse, shape=shape):
                self.sse, self.shape = sse, shape
                generation = self.chat.begin_turn()["generation"]
                result = self.chat.save(CHECKPOINT, "projects/client-film")
                self.assertTrue(result["verified"])
                self.assertEqual(result["generation"], generation)
                self.assertTrue(Path(result["local_attempt"]).exists())
                status = self.chat.status()
                self.assertEqual(status["verified_generation"], generation)
                self.assertIsInstance(status["verified_at"], float)
                self.assertFalse(status["needs_checkpoint"])
                self.assertEqual(status["pending_attempts"], [])
                recovered = self.chat.recover()
                self.assertEqual(recovered["checkpoint"], CHECKPOINT)
                self.assertEqual(recovered["source"], "graph")
                self.assertTrue(recovered["graph_validated"])
        self.assertEqual(len(self.notes), 1)
        self.assertEqual(self.notes[self.chat.identifier]["directory"], "projects/client-film/live/chats")
        self.assertGreaterEqual(self.deleted, 8)

    def test_all_remote_failures_preserve_receipt_and_stage_new_candidate(self):
        self.chat.save(CHECKPOINT)
        receipt = copy.deepcopy(self.chat.read_state()["receipt"])
        for mode in ("write_error", "rpc_error", "read_error", "mismatch", "wrong_chat", "offline"):
            with self.subTest(mode=mode):
                self.mode = mode
                self.chat.begin_turn()
                with self.assertRaises(core.ContinuityError):
                    self.chat.save({**CHECKPOINT, "progress": "Updated " + mode})
                state = self.chat.read_state()
                self.assertEqual(state["receipt"], receipt)
                status = self.chat.status()
                self.assertTrue(status["needs_checkpoint"])
                self.assertGreater(len(status["pending_attempts"]), 0)
                self.assertTrue(all(Path(item["path"]).exists() for item in status["pending_attempts"]))

    def test_offline_recovery_uses_only_last_verified_snapshot(self):
        self.chat.save(CHECKPOINT)
        self.chat.begin_turn()
        self.mode = "offline"
        with self.assertRaises(core.ContinuityError):
            self.chat.save({**CHECKPOINT, "progress": "Unsaved new colour grade"})
        result = self.chat.recover()
        self.assertEqual(result["source"], "local_snapshot")
        self.assertFalse(result["graph_validated"])
        self.assertEqual(result["checkpoint"], CHECKPOINT)
        self.assertTrue(result["pending_attempts"])
        self.assertTrue(self.chat.status()["needs_checkpoint"])

    def test_pending_work_is_preserved_when_no_verified_snapshot_exists(self):
        self.mode = "offline"
        for progress in ("First draft", "Revised draft"):
            with self.assertRaises(core.ContinuityError):
                self.chat.save({**CHECKPOINT, "progress": progress})
        status = self.chat.status()
        self.assertEqual(status["verified_generation"], 0)
        self.assertEqual(len(status["pending_attempts"]), 2)
        with self.assertRaisesRegex(core.ContinuityError, "No verified checkpoint"):
            self.chat.recover()

    def test_receipt_write_failure_after_remote_success_does_not_acknowledge(self):
        original = core._atomic_json

        def fail_receipt(path, value):
            if path == self.chat.state_path and value.get("receipt"):
                raise core.ContinuityError("simulated full disk during receipt commit")
            return original(path, value)

        with patch.object(core, "_atomic_json", side_effect=fail_receipt):
            with self.assertRaisesRegex(core.ContinuityError, "not acknowledged"):
                self.chat.save(CHECKPOINT)
        self.assertIn(self.chat.identifier, self.notes)
        self.assertTrue(self.chat.status()["needs_checkpoint"])
        self.assertEqual(self.chat.status()["verified_generation"], 0)
        self.assertTrue(self.chat.status()["pending_attempts"])
        self.assertTrue(self.chat.recover()["graph_validated"])
        self.assertEqual(self.chat.status()["verified_generation"], 0)
        self.assertTrue(self.chat.status()["needs_checkpoint"])

    def test_graph_only_recovery_preserves_route_and_never_acknowledges_a_save(self):
        self.chat.begin_turn()
        saved = self.chat.save(CHECKPOINT, "projects/client-film")
        shutil.rmtree(self.chat.directory)
        recovered = self.chat.recover()
        self.assertEqual(recovered["checkpoint"], CHECKPOINT)
        status = self.chat.status()
        self.assertEqual(status["project_directory"], "projects/client-film")
        self.assertGreater(status["generation"], saved["generation"])
        self.assertEqual(status["verified_generation"], 0)
        self.assertTrue(status["needs_checkpoint"])
        updated = self.chat.save({**CHECKPOINT, "progress": "Recovered progress reconciled"})
        self.assertGreater(updated["generation"], saved["generation"])
        self.assertEqual(self.notes[self.chat.identifier]["directory"], "projects/client-film/live/chats")

    def test_missing_local_state_cannot_overwrite_existing_graph_without_recovery(self):
        self.chat.begin_turn()
        self.chat.save(CHECKPOINT, "projects/client-film")
        stored = copy.deepcopy(self.notes[self.chat.identifier])
        shutil.rmtree(self.chat.directory)
        with self.assertRaisesRegex(core.ContinuityError, "must be recovered"):
            self.chat.save({**CHECKPOINT, "progress": "Incomplete replacement"})
        self.assertEqual(self.notes[self.chat.identifier], stored)
        self.assertEqual(self.writes, 1)
        self.assertTrue(self.chat.status()["pending_attempts"])

    def test_missing_graph_note_is_only_optional_for_startup_recovery(self):
        self.assertEqual(self.chat.recover(allow_missing=True)["source"], "none")
        self.assertFalse(self.chat.directory.exists())
        with self.assertRaisesRegex(core.ContinuityError, "No graph checkpoint exists"):
            self.chat.recover()

    def test_concurrent_new_turn_survives_save_receipt_commit(self):
        self.on_read = self.chat.begin_turn
        result = self.chat.save(CHECKPOINT)
        self.assertEqual(result["generation"], 1)
        status = self.chat.status()
        self.assertEqual(status["generation"], 2)
        self.assertEqual(status["verified_generation"], 1)
        self.assertTrue(status["needs_checkpoint"])

    def test_chats_are_isolated_and_route_is_stable(self):
        other = core.Continuity("chat-two", self.env)
        self.chat.save(CHECKPOINT, "projects/client-film")
        other.save({**CHECKPOINT, "objective": "Another film"}, "projects/client-film")
        self.assertNotEqual(self.chat.identifier, other.identifier)
        self.assertEqual(len(self.notes), 2)
        self.assertEqual(self.chat.recover()["checkpoint"]["objective"], CHECKPOINT["objective"])
        self.chat.save(CHECKPOINT)  # An omitted project reuses the established route.
        with self.assertRaisesRegex(core.ContinuityError, "route is already"):
            self.chat.save(CHECKPOINT, "projects/other-project")

    def test_malformed_checkpoint_and_unsafe_project_never_reach_network(self):
        for value in ({}, {**CHECKPOINT, "progress": " "}, {**CHECKPOINT, "blockers": [None]},
                      {**CHECKPOINT, "verification": None}, {**CHECKPOINT, "extra": "transcript"},
                      {**CHECKPOINT, "progress": "x" * core.MAX_INPUT_BYTES}):
            with self.subTest(value=str(value)[:60]), self.assertRaises(core.ContinuityError):
                self.chat.save(value)
        with self.assertRaises(core.ContinuityError):
            self.chat.save(CHECKPOINT, "projects/../escape")
        self.assertEqual(self.writes, 0)
        for identifier in ("", "unknown", " UNKNOWN ", None):
            with self.assertRaises(core.ContinuityError):
                core.session_key(identifier)

    def test_wrong_service_project_prevents_write(self):
        self.mode = "wrong_project"
        with self.assertRaisesRegex(core.ContinuityError, "not constrained"):
            self.chat.save(CHECKPOINT)
        self.assertEqual(self.writes, 0)
        self.assertTrue(self.chat.status()["pending_attempts"])

    def test_process_crash_releases_state_lock(self):
        code = "import os,sys;sys.path.insert(0,sys.argv[1]);from engram_continuity import Continuity;c=Continuity('chat-one',{'CODEX_HOME':sys.argv[2]});lock=c._lock();lock.__enter__();os._exit(0)"
        child = subprocess.run([sys.executable, "-B", "-c", code, str(Path(core.__file__).parent), self.env["CODEX_HOME"]], capture_output=True)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(self.chat.begin_turn()["generation"], 2)

    def test_cli_status_and_input_limit(self):
        result = subprocess.run([sys.executable, "-B", core.__file__, "status", "--session-id", "chat-one"],
                                env={**__import__("os").environ, **self.env}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["needs_checkpoint"])
        path = self.root / "too-large.json"
        path.write_bytes(b"x" * (core.MAX_INPUT_BYTES + 1))
        result = subprocess.run([sys.executable, "-B", core.__file__, "save", "--session-id", "chat-one", "--file", str(path)],
                                env={**__import__("os").environ, **self.env}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("32 KiB", result.stderr)
        self.assertEqual(self.writes, 0)


if __name__ == "__main__":
    unittest.main()
