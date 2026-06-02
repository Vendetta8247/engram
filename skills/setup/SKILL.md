---
name: setup
description: OPTIONAL install-only bootstrap — install Basic Memory, wire the MCP, create the store (global/ + projects/ buckets) + inbox, WITHOUT taking over native memory. Use this to try Engram alongside native memory first. Most users can skip straight to /engram:adopt, which self-bootstraps this. Idempotent.
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

## 3. Create the ONE store (~/Engram)
Everything lives under `~/Engram`, split into exactly two top-level buckets: **`global/`** (reusable knowledge, in domain folders) and **`projects/`** (one folder per project). There are no per-repo brains.
- Create the directory tree (only if absent — never overwrite):
  `~/Engram/global/{workflow,kmp,ios,android,tooling}`, `~/Engram/projects`, and `~/Engram/inbox`.
  (Note: project config like Firebase IDs/buckets is per-project → it lives under `projects/<name>/`, not a `global/firebase/` domain.)
- `git init` `~/Engram` if it isn't already a repo; add a `.gitignore` for `.obsidian/` and OS cruft; initial commit.
- Seed `~/Engram/INDEX.md` — a short map-of-content listing the `global/` domains + a `projects/` section. (This file is also the "Engram is set up" sentinel the hooks check.)

## 4. Register the single Basic Memory project
- Discover the exact CLI first: `basic-memory project --help` (subcommand names can change — adapt).
- Add ONE project named `engram` pointing at the store root: `basic-memory project add engram ~/Engram --local`. (One project over the whole store = cross-project search in a single query. Don't create a project per repo — that would nest and break.)
- Make it the default: `basic-memory project default engram` (or set `default_project` in `~/.basic-memory/config.json`). The plugin's `.mcp.json` also pins `BASIC_MEMORY_MCP_PROJECT=engram`.
- Verify with `basic-memory project list` (engram → ~/Engram, local).

## 5. Inbox + sync note
- Confirm `~/Engram/inbox/` exists. Tell the user: drop raw thoughts here as markdown from anywhere; `/engram:triage` files them into the graph. To capture from a phone, point Obsidian (or any sync — iCloud/Dropbox/git) at `~/Engram` so the inbox syncs to mobile. Engram mandates no sync provider.

## 6. Report
- Summarize: what was installed, the store path (`~/Engram`), the MCP status, the inbox path.
- Tell the user: `/engram:adopt` migrates existing Claude memory in (backs up first). No per-repo init is needed — project folders auto-create under `~/Engram/projects/` as you work.

Do NOT migrate or modify any existing Claude memory here — that's `/engram:adopt`, which backs up first.
