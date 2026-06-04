#!/usr/bin/env bash
# engram-bmignore.sh — exclude backups/ and inbox/ from the basic-memory search
# index, portably (macOS + Linux). Idempotent: safe to run repeatedly.
#
# basic-memory reads .bmignore from its DATA DIR, resolved exactly as the library
# does (basic_memory/config.py resolve_data_dir):
#   1. $BASIC_MEMORY_CONFIG_DIR          (if set)         — explicit override
#   2. $XDG_CONFIG_HOME/basic-memory     (if XDG set)     — common on Linux
#   3. ~/.basic-memory                   (default)        — macOS + bare Linux
# A project-root .bmignore (e.g. ~/Engram/.bmignore) is NOT honored, so the file
# must live in that data dir. We mirror the library's resolution so it lands in
# the right place on every platform.
#
# Why exclude these: backups/ are point-in-time native-memory snapshots that would
# otherwise outrank real notes in recall; inbox/ is raw capture that /engram:triage
# reads from disk, not via search.
set -euo pipefail

if [ -n "${BASIC_MEMORY_CONFIG_DIR:-}" ]; then
  BM_DIR="${BASIC_MEMORY_CONFIG_DIR}"
elif [ -n "${XDG_CONFIG_HOME:-}" ]; then
  BM_DIR="${XDG_CONFIG_HOME}/basic-memory"
else
  BM_DIR="${HOME}/.basic-memory"
fi

mkdir -p "${BM_DIR}"
IGNORE="${BM_DIR}/.bmignore"
touch "${IGNORE}"

changed=0
ensure_line() {
  # add $1 as its own line only if that exact line isn't already present
  grep -qxF "$1" "${IGNORE}" 2>/dev/null || { printf '%s\n' "$1" >> "${IGNORE}"; changed=1; }
}
ensure_line "backups/"
ensure_line "inbox/"

echo "bmignore: ${IGNORE}"
if [ "${changed}" -eq 1 ]; then
  echo "  ensured backups/ + inbox/ — run 'basic-memory reindex --full --project engram' to prune any already-indexed entries"
else
  echo "  already configured — no change"
fi
