# 🧠 Engram

**Durable, graph-shaped memory for Codex and Claude Code — a second brain, shared across every project.**

Engram replaces ad-hoc agent memory with a knowledge graph stored as **plain markdown** (git-versioned, Obsidian-browsable) and queried over MCP. One store, two buckets: **`global/`** carries reusable knowledge across all your projects, and **`projects/<name>/`** is each project's operational encyclopedia. Codex and Claude recall from it before work and write to it as they learn — automatically.

> Built on [Basic Memory](https://github.com/basicmachines-co/basic-memory). Engram packages it with a two-tier layout, conventions, automatic recall/capture, a phone-friendly capture inbox, and a safe migration off Claude's native memory. The bundled shared-service installer is turnkey on **macOS**; the knowledge graph and host-neutral plugin behavior remain usable on **Linux** with a separately configured user service.

## Why

- **Future-proof.** Your memory is a folder of markdown files in git. No proprietary database is ever the source of truth. Readable with `cat` in 20 years; openable in Obsidian today.
- **A graph, not a list.** Entities + typed relations (`uses`, `supersedes`, `applies_to`), so knowledge is *traversable*, not grepped.
- **Two buckets, no duplication.** Reusable patterns live once in `global/`; each project's facts live in `projects/<name>/` and link up.
- **Agents actually consult it.** A session-start briefing plus read/write MCP tools mid-task — not "hope it gets recalled."
- **Precise by design.** Notes are concept-scoped and structured, but technically complete: exact entry points, contracts, data flow, commands, constraints, edge cases, decisions, and sources where needed.
- **Capture from anywhere.** A markdown inbox you can sync to your phone (Obsidian or any sync); triage curates it into the graph.
- **Safe & reversible.** Going live backs up *everything* first and waits for your explicit yes; one command puts native memory back.

## How to install

**Prerequisites:** Codex and/or [Claude Code](https://claude.com/claude-code), `git`, [uv](https://docs.astral.sh/uv/), `curl`, and `jq`. The shared supervised service installer described below currently supports **macOS**. It discovers the installing user's home directory and `uvx`; no developer-specific absolute paths are shipped.

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

### Codex integration

Engram includes a Codex manifest and a Codex-specific lifecycle adapter while preserving Claude compatibility. On macOS, Codex and Claude share one Basic Memory 0.23.2 streamable-HTTP process supervised by `launchd`; new chats no longer spawn one indexing process each. The service binds only to `127.0.0.1:18765` and is constrained to the `engram` project.

The macOS service is installed from the plugin source with `bash scripts/engram-install-service.sh`. The installer generates `~/Library/LaunchAgents/com.yegor.engram.basic-memory.plist` for the current account, discovers `uvx`, validates the plist, and backs up a changed existing plist before replacing it. The `com.yegor...` string is a stable service identifier, not a username or machine binding.

Every chat checks the service through a real MCP initialize + diagnostics + project handshake. `SessionStart` and `PreCompact` checks are uncached; `UserPromptSubmit` checks are cached for five minutes per chat. An outage produces one visible warning, keeps the offline policy in agent context, forbids claims of durable capture, and blocks Codex compaction until checkpoint storage recovers. Recovery is announced once. Codex also marks the MCP server `required`, so a new or resumed task cannot silently start without it.

The live checkpoint is only a handoff mechanism. Permanent project knowledge belongs in canonical encyclopedia notes. Unverified research is staged temporarily under `projects/<name>/research/`; validated conclusions are migrated into permanent product/system/architecture/runbook notes, and stale research is removed rather than becoming a second memory pile.

Default limits:

- At **256 MiB per task**, Codex must update the project's mutable live checkpoint.
- At **2 GiB per task**, normal work is blocked at an emergency boundary. The same responsibility task is retained; only checkpoint, recovery, and verified history-maintenance work remains allowed.
- At **40 GiB total** under `~/.codex/sessions`, Codex warns that aggregate history is approaching its ceiling.
- At **50 GiB total**, normal prompts are blocked until old tasks are cleaned or archived.
- If installed while history is already over 50 GiB, Engram records a one-time legacy baseline and permits at most **512 MiB** of additional growth. Once cleanup drops below 50 GiB, it permanently switches to the absolute cap.

The guard never copies transcripts into Engram and does not yet delete or rewrite Codex history. Persistent-history pruning remains disabled until copied-session resume and rollback tests prove a safe procedure. It retains only operational state: objective, progress, decisions and why, exact references, verification, blockers, and the next action.

Useful commands:

- `scripts/engram-status.sh` — full MCP, launchd, process-count, and Codex-history status.
- `scripts/engram-codex-hook.sh --status` — active history mode and thresholds.
- `scripts/engram-recovery-command.sh` — print the platform-appropriate service restart command.
- `scripts/engram-install-service.sh` — install or repair the current macOS user's shared service.

Limits can be overridden with the `ENGRAM_CODEX_*` environment variables documented in the adapter.

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
- **curl + jq** — required by the end-to-end MCP health probe and deterministic memory router.
- **[Obsidian](https://obsidian.md)** *(optional)* — to browse/edit the graph as a human.

## Safety

Going live never destroys anything: `/engram:adopt` backs up all native memory (a timestamped tree + tarball + manifest) *before* it touches a thing, shows you the manifest, and waits for an explicit yes. It leaves your native files in place and only flips native auto-memory off. `/engram:revert` puts it all back. The store itself is git-versioned, so every change is recoverable.

## License

MIT (Engram). [Basic Memory](https://github.com/basicmachines-co/basic-memory) is an AGPL-3.0 dependency that Engram installs and calls over MCP — it is not redistributed in this repository.
