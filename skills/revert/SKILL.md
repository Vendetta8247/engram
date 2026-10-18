---
name: revert
description: Undo Engram adoption for the current client while preserving the graph. Codex-only adoption removes its marked routing block without touching Claude; an explicitly requested Claude restore uses the pre-adoption backup and confirmation.
allowed-tools: Bash Read Edit AskUserQuestion
---

# /engram:revert — undo adoption for the current client

## Codex-only adoption

Use this branch for Codex-only adoption unless the user explicitly requests a
Claude memory restore. A request to revert authorizes the bounded routing
cleanup below; the Claude backup/confirmation flow applies only to an actual
Claude restore.

1. Read `$CODEX_HOME/AGENTS.md` when configured, otherwise `~/.codex/AGENTS.md`.
   Back up the file before editing, then remove only the complete block bounded
   by `<!-- engram:start -->` and `<!-- engram:end -->`. Preserve all other
   instructions and formatting. If the markers are missing or malformed,
   report that no safely identifiable block was removed; do not guess which
   user-written memory instructions to delete.
2. Preserve the configured Markdown store, checkpoint notes/settings,
   runtime/database, and backups. Do not inspect or restore `.claude` files,
   change Claude settings, or require a Claude migration backup.
3. If disabling/removing the plugin or MCP connection is also requested, use
   Codex's plugin controls and edit only its `mcp_servers.engram` entry as
   applicable, preserving unrelated plugins/configuration. Do not give Claude's
   `/plugin uninstall` command for Codex. Keep the shared memory service running
   for other clients unless stopping that service was requested.
4. Verify that the marked routing block is gone and other global instructions
   remain. Report exactly which routing/plugin/MCP changes occurred and whether
   the plugin's hooks or MCP connection remain enabled. Removing the routing
   block alone does not disable those hooks. Restart Codex after client changes.
   Stop here; do not enter the Claude restore steps.

## Claude memory restore

This reverses a real Claude migration using its pre-adoption backup. The
explicit confirmation below remains required before restoring native files.

## 1. Find the restore point
- List `~/Engram/backups/` (newest first). Use `$ARGUMENTS` if a timestamp was given; otherwise the **most recent** adopt backup. Each backup's `tree/` mirrors `~/.claude/` as it was pre-adoption (CLAUDE.md, settings.json(+local), every project `memory/`, MEMORY.md).
- If there is no backup (adopt was never run), say so and skip to step 5 (plugin removal) — there's nothing to restore.
- Read the chosen backup's `manifest.txt` and show the user exactly what will be restored, from which timestamp.

## 2. Confirm (hard stop)
- Spell out what reverting does: (a) restore `~/.claude/CLAUDE.md` (removes the Engram routing directive), (b) restore `settings.json`(+local) — **this re-enables native auto-memory** (`autoMemoryEnabled` returns to its pre-adopt value), (c) restore each project `memory/` + `MEMORY.md` (un-thins the pointer stubs back to full content), (d) leave the Engram graph at `~/Engram/` intact unless they ask to remove it.
- **Require explicit "yes"** before writing anything.

## 3. Restore from the backup
- Copy each file/dir from `~/Engram/backups/<stamp>/tree/<relpath>` back to `~/.claude/<relpath>`. This is the inverse of adopt; the backup is the source of truth.
- Belt-and-suspenders: the user also has the independent `~/Coding/claude-backup` — mention it as an alternate restore source if the adopt backup looks incomplete.

## 4. Verify
- Confirm `~/.claude/settings.json` no longer has `autoMemoryEnabled: false` (native memory live again), `~/.claude/CLAUDE.md` no longer contains the Engram routing block, and a project `MEMORY.md` shows restored content (not the thin pointer).

## 5. Step Engram aside / remove it
- **Default:** leave `~/Engram/` (the graph) on disk — harmless, and makes re-adopting trivial. Just tell the user native memory is back in charge and Engram is dormant.
- **Disable the plugin entirely** (stops the MCP, hooks, and commands): that's Claude Code's own `/plugin uninstall engram` (or remove `--plugin-dir` on next launch / disable in `/plugin`). Engram can't uninstall itself; tell the user the exact command.
- **Full wipe (only if the user explicitly asks):** after confirming, `rm -rf ~/Engram` removes the graph + backups too — irreversible, so require a second explicit yes and remind them `~/Coding/claude-backup` still holds their original native memory.

## 6. Report
- Summarize what was restored from which timestamp, that native auto-memory is re-enabled, whether the graph was preserved or wiped, and the `/plugin uninstall engram` command to fully remove Engram. Confirm they're back to exactly the pre-adopt state.
