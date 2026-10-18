---
name: checkpoints
description: Enable, disable, or show Engram's automatic live checkpoint setting. Defaults to on; normal memory recall and durable capture continue when checkpoints are off.
allowed-tools: Bash Read
---

# /engram:checkpoints — on, off, or status

Interpret `$ARGUMENTS` as `on`, `off`, or `status` (no argument means status).
Resolve the installed plugin root from the client; do not assume an environment
variable exists or use a literal placeholder as a path. Run the shared settings
CLI, using native shell quoting. With uv available, these work without a system
Python installation:

PowerShell (Windows):

```powershell
uv run --no-project --python 3.12 python "$env:PLUGIN_ROOT/scripts/engram_settings.py" status
uv run --no-project --python 3.12 python "$env:PLUGIN_ROOT/scripts/engram_settings.py" checkpoints off
uv run --no-project --python 3.12 python "$env:PLUGIN_ROOT/scripts/engram_settings.py" checkpoints on
```

macOS/Linux:

```sh
uv run --no-project --python 3.12 python "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/engram_settings.py" status
uv run --no-project --python 3.12 python "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/engram_settings.py" checkpoints off
uv run --no-project --python 3.12 python "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/engram_settings.py" checkpoints on
```

Execute only the requested operation; the three lines are alternatives. A
resolved absolute plugin path can replace the environment-variable prefix.
`python <path>/scripts/engram_settings.py ...` also works with Python 3.10+.

Report the effective value and config path from the JSON result. Settings live
in `~/.engram/settings.json` by default; `ENGRAM_CONFIG_PATH` changes the file.
`ENGRAM_CHECKPOINTS_ENABLED` (`true/false`, `on/off`, `1/0`) overrides the saved
setting. If a toggle succeeds but the effective value differs because of that
override, explain that plainly; do not silently edit the user's environment.
Invalid configuration is an error, not an off/on value; report it and preserve
the file for repair.

When enabled, follow [verified chat continuity](../using-the-graph/references/chat-continuity.md):
save each chat's current state through `engram_continuity.py` after milestones,
before long actions and at the end of each user turn. Only exact graph readback
creates a verified receipt; Stop requires current-turn verification and
PreCompact revalidates remotely before allowing compaction. This restores
checked progress rather than the full chat transcript.

When disabled, stop automatic checkpoint saves and verification gates
immediately, including from previously loaded instructions. Explain briefly
that automatic per-chat progress recovery is reduced; respect the user's
choice. Continue selective recall, ordinary durable capture, explicit manual
checkpoint saves, access to earlier recovery notes, and service/storage health
checks. Do not silently re-enable checkpoints. This setting does not prune or
shrink Codex chat history or disable storage protection.
