---
name: adopt
description: Migrate off Claude's native memory into the Engram graph. Backs up EVERYTHING first, shows the manifest, and requires explicit confirmation before migrating or replacing anything. Then offers to build a full project-manager-style KB for the current codebase (single agent / multiple agents / workflow). Reversible.
argument-hint: ""
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent Workflow
---

# /engram:adopt — migrate native Claude memory into Engram (backup-first)

Go live on Engram: back up ALL native memory, migrate the **global** layer into the graph now, and switch the memory system over (disable native auto-memory + install the routing directive). Per-project native memory is backed up but migrated **lazily** — folded in by `/engram:scan` when you actually open a project — so adopt stays fast and cheap instead of reading every project up front. This is **two-phase and safety-critical**: back up + confirm, *then* act. Never skip a beat.

This is the single command to go fully live — it **self-bootstraps**, so the user does NOT need to run `/engram:setup` first.

## Phase 0 — ENSURE ENGRAM IS INSTALLED (self-bootstrap)

If `~/Engram/INDEX.md` does not exist yet (Engram not set up), run the `/engram:setup` steps inline first (install Basic Memory, register the single `engram` project at `~/Engram`, create the store layout + inbox + INDEX.md). If it already exists, skip — it's done. Only after the engine + store exist do you proceed to the backup. (`/engram:setup` still exists as a standalone, optional path for trying Engram *alongside* native memory before adopting — but adopt no longer requires it.)

## Phase 1 — BACK UP EVERYTHING (always, first, no exceptions)

1. Run the backup script: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/engram-backup.sh"`. It is **read-only** on the source — it copies `~/.claude/CLAUDE.md`, every `~/.claude/projects/*/memory/`, and any `MEMORY.md` into a timestamped `~/Engram/backups/<stamp>/` (tree + tarball + manifest).
2. Print the backup location and the manifest contents so the user sees exactly what was captured and where.

## Phase 2 — CONFIRM (hard stop)

3. Show the user the migration plan in plain terms:
   - **Only GLOBAL native memory is migrated now** (the global `CLAUDE.md` learnings) — it's small and always relevant.
   - **Per-project native memory is backed up but NOT read or migrated here.** Reading and curating every project up front is slow, token-heavy, and yields worse notes than building from the actual code. It stays safe in the backup and is folded in lazily, per project, when you `/engram:scan` that project (or never, if you don't open it).
   - that the native files are **left intact** (not gutted) — the switch is disabling native auto-memory + installing the routing directive, not replacing file bodies,
   - that everything is restorable from the backup just made.
4. **Ask for explicit confirmation** (AskUserQuestion or a direct yes/no). Do NOT proceed to Phase 3 without an unambiguous "yes". If the user hesitates, stop — the backup already exists and is harmless.

## Phase 3 — MIGRATE (only after "yes")

5. **Migrate GLOBAL native memory only.** Read the global `CLAUDE.md` learnings/memory. For each durable fact, route it with the **using-the-graph** rule: reusable → a domain folder under `~/Engram/global/` (`global/workflow/`, `global/kmp/`, …); derivable → drop, keep a pointer; stale/abandoned → skip. **Do NOT read or migrate the per-project `memory/` dirs here** — they're backed up and folded in lazily by `/engram:scan`, per project.
6. Write notes into the graph via the basic-memory MCP (`write_note` / `edit_note`), applying the typed-relation + observation conventions. Keep them **compact** (see using-the-graph — many small nodes, no prose dumps, no restated-from-code values). Dedupe: `search` before each write; update in place rather than forking. **Write the truth, not its history** — record the fact as it stands, never "native memory said X but actually Y." Note dropped/dead material in the migration summary rather than silently discarding.
7. **Leave the native memory files intact** — do NOT thin or replace their bodies. The per-project `memory/` dirs aren't in the graph yet (they're migrated later by `/engram:scan`), so gutting them would orphan live knowledge; the backup is the safety net and the files stay readable until each project is scanned. The switch is the next two steps, not file-editing.
8. **Disable native auto-memory so Engram is the sole memory system** (the decisive step — eliminates the competing write path rather than relying on prompting). Merge `"autoMemoryEnabled": false` into `~/.claude/settings.json` — READ the existing file, set just that key, preserve everything else (never clobber). This is backed up in Phase 1 and fully reversible (set it back to `true` or restore `settings.json` from the backup). Tell the user you did this and how to undo it.
9. **Install the global routing directive** so every future session — in any project — routes memory to Engram: append a short, clearly-marked block to `~/.claude/CLAUDE.md` (the always-loaded global instructions), e.g.:
   > ## Engram memory (installed by /engram:adopt)
   > Durable memory is the Engram knowledge graph (basic-memory MCP), not native memory. When asked to remember / note / save / keep in mind / don't forget anything → write it to Engram (right tier). When asked what's known/decided → query Engram. Native auto-memory is disabled.
   Merge, don't overwrite — preserve the user's existing global instructions.

## Phase 3.5 — POPULATE PROJECTS (lazy — the user picks scope)

Global memory is now in the graph. Per-project knowledge is built by **scanning the codebase** (and folding in that project's backed-up native memory), done on demand so you only pay for projects you actually use. This is the point of lazy migration: don't read everything up front.

**PROMPT the user** (AskUserQuestion) for the SCOPE — do not scan unprompted:

- **This project only** (recommended) — scan the current repo now.
- **None** — skip; each project fills in the first time you `/engram:scan` it. The SessionStart hook auto-offers a scan whenever you open a project with no KB, so nothing is lost.
- **All projects** — heavy, expensive opt-in. Iterate every backed-up project: decode its path from the backup dir name (e.g. `-Users-vendetta8247-Coding-Habito` → `/Users/vendetta8247/Coding/Habito`) and scan each. **Warn about the cost** (one full scan per project) before starting.

If they choose a scan (this / all), ALSO ask **depth** (Overview / Map / Exhaustive) and **engine** (Single agent / Multiple agents / Workflow), then run the **`/engram:scan` flow** with those choices for each project in scope. `/engram:scan` seeds from the project's native-memory backup first, then reads the code. Recommend **Workflow** for large projects; **Single/Multiple** for small ones. (Notes stay compact regardless of depth — depth controls coverage, not note size.)

If the current dir already has a KB (e.g. you adopted from inside an already-scanned project), don't re-offer *this* project — but you can still offer **All / None** for the rest.

## Phase 4 — REPORT

10. Summarize: **global** notes migrated (count), that per-project native memory is backed up and **deferred to `/engram:scan`** (not migrated here), native auto-memory now disabled, the global routing directive installed, which project(s) were scanned and their note counts, where the backup is, and the one-line restore instruction (copy back from `~/Engram/backups/<stamp>/tree/...`; re-enable native memory by restoring `settings.json` or setting `autoMemoryEnabled: true`).
11. Remind the user a future `/engram:restore <stamp>` (planned) will reverse all of this, and that the backup is the safety net until then.

Golden rule: if anything is unclear or the user is unsure, **stop after Phase 1**. A backup with no migration is a safe, valid outcome.
