---
name: scan
description: Scan the current project and build (or refresh) a COMPREHENSIVE Engram knowledge base for it — product/PM overview, systems, screens/surfaces, architecture, data model, technical details, conventions. Runs a documentation workflow (NOT a bug audit), then curates the results into projects/<name>/. This is the standard new-project onboarding flow.
when_to_use: When the current repo has no projects/<name>/ knowledge base yet (offer it — don't run unprompted), or the user asks to "scan / document / onboard this project", "build a knowledge base", "learn this codebase", "add project-manager / overview info". Also to refresh after big changes.
argument-hint: "[project-name]"
allowed-tools: Bash Read Glob Grep AskUserQuestion Agent Workflow Write Edit
---

# /engram:scan — build a comprehensive project knowledge base

Give future sessions a deep, queryable understanding of this project: what it **is** (product + business/PM layer), how every **system** works, what each **screen/surface** does, the **architecture**, the **data model**, plus conventions and gotchas. Output is a structured, cross-linked set of Engram notes under `~/Engram/projects/<name>/`.

This is the standard **new-project onboarding** flow. **Never scan unprompted — offer it and wait for a yes.**

## Phase 0 — Decide & consent
1. `<name>` = `$ARGUMENTS` or the current git repo's folder name (kebab-case).
2. Check existing coverage: list `~/Engram/projects/<name>/`.
   - **Has substantive notes** → this is a REFRESH. Confirm with the user what to (re)scan: whole project / one subsystem / only changed areas.
   - **Empty or absent** → first-time onboarding. **PROMPT the user** (AskUserQuestion) for TWO choices — do not proceed without a yes:
     - **Depth:** *Overview* (a note per feature/module), *Feature + architecture map* (≈25 notes), or *Exhaustive* (per-system + per-screen + per-module + component/data, 50+ notes).
     - **Engine:** *Single agent* (fast, cheap), *Multiple agents* (parallel, medium), or *Workflow* (the full Habeeto-style fan-out + completeness critic, most exhaustive) — see Phase 1. Recommend **Workflow** for an Exhaustive scan of a large established project; **Single/Multiple** for small projects or a quick pass.
3. Confirm Engram is set up (`~/Engram/INDEX.md` exists); if not, run `/engram:setup` inline first.

## Phase 1 — Document (this is documentation, NOT a defect audit)

This is a **project-manager-style scan**: it captures the product/PM layer (what it is, monetization, roadmap, external systems, team/process) on top of the technical layer (systems, screens, architecture, data model). All three engines below produce the **same output shape** — delimited `===ENGRAM-NOTE===` blocks across `product` / `systems` / `screens` / `architecture` — which feed Phase 2 identically. Pick the engine the user chose in Phase 0.

Every engine follows the same **survey → document → (review)** shape and the same note format:
```
===ENGRAM-NOTE===
folder: projects/<name>/systems
title: <title>
tags: a, b
---BODY---
<prose + "- [category] fact" observations + "- relation_type [[Other Note]]" relations>
===END-NOTE===
```
(Agents **return delimited markdown, NOT StructuredOutput** — a schema with a big "write a whole doc" field makes models emit prose instead of calling the tool and fail "without calling StructuredOutput." Delimited text is what they do naturally, lighter on tokens, immune to that failure. A small *inventory* schema is fine.)

### Engine A — Single agent (fast, cheap)
One subagent surveys the project and documents it in a single pass, returning all notes as delimited blocks. Best for small projects or a quick first pass. Bounded by one agent's context, so depth/breadth suffer on a large codebase — use Overview/Map depth here, not Exhaustive.

### Engine B — Multiple agents (parallel, medium — no Workflow tool)
Do a quick **inline survey** (or one survey Agent) to get the work-list, then spawn a **bounded set of parallel `Agent` calls** (≈3–8), one per area/cluster — e.g. *PM/product profile*, *systems*, *screens*, *architecture* (split further for bigger projects). Each returns delimited notes; reconcile + curate in Phase 2. Parallel and thorough without the full fan-out or the Workflow opt-in.

### Engine C — Workflow (the Habeeto-style full fan-out — most exhaustive)
Run a documentation **workflow** via the Workflow tool. Reference implementation: `${CLAUDE_PLUGIN_ROOT}/scripts/example-project-kb-workflow.js` (run it with `args: {projectRoot, projectName, depth, auditFile?}`). Shape:
- **Survey** (parallel barrier): a **PM/product profile** agent + an **inventory** agent (systems / screens / modules / dataModel, each with key files — the work-list).
- **Document** (fan-out, ONE agent per system/screen/module) → delimited notes.
- **Review** (completeness critic) → cross-checks produced titles vs the work-list + repo and drafts the missing notes (exhaustiveness safety net).
- **Resilience (learned the hard way):** run the fan-out in **sequential chunks of ~6** (not a 16-wide burst — a server-side rate-limit, "not your usage limit · Rate limited", kills agents mid-flight); **retry** the inventory + critic + any failed chunk-members; carry a **fallback work-list** so it proceeds even if the inventory agent is throttled.
- Choosing this engine **is** the user's opt-in to multi-agent orchestration.

**Adapt the vocabulary to the project type** (all engines). A web app has pages/routes/services; a backend has endpoints/jobs/schemas; a library has modules/public APIs; a CLI has commands. Don't force a mobile-app shape onto a non-mobile project. Tell agents to mine any prior audit/digest if present, but verify against current code, and write for a developer who has never seen the project.

## Phase 2 — Curate into Engram
1. **Parse** every text channel for `===ENGRAM-NOTE=== … ===END-NOTE===` blocks. **`html.unescape` first** (the workflow result is JSON-encoded, so `&` arrives as `&amp;`). Split each block into `folder` / `title` / `tags` header + body.
2. **Dedupe & drop thin duplicates** — when two notes cover the same topic, keep the longer/more-detailed one. `search` the store for each title; if a real note exists, edit/supersede in place rather than forking.
3. **Route & write** each note to its folder (`projects/<name>/product` | `systems` | `screens` | `architecture`, or `global/<domain>/`). Create subfolders. Write frontmatter (`title`, `type: note`, `tags`) + body; sanitize the filename (`/`→`-`, `:`→`-`).
4. **Reconcile cross-links.** Agents invent `[[Sibling Title]]` links that don't exactly match real titles. After writing, map each `[[link]]` to the nearest actual title (exact → normalized-exact → unique prefix match) and rewrite. **Gotcha:** `basic-memory reindex` *folds* long `title:` values across indented continuation lines in the frontmatter, so a naive `^title:` regex truncates them — parse the folded YAML scalar when collecting real titles. Leave genuinely non-existent targets dangling (harmless).
5. Seed/refresh `~/Engram/projects/<name>/INDEX.md` (title e.g. "`<Project> Knowledge Base`" so `- part_of [[…]]` links resolve) as a map-of-content linking the product/systems/screens/architecture notes.
Then `basic-memory reindex --project engram` and git-commit `~/Engram`.

## Phase 3 — Report
Summarize notes written by folder, the project INDEX, and one sample note. List any `missing` items the critic flagged but couldn't fully draft (follow-ups). Remind the user: the KB is markdown in git — browsable/editable in Obsidian, refreshable by re-running `/engram:scan`.
