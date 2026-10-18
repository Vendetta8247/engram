# Engram on native Windows

Another Codex can install and configure Engram for you. Install/enable the plugin
and ask it:

> Run /engram:setup for native Windows Codex. My work is in video production
> folders. Preserve existing memory and configuration, keep checkpoints on by
> default, and verify per-chat progress recovery after restart/compaction,
> memory read/write and service recovery on this machine.

The plugin contains native Python hooks and skills; installing it alone does
not start Basic Memory. There is no standalone Windows installer. Native Windows
setup has not been tested end to end locally, so the installing Codex must
verify it on the target machine. WSL, Git Bash, jq, Git repositories and Claude
Code are not required.

## Recipe for the installing Codex

Follow [the setup skill](../skills/setup/SKILL.md), including its global Codex
routing block. Inspect the existing service, store and Codex config first;
reuse a healthy service and preserve unrelated settings. For a new setup:

1. Ensure Codex, `uv` and `uvx` are available, installing missing prerequisites
   from their official documentation. [uv's Windows installation guide](https://docs.astral.sh/uv/getting-started/installation/)
   covers uv. Run `uv python install 3.12`; normal hooks use that cached Python
   with `--offline`.
2. Default the Markdown store to `%USERPROFILE%\Engram` and Basic Memory
   config/database to `%LOCALAPPDATA%\Engram\basic-memory`. Preserve existing
   paths when already configured. Use [engram_portable.py](../scripts/engram_portable.py)
   to create only missing layout and ignore rules:

   ```powershell
   uv run --no-project --python 3.12 python "$env:PLUGIN_ROOT/scripts/engram_portable.py" init-store --store $engramStore --config-dir $engramConfig
   ```

   Resolve the plugin root and set the two path variables before running. This
   command does not install/register Basic Memory or start a service.
3. With `BASIC_MEMORY_CONFIG_DIR` scoped to the chosen config directory, run
   `uvx --python 3.12 --prerelease=allow --from basic-memory==0.23.2 basic-memory
   project add engram STORE --local --default` only if `engram` is absent,
   then `project default engram --local` through the same pinned command.
   Verify an existing project's path instead of replacing it. Restore the
   caller's environment afterward; see the skill's PowerShell example.
4. Configure a current-user background service and logs appropriate to the
   machine. Its process must set `BASIC_MEMORY_CONFIG_DIR` itself and launch:

   ```powershell
   uvx --python 3.12 --prerelease=allow --from basic-memory==0.23.2 basic-memory mcp --transport streamable-http --host 127.0.0.1 --port 18765 --path /mcp --project engram
   ```

   A native scheduled task is one option. Record the actual supervisor,
   startup/recovery command and log paths in the installation's runbook; Engram
   does not require a particular task name or shipped wrapper. Ensure one
   listener, loopback binding and reliable background startup/recovery.
5. Back up and merge only Engram's table into Codex `config.toml` (`CODEX_HOME`
   when set, otherwise `%USERPROFILE%\.codex`), preserving unrelated TOML:

   ```toml
   [mcp_servers.engram]
   url = "http://127.0.0.1:18765/mcp"
   enabled = true
   required = true
   startup_timeout_sec = 15
   ```

   Merge the setup skill's marked global routing block, review/trust the plugin
   hooks, and restart Codex. Remove duplicate Engram hook registrations while
   preserving unrelated hooks. Codex-only adoption does not inspect or migrate
   Claude memory.

## Verify and record recovery

Run `health` and `status` using the resolved plugin root:

```powershell
uv run --no-project --offline --python 3.12 python "$env:PLUGIN_ROOT/scripts/engram_portable.py" health
uv run --no-project --offline --python 3.12 python "$env:PLUGIN_ROOT/scripts/engram_portable.py" status
```

Require MCP initialize, diagnostics confirming Basic Memory `0.23.2`, and the
exact `engram` project constraint; a listening port alone is insufficient.
Verify a temporary note can be written, read, updated, recalled in a fresh chat,
and removed through MCP. Exercise the recorded service recovery command and
repeat health/read verification. Then follow [verified chat continuity](../skills/using-the-graph/references/chat-continuity.md):

- Save using the actual hook session ID and confirm graph readback plus receipt.
- Restart/resume and exercise compaction; confirm the objective, completed work,
  references and next action restore correctly.
- Use two chats in the same video project and verify separate checkpoint notes.
- After a milestone save, run another local tool and confirm PreToolUse makes
  the old receipt dirty. The final save tool must verify its own new revision
  without a retry loop. Confirm the preference switch remains usable during
  continuity-state repair.
- Exercise a service outage: a failed save must be reported honestly, preserve
  the previous verified snapshot, and block compaction while enabled. Confirm
  offline recovery is explicitly labelled local/offline.
- Check on/off behavior: off skips automatic saves/gates without turning off
  ordinary memory. Restore the user's chosen setting after the check.

Test native hook execution in the non-Git production folder. Report actual
results; local Python tests do not establish Windows restart/compaction recovery.

The portable adapter is [engram_portable.py](../scripts/engram_portable.py),
continuity uses [engram_continuity.py](../scripts/engram_continuity.py),
settings are [engram_settings.py](../scripts/engram_settings.py), and the
platform-specific hook commands are in [hooks.json](../hooks/hooks.json).

## Checkpoints and video projects

Checkpoints default on and save each chat's progress from the first turn,
including small chats. Local journaling precedes network access, and only graph
write plus exact readback counts as verified. Resume can restore that checked
state; it does not archive the full conversation or guarantee unsaved work.
A lost drive needs an independent backup, chosen separately.

`/engram:checkpoints off`, `on`, or `status` controls automatic saves and gates.
Off reduces automatic progress recovery; normal recall/capture, manual saves,
and earlier recovery notes remain available. The direct native command uses
the same resolved plugin root:

```powershell
uv run --no-project --offline --python 3.12 python "$env:PLUGIN_ROOT/scripts/engram_settings.py" checkpoints off
```

Use a selected production folder or `/engram:init channel-trailer`. Store the
brief, audience/style, storyboard decisions, asset paths/rights, editing/audio/
color/captions, export settings and delivery requirements as Markdown notes.
Keep footage, audio, editor binaries and rendered exports in production folders;
Engram retains references, not media copies.
