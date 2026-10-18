# Engram — Spec

> **Name: Engram** (confirmed). **Distribution: public from day one** — plugin code MIT-licensed; Basic Memory is an AGPL *dependency* the plugin installs (not redistributed), so no license bleed. **Global store: local for now** (`~/Engram/`; Git history and cross-machine sync are optional user choices).

## 1. What it is

**Engram is a Codex- and Claude-compatible memory layer that replaces ad-hoc chat memory with a durable, graph-shaped, two-tier knowledge base — stored as plain markdown, browsable in Obsidian, optionally versioned in Git, and queried by agents over MCP.**

One-liner: *Durable project knowledge shared by Codex and Claude — portable, graph-shaped, and precise enough to operate from.*

It is installable by anyone via `/` commands, migrates existing Claude memory in (backing everything up first), and gives you and your agents one knowledge graph that spans projects.

## 2. Design principles (non-negotiable)

1. **Future-proof first.** The store is plain Markdown + YAML frontmatter, optionally versioned in Git. No proprietary DB is ever the source of truth. You can read it with `cat` in 20 years and open it in Obsidian today. Any index/embedding layer is a *disposable, rebuildable cache*.
2. **Two tiers: global + project.** Reusable cross-project knowledge (how we work, KMP/iOS/Firebase patterns) lives in a **global** graph; project-specific facts live in a **project** graph that links *up* into global. Same mechanism as Claude's own global-vs-project scoping, made first-class.
3. **Graph, not a list.** Entities + typed relations, so knowledge is traversable, not grepped. Edges carry meaning (`uses`, `supersedes`, `pairs_with`, `applies_to`).
4. **Memory is automatic, not on-demand.** The agent auto-recalls relevant knowledge before non-trivial work and captures durable learnings as it goes. Verified per-chat progress checkpoints are a separate, optional preference, enabled by default; disabling them preserves recall and ordinary capture while reducing automatic progress recovery. Only graph write plus exact readback produces a verified receipt. `/engram:remember` and `/engram:recall` are manual overrides.
5. **Safe by default.** Nothing destructive happens without an explicit, backed-up, confirmable step. An explicitly requested Claude migration snapshots native memory first and preserves its file bodies.
6. **Shareable.** Ships as a Claude Code plugin via a marketplace repo. A friend runs two commands and has the same system.
7. **Project encyclopedia, not a fact scrapbook.** A mature project tier contains the key product and technical knowledge needed to work on the project. Concept-scoped notes remain precise and complete; compactness never justifies vagueness.
8. **Research has a lifecycle.** Unverified work is temporary and explicitly marked. Validated conclusions are promoted into canonical permanent notes; rejected or stale scratch material is distilled or removed.

## 3. Architecture

### 3.1 Shared local MCP runtime

- Codex and Claude connect to one loopback streamable-HTTP Basic Memory service instead of launching one stdio process per chat.
- The macOS service is supervised by `launchd`, version-pinned, constrained to the `engram` project, and backed by an Engram-owned runtime directory separate from legacy Basic Memory clients.
- Native Windows Codex uses PowerShell and a standard-library Python lifecycle adapter. The installing Codex follows `/engram:setup`, preserves existing configuration, and configures an appropriate current-user background service/logs on the target machine. The default Basic Memory config/database is `%LOCALAPPDATA%/Engram/basic-memory`; there is no standalone Windows installer or fixed task/wrapper identity. No WSL, Bash, jq, project Git repository, or Claude installation is required. Native Windows end-to-end read/write and recovery still require verification on the target machine; see `docs/windows.md`.
- Health means a successful MCP initialize followed by Basic Memory version diagnostics and an exact `engram` project constraint. A listening TCP port alone is insufficient.
- SessionStart and PreCompact probe immediately. UserPromptSubmit uses a short per-chat cache. Outage and recovery notifications are transition-based to avoid warning floods.
- While unhealthy, agents may continue using native context but must not claim durable recall or capture. Native Codex compaction remains available with an explicit warning about unverified checkpoint coverage; native history is retained.

### 3.2 Verified chat continuity and native history boundary

- `scripts/engram_continuity.py` is the standard-library save/status/recover path. It accepts a JSON checkpoint of at most 32 KiB with nonempty strings `objective`, `progress`, `next_action`, lists `decisions`, `references`, `blockers`, and a `verification` string. It retains semantic work state, never transcript dumps or media binaries.
- Identity is the actual lifecycle-hook session ID, not only a project name. Each chat has its own canonical note under `projects/<project>/live/chats/`, or `global/workflow/live/chats/` without a project. Chats in the same project cannot overwrite one another's checkpoints.
- Before network access, save journals the semantic attempt under `CODEX_HOME/engram/continuity/<sha-session>/attempts/` (default `~/.codex/engram/continuity/`). Only a successful graph write and exact readback produces a verified receipt. Earlier versions remain available, and a failed attempt cannot replace the last verified local recovery snapshot.
- UserPromptSubmit and PreToolUse mark new work generations before user requests and supported local tool calls. This includes the save tool, which verifies its own current revision without a post-save loop. A mid-turn receipt cannot cover later tool calls. Hosted/specialized tools may not expose hooks, so milestone capture remains necessary. With checkpoints enabled, Stop requires a verified current-revision checkpoint. PreCompact attempts fresh remote revalidation as a best-effort check and explicitly warns about missing, stale, dirty, offline or unvalidated coverage without vetoing compaction; default receipt age is 300 seconds, configurable with `ENGRAM_CHECKPOINT_MAX_AGE_SECONDS`.
- Hooks have no remaining-token-budget input, and the model cannot write a checkpoint before compaction that occurs before its next turn. Automatic saves remain enabled: save earlier, then recover and reconcile after compaction before saving a verified current checkpoint. Never imply an older checkpoint covers later work. Stop still requires a verified current-turn save; if its recovery continuation cannot save, report the failure visibly and stop rather than claim success or loop.
- Resume injects a restoration pointer. Recover uses the validated graph checkpoint, or clearly identifies the last verified local snapshot as offline. It restores checked progress and next action, not guaranteed full conversation wording or unsaved work. A lost drive requires an independently configured backup; local snapshots alone do not cover that failure.
- `scripts/engram_settings.py` stores `checkpoints_enabled` (default true) in `~/.engram/settings.json`. `ENGRAM_CONFIG_PATH` selects the file; `ENGRAM_CHECKPOINTS_ENABLED` overrides it. Off skips automatic saves and checkpoint gates without changing normal memory or storage protection. Explicit manual saves and access to old recovery notes remain available; never silently override off.
- Per-chat continuity verification starts with the first turn, independently of saved-history size. Normal work stops at the 2 GiB emergency boundary, preserving the same chat. Aggregate history warns at 40 GiB and hard-stops normal work at 50 GiB; an installation already above 50 GiB receives one fixed 512 MiB migration allowance above its recorded baseline. These are transcript bytes, not remaining tokens.
- Native Codex history is untouched: no automatic cleanup, deletion or rewriting, and no required replacement chat. Setup on every Codex platform warms uv-managed Python 3.12 and verifies restart/compaction recovery, offline failure behavior and two-chat isolation. Native Windows requires those checks on the actual target machine.

### 3.3 Software and creative project identity

- Use an explicit project name, selected workspace, repository root, then ordinary working folder. A projectless chat, home folder, or memory store is not an invented project. Use an explicit name to distinguish folders with identical basenames.
- Creative video notes retain brief/audience/style, script/storyboard and shot decisions, source paths/IDs/provenance, timeline and editing conventions, audio/color/captions, export settings, feedback and delivery. Inspect written materials and metadata first. Footage/renders/editing binaries remain in production folders.

```
┌──────────────────────────────────────────────────────────────┐
│  Engram integration (Codex + Claude Code)                     │
│   • skills/commands  • health hooks  • history guard           │
└───────────────┬──────────────────────────────────────────────┘
                │ configures + drives
                ▼
┌──────────────────────────────────────────────────────────────┐
│  One supervised Basic Memory HTTP MCP service                 │
│   read/write/traverse markdown as a typed-relation graph      │
└───────────────┬──────────────────────────────────────────────┘
                │ operates on
                ▼
┌──────────────────────────────────────────────────────────────┐
│  The Markdown graph (source of truth; Git optional)           │
│                                                                │
│   ~/Engram/   ← ONE store, ONE basic-memory project "engram"  │
│      global/<domain>/   ← reusable (workflow/kmp/ios/...)      │
│      projects/<name>/   ← each project's facts (config/internals)│
│      inbox/             ← capture                              │
│   (project notes [[link]] up into the global/ domains)        │
└──────────────────────────────────────────────────────────────┘
```

**Engine = Basic Memory** (`basicmachines-co/basic-memory`). Chosen after research: it's the only option that is simultaneously markdown/git/Obsidian-native, a true typed-relation graph, MCP read+write, first-class multi-project, and actively maintained. Engram does **not** reinvent the engine — it *packages, configures, and adds discipline on top of it* (conventions, the two-tier layout, the migration/backup flow, the "consult the graph" rule), and bundles it as a turnkey plugin.

**Native memory bodies are preserved.** An explicitly requested Claude migration backs up native memory, migrates global knowledge, disables Claude auto-memory and merges a routing block into the existing global instructions. It does not replace or shorten `CLAUDE.md` or `MEMORY.md` bodies; per-project memory stays readable for lazy migration during a later authorized scan. Codex-only adoption installs Codex routing and service configuration without inspecting or changing Claude memory/settings.

## 4. Plugin shape (Claude Code)

A standard Claude Code plugin repo:

```
engram/
  .claude-plugin/plugin.json      # manifest
  marketplace.json                # so friends can `marketplace add`
  commands/                       # the / commands (§5)
  hooks/                          # recall, verified continuity gates, history guard
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
| `/engram:adopt` ⭐ | **Go live — self-bootstraps.** Codex-only use runs setup and installs its routing directive without touching Claude. An explicitly requested Claude migration follows the backup/confirmation flow below. |
| `/engram:setup` | Install/repair the shared Basic Memory service, Codex MCP wiring, routing instructions and central store without migrating native memory. Uses the bundled macOS installer or agent-run native Windows setup. Git is optional; preserve existing data/configuration and verify MCP read/write plus service recovery. |
| Explicit Claude migration through `/engram:adopt` | Back up native instructions/settings and per-project memory to a timestamped copied tree, archive and manifest; show the manifest and require explicit confirmation. Migrate global knowledge now and defer per-project knowledge to authorized scans. Preserve every native memory body, merge `autoMemoryEnabled: false` into Claude settings, and append the global routing directive. Restore from the snapshot if requested. No automatic Git commits. |
| `/engram:scan` | **Onboard a project — build a comprehensive KB.** The standard new-project flow: when a repo has no `projects/<name>/` notes, the SessionStart hook prompts the agent to OFFER this (never unprompted). Runs a *documentation* workflow (NOT a bug audit) — survey (PM/product profile + systems/screens/modules inventory) → fan-out one agent per unit → completeness critic — then curates the result into `projects/<name>/{product,systems,screens,architecture}` + `global/<domain>`, cross-linked. Depth is user-chosen (overview / map / exhaustive). Reference workflow: `scripts/example-project-kb-workflow.js`. |

### How Engram owns the "remember" verb (defense-in-depth)

No single instruction-driven mechanism is guaranteed, so the routing is layered, strongest first:

1. **Explicit Claude migration only.** After backup and confirmation, `/engram:adopt` sets `autoMemoryEnabled: false` while preserving native memory bodies. Codex-only adoption does not change Claude settings.
2. **Deterministic interceptor.** A `UserPromptSubmit` hook (`engram-prompt-router.sh`) regex-detects memory-intent verbs in the actual prompt and injects an `additionalContext` instruction to route to Engram — fires on the words, every prompt, independent of model judgment.
3. **Always-loaded directive.** The global `~/.claude/CLAUDE.md` block (installed by adopt) keeps the routing rule in context every session, in every project.
4. **Standing rule.** The `using-the-graph` skill's "Engram OWNS the remember verb" section.
5. **Skill auto-invocation.** The `remember`/`recall` skill descriptions include the natural-language trigger phrases that bias the model to pick them on memory requests.

If layer 1 is active, the rest are belt-and-suspenders; if a user declines disabling native memory, layers 2–5 still route the verb.
| `/engram:revert` | Undo adoption for the current client. Codex-only use removes only its marked routing block and preserves unrelated instructions/Claude data. An explicitly requested Claude restore confirms and restores the pre-adoption snapshot/settings, including the previous routing instructions. The graph is preserved by default; plugin removal is client-specific. |
| `/engram:init` | *Optional / automatic.* Pre-create `~/Engram/projects/<name>/` for a project + seed its index. **Normally automatic** — the agent creates the project folder lazily on first project capture (per `using-the-graph`), so the user rarely runs it. No per-repo files, no separate Basic Memory project, no `.mcp.json` pin — it's all one store. |
| `/engram:remember <fact>` | Capture a fact as a graph note. Auto-routes global vs project (asks if ambiguous), applies the typed-relation conventions, dedupes against existing notes. |
| `/engram:recall <query>` | Query + traverse the graph (semantic + full-text + link-following) and summarize. |
| `/engram:status` | Show: engine health, current project + tier, note counts per domain, last backup timestamp. |
| `/engram:backup` | On request, snapshot graph notes/settings to a restorable tree, archive and manifest. Include Claude memory only when requested or required by an explicit Claude migration. Git is optional; no automatic commits. |

Safety rule: an actual Claude migration or restore is **two-phase** — back up/show the plan and require explicit confirmation before changing native settings or restoring files. Codex-only adoption does not enter the Claude migration flow. Preserve unrelated configuration and existing native memory bodies.

## 6. The two-tier model + linking

- **Global** (`~/Engram`, the Basic Memory `default_project`): cross-project truth.
  - `workflow/` — how we work (preferences, runbooks, the destructive-ops ban, stage-vs-live rules).
  - `kmp/`, `ios/`, `android/`, `firebase/` — reusable engineering patterns (KMP localization, theming, SQLDelight flow, expect/actual; iOS StoreKit; Firebase stage/live).
- **Project** (`~/Engram/projects/<name>/`, inside the one store): app-specific facts (config, IDs, this app's internals). Auto-created on first project capture; no per-repo files.
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
- **Technical specificity:** record exact paths/symbols, contracts, schemas/data flow, commands, constraints, edge cases, failure modes, decisions+why, and dated sources where relevant. Do not duplicate routine code.
- **State separation:** a verified checkpoint belongs to one chat and retains earlier local versions; it is a current-work handoff, not the encyclopedia or full transcript archive. Temporary research lives under `projects/<name>/research/` until promoted or discarded.

## 8. Capture inbox (phone-friendly) — first-class component

A frictionless place to dump a raw thought from anywhere (phone, mid-flow) that later gets triaged into the curated graph. Generalizes the old "UNSORTED THOUGHTS → Discussions" pipeline and makes it sync-agnostic + shareable.

- **The inbox is just markdown** in the graph: `~/Engram/inbox/` (one file per thought, or a single appendable `inbox.md`). No special format — type a line, done.
- **Sync is the user's choice — Engram mandates none.** Because the inbox is plain markdown on disk, any sync works: **Obsidian mobile** (recommended) over iCloud Drive / Dropbox / a git remote (Working Copy on iOS) / Obsidian Sync. The phone edits the same files the agent reads. Engram ships docs for the common setups; it does not lock you to a provider.
- **Triage flow** (the curation step, agent-assisted):
  - `/engram:triage` — read the inbox, surface each new item, and help file it: promote to a graph note (global vs project, typed relations), park it, or drop it with a note. Clears the inbox as items are filed. This is the old `UNSORTED THOUGHTS → Discussions` move, generalized.
  - Optional **SessionStart hook** — if the inbox is non-empty, surface "you have N uncaptured thoughts" so they don't rot.
- **Why it matters:** capture and curation are different jobs. The inbox is for *frictionless capture from anywhere*; the graph is for *curated, linked knowledge*. Keeping them distinct (but connected by triage) is the whole point — and the phone path is what makes capture actually happen.

> **Open:** pick a *recommended default* sync for the docs (likely Obsidian mobile + iCloud on Apple, or a git-based flow cross-platform). Doesn't block the build — the inbox folder works the moment it exists; sync is wired per-user.

## 9. Safety: backup-before-replace (detail)

An explicitly requested Claude migration through `/engram:adopt` backs up:

- `~/.claude/CLAUDE.md` (existing global instructions)
- `~/.claude/settings.json` and `settings.local.json` when present
- every `~/.claude/projects/*/memory/` and project `MEMORY.md`

The snapshot under `~/Engram/backups/<timestamp>/` contains a copied tree,
archive and manifest (tar on the POSIX helper or ZIP with the portable snapshot
procedure). Show the manifest and require confirmation before migrating global
knowledge, disabling Claude auto-memory or adding the routing directive. Keep
native memory bodies intact. `/engram:revert` uses that snapshot for an explicitly
requested Claude restore; Codex-only adoption/revert skips these Claude files.

Manual graph snapshots run on request through `/engram:backup`. Git versioning
is optional, and agents do not create backup commits automatically.

## 10. Decisions (ratified) + what's left

**Ratified:**
1. **Name** — Engram. ✓
2. **Global store** — local `~/Engram/`; Git history and cross-machine sync are optional user choices. Existing repositories are preserved and no commits are created automatically. ✓
3. **Capture inbox** — a first-class component (§8), sync-agnostic, phone-friendly. The old `UNSORTED THOUGHTS` pipeline is *not* carried over verbatim (it was lost in the PC migration) but its *role* is rebuilt here, generalized. ✓
4. **Distribution** — public from day one; plugin MIT, Basic Memory AGPL dependency. ✓

**Still open (non-blocking):**
- Recommended default sync for the inbox docs (Obsidian + iCloud vs git-based). Decide during the inbox build.

---

### Build order
1. **Scaffold the plugin repo** (`~/Coding/engram/`): manifest, marketplace.json, dir skeleton, MIT license, README, move this spec to `docs/`.
2. **`/engram:setup`** — install Basic Memory + register global MCP + create missing central store/inbox layout, preserving existing data. Git is optional.
3. **`/engram:adopt`** — Codex-only routing/setup, or explicit Claude backup → confirmation → global migration → disable auto-memory/merge routing, preserving native memory bodies.
4. **`/engram:init`, `remember`, `recall`, `triage`, `status`, `backup`.**
5. **Dogfood on Habeeto:** migrate the keepers as the first project tier; extract reusable KMP knowledge into `global/kmp/` as the first global domain.
