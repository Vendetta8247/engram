---
name: scan
description: Scan the current project and build (or refresh) a COMPREHENSIVE Engram knowledge base for it — product/PM overview, systems, screens/surfaces, architecture, data model, technical details, conventions. Runs a documentation workflow (NOT a bug audit), then curates the results into projects/<name>/. This is the standard new-project onboarding flow.
when_to_use: When the current repo has no projects/<name>/ knowledge base yet (offer it — don't run unprompted), or the user asks to "scan / document / onboard this project", "build a knowledge base", "learn this codebase", "add project-manager / overview info". Also to refresh after big changes.
argument-hint: "[project-name]"
allowed-tools: Bash Read Glob Grep AskUserQuestion Workflow Write Edit
---

# /engram:scan — build a comprehensive project knowledge base

Give future sessions a deep, queryable understanding of this project: what it **is** (product + business/PM layer), how every **system** works, what each **screen/surface** does, the **architecture**, the **data model**, plus conventions and gotchas. Output is a structured, cross-linked set of Engram notes under `~/Engram/projects/<name>/`.

This is the standard **new-project onboarding** flow. **Never scan unprompted — offer it and wait for a yes.**

## Phase 0 — Decide & consent
1. `<name>` = `$ARGUMENTS` or the current git repo's folder name (kebab-case).
2. Check existing coverage: list `~/Engram/projects/<name>/`.
   - **Has substantive notes** → this is a REFRESH. Confirm with the user what to (re)scan: whole project / one subsystem / only changed areas.
   - **Empty or absent** → first-time onboarding. **PROMPT the user** (AskUserQuestion): do they want a full scan, and at what depth — *Overview* (a note per feature/module), *Feature + architecture map* (≈25 notes), or *Exhaustive* (per-system + per-screen + per-module + component/data, 50+ notes). Do not proceed without a yes.
3. Confirm Engram is set up (`~/Engram/INDEX.md` exists); if not, run `/engram:setup` inline first.

## Phase 1 — Document via a workflow (this is documentation, NOT a defect audit)
Author and run a **documentation workflow** (the Workflow tool) tailored to THIS project. Reference implementation: `${CLAUDE_PLUGIN_ROOT}/scripts/example-project-kb-workflow.js`. The pattern:

- **Survey** (parallel barrier):
  - a **PM/product profile** agent → overview & elevator pitch, monetization/business model, release & versioning, external systems/infrastructure, roadmap + disabled/deferred work, team/process.
  - an **inventory** agent → enumerate the project's `systems`, `screens`/surfaces, `modules`, and `dataModel`, each with real key files. **This inventory is the work-list.**
- **Document** (fan-out, one agent per system/screen/module) → each agent **returns its note(s) as delimited markdown**, NOT StructuredOutput:
  ```
  ===ENGRAM-NOTE===
  folder: projects/<name>/systems
  title: <title>
  tags: a, b
  ---BODY---
  <prose + "- [category] fact" observations + "- relation_type [[Other Note]]" relations>
  ===END-NOTE===
  ```
  (A schema with a big "write a whole doc" field makes models emit prose *instead* of calling the tool and the agent fails "without calling StructuredOutput." Delimited text is what they do naturally, is lighter on tokens, and can't hit that failure. The inventory agent keeps a small schema — that's fine.)
- **Review** (completeness critic) → one agent cross-checks produced titles against the work-list + repo and **drafts the missing notes**. The exhaustiveness safety net.

**Resilience (learned the hard way).** Run the Document fan-out in **sequential chunks of ~6**, not one big 16-wide burst — a server-side rate-limit ("not your usage limit · Rate limited") will otherwise kill agents mid-flight. Wrap the inventory + critic in a **retry** helper, **retry** any failed doc chunk-members once, and pass a **fallback work-list** so documentation proceeds even if the inventory agent is throttled. Scale the fan-out to the chosen depth. Tell agents to mine any prior audit/digest if present, but verify against current code, and to write for a developer who has never seen the project.

**Adapt the vocabulary to the project type.** A web app has pages/routes/services; a backend has endpoints/jobs/schemas; a library has modules/public APIs; a CLI has commands. Don't force a mobile-app shape onto a non-mobile project.

## Phase 2 — Curate into Engram
1. **Parse** every text channel for `===ENGRAM-NOTE=== … ===END-NOTE===` blocks. **`html.unescape` first** (the workflow result is JSON-encoded, so `&` arrives as `&amp;`). Split each block into `folder` / `title` / `tags` header + body.
2. **Dedupe & drop thin duplicates** — when two notes cover the same topic, keep the longer/more-detailed one. `search` the store for each title; if a real note exists, edit/supersede in place rather than forking.
3. **Route & write** each note to its folder (`projects/<name>/product` | `systems` | `screens` | `architecture`, or `global/<domain>/`). Create subfolders. Write frontmatter (`title`, `type: note`, `tags`) + body; sanitize the filename (`/`→`-`, `:`→`-`).
4. **Reconcile cross-links.** Agents invent `[[Sibling Title]]` links that don't exactly match real titles. After writing, map each `[[link]]` to the nearest actual title (exact → normalized-exact → unique prefix match) and rewrite. **Gotcha:** `basic-memory reindex` *folds* long `title:` values across indented continuation lines in the frontmatter, so a naive `^title:` regex truncates them — parse the folded YAML scalar when collecting real titles. Leave genuinely non-existent targets dangling (harmless).
5. Seed/refresh `~/Engram/projects/<name>/INDEX.md` (title e.g. "`<Project> Knowledge Base`" so `- part_of [[…]]` links resolve) as a map-of-content linking the product/systems/screens/architecture notes.
Then `basic-memory reindex --project engram` and git-commit `~/Engram`.

## Phase 3 — Report
Summarize notes written by folder, the project INDEX, and one sample note. List any `missing` items the critic flagged but couldn't fully draft (follow-ups). Remind the user: the KB is markdown in git — browsable/editable in Obsidian, refreshable by re-running `/engram:scan`.
