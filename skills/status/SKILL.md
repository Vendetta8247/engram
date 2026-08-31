---
name: status
description: Diagnose Engram's shared MCP service, Basic Memory version/project constraint, client wiring, history guard, project knowledge, inbox, and rollback state.
allowed-tools: Bash Read
---

# /engram:status — show Engram state

Start with `bash "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/engram-status.sh"`. Then gather and present concisely:

1. **Engine:** the full MCP probe must report Basic Memory 0.23.2 and constrained project `engram` at `http://127.0.0.1:18765/mcp`.
2. **Supervisor and clients:** show the platform user-service state/PID/restart count, `codex mcp get engram`, and `claude mcp list`. Count Basic Memory MCP processes and distinguish the one HTTP service from legacy stdio clients waiting for application restart.
3. **History guard:** run `scripts/engram-codex-hook.sh --status`; report absolute vs legacy-baseline mode, total storage, warning boundary, per-task checkpoint boundary, and 2 GiB emergency boundary.
4. **Global brain:** path `~/Engram`; note count per domain (`workflow/kmp/ios/android/firebase`) via `find ... -name '*.md' | wc -l`.
5. **Research debt:** count temporary notes under the current project's `research/`; flag `validated` notes not yet promoted and active/abandoned notes past their review date.
6. **Inbox:** count of items in `~/Engram/inbox/`.
7. **Rollback:** newest memory snapshot under `~/Engram/backups/` and client/runtime config backup under `~/Library/Application Support/Engram/backups/`.

Present a short status block. An unavailable probe, wrong version/project, more than one post-restart MCP service, missing rollback snapshot, or an exceeded history boundary is a warning—not a healthy state.
