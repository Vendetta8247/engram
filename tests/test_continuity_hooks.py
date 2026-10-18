"""Compaction stays live without treating hook execution as a verified save."""

import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import engram_portable as runtime


HEALTHY = {"healthy": True, "notify": False, "message": ""}
OFFLINE = {"healthy": False, "notify": True, "message": "Engram unavailable"}


class FakeContinuityError(ValueError):
    pass


class FakeContinuity:
    """A stateful persistence boundary, independent of the hook implementation."""

    def __init__(self, session_id):
        self.session_id = session_id
        self.generation = 0
        self.verified_generation = 0
        self.verified_at = None
        self.identifier = None
        self.source = "graph"
        self.graph_validated = True
        self.recovered_generation = None
        self.begin_error = None
        self.recover_error = None
        self.begin_calls = 0
        self.recover_calls = 0
        self.checkpoint = {
            "objective": "Deliver the channel trailer",
            "progress": "Sequence 12 is cut and approved",
            "decisions": ["Use the approved blue title treatment"],
            "references": ["D:/Creative/Channel Trailer/edit-v7.drp"],
            "verification": "Reviewed the 1080p proof export",
            "blockers": [],
            "next_action": "Mix the final voiceover",
        }

    def read_state(self):
        return self.status()

    def status(self):
        return {
            "generation": self.generation,
            "verified_generation": self.verified_generation,
            "needs_checkpoint": self.generation != self.verified_generation,
            "verified_at": self.verified_at,
            "identifier": self.identifier,
            "session_key": "chat-" + self.session_id,
        }

    def begin_turn(self):
        if self.begin_error:
            raise self.begin_error
        self.begin_calls += 1
        self.generation += 1
        return self.status()

    def verify(self):
        self.verified_generation = self.generation
        self.verified_at = time.time()
        self.identifier = "projects/channel-trailer/checkpoints/chat-" + self.session_id

    def recover(self, allow_missing=False):
        self.recover_calls += 1
        if self.recover_error:
            raise self.recover_error
        if not self.identifier:
            if allow_missing:
                return {"source": "none", "graph_validated": False}
            raise FakeContinuityError("No verified checkpoint exists")
        return {
            "checkpoint": copy.deepcopy(self.checkpoint),
            "generation": self.verified_generation if self.recovered_generation is None else self.recovered_generation,
            "source": self.source,
            "graph_validated": self.graph_validated,
            "identifier": self.identifier,
        }


class ContinuityHookTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="engram continuity hooks ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.workspace = self.root / "Channel Trailer"
        self.workspace.mkdir()
        self.sessions = self.root / "codex" / "sessions"
        self.sessions.mkdir(parents=True)
        self.transcript = self.sessions / "trailer.jsonl"
        self.transcript.write_text('{"type":"test-fixture"}\n', encoding="utf-8")
        self.original_transcript = self.transcript.read_bytes()
        self.env = {
            # CLI tests clear the process environment. Supply a temporary home
            # for both POSIX and Windows instead of inheriting the user's home.
            "HOME": str(self.root),
            "USERPROFILE": str(self.root),
            "CODEX_HOME": str(self.root / "codex"),
            "ENGRAM_CONFIG_PATH": str(self.root / "settings.json"),
            "ENGRAM_CHECKPOINTS_ENABLED": "true",
            "ENGRAM_HEALTH_STATE_DIR": str(self.root / "health"),
        }
        self.ledgers = {}
        self.constructor_calls = []

        def factory(session_id, environ=None):
            self.constructor_calls.append((session_id, environ))
            return self.ledgers.setdefault(session_id, FakeContinuity(session_id))

        self.addCleanup(patch.stopall)
        patch.object(runtime, "Continuity", side_effect=factory, create=True).start()
        patch.object(runtime, "ContinuityError", FakeContinuityError, create=True).start()

    def ledger(self, session_id="trailer-chat"):
        return self.ledgers.setdefault(session_id, FakeContinuity(session_id))

    def hook(self, event, health=HEALTHY, session_id="trailer-chat", enabled=True, **values):
        payload = {
            "hook_event_name": event,
            "session_id": session_id,
            "cwd": str(self.workspace),
            "transcript_path": str(self.transcript),
            **values,
        }
        environ = {**self.env, "ENGRAM_CHECKPOINTS_ENABLED": str(enabled).lower()}
        return runtime.handle_hook(payload, environ, health)

    def begin(self, session_id="trailer-chat"):
        return self.hook("UserPromptSubmit", session_id=session_id, prompt="Continue editing the trailer")

    def verified(self, session_id="trailer-chat"):
        self.begin(session_id)
        ledger = self.ledger(session_id)
        ledger.verify()
        return ledger

    def assert_compaction_allows_deferred_recovery(self, result):
        self.assertIs(result.get("continue"), True, result)
        self.assertNotEqual(result.get("decision"), "block", result)
        self.assertNotIn("stopReason", result)
        warning = result.get("systemMessage", "").lower()
        self.assertIn("no fresh checkpoint save was confirmed", warning, result)
        self.assertIn("native history", warning, result)
        self.assertIn("after compaction", warning, result)
        self.assertIn("reconcile", warning, result)

    def test_small_chat_prompt_starts_capture_generation_and_stop_requests_save(self):
        prompt = self.begin()
        self.assertEqual(self.ledger().generation, 1)
        self.assertIn("checkpoint", prompt["hookSpecificOutput"]["additionalContext"].lower())
        stopped = self.hook("Stop")
        self.assertEqual(stopped.get("decision"), "block", stopped)
        self.assertIn("checkpoint", stopped["reason"].lower())
        self.assertEqual(self.ledger().verified_generation, 0)
        self.assertLess(self.transcript.stat().st_size, 1024)

    def test_repeated_stop_never_acknowledges_an_unsaved_checkpoint(self):
        self.begin()
        self.assertEqual(self.hook("Stop").get("decision"), "block")
        self.assertEqual(self.hook("Stop").get("decision"), "block")
        retry = self.hook("Stop", stop_hook_active=True)
        self.assertIs(retry.get("continue"), False, retry)
        self.assertTrue(retry.get("systemMessage"), retry)
        self.assertEqual(self.ledger().verified_generation, 0)
        self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact"))

    def test_verified_save_allows_stop_including_the_continuation(self):
        ledger = self.verified()
        for active in (False, True):
            with self.subTest(stop_hook_active=active):
                result = self.hook("Stop", stop_hook_active=active)
                self.assertNotEqual(result.get("decision"), "block", result)
                self.assertIsNot(result.get("continue"), False, result)
        self.assertEqual(ledger.verified_generation, 1)

    def test_next_user_turn_invalidates_the_previous_verified_generation(self):
        ledger = self.verified()
        self.begin()
        self.assertEqual((ledger.generation, ledger.verified_generation), (2, 1))
        self.assertEqual(self.hook("Stop").get("decision"), "block")
        self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact"))

    def test_tool_work_after_a_midturn_save_invalidates_that_checkpoint(self):
        ledger = self.verified()
        result = self.hook("PreToolUse", tool_name="apply_patch", tool_input={"command": "fixture"})
        self.assertEqual(result, {})
        self.assertEqual((ledger.generation, ledger.verified_generation), (2, 1))
        self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact"))
        self.assertEqual(self.hook("Stop").get("decision"), "block")

    def test_repeated_precompact_before_model_sampling_never_deadlocks_or_verifies_dirty_work(self):
        ledger = self.verified()
        # Reproduce a resumed chat already over the context limit. The model
        # cannot sample a checkpoint-save call until native compaction succeeds.
        ledger.generation = 7
        ledger.verified_generation = 6
        before = copy.deepcopy(ledger.status())
        begin_calls = ledger.begin_calls
        for attempt in range(3):
            with self.subTest(attempt=attempt):
                self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact"))
                self.assertEqual(ledger.status(), before)
                self.assertEqual(ledger.begin_calls, begin_calls)
                self.assertEqual(self.transcript.read_bytes(), self.original_transcript)
        self.assertEqual(self.hook("Stop").get("decision"), "block")

    def test_deferred_compaction_does_not_create_or_refresh_verification_receipts(self):
        for condition in ("missing", "dirty", "expired", "offline", "local", "older", "unvalidated", "error"):
            with self.subTest(condition=condition):
                ledger = self.ledger(condition)
                health = HEALTHY
                if condition != "missing":
                    ledger.begin_turn()
                    ledger.verify()
                if condition == "dirty":
                    ledger.begin_turn()
                elif condition == "expired":
                    ledger.verified_at = time.time() - 301
                elif condition == "offline":
                    health = OFFLINE
                elif condition == "local":
                    ledger.source = "local_snapshot"
                    ledger.graph_validated = False
                elif condition == "older":
                    ledger.recovered_generation = 0
                elif condition == "unvalidated":
                    ledger.graph_validated = False
                elif condition == "error":
                    ledger.recover_error = OSError("Readback unavailable")
                before = copy.deepcopy(ledger.status())
                self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact", session_id=condition, health=health))
                self.assertEqual(ledger.status(), before)
                self.assertEqual(self.transcript.read_bytes(), self.original_transcript)

    def test_checkpoint_save_can_verify_its_own_tool_revision(self):
        ledger = self.verified()
        self.hook("PreToolUse", tool_name="Bash", tool_input={"command": "checkpoint save"})
        ledger.verify()
        self.assertNotEqual(self.hook("Stop").get("decision"), "block")
        self.assertIsNot(self.hook("PreCompact").get("continue"), False)

    def test_other_chat_save_does_not_satisfy_this_chat(self):
        self.verified("chat-a")
        self.begin("chat-b")
        self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact", session_id="chat-b"))
        self.assertEqual(self.hook("Stop", session_id="chat-b").get("decision"), "block")
        self.assertEqual(self.ledger("chat-a").verified_generation, 1)
        self.assertEqual(self.ledger("chat-b").verified_generation, 0)
        self.assertEqual({item[0] for item in self.constructor_calls}, {"chat-a", "chat-b"})

    def test_missing_verified_receipt_defers_recovery_without_blocking_compaction(self):
        self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact"))
        self.assertIsNone(self.ledger().identifier)

    def test_compaction_revalidates_current_checkpoint_without_warning(self):
        ledger = self.verified()
        result = self.hook("PreCompact")
        self.assertIsNot(result.get("continue"), False, result)
        self.assertGreater(ledger.recover_calls, 0)
        self.assertNotIn("systemMessage", result)
        self.assertEqual((ledger.generation, ledger.verified_generation), (1, 1))

    def test_expired_verification_defers_recovery_without_blocking_compaction(self):
        ledger = self.verified()
        ledger.verified_at = time.time() - 301
        self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact"))

    def test_older_remote_generation_defers_recovery_without_blocking_compaction(self):
        ledger = self.verified()
        ledger.recovered_generation = 0
        self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact"))

    def test_local_snapshot_defers_recovery_even_when_health_is_good(self):
        ledger = self.verified()
        ledger.source = "local_snapshot"
        ledger.graph_validated = False
        self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact"))

    def test_local_snapshot_cannot_confirm_fresh_save_through_inconsistent_validation_flag(self):
        ledger = self.verified()
        ledger.source = "local_snapshot"
        ledger.graph_validated = True
        self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact"))

    def test_unvalidated_graph_response_defers_recovery_without_blocking_compaction(self):
        ledger = self.verified()
        ledger.graph_validated = False
        self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact"))

    def test_read_validation_failures_defer_recovery_without_blocking_compaction(self):
        for error in (FakeContinuityError("Readback generation mismatch"), OSError("Readback failed")):
            with self.subTest(error=type(error).__name__):
                ledger = self.verified()
                ledger.recover_error = error
                self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact"))

    def test_offline_compaction_never_uses_previously_verified_receipt_as_ack(self):
        self.verified()
        self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact", health=OFFLINE))

    def test_startup_recovers_progress_and_a_recovery_pointer(self):
        ledger = self.verified()
        result = self.hook("SessionStart", source="compact")
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Sequence 12", context)
        self.assertIn("voiceover", context)
        self.assertIn("recover", context.lower())
        self.assertIn("--session-id", context)
        self.assertIn("trailer-chat", context)
        self.assertGreater(ledger.recover_calls, 0)

    def test_startup_recovers_graph_without_a_local_receipt(self):
        ledger = self.ledger()
        ledger.identifier = "Chat checkpoint remote-only"
        ledger.recovered_generation = 17
        result = self.hook("SessionStart", source="resume")
        self.assertIn("Sequence 12", result["hookSpecificOutput"]["additionalContext"])
        self.assertGreater(ledger.recover_calls, 0)
        self.assertEqual(ledger.verified_generation, 0)
        self.assertEqual(self.hook("Stop").get("decision"), "block")

    def test_offline_startup_labels_local_snapshot_without_claiming_graph_validation(self):
        ledger = self.verified()
        ledger.source = "local_snapshot"
        ledger.graph_validated = False
        result = self.hook("SessionStart", source="resume", health=OFFLINE)
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Sequence 12", context)
        self.assertIn("local", context.lower())
        self.assertIn("snapshot", context.lower())
        self.assertIn("offline", context.lower())
        self.assert_compaction_allows_deferred_recovery(self.hook("PreCompact", health=OFFLINE))

    def test_startup_does_not_invent_a_completed_save_or_start_a_new_generation(self):
        result = self.hook("SessionStart", source="startup")
        self.assertIn("1-3", result["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.ledger().begin_calls, 0)
        self.assertIsNone(self.ledger().identifier)
        self.assertIsNot(result.get("continue"), False, result)

    def test_failed_startup_recovery_keeps_memory_policy_and_reports_missing_progress(self):
        ledger = self.verified()
        ledger.recover_error = FakeContinuityError("Saved checkpoint readback failed")
        result = self.hook("SessionStart", source="resume")
        self.assertIn("1-3", result["hookSpecificOutput"]["additionalContext"])
        self.assertIn("readback failed", result.get("systemMessage", "").lower())
        self.assertEqual(ledger.verified_generation, 1)
        self.assertEqual(ledger.begin_calls, 1)

    def test_large_recovered_checkpoint_does_not_flood_startup_context(self):
        ledger = self.verified()
        ledger.checkpoint["progress"] = "Approved sequence. " * 5000
        result = self.hook("SessionStart", source="resume")
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertLess(len(context), 16000)
        self.assertIn("recover", context.lower())
        self.assertIn("trailer-chat", context)

    def test_disabled_mode_never_constructs_continuity_or_changes_native_history(self):
        for event in ("SessionStart", "UserPromptSubmit", "PreToolUse", "Stop", "PreCompact"):
            with self.subTest(event=event):
                result = self.hook(event, enabled=False, health=OFFLINE, prompt="Continue editing")
                self.assertNotEqual(result.get("decision"), "block", result)
                self.assertIsNot(result.get("continue"), False, result)
        self.assertEqual(self.constructor_calls, [])
        self.assertEqual(self.transcript.read_bytes(), self.original_transcript)

    def test_failed_turn_state_write_produces_explicit_failure_at_cli_boundary(self):
        ledger = self.ledger()
        ledger.begin_error = OSError("Checkpoint state write failed")
        payload = {"hook_event_name": "UserPromptSubmit", "session_id": "trailer-chat",
                   "cwd": str(self.workspace), "transcript_path": str(self.transcript), "prompt": "Continue editing"}
        stdin = io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode("utf-8")), encoding="utf-8")
        stdout = io.StringIO()
        with patch.object(sys, "argv", ["engram_portable.py", "hook"]), patch.object(sys, "stdin", stdin), \
                patch.object(sys, "stdout", stdout), patch.dict(os.environ, self.env, clear=True), \
                patch.object(runtime, "health_for_hook", return_value=HEALTHY):
            runtime.main()
        result = json.loads(stdout.getvalue())
        self.assertIs(result.get("continue"), False, result)
        self.assertIn("Checkpoint state write failed", result.get("systemMessage", ""), result)
        self.assertEqual(ledger.verified_generation, 0)
        self.assertIsNone(ledger.identifier)
        self.assertEqual(self.transcript.read_bytes(), self.original_transcript)

    def test_precompact_cli_exceptions_defer_recovery_without_blocking_or_faking_a_save(self):
        ledger = self.verified()
        before = copy.deepcopy(ledger.status())
        payload = {"hook_event_name": "PreCompact", "session_id": "trailer-chat",
                   "cwd": str(self.workspace), "transcript_path": str(self.transcript)}
        for error in (OSError("Checkpoint state unreadable"), ValueError("Invalid checkpoint settings")):
            with self.subTest(error=type(error).__name__):
                stdin = io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode("utf-8")), encoding="utf-8")
                stdout = io.StringIO()
                with patch.object(sys, "argv", ["engram_portable.py", "hook"]), patch.object(sys, "stdin", stdin), \
                        patch.object(sys, "stdout", stdout), patch.dict(os.environ, self.env, clear=True), \
                        patch.object(runtime, "handle_hook", side_effect=error):
                    self.assertEqual(runtime.main(), 0)
                result = json.loads(stdout.getvalue())
                self.assert_compaction_allows_deferred_recovery(result)
                self.assertIn(str(error), result["systemMessage"])
                self.assertEqual(ledger.status(), before)
                self.assertEqual(self.transcript.read_bytes(), self.original_transcript)

    def test_failed_pretool_state_write_uses_the_supported_tool_denial_shape(self):
        ledger = self.verified()
        ledger.begin_error = OSError("Checkpoint state write failed")
        payload = {"hook_event_name": "PreToolUse", "session_id": "trailer-chat", "tool_name": "apply_patch"}
        stdin = io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode()), encoding="utf-8")
        stdout = io.StringIO()
        with patch.object(sys, "argv", ["engram_portable.py", "hook"]), patch.object(sys, "stdin", stdin), \
                patch.object(sys, "stdout", stdout), patch.dict(os.environ, self.env, clear=True):
            self.assertEqual(runtime.main(), 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertNotIn("continue", result)
        self.assertEqual(ledger.verified_generation, 1)

    def test_preference_repair_is_available_without_touching_broken_continuity(self):
        ledger = self.verified()
        ledger.begin_error = OSError("Checkpoint state is unavailable")
        command = 'uv run --no-project --offline --python 3.12 python "' + str(runtime.PLUGIN_ROOT / "scripts/engram_settings.py") + '" checkpoints off'
        before = len(self.constructor_calls)
        self.assertEqual(self.hook("PreToolUse", tool_name="Bash", tool_input={"command": command}), {})
        self.assertEqual(len(self.constructor_calls), before)
        self.assertFalse(runtime.settings_maintenance({"tool_input": {"command": command + '; edit-video'}}))


if __name__ == "__main__":
    unittest.main()
