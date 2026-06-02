---
name: adopt
description: Migrate off Claude's native memory into the Engram graph. Backs up EVERYTHING first, shows the manifest, and requires explicit confirmation before migrating or replacing anything. Reversible.
argument-hint: ""
allowed-tools: Bash Read Edit Write AskUserQuestion
---

# /engram:adopt — migrate native Claude memory into Engram (backup-first)

Move the user's existing Claude memory into the Engram graph and reduce the native files to thin pointers. This is **two-phase and safety-critical**: back up + confirm, *then* act. Never skip a beat.

Precondition: `/engram:setup` has run (the global brain + basic-memory MCP exist). If `~/.engram/global` is missing, stop and tell the user to run `/engram:setup` first.

## Phase 1 — BACK UP EVERYTHING (always, first, no exceptions)

1. Run the backup script: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/engram-backup.sh"`. It is **read-only** on the source — it copies `~/.claude/CLAUDE.md`, every `~/.claude/projects/*/memory/`, and any `MEMORY.md` into a timestamped `~/.engram/backups/<stamp>/` (tree + tarball + manifest).
2. Print the backup location and the manifest contents so the user sees exactly what was captured and where.

## Phase 2 — CONFIRM (hard stop)

3. Show the user the migration plan in plain terms:
   - which native stores will be read (global `CLAUDE.md`, each project `memory/`),
   - that durable facts will be written into the Engram graph (global vs project),
   - that the native `MEMORY.md`/`CLAUDE.md` **bodies will be replaced with short pointers** to Engram,
   - that everything is restorable from the backup just made.
4. **Ask for explicit confirmation** (AskUserQuestion or a direct yes/no). Do NOT proceed to Phase 3 without an unambiguous "yes". If the user hesitates, stop — the backup already exists and is harmless.

## Phase 3 — MIGRATE (only after "yes")

5. For each source memory note, decide its tier using the **using-the-graph** skill's routing rule (reusable → global; project-specific → that repo's project brain; derivable → drop, keep a pointer; stale/abandoned → skip or archive). Apply the typed-relation + observation conventions when writing.
6. Write notes into the graph via the basic-memory MCP (`write_note` / `edit_note`). Dedupe: `search` before each write; update in place rather than forking. Preserve genuinely useful content (code anchors, gotchas, runbooks); drop restated-from-code values and dead/abandoned material (note it in the migration summary rather than silently dropping).
7. Once a store's content is safely in the graph, **thin the native file**: replace the body of `MEMORY.md` (and, if the user agrees, the project `CLAUDE.md` memory sections) with a short pointer, e.g.:
   > Durable memory now lives in the **Engram** knowledge graph (basic-memory MCP). Consult it for project + global knowledge; write learnings there, not here. See the `using-the-graph` skill. Pre-migration backup: `~/.engram/backups/<stamp>/`.
   Do not delete the native files — just thin them.

## Phase 4 — REPORT

8. Summarize: how many notes migrated to global vs project, what was dropped and why, where the backup is, and the one-line restore instruction (copy back from `~/.engram/backups/<stamp>/tree/...`).
9. Remind the user a future `/engram:restore <stamp>` (planned) will reverse this, and that the backup is the safety net until then.

Golden rule: if anything is unclear or the user is unsure, **stop after Phase 1**. A backup with no migration is a safe, valid outcome.
