"""Settings precedence and checkpoint gates, without touching live user state."""

import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("engram_settings", ROOT / "scripts/engram_settings.py")
settings = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(settings)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.config = self.directory / "settings.json"

    def test_default_and_platform_home(self):
        self.assertEqual(settings.load_settings(self.config, {}), {"checkpoints_enabled": True})
        with patch.object(settings.Path, "home", return_value=self.directory):
            self.assertEqual(settings.settings_path({}), self.directory / ".engram/settings.json")
        self.assertFalse(self.config.exists())

    def test_saved_false_and_environment_precedence(self):
        self.config.write_text('{"checkpoints_enabled": false, "other": "preserved"}')
        self.assertFalse(settings.load_settings(self.config, {})["checkpoints_enabled"])
        for token in ("true", "on", "1", " TRUE "):
            self.assertTrue(settings.load_settings(self.config, {"ENGRAM_CHECKPOINTS_ENABLED": token})["checkpoints_enabled"])
        for token in ("false", "off", "0", " OFF ", "\n false\t\n"):
            self.assertFalse(settings.load_settings(self.config, {"ENGRAM_CHECKPOINTS_ENABLED": token})["checkpoints_enabled"])

    def test_invalid_config_is_not_masked_by_override(self):
        for value in ("", "{", "[]", "null", '{"checkpoints_enabled": 0}', '{"checkpoints_enabled": "false"}', '{} {}'):
            self.config.write_text(value)
            with self.subTest(value=value), self.assertRaises(settings.SettingsError):
                settings.load_settings(self.config, {"ENGRAM_CHECKPOINTS_ENABLED": "false"})
        self.config.unlink()
        for token in ("", "yes", "no", "2"):
            with self.subTest(token=token), self.assertRaises(settings.SettingsError):
                settings.load_settings(self.config, {"ENGRAM_CHECKPOINTS_ENABLED": token})
        with self.assertRaises(settings.SettingsError):
            settings.settings_path({"ENGRAM_CONFIG_PATH": " "})

    def test_atomic_save_preserves_unknown_keys_and_env_is_not_saved(self):
        self.config.write_text('{"other": {"value": 42}}')
        result = settings.set_checkpoints(False, self.config, {"ENGRAM_CHECKPOINTS_ENABLED": "true"})
        self.assertTrue(result["checkpoints_enabled"])
        self.assertEqual(json.loads(self.config.read_text()), {"other": {"value": 42}, "checkpoints_enabled": False})
        before = self.config.read_bytes()
        with patch.object(settings.os, "replace", side_effect=OSError("test failure")):
            with self.assertRaises(settings.SettingsError):
                settings.set_checkpoints(True, self.config, {})
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(list(self.directory.iterdir()), [self.config])

    def test_cli_and_bom(self):
        self.config.write_text('\ufeff{"checkpoints_enabled": false}', encoding="utf-8")
        self.assertFalse(settings.load_settings(self.config, {})["checkpoints_enabled"])
        env = {**os.environ, "ENGRAM_CONFIG_PATH": str(self.config)}
        env.pop("ENGRAM_CHECKPOINTS_ENABLED", None)
        result = subprocess.run([sys.executable, str(ROOT / "scripts/engram_settings.py"), "checkpoints", "on"], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["checkpoints_enabled"])
        self.assertTrue(settings.load_settings(self.config, {})["checkpoints_enabled"])


@unittest.skipUnless(os.name != "nt" and shutil.which("bash") and shutil.which("jq"), "Unix shell adapters need bash and jq")
class ShellAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.config = self.directory / "settings.json"
        self.root = self.directory / "plugin with spaces"
        scripts = self.root / "scripts"
        scripts.mkdir(parents=True)
        for name in ("engram-codex-hook.sh", "engram-session-start.sh", "engram-precompact.sh"):
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        self.health = scripts / "engram-mcp-health.sh"
        self.set_health(True)
        (scripts / "engram-recovery-command.sh").write_text('#!/bin/sh\necho "restart test service"\n')
        (self.directory / "Engram").mkdir()
        (self.directory / "Engram/INDEX.md").write_text("# Test\n")
        self.transcript = self.directory / "rollout.jsonl"
        self.transcript.write_text("{}\n", encoding="utf-8")
        self.portable = scripts / "engram_portable.py"
        self.portable.write_text(
            'import json, os, sys\n'
            'if os.environ.get("ENGRAM_TEST_PORTABLE_FAIL"): raise SystemExit(23)\n'
            'payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))\n'
            'print(json.dumps({"dispatched": True, "received": payload, "hookSpecificOutput": '
            '{"hookEventName": payload["hook_event_name"], "additionalContext": "Portable fixture context"}}))\n',
            encoding="utf-8",
        )
        temporary_bin = self.directory / "test bin"
        temporary_bin.mkdir()
        self.uv_arguments = self.directory / "uv arguments.txt"
        uv_shim = temporary_bin / "uv"
        uv_shim.write_text(
            '#!/bin/sh\n'
            'printf "%s\\n" "$@" > "$ENGRAM_TEST_UV_ARGUMENTS"\n'
            'while [ "$#" -gt 0 ]; do\n'
            '  if [ "$1" = python ]; then\n'
            '    shift\n'
            '    exec ' + shlex.quote(sys.executable) + ' "$@"\n'
            '  fi\n'
            '  shift\n'
            'done\n'
            'exit 64\n',
            encoding="utf-8",
        )
        uv_shim.chmod(0o700)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("ENGRAM_")}
        self.env.pop("PLUGIN_ROOT", None)
        self.env.pop("CLAUDE_PLUGIN_ROOT", None)
        self.env.update({
            "HOME": str(self.directory), "CODEX_HOME": str(self.directory / ".codex"),
            "ENGRAM_CONFIG_PATH": str(self.config),
            "ENGRAM_CODEX_SESSION_SOFT_MIB": "1",
            "ENGRAM_CODEX_SESSION_HARD_MIB": "2",
            "ENGRAM_TEST_UV_ARGUMENTS": str(self.uv_arguments),
            "PATH": str(temporary_bin) + os.pathsep + self.env.get("PATH", ""),
        })

    def set_health(self, healthy):
        self.health.write_text("#!/bin/sh\nprintf '%s\\n' '" + json.dumps({"healthy": healthy, "notify": True, "message": "test health warning" if not healthy else ""}) + "'\n")
        self.health.chmod(0o700)

    def run_script(self, name="engram-codex-hook.sh", event="SessionStart", prompt="", args=(), **values):
        payload = {"hook_event_name": event, "session_id": "test", "transcript_path": str(self.transcript), "prompt": prompt}
        payload.update(values)
        return subprocess.run(["bash", str(self.root / "scripts" / name), *args], input=json.dumps(payload, ensure_ascii=False),
                              env=self.env, cwd=self.directory, capture_output=True, text=True, encoding="utf-8")

    def test_shell_and_python_parse_same_values(self):
        for saved, override in ((True, None), (False, None), (False, "on"), (True, "off"), (True, "\n false\t\n")):
            self.config.write_text(json.dumps({"checkpoints_enabled": saved}))
            if override is None:
                self.env.pop("ENGRAM_CHECKPOINTS_ENABLED", None)
            else:
                self.env["ENGRAM_CHECKPOINTS_ENABLED"] = override
            result = self.run_script(args=("--checkpoints-enabled",))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), settings.load_settings(self.config, self.env)["checkpoints_enabled"])
        self.config.write_text('{"checkpoints_enabled": "false"}')
        result = self.run_script(args=("--checkpoints-enabled",))
        self.assertEqual(result.returncode, 2)
        self.assertIn("Engram settings:", result.stderr)
        self.config.write_text('\ufeff{"checkpoints_enabled": false}', encoding="utf-8")
        self.env.pop("ENGRAM_CHECKPOINTS_ENABLED", None)
        result = self.run_script(args=("--checkpoints-enabled",))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), False)

    def test_claude_hooks_respect_disabled_mode(self):
        self.config.write_text('{"checkpoints_enabled": false}')
        start = self.run_script("engram-session-start.sh")
        self.assertEqual(start.returncode, 0, start.stderr)
        self.assertIn("Automatic live checkpoints are disabled", start.stdout)
        compact = self.run_script("engram-precompact.sh", event="PreCompact")
        self.assertEqual(compact.returncode, 0, compact.stderr)
        self.assertNotIn("update the small live procedure checkpoint", compact.stdout)
        self.assertIn("Write precise canonical notes", compact.stdout)

    def test_non_git_video_project_and_explicit_routing(self):
        workspace = self.directory / "Launch Video 2026"
        footage = workspace / "Footage"
        footage.mkdir(parents=True)
        fallback = self.run_script("engram-session-start.sh", cwd=str(workspace))
        self.assertEqual(fallback.returncode, 0, fallback.stderr)
        self.assertIn("projects/launch-video-2026/", fallback.stdout)
        self.assertIn("source/asset references", fallback.stdout)
        selected = self.run_script("engram-session-start.sh", cwd=str(footage), workspace_root=str(workspace))
        self.assertIn("projects/launch-video-2026/", selected.stdout)
        self.env["ENGRAM_PROJECT_NAME"] = "../Client Film / 2026"
        explicit = self.run_script("engram-session-start.sh", cwd=str(footage), workspace_root=str(workspace))
        self.assertIn("projects/client-film-2026/", explicit.stdout)
        self.assertNotIn("projects/../", explicit.stdout)

    def test_shell_routing_skips_projectless_locations(self):
        for directory in (self.directory, self.directory / "Engram", self.root, self.root / "scripts", Path("/")):
            with self.subTest(directory=directory):
                result = self.run_script("engram-session-start.sh", cwd=str(directory))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("has NO Engram knowledge base", result.stdout)
                self.assertNotIn("Working in project", result.stdout)

    def test_unicode_project_uses_same_tier_in_claude_and_codex(self):
        workspace = self.directory / "Моє ВІДЕО"
        workspace.mkdir()
        portable = subprocess.run(
            [sys.executable, str(ROOT / "scripts/engram_portable.py"), "project", "--cwd", str(workspace)],
            env=self.env, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(portable.returncode, 0, portable.stderr)
        directory = json.loads(portable.stdout)["directory"]
        self.assertEqual(directory, "projects/моє-відео")
        shell = self.run_script("engram-session-start.sh", cwd=str(workspace))
        self.assertEqual(shell.returncode, 0, shell.stderr)
        self.assertIn(directory + "/", shell.stdout)

    def test_codex_shell_adapter_dispatches_portable_runtime_with_utf8_stdin(self):
        workspace = self.directory / "Моє відео"
        workspace.mkdir()
        self.env["PLUGIN_ROOT"] = str(self.root)
        prompt = "Збережи рішення про монтаж"
        result = self.run_script("engram-session-start.sh", cwd=str(workspace), prompt=prompt)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertTrue(output["dispatched"])
        self.assertEqual(output["received"]["cwd"], str(workspace))
        self.assertEqual(output["received"]["prompt"], prompt)
        self.assertEqual(output["hookSpecificOutput"]["additionalContext"], "Portable fixture context")
        self.assertEqual(self.uv_arguments.read_text().splitlines(), [
            "run", "--no-project", "--offline", "--python", "3.12", "python", str(self.portable), "hook",
        ])
        self.assertFalse((self.directory / ".codex/engram").exists())

    def test_missing_or_failed_portable_runtime_explicitly_denies_protected_hooks(self):
        self.env["PLUGIN_ROOT"] = str(self.root)
        for missing in (False, True):
            if missing:
                self.portable.unlink()
            else:
                self.env["ENGRAM_TEST_PORTABLE_FAIL"] = "1"
            for event in ("PreCompact", "Stop", "UserPromptSubmit", "SessionStart"):
                with self.subTest(missing=missing, event=event):
                    result = self.run_script(event=event)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    output = json.loads(result.stdout)
                    self.assertIs(output.get("continue"), False, output)
                    self.assertTrue(output.get("systemMessage"), output)

    def test_disabled_compaction_warns_and_continues_if_runtime_cannot_run(self):
        self.config.write_text('{"checkpoints_enabled": false}')
        self.env["ENGRAM_TEST_PORTABLE_FAIL"] = "1"
        result = self.run_script(event="PreCompact")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertIs(output.get("continue"), True, output)
        self.assertTrue(output.get("systemMessage"), output)

    def test_project_helper_skips_health_settings_and_uses_custom_store(self):
        workspace = self.directory / "Client Film"
        workspace.mkdir()
        store = self.directory / "Personal Brain"
        store.mkdir()
        (store / "INDEX.md").write_text("# Brain\n")
        self.env.update(PLUGIN_ROOT=str(self.root), ENGRAM_STORE_PATH=str(store))
        self.config.write_text("invalid settings")
        self.health.write_text("#!/bin/sh\nexit 23\n")
        result = self.run_script("engram-session-start.sh", args=("--project-context",), cwd=str(workspace))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(store.resolve() / "projects/client-film"), result.stdout)
        self.assertNotIn("Engram memory is active", result.stdout)
        excluded = self.run_script("engram-session-start.sh", args=("--project-context",), cwd=str(store))
        self.assertEqual(excluded.returncode, 0, excluded.stderr)
        self.assertEqual(excluded.stdout, "")


if __name__ == "__main__":
    unittest.main()
