---
name: revert
description: Undo /engram:adopt — restore Claude's native memory exactly as it was before adoption and step Engram aside. The "deinit" / go-back switch. Re-enables native auto-memory, un-thins the native files, removes the routing directive. The Engram graph is preserved (not deleted) unless you ask.
when_to_use: When the user wants to go back, undo Engram, disable it, restore native memory, deinit, or "remove Engram".
argument-hint: "[backup-timestamp]"
allowed-tools: Bash Read AskUserQuestion
---

# /engram:revert — restore native memory, step Engram aside (the undo of adopt)

This reverses everything `/engram:adopt` changed, using the pre-adoption backup adopt made. Safety-critical and confirm-gated.

## 1. Find the restore point
- List `~/.engram/backups/` (newest first). Use `$ARGUMENTS` if a timestamp was given; otherwise the **most recent** adopt backup. Each backup's `tree/` mirrors `~/.claude/` as it was pre-adoption (CLAUDE.md, settings.json(+local), every project `memory/`, MEMORY.md).
- If there is no backup (adopt was never run), say so and skip to step 5 (plugin removal) — there's nothing to restore.
- Read the chosen backup's `manifest.txt` and show the user exactly what will be restored, from which timestamp.

## 2. Confirm (hard stop)
- Spell out what reverting does: (a) restore `~/.claude/CLAUDE.md` (removes the Engram routing directive), (b) restore `settings.json`(+local) — **this re-enables native auto-memory** (`autoMemoryEnabled` returns to its pre-adopt value), (c) restore each project `memory/` + `MEMORY.md` (un-thins the pointer stubs back to full content), (d) leave the Engram graph at `~/.engram/` intact unless they ask to remove it.
- **Require explicit "yes"** before writing anything.

## 3. Restore from the backup
- Copy each file/dir from `~/.engram/backups/<stamp>/tree/<relpath>` back to `~/.claude/<relpath>`. This is the inverse of adopt; the backup is the source of truth.
- Belt-and-suspenders: the user also has the independent `~/Coding/claude-backup` — mention it as an alternate restore source if the adopt backup looks incomplete.

## 4. Verify
- Confirm `~/.claude/settings.json` no longer has `autoMemoryEnabled: false` (native memory live again), `~/.claude/CLAUDE.md` no longer contains the Engram routing block, and a project `MEMORY.md` shows restored content (not the thin pointer).

## 5. Step Engram aside / remove it
- **Default:** leave `~/.engram/` (the graph) on disk — harmless, and makes re-adopting trivial. Just tell the user native memory is back in charge and Engram is dormant.
- **Disable the plugin entirely** (stops the MCP, hooks, and commands): that's Claude Code's own `/plugin uninstall engram` (or remove `--plugin-dir` on next launch / disable in `/plugin`). Engram can't uninstall itself; tell the user the exact command.
- **Full wipe (only if the user explicitly asks):** after confirming, `rm -rf ~/.engram` removes the graph + backups too — irreversible, so require a second explicit yes and remind them `~/Coding/claude-backup` still holds their original native memory.

## 6. Report
- Summarize what was restored from which timestamp, that native auto-memory is re-enabled, whether the graph was preserved or wiped, and the `/plugin uninstall engram` command to fully remove Engram. Confirm they're back to exactly the pre-adopt state.
