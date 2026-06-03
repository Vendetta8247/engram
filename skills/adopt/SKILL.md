---
name: adopt
description: Migrate off Claude's native memory into the Engram graph. Backs up EVERYTHING first, shows the manifest, and requires explicit confirmation before migrating or replacing anything. Then offers to build a full project-manager-style KB for the current codebase (single agent / multiple agents / workflow). Reversible.
argument-hint: ""
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent Workflow
---

# /engram:adopt — migrate native Claude memory into Engram (backup-first)

Move the user's existing Claude memory into the Engram graph and reduce the native files to thin pointers. This is **two-phase and safety-critical**: back up + confirm, *then* act. Never skip a beat.

This is the single command to go fully live — it **self-bootstraps**, so the user does NOT need to run `/engram:setup` first.

## Phase 0 — ENSURE ENGRAM IS INSTALLED (self-bootstrap)

If `~/Engram/INDEX.md` does not exist yet (Engram not set up), run the `/engram:setup` steps inline first (install Basic Memory, register the single `engram` project at `~/Engram`, create the store layout + inbox + INDEX.md). If it already exists, skip — it's done. Only after the engine + store exist do you proceed to the backup. (`/engram:setup` still exists as a standalone, optional path for trying Engram *alongside* native memory before adopting — but adopt no longer requires it.)

## Phase 1 — BACK UP EVERYTHING (always, first, no exceptions)

1. Run the backup script: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/engram-backup.sh"`. It is **read-only** on the source — it copies `~/.claude/CLAUDE.md`, every `~/.claude/projects/*/memory/`, and any `MEMORY.md` into a timestamped `~/Engram/backups/<stamp>/` (tree + tarball + manifest).
2. Print the backup location and the manifest contents so the user sees exactly what was captured and where.

## Phase 2 — CONFIRM (hard stop)

3. Show the user the migration plan in plain terms:
   - which native stores will be read (global `CLAUDE.md`, each project `memory/`),
   - that durable facts will be written into the Engram graph (global vs project),
   - that the native `MEMORY.md`/`CLAUDE.md` **bodies will be replaced with short pointers** to Engram,
   - that everything is restorable from the backup just made.
4. **Ask for explicit confirmation** (AskUserQuestion or a direct yes/no). Do NOT proceed to Phase 3 without an unambiguous "yes". If the user hesitates, stop — the backup already exists and is harmless.

## Phase 3 — MIGRATE (only after "yes")

5. For each source memory note, decide where it goes using the **using-the-graph** routing rule: reusable → a domain folder under `~/Engram/global/` (`global/workflow/`, `global/kmp/`, …); specific to one project → `~/Engram/projects/<name>/` (derive `<name>` from which project the native note came from — e.g. the Habito memory dir → `projects/habito/`); derivable → drop, keep a pointer; stale/abandoned → skip or archive. Apply the typed-relation + observation conventions when writing.
6. Write notes into the graph via the basic-memory MCP (`write_note` / `edit_note`). Dedupe: `search` before each write; update in place rather than forking. Preserve genuinely useful content (code anchors, gotchas, runbooks); drop restated-from-code values and dead/abandoned material (note it in the migration summary rather than silently dropping).
7. Once a store's content is safely in the graph, **thin the native file**: replace the body of `MEMORY.md` (and, if the user agrees, the project `CLAUDE.md` memory sections) with a short pointer, e.g.:
   > Durable memory now lives in the **Engram** knowledge graph (basic-memory MCP). Consult it for project + global knowledge; write learnings there, not here. ALL "remember/note/save" requests route to Engram, never native memory. See the `using-the-graph` skill. Pre-migration backup: `~/Engram/backups/<stamp>/`.
   Do not delete the native files — just thin them.
8. **Disable native auto-memory so Engram is the sole memory system** (the decisive step — eliminates the competing write path rather than relying on prompting). Merge `"autoMemoryEnabled": false` into `~/.claude/settings.json` — READ the existing file, set just that key, preserve everything else (never clobber). This is backed up in Phase 1 and fully reversible (set it back to `true` or restore `settings.json` from the backup). Tell the user you did this and how to undo it.
9. **Install the global routing directive** so every future session — in any project — routes memory to Engram: append a short, clearly-marked block to `~/.claude/CLAUDE.md` (the always-loaded global instructions), e.g.:
   > ## Engram memory (installed by /engram:adopt)
   > Durable memory is the Engram knowledge graph (basic-memory MCP), not native memory. When asked to remember / note / save / keep in mind / don't forget anything → write it to Engram (right tier). When asked what's known/decided → query Engram. Native auto-memory is disabled.
   Merge, don't overwrite — preserve the user's existing global instructions.

## Phase 3.5 — OFFER A PROJECT SCAN (if in an established codebase)

Migrating native memory above moves *remembered facts* into Engram. This step is different: it documents the **current codebase itself**. After the migration, look at the working directory:

- `<name>` = the current git repo's folder (kebab-case).
- If it's an **established codebase** (real source, not an empty/throwaway dir) AND `~/Engram/projects/<name>/` has no substantive KB yet → **PROMPT the user** (AskUserQuestion): build a full **project-manager-style knowledge base** for this project now, as part of going live? — the same comprehensive scan Habeeto got (product/PM overview + systems + screens + architecture + data model), not a bug audit.
  - If **yes**: ask for **depth** (Overview / Map / Exhaustive) and **engine** (Single agent / Multiple agents / Workflow), then run the **`/engram:scan` Phase 1 → Phase 2** flow with those choices. Recommend **Workflow + Exhaustive** for a large established project; Single/Multiple for small ones.
  - If **skip**: fine — the project folder auto-fills as you work, or they can run `/engram:scan` anytime.
- **Never scan unprompted** — always offer. (If the current dir already has a KB — e.g. you adopted from inside Habeeto — skip the offer; it's already scanned.)

## Phase 4 — REPORT

10. Summarize: notes migrated to global vs project, what was dropped and why, native auto-memory now disabled, the global routing directive installed, whether a project scan was run (and its note count), where the backup is, and the one-line restore instruction (copy back from `~/Engram/backups/<stamp>/tree/...`; re-enable native memory by restoring `settings.json` or setting `autoMemoryEnabled: true`).
11. Remind the user a future `/engram:restore <stamp>` (planned) will reverse all of this, and that the backup is the safety net until then.

Golden rule: if anything is unclear or the user is unsure, **stop after Phase 1**. A backup with no migration is a safe, valid outcome.
