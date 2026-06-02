---
name: setup
description: OPTIONAL install-only bootstrap — install Basic Memory, wire the MCP, create the global brain + inbox, WITHOUT taking over native memory. Use this to try Engram alongside native memory first. Most users can skip straight to /engram:adopt, which self-bootstraps this. Idempotent.
argument-hint: ""
allowed-tools: Bash Read AskUserQuestion
---

# /engram:setup — bootstrap Engram

Set up Engram on this machine. **Idempotent** — re-running must not clobber existing data. Work through these steps, reporting concisely as you go. If a step is already done, say so and skip it.

## 1. Prerequisites
- Check `uv` is installed (`command -v uv`). If missing, install it with the official installer: `curl -LsSf https://astral.sh/uv/install.sh | sh` (tell the user you're doing this; on Windows direct them to https://docs.astral.sh/uv/). Re-check.
- Check `git` is available.

## 2. Install Basic Memory (the engine)
- `uv tool install basic-memory` (or `uv tool upgrade basic-memory` if already installed).
- Verify: `basic-memory --version`. The MCP server is declared in the plugin's `.mcp.json` (`uvx basic-memory mcp`) and starts when the plugin is enabled — confirm it shows up under `/mcp` after setup (mention this to the user).

## 3. Create the global brain
- Create the directory tree (only if absent — never overwrite):
  `~/Engram/global/{workflow,kmp,ios,android,firebase}` and `~/Engram/global/inbox`.
- `git init` `~/Engram/global` if it isn't already a repo; add a `.gitignore` for `.obsidian/` and OS cruft; make an initial commit.
- Seed `~/Engram/global/INDEX.md` — a short map-of-content note listing the domains, only if it doesn't exist.

## 4. Register the global Basic Memory project
- Discover the exact CLI first: `basic-memory project --help` (subcommand names can change — adapt to what you see).
- Add the project pointing at the global brain, e.g. `basic-memory project add engram-global ~/Engram/global`.
- Make it the default (e.g. `basic-memory project default engram-global`; if there's no such subcommand, set `default_project` in `~/.basic-memory/config.json`).
- Verify with `basic-memory project list`.

## 5. Inbox + sync note
- Confirm `~/Engram/global/inbox/` exists. Tell the user: drop raw thoughts here as markdown from anywhere; `/engram:triage` files them into the graph. To capture from a phone, point Obsidian (or any sync — iCloud/Dropbox/git) at `~/Engram/global` so the inbox syncs to mobile. Engram doesn't mandate a sync provider.

## 6. Report
- Summarize: what was installed, the global brain path, the MCP status, the inbox path.
- Tell the user the next steps: `/engram:adopt` to migrate existing Claude memory in (backs up first), and `/engram:init` inside any repo to create its project brain.

Do NOT migrate or modify any existing Claude memory here — that's `/engram:adopt`, which backs up first.
