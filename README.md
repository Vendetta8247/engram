# 🧠 Engram

**Durable, graph-shaped memory for Claude Code — a second brain, shared across every project.**

Engram replaces Claude's ad-hoc memory with a knowledge graph stored as **plain markdown** (git-versioned, Obsidian-browsable) and queried by agents over MCP. One store, two buckets: **`global/`** carries reusable knowledge across all your projects, and **`projects/<name>/`** holds app-specific facts that link up into it. Claude recalls from it before work and writes to it as it learns — automatically.

> Built on [Basic Memory](https://github.com/basicmachines-co/basic-memory). Engram packages it into a turnkey Claude Code plugin with a two-tier layout, conventions, automatic recall/capture, a phone-friendly capture inbox, and a safe one-command migration off Claude's native memory. **macOS and Linux.**

## Why

- **Future-proof.** Your memory is a folder of markdown files in git. No proprietary database is ever the source of truth. Readable with `cat` in 20 years; openable in Obsidian today.
- **A graph, not a list.** Entities + typed relations (`uses`, `supersedes`, `applies_to`), so knowledge is *traversable*, not grepped.
- **Two buckets, no duplication.** Reusable patterns live once in `global/`; each project's facts live in `projects/<name>/` and link up.
- **Agents actually consult it.** A session-start briefing plus read/write MCP tools mid-task — not "hope it gets recalled."
- **Compact by design.** Notes are operational memory for the agent: many small, linked nodes — not essays — so recall is sharp and cheap.
- **Capture from anywhere.** A markdown inbox you can sync to your phone (Obsidian or any sync); triage curates it into the graph.
- **Safe & reversible.** Going live backs up *everything* first and waits for your explicit yes; one command puts native memory back.

## How to install

**Prerequisites:** [Claude Code](https://claude.com/claude-code), `git`, and [uv](https://docs.astral.sh/uv/) (Engram installs uv for you if it's missing). `jq` is optional (enables one hook; safely skipped if absent). Works on **macOS and Linux**.

```bash
# 1. add this repo as a plugin marketplace
/plugin marketplace add vendetta8247/engram

# 2. install the plugin
/plugin install engram@engram

# 3. go live — ONE command. Self-bootstraps (installs Basic Memory + builds your
#    store under ~/Engram), backs up all native memory, and switches memory over.
#    It backs up first and waits for your explicit confirmation before changing anything.
/engram:adopt
```

That's the whole setup. `/engram:adopt` self-bootstraps everything (you don't need `/engram:setup` first). When it finishes, it offers to **scan** the current project into a knowledge base — say yes, or do it later with `/engram:scan`.

Want to try it *alongside* native memory before committing? Run `/engram:setup` (install only, no takeover), then `/engram:adopt` when ready. Changed your mind after adopting? `/engram:revert` restores native memory exactly as it was.

## Using Engram

Once you're live, memory is **ambient** — you mostly don't run commands:

- **It recalls automatically.** Before non-trivial work, Claude searches the store (current project first, then global) and leads with what's already known.
- **It captures automatically.** The moment Claude learns something durable — a preference, a correction, a gotcha, a decision and its *why*, a reusable pattern — it writes a compact note to the graph, mid-task, without being asked.
- **You can still drive it by hand.** "Remember that…" / "what do you know about…" route to the graph (never native memory). Or use `/engram:remember` and `/engram:recall` explicitly.
- **Onboard a codebase** with `/engram:scan` — it builds a structured, cross-linked KB (product/overview, systems, screens, architecture) under `projects/<name>/`. Offered automatically the first time you open a repo with no KB.
- **Capture on the go.** Drop raw notes into `~/Engram/inbox/` from anywhere (point Obsidian/iCloud/Dropbox/git at `~/Engram` to sync from your phone); `/engram:triage` files them into the graph later.
- **Browse it like a human.** Open `~/Engram` in Obsidian — it's just markdown with wikilinks.

## Commands you run

| Command | What it does |
|---|---|
| `/engram:adopt` | **Go live.** Self-bootstraps, backs up everything, then switches memory to Engram (disables native auto-memory, installs the routing directive; native files left intact). Migration is **lazy** — only your *global* memory is migrated up front; per-project memory is backed up and folded in later by `/engram:scan`. Then offers a project scan (scope: this / all / none). |
| `/engram:revert` | **Go back.** Restore native memory exactly as it was pre-adopt (re-enables native auto-memory, removes the routing directive). The graph is preserved unless you ask otherwise. |
| `/engram:scan` | **Onboard a project.** Seeds from the project's backed-up native memory, surveys the repo, writes **compact, agent-readable** notes into `projects/<name>/`, then runs a consolidation pass that dedups and tightens them. Pick **depth** (overview / map / exhaustive — coverage, not note size) and **engine** (single agent / multiple agents / workflow). Re-run to refresh after big changes. |
| `/engram:remember <fact>` | Capture a fact into the graph (auto-routes global vs project). Mostly automatic — this is the manual override. |
| `/engram:recall <query>` | Query + traverse the graph. Mostly automatic — this is the manual override. |
| `/engram:triage` | Process the capture inbox into the curated graph. |
| `/engram:backup` | Snapshot the whole graph + native memory to a restorable backup. |
| `/engram:status` | Show config, current project, note counts, last backup. |
| `/engram:setup` | *Optional.* Install + create the store **without** taking over native memory — to try Engram alongside native memory first. (`adopt` does this for you.) |
| `/engram:init` | *Optional / rarely needed.* A project's folder auto-creates the first time you store knowledge in a repo. Use this only to set one up deliberately ahead of time. |

## Internal / automatic (you don't run these)

- **`using-the-graph`** — *internal skill* (not user-invocable). The behavior spec the agent loads to know how to recall, route, and write notes. It's the brain behind the automatic recall/capture; you never type it.
- **Hooks** (run by Claude Code, no action from you):
  - *SessionStart* — briefs the agent that memory is active and to recall before work.
  - *UserPromptSubmit* — when your prompt looks like "remember…", deterministically routes it to Engram (needs `jq`; a no-op if absent).
  - *PreCompact* — before the context window compacts, prompts the agent to persist anything durable first.

## How it's laid out

```
~/Engram/                 ← ONE store (open this in Obsidian; one searchable graph)
   global/                 ← reusable knowledge, in domain folders
     workflow/ kmp/ ios/ android/ tooling/ ...
   projects/
     my-app/  api/  ...    ← each project's own facts (config, internals)
   inbox/                  ← capture inbox (sync to your phone via Obsidian/iCloud/git)
```

Two top-level buckets: **`global/`** (reusable across projects) and **`projects/`** (per project). Everything lives in `~/Engram`, so a fact from any project is one search away. No per-repo files.

## Requirements

- **Claude Code** — the host.
- **git** — the store is a git repo.
- **[uv](https://docs.astral.sh/uv/)** — runs Basic Memory (Engram's `setup` installs it if missing). macOS and Linux.
- **jq** *(optional)* — enables the deterministic "remember" prompt router; without it that one hook is a silent no-op.
- **[Obsidian](https://obsidian.md)** *(optional)* — to browse/edit the graph as a human.

## Safety

Going live never destroys anything: `/engram:adopt` backs up all native memory (a timestamped tree + tarball + manifest) *before* it touches a thing, shows you the manifest, and waits for an explicit yes. It leaves your native files in place and only flips native auto-memory off. `/engram:revert` puts it all back. The store itself is git-versioned, so every change is recoverable.

## License

MIT (Engram). [Basic Memory](https://github.com/basicmachines-co/basic-memory) is an AGPL-3.0 dependency that Engram installs and calls over MCP — it is not redistributed in this repository.
