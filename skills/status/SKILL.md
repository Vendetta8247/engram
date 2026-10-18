---
name: status
description: Diagnose Engram's shared MCP service, Basic Memory version/project constraint, client wiring, history guard, project knowledge, inbox, and rollback state.
allowed-tools: Bash Read
---

# /engram:status — show Engram state

On native Windows run this PowerShell command using the resolved plugin path:

```powershell
uv run --no-project --python 3.12 python "$env:PLUGIN_ROOT/scripts/engram_portable.py" status
```

Use the helper's `health` command for the full probe when necessary. This path
requires no Bash, jq, Git or Claude. Report the effective checkpoint setting
with `scripts/engram_settings.py status` through the same Python invocation.
On macOS/Linux start with `bash
"${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/engram-status.sh"` as one command.
Then gather only applicable details and present concisely:

1. **Engine:** the full MCP probe must report Basic Memory 0.23.2 and constrained project `engram` at `http://127.0.0.1:18765/mcp`.
2. **Supervisor and clients:** show the platform user-service state/PID/restart count, `codex mcp get engram`, and `claude mcp list` only when Claude is installed. On Windows inspect the actual background supervisor and log paths recorded during setup; a scheduled task may be used, but no fixed task name is shipped. Use the installation's recorded recovery command. Count Basic Memory MCP processes and distinguish the one HTTP service from legacy stdio clients waiting for application restart.
3. **Verified chat continuity:** when a current session ID is available, run `scripts/engram_continuity.py status --session-id ID` using `uv run --no-project --offline --python 3.12 python` and the resolved plugin path. Report whether current-turn progress is verified/fresh, dirty/stale, or unavailable, plus the recovery note pointer. Use `recover --session-id ID` when checking the actual restored state and label offline local recovery honestly. See [chat continuity](../using-the-graph/references/chat-continuity.md); a service health result alone does not prove a checkpoint was saved.
4. **Checkpoint setting and history guard:** report effective `checkpoints_enabled` and its config/override source. On macOS/Linux run `scripts/engram-codex-hook.sh --status`; on Windows use portable `status`. Report measured storage and available boundaries. Checkpoints default on; off suppresses automatic checkpoint demands without disabling storage protection. Chat bytes measure saved history, not context-window tokens.
5. **Global brain:** configured store path and note counts for the domains that actually exist (for example `workflow`, `video`, `tooling`, `kmp`); use portable status, Python or native shell operations.
6. **Research debt:** count temporary notes under the current project's `research/`; flag `validated` notes not yet promoted and active/abandoned notes past their review date.
7. **Inbox:** count of items in `~/Engram/inbox/`.
8. **Rollback:** newest memory snapshot under the configured store's `backups/` and any client/runtime config backup. macOS runtime backups live under `~/Library/Application Support/Engram/backups/`; Windows runtime lives under `$env:LOCALAPPDATA/Engram`. Do not report a missing pre-migration snapshot as a failure when no migration/upgrade has occurred.

Present a short status block. An unavailable probe, wrong version/project, more than one post-restart MCP service, missing required upgrade/migration rollback snapshot, or an exceeded history boundary is a warning—not a healthy state.
