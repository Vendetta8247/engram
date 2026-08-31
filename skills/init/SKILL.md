---
name: init
description: OPTIONAL — pre-create the current project's folder in the Engram store. Normally automatic — the agent creates the named directory under ~/Engram/projects/ the first time it stores project knowledge, so you rarely run this. Use it to set a project up deliberately (e.g. seed its index) ahead of time.
allowed-tools: Bash Read Write
---

# /engram:init — pre-create this project's folder in the store

Engram is ONE store at `~/Engram`. A project's facts live in `~/Engram/projects/<name>/` — there are no per-repo `.engram` folders, no separate Basic Memory project, and no `.mcp.json` pin. This command just sets up that subfolder deliberately; normally it happens automatically on first project capture.

Precondition: `~/Engram/INDEX.md` exists (Engram is set up). If not, run `/engram:adopt` (or `/engram:setup`) first.

1. Determine the project name: use `$ARGUMENTS` if given, else the current git repo's folder name (kebab-cased).
2. Create `~/Engram/projects/<name>/` (only if absent).
3. Seed `~/Engram/projects/<name>/INDEX.md` — a one-line map-of-content: `- part_of [[INDEX]]` linking up to the global index, plus a title line.
4. Tell the user: project-specific facts (config, IDs, this app's internals) now land in `~/Engram/projects/<name>/`, and should `- applies_to [[...]]` the reusable notes under `~/Engram/global/` rather than restating them. No repo files are created — it's all in the central store, so it's searchable alongside every other project.

> `init` only creates an empty folder. To populate a comprehensive knowledge base up front (product/PM overview, systems, screens, architecture), use **`/engram:scan`** instead — it surveys the project and writes the whole KB in one pass.
