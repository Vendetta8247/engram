#!/usr/bin/env bash
# Codex records a dirty recovery revision before tool execution. Claude retains
# its existing capture conventions; this adapter does not intercept its tools.
set -uo pipefail
ROOT="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
if [ "${ENGRAM_HOST:-}" = codex ] || [ -n "${PLUGIN_ROOT:-}" ]; then
  exec bash "$ROOT/scripts/engram-codex-hook.sh"
fi
printf '%s\n' '{}'
