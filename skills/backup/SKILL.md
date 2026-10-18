---
name: backup
description: Create a timestamped, restorable snapshot of Engram Markdown and settings; include native Claude memory only when explicitly requested or part of a Claude migration.
allowed-tools: Bash Read Write
---

# /engram:backup — snapshot memory

1. Resolve the configured store (default `~/Engram`) and use the Python
   standard-library procedure in [portable backups](../using-the-graph/references/portable-backups.md).
   It works on native Windows, macOS and Linux with uv, excludes previous backups
   and Git internals, and emits a copied tree, ZIP and SHA-256 manifest. No Git
   repository is needed and no commits are created.
2. Include Claude native memory only for an explicit request or authorized Claude
   migration. On macOS/Linux the existing read-only native backup helper is also
   available: `bash "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/engram-backup.sh"`.
   Codex-only users do not need Claude or that Bash helper.
3. Verify the archive and manifest, then report the snapshot location and precise
   restore paths. Preserve failed/partial output for inspection and report the
   failure. This is a note/config snapshot; runtime upgrades must use consistent
   SQLite database backups through the installer.
