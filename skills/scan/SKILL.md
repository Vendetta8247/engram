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
- **Document** (fan-out, one agent per system/screen/module) → comprehensive note specs: what it is (for product AND devs), end-to-end flow, key files with paths, data it touches, important flows + edge cases, conventions/gotchas, current status. Each agent returns NOTE specs: `{title, folder, tags, markdownBody, relatesTo}` where `markdownBody` mixes readable prose with basic-memory lines — observations `- [category] fact` and relations `- relation_type [[Other Note]]`.
- **Review** (completeness critic) → one agent cross-checks produced titles against the work-list + repo and **drafts the missing notes**. The exhaustiveness safety net.

Scale the fan-out to the chosen depth. Tell agents to mine any prior audit/digest if present, but verify against current code, and to write for a developer who has never seen the project.

**Adapt the vocabulary to the project type.** A web app has pages/routes/services; a backend has endpoints/jobs/schemas; a library has modules/public APIs; a CLI has commands. Don't force a mobile-app shape onto a non-mobile project.

## Phase 2 — Curate into Engram
For every returned note spec:
- **Route** to its folder: `projects/<name>/product` | `systems` | `screens` | `architecture`, or `global/<domain>/` for genuinely reusable patterns. Create subfolders as needed.
- **Dedupe**: `search` for the title; if a note exists, edit/supersede in place — never fork a duplicate.
- **Write** the file: frontmatter (`title`, `type: note`, `tags`) + the `markdownBody`. Keep the observation/relation grammar intact so the graph connects.
- Seed/refresh `~/Engram/projects/<name>/INDEX.md` as a map-of-content linking the product/systems/screens/architecture notes, with `- part_of [[INDEX]]` up to the root index.
Then `basic-memory reindex --project engram` and git-commit `~/Engram`.

## Phase 3 — Report
Summarize notes written by folder, the project INDEX, and one sample note. List any `missing` items the critic flagged but couldn't fully draft (follow-ups). Remind the user: the KB is markdown in git — browsable/editable in Obsidian, refreshable by re-running `/engram:scan`.
