import http.server
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import engram_portable as runtime


HEALTHY = {"healthy": True, "notify": False, "message": ""}
OFFLINE = {"healthy": False, "notify": True, "message": "Engram unavailable"}


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="engram portable ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "settings.json"
        self.sessions = self.root / "codex" / "sessions"
        self.sessions.mkdir(parents=True)
        self.transcript = self.sessions / "video session.jsonl"
        self.transcript.write_text("{}\n", encoding="utf-8")
        self.env = {"ENGRAM_CONFIG_PATH": str(self.config), "CODEX_HOME": str(self.root / "codex"),
                    "ENGRAM_CODEX_SESSION_SOFT_MIB": "1", "ENGRAM_CODEX_SESSION_HARD_MIB": "2"}
        self.payload = {"hook_event_name": "SessionStart", "session_id": "video-session", "cwd": str(self.root / "My Film"),
                        "transcript_path": str(self.transcript)}

    def hook(self, event, enabled=True, health=HEALTHY, **values):
        env = dict(self.env, ENGRAM_CHECKPOINTS_ENABLED=str(enabled).lower())
        return runtime.handle_hook(dict(self.payload, hook_event_name=event, **values), env, health)

    def grow(self, size):
        with self.transcript.open("r+b") as stream:
            stream.truncate(size)

    def test_video_project_without_git(self):
        result = runtime.resolve_project(str(self.root / "Launch Video 2026"))
        self.assertEqual(result["directory"], "projects/launch-video-2026")
        self.assertEqual(runtime.resolve_project()["directory"], "global")

    def test_explicit_name_and_selected_workspace(self):
        result = runtime.resolve_project(str(self.root / "assets"), "Client Film", str(self.root / "Campaign"))
        self.assertEqual(result["name"], "client-film")
        self.assertEqual(result["root"], str((self.root / "Campaign").resolve()))

    def test_home_and_store_are_not_invented_projects(self):
        self.assertIsNone(runtime.resolve_project(str(Path.home()))["name"])
        self.assertIsNone(runtime.resolve_project(str(Path.home() / "Engram"))["name"])
        self.assertEqual(runtime.resolve_project(str(Path.home()), "My Film")["name"], "my-film")
        custom = self.root / "Personal Brain"
        self.assertIsNone(runtime.resolve_project(str(custom), store_path=str(custom))["name"])
        runtime.init_store(custom, self.root / "Runtime")
        self.assertIsNone(runtime.resolve_project(str(custom))["name"])

    def test_status_uses_configured_store_and_keeps_media_outside_note_counts(self):
        store = self.root / "Personal Brain"
        runtime.init_store(store, self.root / "Runtime")
        (store / "projects" / "film.md").write_text("# Film", encoding="utf-8")
        (store / "projects" / "video.mp4").write_bytes(b"not media content")
        result = runtime.store_summary({"store_path": str(store)})
        self.assertEqual(result["path"], str(store))
        self.assertEqual(result["note_counts"], {"global": 0, "projects": 1})

    def test_git_root_without_git_command(self):
        repo = self.root / "Old Film"
        (repo / ".git").mkdir(parents=True)
        assets = repo / "assets"
        assets.mkdir()
        self.assertEqual(runtime.resolve_project(str(assets))["name"], "old-film")

    def test_store_descendants_are_not_projects_after_git_root_discovery(self):
        store = self.root / "Personal Brain"
        runtime.init_store(store, self.root / "Runtime")
        (store / ".git").mkdir()
        nested = store / "global" / "workflow"
        self.assertEqual(runtime.resolve_project(str(nested))["directory"], "global")
        self.assertEqual(runtime.resolve_project(str(nested), store_path=str(store))["directory"], "global")
        self.assertEqual(runtime.resolve_project(str(nested), "Explicit Film")["directory"], "projects/explicit-film")

    def test_start_context_retains_memory_when_checkpoints_disabled(self):
        result = self.hook("SessionStart", enabled=False)
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("1-3", context)
        self.assertIn("verified knowledge", context)
        self.assertIn("projects/my-film", context)
        self.assertIn("checkpoints are disabled", context)
        self.assertNotIn("Update one small", context)

    def test_offline_compaction_gate_respects_toggle(self):
        self.assertFalse(self.hook("PreCompact", health=OFFLINE)["continue"])
        result = self.hook("PreCompact", enabled=False, health=OFFLINE)
        self.assertTrue(result["continue"])
        self.assertIn("unavailable", result["systemMessage"])

    def test_checkpoint_request_is_gated_by_settings(self):
        self.grow(1024**2)
        self.assertEqual(self.hook("Stop")["decision"], "block")
        self.assertFalse(self.hook("Stop", stop_hook_active=True)["continue"])
        self.assertEqual(self.hook("Stop")["decision"], "block")
        self.grow(2 * 1024**2)
        self.assertEqual(self.hook("Stop", enabled=False), {})
        self.assertFalse(self.hook("Stop", stop_hook_active=True)["continue"])

    def test_history_emergency_boundary_remains_when_checkpoints_off(self):
        self.grow(2 * 1024**2)
        result = self.hook("UserPromptSubmit", enabled=False, prompt="Continue editing")
        self.assertEqual(result["decision"], "block")
        self.assertNotIn("Update one small", result["reason"])
        self.assertNotIn("decision", self.hook("UserPromptSubmit", enabled=False, prompt="Engram history recovery"))

    def test_disabled_soft_threshold_does_not_inject_checkpoint(self):
        self.grow(1024**2)
        self.assertEqual(self.hook("UserPromptSubmit", enabled=False, prompt="Continue editing"), {})

    def test_explicit_memory_request_still_routes_when_disabled(self):
        result = self.hook("UserPromptSubmit", enabled=False, prompt="Remember my export preset")
        self.assertIn("Route this memory request", result["hookSpecificOutput"]["additionalContext"])

    def test_legacy_allowance_cannot_reset_on_each_hook(self):
        self.env.update(ENGRAM_CODEX_TOTAL_SOFT_GIB="1", ENGRAM_CODEX_TOTAL_HARD_GIB="1", ENGRAM_CODEX_LEGACY_GROWTH_MIB="1")
        self.grow(1024**3)
        first = runtime.HistoryGuard(self.payload, self.env)
        self.grow(1024**3 + 1024**2)
        second = runtime.HistoryGuard(self.payload, self.env)
        self.assertEqual(first.total_hard, second.total_hard)
        self.assertGreaterEqual(second.total_bytes, second.total_hard)
        self.grow(1)
        self.assertEqual(runtime.HistoryGuard(self.payload, self.env).mode, "absolute")

    def test_partial_legacy_state_repairs_fixed_baseline(self):
        self.env.update(ENGRAM_CODEX_TOTAL_SOFT_GIB="1", ENGRAM_CODEX_TOTAL_HARD_GIB="1", ENGRAM_CODEX_LEGACY_GROWTH_MIB="1")
        self.grow(1024**3)
        state = self.root / "codex" / "engram"
        state.mkdir()
        (state / "history-guard-mode").write_text("legacy")
        baseline = state / "history-guard-legacy-baseline-bytes"
        runtime.HistoryGuard(self.payload, self.env, persist=False)
        self.assertFalse(baseline.exists())
        first = runtime.HistoryGuard(self.payload, self.env)
        self.assertTrue(baseline.exists())
        self.grow(1024**3 + 1024**2)
        second = runtime.HistoryGuard(self.payload, self.env)
        self.assertEqual(first.total_hard, second.total_hard)
        self.assertGreaterEqual(second.total_bytes, second.total_hard)

    def test_small_start_does_not_demand_immediate_checkpoint(self):
        result = self.hook("SessionStart")
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("before finishing each turn", context)
        self.assertNotIn("Update one small", context)

    def test_init_preserves_existing_store_and_ignore(self):
        store, config = self.root / "Personal Brain", self.root / "Runtime"
        store.mkdir()
        (store / "INDEX.md").write_text("Existing", encoding="utf-8")
        config.mkdir()
        (config / ".bmignore").write_text("custom/\n", encoding="utf-8")
        runtime.init_store(store, config)
        runtime.init_store(store, config)
        self.assertEqual((store / "INDEX.md").read_text(), "Existing")
        self.assertEqual((config / ".bmignore").read_text(), "custom/\nbackups/\ninbox/\n")
        self.assertTrue((store / "global" / "video").is_dir())

    def test_invalid_settings_are_not_silently_ignored(self):
        self.config.write_text('{"checkpoints_enabled": "false"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            runtime.handle_hook(self.payload, self.env, HEALTHY)

    def test_unknown_hook_has_no_state_side_effect(self):
        self.assertEqual(runtime.handle_hook({"hook_event_name": "Other"}, self.env), {})
        self.assertFalse((self.root / "codex" / "engram").exists())

    def test_utf8_hook_input_is_independent_of_python_pipe_encoding(self):
        env = {key: value for key, value in os.environ.items() if not key.startswith("ENGRAM_")}
        env.update(self.env, ENGRAM_MCP_URL="http://127.0.0.1:9/mcp", PYTHONIOENCODING="ascii")
        payload = dict(self.payload, cwd=str(self.root / "Моє відео"))
        result = subprocess.run([sys.executable, str(runtime.PLUGIN_ROOT / "scripts/engram_portable.py"), "hook"],
                                input=json.dumps(payload, ensure_ascii=False).encode("utf-8"), env=env,
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("projects/моє-відео", context)


class RpcTests(unittest.TestCase):
    def serve(self, use_sse=True, version="0.23.2", project="engram"):
        self.deleted = False
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if payload["method"] == "notifications/initialized":
                    self.send_response(202)
                    self.end_headers()
                    return
                if payload["method"] == "initialize":
                    result = {"protocolVersion": "2025-06-18", "serverInfo": {"name": "test", "version": "1"}}
                elif payload["params"]["name"] == "basic_memory_diagnostics":
                    result = {"content": [{"type": "text", "text": "- basic-memory: " + version}]}
                else:
                    result = {"structuredContent": {"result": {"constrained_project": project}}}
                response = json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": result})
                if use_sse:
                    response = "event: message\ndata: " + response + "\n\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream" if use_sse else "application/json")
                self.send_header("Mcp-Session-Id", "test-session")
                self.end_headers()
                self.wfile.write(response.encode())

            def do_DELETE(self):
                outer.deleted = self.headers.get("Mcp-Session-Id") == "test-session"
                self.send_response(200)
                self.end_headers()

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return {"ENGRAM_MCP_URL": f"http://127.0.0.1:{server.server_port}/mcp"}

    def test_full_handshake_json_and_sse_and_session_cleanup(self):
        for use_sse in (False, True):
            with self.subTest(sse=use_sse):
                result = runtime.probe(self.serve(use_sse=use_sse))
                self.assertTrue(result["healthy"], result)
                self.assertTrue(self.deleted)

    def test_wrong_project_and_wrong_version_fail(self):
        for values in ({"project": "other"}, {"version": "0.23.20"}):
            with self.subTest(values=values):
                self.assertFalse(runtime.probe(self.serve(**values))["healthy"])


if __name__ == "__main__":
    unittest.main()
