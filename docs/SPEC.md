# Engram — Spec v0.2 (Foundations)

> **Name: Engram** (confirmed). **Distribution: public from day one** — plugin code MIT-licensed; Basic Memory is an AGPL *dependency* the plugin installs (not redistributed), so no license bleed. **Global store: local for now** (`~/.engram/`, `git init`'d for history but no remote yet — cross-machine sync deferred by choice).

## 1. What it is

**Engram is a Claude Code plugin that replaces Claude's ad-hoc memory with a durable, graph-shaped, two-tier knowledge base — stored as plain markdown, browsable in Obsidian, versioned in git, and queried by agents over MCP.**

One-liner: *Your second brain for Claude — portable, graph-shaped, and shared across every project you build.*

It is installable by anyone via `/` commands, migrates existing Claude memory in (backing everything up first), and gives you and your agents one knowledge graph that spans projects.

## 2. Design principles (non-negotiable)

1. **Future-proof first.** The store is plain markdown + YAML frontmatter in git. No proprietary DB is ever the source of truth. You can read it with `cat` in 20 years and open it in Obsidian today. Any index/embedding layer is a *disposable, rebuildable cache*.
2. **Two tiers: global + project.** Reusable cross-project knowledge (how we work, KMP/iOS/Firebase patterns) lives in a **global** graph; project-specific facts live in a **project** graph that links *up* into global. Same mechanism as Claude's own global-vs-project scoping, made first-class.
3. **Graph, not a list.** Entities + typed relations, so knowledge is traversable, not grepped. Edges carry meaning (`uses`, `supersedes`, `pairs_with`, `applies_to`).
4. **Agents actively consult it.** Not "hope it gets recalled" — a deliberate, hook-driven "check the graph" step at session start and before non-trivial work, plus read/write MCP tools mid-task.
5. **Safe by default.** Nothing destructive happens without an explicit, backed-up, confirmable step. Replacing native memory always snapshots everything first.
6. **Shareable.** Ships as a Claude Code plugin via a marketplace repo. A friend runs two commands and has the same system.

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Engram plugin (Claude Code)                                  │
│   • slash commands  • hooks  • a "how to use the graph" skill │
└───────────────┬──────────────────────────────────────────────┘
                │ configures + drives
                ▼
┌──────────────────────────────────────────────────────────────┐
│  Basic Memory (MCP server)  ← the engine, not our code        │
│   read/write/traverse markdown as a typed-relation graph      │
└───────────────┬──────────────────────────────────────────────┘
                │ operates on
                ▼
┌──────────────────────────────────────────────────────────────┐
│  The markdown graph (source of truth, git + Obsidian)         │
│                                                                │
│   ~/.engram/global/        ← global tier (default project)    │
│      workflow/  kmp/  ios/  firebase/  android/               │
│   <repo>/.engram/          ← project tier (pinned per repo)   │
│      notes that [[link]] up into global                       │
└──────────────────────────────────────────────────────────────┘
```

**Engine = Basic Memory** (`basicmachines-co/basic-memory`). Chosen after research: it's the only option that is simultaneously markdown/git/Obsidian-native, a true typed-relation graph, MCP read+write, first-class multi-project, and actively maintained. Engram does **not** reinvent the engine — it *packages, configures, and adds discipline on top of it* (conventions, the two-tier layout, the migration/backup flow, the "consult the graph" rule), and bundles it as a turnkey plugin.

**Native Claude memory becomes a pointer.** After adoption, `~/.claude/CLAUDE.md` and each project's `MEMORY.md` shrink to a few lines: *"Your durable memory is the Engram graph — consult it via the basic-memory MCP; write learnings there, not here."*

## 4. Plugin shape (Claude Code)

A standard Claude Code plugin repo:

```
engram/
  .claude-plugin/plugin.json      # manifest
  marketplace.json                # so friends can `marketplace add`
  commands/                       # the / commands (§5)
  hooks/                          # session-start consult + pre-compact checkpoint
  skills/using-the-graph/         # conventions any agent reads (§7)
  mcp/                            # basic-memory MCP config templates
  scripts/                        # install / backup helpers
  docs/SPEC.md                    # this file
```

Distribution: `claude plugin marketplace add <github-repo>` → `claude plugin install engram@<marketplace>`.

## 5. Command set (the `/` commands)

All namespaced (`/engram:<cmd>`). The two the user explicitly called out — **install everything** and **replace memory with a backup first** — are `setup` and `adopt`.

| Command | Does |
|---|---|
| `/engram:setup` | **One-shot bootstrap.** Check prereqs (uv/uvx, node, git). Install Basic Memory. Register the global MCP (user scope). Create the global graph at `~/.engram/global` + `git init` it. Install Basic Memory's CC plugin hooks. Idempotent — safe to re-run. |
| `/engram:adopt` | **Replace native Claude memory — backup first.** (1) Snapshot EVERYTHING: `~/.claude/CLAUDE.md`, every `~/.claude/projects/*/memory/`, project `CLAUDE.md`s → timestamped tarball **and** a git commit in `~/.engram/backups/`. (2) Print exactly what was backed up + where. (3) **Require explicit "yes" to proceed.** (4) Migrate notes into the graph (route global vs project), converting to typed-relation format. (5) Replace native `MEMORY.md`/`CLAUDE.md` bodies with thin pointers. Reversible from the snapshot. |
| `/engram:init` | Initialize the **current repo** as a project tier: create `<repo>/.engram/`, add a Basic Memory project, write a committed `.mcp.json` pinning `BASIC_MEMORY_MCP_PROJECT`, seed an index/MOC note linking up to global. |
| `/engram:remember <fact>` | Capture a fact as a graph note. Auto-routes global vs project (asks if ambiguous), applies the typed-relation conventions, dedupes against existing notes. |
| `/engram:recall <query>` | Query + traverse the graph (semantic + full-text + link-following) and summarize. |
| `/engram:status` | Show: engine health, current project + tier, note counts per domain, last backup timestamp. |
| `/engram:backup` | Manual snapshot of the whole graph (+ native memory) to `~/.engram/backups/`. |

Safety rule: `adopt` and any overwrite are **two-phase** — back up + show + confirm, then act. Never destructive on the first beat.

## 6. The two-tier model + linking

- **Global** (`~/.engram/global`, the Basic Memory `default_project`): cross-project truth.
  - `workflow/` — how we work (preferences, runbooks, the destructive-ops ban, stage-vs-live rules).
  - `kmp/`, `ios/`, `android/`, `firebase/` — reusable engineering patterns (KMP localization, theming, SQLDelight flow, expect/actual; iOS StoreKit; Firebase stage/live).
- **Project** (`<repo>/.engram`, pinned via `.mcp.json` env `BASIC_MEMORY_MCP_PROJECT`): app-specific facts.
- **Linking up:** a project note references global knowledge with a typed wikilink, e.g. Habeeto's theming note: `- applies [[kmp/theming]]`. The project note holds only what's *unique* to the project; the reusable substance lives once, in global.
- **Promotion rule:** when a project fact turns out to be reusable (e.g., a KMP pattern), it gets *promoted* to global and the project note becomes a thin link. One fact, one home.

## 7. Conventions (the "using-the-graph" skill)

Bundled as a skill so every agent follows the same rules.

- **Note = entity.** One concept per file. Frontmatter: `title`, `type`, `tags`, `tier` (global|project).
- **Typed relations** (Basic Memory grammar): `- uses [[X]]`, `- supersedes [[Y]]`, `- applies_to [[Z]]`, `- pairs_with [[W]]`. Bare `[[X]]` = generic link.
- **Observations** as categorized facts: `- [fact] …`, `- [rule] …`, `- [gotcha] …`, `- [cmd] …`.
- **Routing rule** (where does a fact go?): derivable from code → store nowhere, keep a pointer · reusable across projects → **global** · project-specific → **project** · idea in flight → Obsidian inbox (existing pipeline). Never two homes.
- **Volatility marker:** volatile facts (versions, SKUs, pricing) carry `verify before quoting — last checked YYYY-MM-DD`; evergreen rules don't.
- **Write discipline:** before creating a note, search the graph; if it exists, update in place — never fork a duplicate.

## 8. Capture inbox (phone-friendly) — first-class component

A frictionless place to dump a raw thought from anywhere (phone, mid-flow) that later gets triaged into the curated graph. Generalizes the old "UNSORTED THOUGHTS → Discussions" pipeline and makes it sync-agnostic + shareable.

- **The inbox is just markdown** in the graph: `~/.engram/global/inbox/` (one file per thought, or a single appendable `inbox.md`). No special format — type a line, done.
- **Sync is the user's choice — Engram mandates none.** Because the inbox is plain markdown on disk, any sync works: **Obsidian mobile** (recommended) over iCloud Drive / Dropbox / a git remote (Working Copy on iOS) / Obsidian Sync. The phone edits the same files the agent reads. Engram ships docs for the common setups; it does not lock you to a provider.
- **Triage flow** (the curation step, agent-assisted):
  - `/engram:triage` — read the inbox, surface each new item, and help file it: promote to a graph note (global vs project, typed relations), park it, or drop it with a note. Clears the inbox as items are filed. This is the old `UNSORTED THOUGHTS → Discussions` move, generalized.
  - Optional **SessionStart hook** — if the inbox is non-empty, surface "you have N uncaptured thoughts" so they don't rot.
- **Why it matters:** capture and curation are different jobs. The inbox is for *frictionless capture from anywhere*; the graph is for *curated, linked knowledge*. Keeping them distinct (but connected by triage) is the whole point — and the phone path is what makes capture actually happen.

> **Open:** pick a *recommended default* sync for the docs (likely Obsidian mobile + iCloud on Apple, or a git-based flow cross-platform). Doesn't block the build — the inbox folder works the moment it exists; sync is wired per-user.

## 9. Safety: backup-before-replace (detail)

`/engram:adopt` snapshot covers, before touching anything:
- `~/.claude/CLAUDE.md` (global instructions)
- every `~/.claude/projects/*/memory/` (all project auto-memories + indexes)
- every discoverable project `CLAUDE.md`
- (optional) a copy of the current Obsidian vault(s)

→ written to `~/.engram/backups/<timestamp>/` as a tarball **and** committed to a git repo there. The command prints the manifest and the restore command, then waits for explicit confirmation before migrating/replacing. A `/engram:restore <timestamp>` (v0.2) reverses it.

## 10. Decisions (ratified) + what's left

**Ratified:**
1. **Name** — Engram. ✓
2. **Global store** — local `~/.engram/`, `git init`'d (history/safety) but **no remote** for now. Cross-machine sync revisited later. ✓
3. **Capture inbox** — a first-class component (§8), sync-agnostic, phone-friendly. The old `UNSORTED THOUGHTS` pipeline is *not* carried over verbatim (it was lost in the PC migration) but its *role* is rebuilt here, generalized. ✓
4. **Distribution** — public from day one; plugin MIT, Basic Memory AGPL dependency. ✓

**Still open (non-blocking):**
- Recommended default sync for the inbox docs (Obsidian + iCloud vs git-based). Decide during the inbox build.

---

### Build order
1. **Scaffold the plugin repo** (`~/Coding/engram/`): manifest, marketplace.json, dir skeleton, MIT license, README, move this spec to `docs/`.
2. **`/engram:setup`** — install Basic Memory + register global MCP + create `~/.engram/global` (git init) + the inbox folder.
3. **`/engram:adopt`** — the safety-critical one: backup-everything → confirm → migrate → thin native files to pointers.
4. **`/engram:init`, `remember`, `recall`, `triage`, `status`, `backup`.**
5. **Dogfood on Habeeto:** migrate the keepers as the first project tier; extract reusable KMP knowledge into `global/kmp/` as the first global domain.
