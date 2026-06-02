#!/usr/bin/env bash
# engram-backup.sh — read-only snapshot of all Claude native memory before any
# Engram migration/replacement. NEVER modifies or deletes source files.
#
# Backs up:
#   - ~/.claude/CLAUDE.md                  (global instructions)
#   - ~/.claude/projects/*/memory/         (all project auto-memories + indexes)
#   - ~/.claude/projects/*/MEMORY.md       (any stray top-level indexes)
# Output:
#   ~/.engram/backups/<UTC-timestamp>/{tree copy, manifest.txt, backup.tar.gz}
#
# Usage: bash engram-backup.sh
set -euo pipefail

CLAUDE_DIR="${HOME}/.claude"
STAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
DEST="${HOME}/.engram/backups/${STAMP}"
mkdir -p "${DEST}/tree"

MANIFEST="${DEST}/manifest.txt"
echo "Engram native-memory backup" > "${MANIFEST}"
echo "Created (UTC): ${STAMP}" >> "${MANIFEST}"
echo "Source: ${CLAUDE_DIR}" >> "${MANIFEST}"
echo "----------------------------------------" >> "${MANIFEST}"

copied=0

copy_in() {
  # $1 = source path (file or dir), preserve relative structure under tree/
  local src="$1"
  [ -e "$src" ] || return 0
  local rel="${src#${CLAUDE_DIR}/}"
  local target="${DEST}/tree/${rel}"
  mkdir -p "$(dirname "$target")"
  cp -R "$src" "$target"
  if [ -d "$src" ]; then
    local n; n=$(find "$src" -type f | wc -l | tr -d ' ')
    echo "DIR   ${rel}  (${n} files)" >> "${MANIFEST}"
  else
    echo "FILE  ${rel}" >> "${MANIFEST}"
  fi
  copied=$((copied+1))
}

# 1. global CLAUDE.md + settings (so disabling native auto-memory is reversible)
copy_in "${CLAUDE_DIR}/CLAUDE.md"
copy_in "${CLAUDE_DIR}/settings.json"
copy_in "${CLAUDE_DIR}/settings.local.json"

# 2. every project's memory/ dir and any MEMORY.md
if [ -d "${CLAUDE_DIR}/projects" ]; then
  while IFS= read -r d; do copy_in "$d"; done < <(find "${CLAUDE_DIR}/projects" -maxdepth 2 -type d -name memory 2>/dev/null)
  while IFS= read -r f; do copy_in "$f"; done < <(find "${CLAUDE_DIR}/projects" -maxdepth 2 -type f -name "MEMORY.md" 2>/dev/null)
fi

echo "----------------------------------------" >> "${MANIFEST}"
echo "Entries backed up: ${copied}" >> "${MANIFEST}"

# tarball
( cd "${DEST}" && tar -czf backup.tar.gz tree manifest.txt )

echo "OK"
echo "Backup dir:  ${DEST}"
echo "Tarball:     ${DEST}/backup.tar.gz"
echo "Manifest:    ${MANIFEST}"
echo "Entries:     ${copied}"
echo ""
echo "Restore (full): rm -rf will NOT run automatically. To restore a file/dir,"
echo "  copy it back from ${DEST}/tree/<relative-path> into ~/.claude/"
