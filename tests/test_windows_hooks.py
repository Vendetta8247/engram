"""Exercise the shipped Windows hook without touching installed services or user config."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = os.environ.get("ENGRAM_TEST_PWSH") or shutil.which("powershell.exe") or shutil.which("pwsh")


@unittest.skipUnless(POWERSHELL and shutil.which("uv"), "PowerShell and uv are needed to exercise the distributed Windows hook")
class WindowsHookTests(unittest.TestCase):
    def test_distributed_windows_hook_with_unicode_paths(self):
        with tempfile.TemporaryDirectory(prefix="Engram video ") as directory:
            root = Path(directory)
            plugin = root / "Мій plugin"
            (plugin / "scripts").mkdir(parents=True)
            for filename in ("engram_portable.py", "engram_settings.py", "engram_continuity.py"):
                shutil.copy2(ROOT / "scripts" / filename, plugin / "scripts" / filename)
            definition = json.loads((ROOT / "hooks/hooks.json").read_text())
            command = definition["hooks"]["SessionStart"][0]["hooks"][0]["commandWindows"]
            match = re.search(r'-Command "(.*)"$', command)
            self.assertIsNotNone(match)
            env = {key: value for key, value in os.environ.items() if not key.startswith("ENGRAM_")}
            env.update(PLUGIN_ROOT=str(plugin), CODEX_HOME=str(root / "Codex home"),
                       ENGRAM_CONFIG_PATH=str(root / "settings.json"), ENGRAM_MCP_URL="http://127.0.0.1:9/mcp")
            payload = {"hook_event_name": "SessionStart", "session_id": "video-test", "cwd": str(root / "Моє відео")}
            result = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-Command", match.group(1)],
                                    input=json.dumps(payload, ensure_ascii=False).encode(), env=env,
                                    capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            context = json.loads(result.stdout.decode("utf-8-sig"))["hookSpecificOutput"]["additionalContext"]
            self.assertIn("projects/моє-відео", context)
            self.assertIn("ENGRAM IS OFFLINE", context)


if __name__ == "__main__":
    unittest.main()
