---
name: scan
description: Scan a software or creative project folder and build or refresh its Engram knowledge base — goals, brief, systems or production workflow, assets, delivery, technical details, and conventions. Runs a documentation workflow (NOT a bug audit), then curates the results into the project's Engram tier. This is the standard new-project onboarding flow.
allowed-tools: Bash Read Glob Grep AskUserQuestion Agent Workflow Write Edit
---

# /engram:scan — build a comprehensive project knowledge base

Build the project's operational encyclopedia: goals and product/creative brief, systems or production workflow, surfaces/storyboard, architecture or asset organization, integrations, runbooks, conventions, decisions, and gotchas. Notes must be specific enough that a future agent can work without reconstructing the project from old chats. Output is a structured, cross-linked set of Engram notes under `~/Engram/projects/<name>/`.

This is the standard **new-project onboarding** flow. **Never scan unprompted — offer it and wait for a yes.**

## Phase 0 — Decide & consent
1. Resolve `<name>` from an explicit project name in `$ARGUMENTS`, then selected workspace, Git root if present, then current folder (kebab-case), following [project workspaces](../using-the-graph/references/project-workspaces.md). Git is optional; do not treat Home, the Engram store, or plugin directory as a creative project.
2. Check existing coverage: list `~/Engram/projects/<name>/`.
   - **Has substantive notes** → this is a REFRESH. Confirm with the user what to (re)scan: whole project / one subsystem / only changed areas.
   - **Empty or absent** → first-time onboarding. **PROMPT the user** (AskUserQuestion) for TWO choices — do not proceed without a yes:
     - **Depth (= coverage breadth):** *Overview* (a note per major feature/module), *Map* (≈25 notes — features + architecture), or *Exhaustive* (per-system + per-screen + per-module + data — broadest coverage). Note length follows the concept: split distinct concerns, but retain all technical detail needed to act correctly.
     - **Engine:** *Single agent* (fast, cheap), *Multiple agents* (parallel, medium), or *Workflow* (the full fan-out + completeness critic, broadest coverage) — see Phase 1. Recommend **Workflow** for an Exhaustive scan of a large established project; **Single/Multiple** for small projects or a quick pass.
3. Confirm Engram is set up (`~/Engram/INDEX.md` exists); if not, run `/engram:setup` inline first.
4. **Seed from native memory only for an authorized Claude migration (if present).** Codex-only onboarding skips this step; do not inspect Claude memory merely because `.claude` exists. For a requested Claude migration, locate this project's backed-up native memory: `~/Engram/backups/<latest>/tree/projects/<encoded>/memory/`, where `<encoded>` is the project's absolute path with `/`→`-` (e.g. `/Users/you/Code/my-app` → `-Users-you-Code-my-app`). If found, read it FIRST and pass it into the documentation engine as prior facts (the workflow's `auditFile` arg, or just hand it to the agents) — it holds decisions/gotchas the code alone won't reveal. **Verify every claim against current code** before committing it, and write the current truth, never "native memory said …". This is the lazy half of migration: adopt backed it up, scan folds it in. If no backup exists, skip.

## Phase 1 — Document (this is documentation, NOT a defect audit)

This is a **project-manager-style scan**: it captures the product/PM layer (what it is, monetization, roadmap, external systems, team/process) on top of the technical layer (systems, screens, architecture, data model). All three engines below produce the **same output shape** — delimited `===ENGRAM-NOTE===` blocks across `product` / `systems` / `screens` / `architecture` (or creative `brief` / `production` / `assets` / `delivery`) — which feed Phase 2 identically. Pick the engine the user chose in Phase 0.

Every engine follows the same **survey → document → (review)** shape and the same note format:
```
===ENGRAM-NOTE===
folder: projects/<name>/systems
title: <title>
tags: a, b
---BODY---
<PRECISE: a clear summary, then "- [category] fact" observations + "- relation_type [[Other Note]]" relations. Include exact paths/symbols, contracts, schemas/data flow, commands, constraints, edge cases, failure modes, decisions+why, and sources/verification dates where relevant. Do not restate routine code; do not omit required detail merely to stay short.>
===END-NOTE===
```
(Agents **return delimited markdown, NOT StructuredOutput** — a schema with a big "write a whole doc" field makes models emit prose instead of calling the tool and fail "without calling StructuredOutput." Delimited text is what they do naturally, lighter on tokens, immune to that failure. A small *inventory* schema is fine.)

### Engine A — Single agent (fast, cheap)
One subagent surveys the project and documents it in a single pass, returning all notes as delimited blocks. Best for small projects or a quick first pass. Bounded by one agent's context, so depth/breadth suffer on a large codebase — use Overview/Map depth here, not Exhaustive.

### Engine B — Multiple agents (parallel, medium — no Workflow tool)
Do a quick **inline survey** (or one survey Agent) to get the work-list, then spawn a **bounded set of parallel `Agent` calls** (≈3–8), one per area/cluster — e.g. *PM/product profile*, *systems*, *screens*, *architecture*, or a video project's *brief*, *production*, *assets*, *delivery* (split further for bigger projects). Each returns delimited notes; reconcile + curate in Phase 2. Parallel and thorough without the full fan-out or the Workflow opt-in.

### Engine C — Workflow (the full fan-out — broadest coverage)
Run a documentation **workflow** via the Workflow tool. Reference implementation: `${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/example-project-kb-workflow.js` (run it with `args: {projectRoot, projectName, depth, auditFile?}`). Shape:
- **Survey** (parallel barrier): a **PM/product profile** agent + an **inventory** agent (systems / screens / modules / dataModel, each with key files — the work-list).
- **Document** (fan-out, ONE agent per system/screen/module) → delimited notes.
- **Review** (completeness critic) → cross-checks produced titles vs the work-list + repo and drafts the missing notes (exhaustiveness safety net).
- **Resilience (learned the hard way):** run the fan-out in **sequential chunks of ~6** (not a 16-wide burst — a server-side rate-limit, "not your usage limit · Rate limited", kills agents mid-flight); **retry** the inventory + critic + any failed chunk-members; carry a **fallback work-list** so it proceeds even if the inventory agent is throttled.
- Choosing this engine **is** the user's opt-in to multi-agent orchestration.

**Adapt the vocabulary and folders to the project type** (all engines). A web app has pages/routes/services; a backend has endpoints/jobs/schemas; a library has modules/public APIs; a CLI has commands. A video project has a brief, audience, style, storyboard, source assets, editing, audio, color, captions, export, delivery, and rights. Survey project files, briefs, timelines and export presets rather than assuming source code. Use `brief/`, `production/`, `assets/`, and `delivery/` as appropriate. Document paths/IDs and verified metadata; keep video/audio/source binaries in their original locations, never copy them into Engram. See [project workspaces](../using-the-graph/references/project-workspaces.md). Verify prior facts against current authoritative project material and write for a collaborator who has never seen the project. If Workflow is unavailable in Codex, use the chosen depth with available single/multiple agents; do not require a Claude-only tool.

## Phase 2 — Curate into Engram
1. **Parse** every text channel for `===ENGRAM-NOTE=== … ===END-NOTE===` blocks. **`html.unescape` first** (the workflow result is JSON-encoded, so `&` arrives as `&amp;`). Split each block into `folder` / `title` / `tags` header + body.
2. **Dedupe & merge** — when two notes cover the same topic, keep the clearer/more-accurate canonical note and merge every unique actionable fact. `search` the store for each title; if a real note exists, edit/supersede in place rather than forking.
3. **Route & write** each note to its folder (`projects/<name>/product` | `systems` | `screens` | `architecture` | `runbooks` (or creative `brief` | `production` | `assets` | `delivery`), or `global/<domain>/`). Create subfolders. Write frontmatter (`title`, `type: note`, `tags`) + body; sanitize the filename (`/`→`-`, `:`→`-`). Unverified findings go to temporary `projects/<name>/research/`, never into canonical notes as fact.
4. **Reconcile cross-links.** Agents invent `[[Sibling Title]]` links that don't exactly match real titles. After writing, map each `[[link]]` to the nearest actual title (exact → normalized-exact → unique prefix match) and rewrite. **Gotcha:** `basic-memory reindex` *folds* long `title:` values across indented continuation lines in the frontmatter, so a naive `^title:` regex truncates them — parse the folded YAML scalar when collecting real titles. Leave genuinely non-existent targets dangling (harmless).
5. Seed/refresh `~/Engram/projects/<name>/INDEX.md` (title e.g. "`<Project> Knowledge Base`" so `- part_of [[…]]` links resolve) as a map-of-content linking the project's actual topic folders and notes.
MCP note writes update the index. If direct Markdown writes need synchronization, use the supervised service startup sync and verify a bounded search finds a new note; never run unattended `basic-memory reindex` on 0.23.2 (it can fail to exit). Do not auto-commit `~/Engram`; use an explicit backup/snapshot only when requested.

## Phase 2.5 — Consolidate & make agent-readable (orchestrator pass)

After the notes are written, run ONE consolidation pass over the freshly-written `~/Engram/projects/<name>/` — a dedicated orchestrator/critic (inline for a small KB; a single `Agent` call or a Workflow stage for a large one). This is **not** the completeness critic (that hunts for *missing* coverage); this audits **what's actually on disk** for redundancy and form. The parallel doc agents can't see each other's output, so near-duplicates and drift are expected here — this pass cleans them up:

1. **Dedup & merge.** List every note in the folder; find pairs/clusters that cover the same entity or overlap heavily (parallel agents commonly emit two notes for one system). Merge each cluster into one: keep the clearest, fold in unique facts, supersede in place, delete the losers. `search`/`build_context` to confirm before deleting. End state: no two notes answer the same question.
2. **Operational specificity.** Every note must let a future Codex or Claude task understand and act on one concept. Require a clear summary, structured observations/relations, concrete file paths and symbols, interfaces/contracts, data flow, commands, constraints, edge cases, failure modes, and decisions+why where relevant. Cut marketing prose, routine code restatement, and empty framing—but never delete technical detail merely to make the note shorter. If a note is vague, it failed.
3. **Fix cross-links** broken by the merges/renames, then refresh the project `INDEX.md` to match what now exists.

MCP note writes update the index. If direct Markdown writes need synchronization, use the supervised service startup sync and verify a bounded search finds a new note; never run unattended `basic-memory reindex` on 0.23.2 (it can fail to exit). Do not auto-commit `~/Engram`; use an explicit backup/snapshot only when requested.

## Phase 3 — Report
Summarize notes written by folder, how many the consolidation pass merged/tightened, the project INDEX, and one sample note. List any `missing` items the critic flagged but couldn't fully draft (follow-ups). The KB is Markdown, browsable/editable in Obsidian and refreshable with `/engram:scan`; Git is optional.
