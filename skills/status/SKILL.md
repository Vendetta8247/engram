---
name: status
description: Show Engram status — engine health, current project + tier, note counts per domain, inbox size, last backup.
argument-hint: ""
allowed-tools: Bash Read
---

# /engram:status — show Engram state

Gather and present concisely:

1. **Engine:** is `basic-memory` installed (`basic-memory --version`)? Is the MCP listed under `/mcp`?
2. **Projects:** `basic-memory project list` — highlight which one this repo is pinned to (read `.mcp.json` `BASIC_MEMORY_MCP_PROJECT` if present; else the default).
3. **Global brain:** path `~/Engram`; note count per domain (`workflow/kmp/ios/android/firebase`) via `find ... -name '*.md' | wc -l`.
4. **Inbox:** count of items in `~/Engram/inbox/`.
5. **Last backup:** newest dir under `~/Engram/backups/` (timestamp).

Present as a short status block. Flag anything not set up (e.g. "run /engram:setup").
