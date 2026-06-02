---
name: backup
description: Snapshot Engram + native Claude memory to a timestamped, restorable backup.
argument-hint: ""
allowed-tools: Bash
---

# /engram:backup — snapshot everything

1. Run the native-memory backup script (read-only): `bash "${CLAUDE_PLUGIN_ROOT}/scripts/engram-backup.sh"`.
2. Also snapshot the Engram graph itself: if `~/Engram` is a git repo, `git -C ~/Engram add -A && git -C ~/Engram commit -m "engram backup <UTC stamp>"` (skip if nothing changed). Otherwise tar `~/Engram` into the same backup dir.
3. Report the backup location, manifest, and restore instructions.

This is the manual equivalent of the snapshot `/engram:adopt` takes automatically before migrating.
