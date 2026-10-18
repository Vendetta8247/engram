#!/usr/bin/env bash
set -uo pipefail

ROOT="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
LABEL="com.yegor.engram.basic-memory"

CHECKPOINTS_ENABLED="$(bash "${ROOT}/scripts/engram-codex-hook.sh" --checkpoints-enabled)" || exit 2
echo "Automatic checkpoints: $CHECKPOINTS_ENABLED"

bash "$ROOT/scripts/engram-mcp-health.sh" --status
health_status=$?
echo
case "$(uname -s)" in
  Darwin)
    if launchctl print "gui/$(id -u)/${LABEL}" >/dev/null 2>&1; then
      echo "launchd: loaded ($LABEL)"
    else
      echo "launchd: NOT LOADED ($LABEL)"
    fi
    ;;
  Linux)
    if systemctl --user is-active --quiet engram-basic-memory.service 2>/dev/null; then
      echo "systemd: active (engram-basic-memory.service)"
    else
      echo "systemd: not active (engram-basic-memory.service)"
    fi
    ;;
  *)
    echo "service supervisor: unsupported platform"
    ;;
esac
if command -v lsof >/dev/null 2>&1; then
  listener_pid="$(lsof -tiTCP:18765 -sTCP:LISTEN 2>/dev/null | head -n 1)"
else
  listener_pid="unknown (lsof unavailable)"
fi
legacy_count="$(ps -axo command | awk '$0 ~ /uv tool uvx basic-memory mcp$/ {count++} END {print count+0}')"
echo "Shared HTTP listener PID: ${listener_pid:-none}"
echo "Legacy per-chat stdio clients: $legacy_count"
echo "Codex session history: $(du -sh "${CODEX_HOME:-${HOME}/.codex}/sessions" 2>/dev/null | awk '{print $1}')"
exit "$health_status"
