#!/usr/bin/env bash
# Claude keeps its existing behavior; Codex gets the checkpoint/size guard.
set -uo pipefail

ROOT="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
if [ "${ENGRAM_HOST:-}" = "codex" ] || [ -n "${PLUGIN_ROOT:-}" ]; then
  exec bash "${ROOT}/scripts/engram-codex-hook.sh"
fi

echo '{}'
