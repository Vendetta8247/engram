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

# go live — ONE command. Self-bootstraps (installs Basic Memory + builds your
# global brain), backs up all native memory, then migrates it in. Confirm-gated.
/engram:adopt
```

That's it. Project brains **auto-create** the first time you store knowledge in a repo — you never run `init`. Changed your mind? `/engram:revert` puts native memory back exactly as it was.

Prefer to try it alongside native memory first? Run `/engram:setup` (install only, no takeover), then `/engram:adopt` when you're ready.

## Commands

| Command | What it does |
|---|---|
| `/engram:adopt` | **The one command to go live.** Self-bootstraps (installs Basic Memory + creates the global brain if needed), then migrates off native memory — backs up everything first, shows the manifest, waits for confirmation, thins the native files, disables native auto-memory. |
| `/engram:revert` | **The go-back button.** Restore native memory exactly as it was pre-adopt (re-enables native auto-memory, un-thins files, removes the routing directive). Graph preserved unless you ask. |
| `/engram:setup` | *Optional.* Install + create the global brain *without* taking over native memory — for trying Engram alongside native memory first. (`adopt` does this for you.) |
| `/engram:init` | *Optional / automatic.* A repo's project brain auto-creates the first time you store project knowledge there — you rarely run this. Use it to set a repo up deliberately + commit the `.mcp.json` pin. |
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
