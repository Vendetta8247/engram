#!/usr/bin/env bash
# Engram PreCompact hook — fires before the context window is compacted. Last
# chance to persist anything durable from this session before it's summarized
# away. Silent if Engram isn't set up.
set -uo pipefail

ROOT="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
if [ "${ENGRAM_HOST:-}" = "codex" ] || [ -n "${PLUGIN_ROOT:-}" ]; then
  exec bash "${ROOT}/scripts/engram-codex-hook.sh"
fi

CHECKPOINTS_ENABLED="$(bash "${ROOT}/scripts/engram-codex-hook.sh" --checkpoints-enabled)" || exit 2

INPUT="$(cat)"
SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)"
HEALTH_JSON="$(bash "${ROOT}/scripts/engram-mcp-health.sh" --hook PreCompact "$SESSION_ID" claude 2>/dev/null)"
HEALTHY="$(printf '%s' "$HEALTH_JSON" | jq -r '.healthy // false' 2>/dev/null)"
HEALTH_NOTIFY="$(printf '%s' "$HEALTH_JSON" | jq -r 'if has("notify") then .notify else true end' 2>/dev/null)"
HEALTH_MESSAGE="$(printf '%s' "$HEALTH_JSON" | jq -r '.message // empty' 2>/dev/null)"

if [ "$HEALTHY" != "true" ]; then
  echo "⚠️ ${HEALTH_MESSAGE:-ENGRAM UNAVAILABLE. Durable capture and history consolidation are unsafe; recover the shared MCP service.}"
  exit 0
elif [ "$HEALTH_NOTIFY" = "true" ] && [ -n "$HEALTH_MESSAGE" ]; then
  echo "$HEALTH_MESSAGE"
fi

[ -f "${HOME}/Engram/INDEX.md" ] || exit 0
if [ "$CHECKPOINTS_ENABLED" = true ]; then
  CHECKPOINT_POLICY="Engram checkpoint (pre-compaction): update the small live procedure checkpoint, then sweep"
else
  CHECKPOINT_POLICY="Engram memory review (automatic checkpoints disabled): sweep"
fi
echo "🧠 ${CHECKPOINT_POLICY} for verified project knowledge not yet in the permanent encyclopedia — product behavior, technical contracts/data flow, authoritative paths, commands, decisions+why, gotchas, runbooks, and reusable patterns. Write precise canonical notes via the basic-memory MCP (dedupe and update in place). Keep unverified research temporary; promote validated conclusions out of research/. Never paste the transcript."
