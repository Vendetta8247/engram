# 🧠 Engram

**Durable, graph-shaped memory for Claude Code — your second brain, shared across every project.**

Engram replaces Claude's ad-hoc memory with a knowledge graph stored as **plain markdown** (git-versioned, Obsidian-browsable) and queried by agents over MCP. One store, two buckets: **`global/`** carries reusable knowledge across all your projects, and **`projects/<name>/`** holds app-specific facts that link up into it.

> Built on [Basic Memory](https://github.com/basicmachines-co/basic-memory). Engram packages it into a turnkey Claude Code plugin with a two-tier layout, conventions, a phone-friendly capture inbox, and a safe one-command migration off Claude's native memory.

## Why

- **Future-proof.** Your memory is a folder of markdown files in git. No proprietary database is ever the source of truth. Readable with `cat` in 20 years; openable in Obsidian today.
- **Graph, not a list.** Entities + typed relations (`uses`, `supersedes`, `applies_to`), so knowledge is *traversable*, not grepped.
- **Two buckets.** Reusable patterns live once in `global/`; each project's facts live in `projects/<name>/` and link up instead of duplicating.
- **Agents actually consult it.** Session-start briefing + read/write MCP tools mid-task — not "hope it gets recalled."
- **Capture from anywhere.** A markdown inbox you can sync to your phone (Obsidian or any sync); triage curates it into the graph.
- **Safe.** Migrating off Claude's native memory backs up *everything* first and waits for your explicit yes.

## Install

```bash
# add this repo as a marketplace, then install the plugin
/plugin marketplace add vendetta8247/engram
/plugin install engram@engram

# go live — ONE command. Self-bootstraps (installs Basic Memory + builds your
# store), backs up all native memory, migrates your global memory in (per-project
# memory is folded in later, lazily, by /engram:scan). Confirm-gated.
/engram:adopt
```

That's it. A project's folder under `projects/` **auto-creates** the first time you store knowledge in that repo — you never run `init`. And when you open a repo Engram has never seen, it **offers to `/engram:scan`** it into a full knowledge base (it asks first). Changed your mind? `/engram:revert` puts native memory back exactly as it was.

Prefer to try it alongside native memory first? Run `/engram:setup` (install only, no takeover), then `/engram:adopt` when you're ready.

## Commands

| Command | What it does |
|---|---|
| `/engram:adopt` | **The one command to go live.** Self-bootstraps (installs Basic Memory + builds the store if needed), then switches memory over — backs up everything first, shows the manifest, waits for confirmation, disables native auto-memory, installs the routing directive (native files left intact). Migration is **lazy**: only your *global* memory is migrated up front; per-project memory is backed up and folded in later by `/engram:scan`, so adopt stays fast. It then **offers a project scan** — pick the scope (this project / all / none), depth, and engine. |
| `/engram:revert` | **The go-back button.** Restore native memory exactly as it was pre-adopt (re-enables native auto-memory, restores any changed files, removes the routing directive). Graph preserved unless you ask. |
| `/engram:setup` | *Optional.* Install + create the store *without* taking over native memory — for trying Engram alongside native memory first. (`adopt` does this for you.) |
| `/engram:scan` | **Onboard a project — build a PM-style KB in one pass.** Seeds from the project's backed-up native memory, surveys the repo (product/PM overview, systems, screens, architecture, data model), writes **compact, agent-readable** notes into `projects/<name>/`, then runs a consolidation pass that dedups and tightens them. Pick the **depth** (overview / map / exhaustive — coverage, not note size) and **engine** (single agent / multiple agents / workflow). Offered automatically when a repo has no KB yet (it asks first); also run it to refresh after big changes. |
| `/engram:init` | *Optional / automatic.* A project's folder (`~/Engram/projects/<name>/`) auto-creates the first time you store project knowledge — you rarely run this. Use it to set a project up deliberately ahead of time. |
| `/engram:remember <fact>` | Capture a fact into the graph (auto-routes global vs project). |
| `/engram:recall <query>` | Query + traverse the graph. |
| `/engram:triage` | Process the capture inbox into the curated graph. |
| `/engram:status` | Show config, current project, note counts, last backup. |
| `/engram:backup` | Snapshot the whole graph + native memory. |

## How it's laid out

```
~/Engram/                 ← ONE store (open this in Obsidian; one searchable graph)
   global/                 ← reusable knowledge, in domain folders
     workflow/ kmp/ ios/ android/ tooling/ ...
   projects/
     habito/  vizix/  ...   ← each project's own facts (config, internals)
   inbox/                  ← capture inbox (sync to phone via Obsidian/iCloud/git)
```
Two top-level buckets: **`global/`** (reusable across projects) and **`projects/`** (per project). Everything lives in `~/Engram`, so a fact from any project is one search away. No per-repo files.

## Requirements

- Claude Code
- [uv](https://docs.astral.sh/uv/) (Engram's `setup` installs it if missing) — runs Basic Memory
- Optional: [Obsidian](https://obsidian.md) to browse/edit the graph as a human

## License

MIT (Engram). Basic Memory is an AGPL-3.0 dependency that Engram installs and calls over MCP — not redistributed here.
