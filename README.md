# 🧠 Engram

**Durable, graph-shaped memory for Claude Code — your second brain, shared across every project.**

Engram replaces Claude's ad-hoc memory with a knowledge graph stored as **plain markdown** (git-versioned, Obsidian-browsable) and queried by agents over MCP. Two tiers: a **global** brain that carries reusable knowledge across all your projects, and a **project** brain for app-specific facts that links up into it.

> Built on [Basic Memory](https://github.com/basicmachines-co/basic-memory). Engram packages it into a turnkey Claude Code plugin with a two-tier layout, conventions, a phone-friendly capture inbox, and a safe one-command migration off Claude's native memory.

## Why

- **Future-proof.** Your memory is a folder of markdown files in git. No proprietary database is ever the source of truth. Readable with `cat` in 20 years; openable in Obsidian today.
- **Graph, not a list.** Entities + typed relations (`uses`, `supersedes`, `applies_to`), so knowledge is *traversable*, not grepped.
- **Two tiers.** Reusable patterns live once in the global brain; projects link up instead of duplicating.
- **Agents actually consult it.** Session-start briefing + read/write MCP tools mid-task — not "hope it gets recalled."
- **Capture from anywhere.** A markdown inbox you can sync to your phone (Obsidian or any sync); triage curates it into the graph.
- **Safe.** Migrating off Claude's native memory backs up *everything* first and waits for your explicit yes.

## Install

```bash
# add this repo as a marketplace, then install the plugin
/plugin marketplace add vendetta8247/engram
/plugin install engram@engram

# one-time bootstrap (installs Basic Memory, wires the MCP, creates your global brain + inbox)
/engram:setup

# (optional) migrate your existing Claude memory in — backs everything up first
/engram:adopt
```

Per project, run `/engram:init` inside the repo to create its project brain.

## Commands

| Command | What it does |
|---|---|
| `/engram:setup` | One-time bootstrap: install Basic Memory, register the MCP, create the global brain + inbox. Idempotent. |
| `/engram:adopt` | Migrate off Claude's native memory — **backs up everything first**, shows the manifest, waits for confirmation, then migrates + thins the native files to pointers. Reversible. |
| `/engram:init` | Initialize the current repo as a project brain (links up to global). |
| `/engram:remember <fact>` | Capture a fact into the graph (auto-routes global vs project). |
| `/engram:recall <query>` | Query + traverse the graph. |
| `/engram:triage` | Process the capture inbox into the curated graph. |
| `/engram:status` | Show config, current project, note counts, last backup. |
| `/engram:backup` | Snapshot the whole graph + native memory. |

## How it's laid out

```
~/.engram/global/        ← global brain (reusable across projects)
   workflow/  kmp/  ios/  firebase/  android/
   inbox/                ← capture inbox (sync to phone via Obsidian/iCloud/git)
<your-repo>/.engram/     ← project brain (pinned per repo, links up into global)
```

## Requirements

- Claude Code
- [uv](https://docs.astral.sh/uv/) (Engram's `setup` installs it if missing) — runs Basic Memory
- Optional: [Obsidian](https://obsidian.md) to browse/edit the graph as a human

## License

MIT (Engram). Basic Memory is an AGPL-3.0 dependency that Engram installs and calls over MCP — not redistributed here.
