#!/usr/bin/env bash
# Engram SessionStart hook — reminds the agent the graph exists and flags an
# unprocessed capture inbox. Stays silent if Engram isn't set up yet.
set -uo pipefail

ROOT="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
if [ "${ENGRAM_HOST:-}" = "codex" ] || [ -n "${PLUGIN_ROOT:-}" ]; then
  exec bash "${ROOT}/scripts/engram-codex-hook.sh"
fi

INPUT="$(cat)"
SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)"
HEALTH_JSON="$(bash "${ROOT}/scripts/engram-mcp-health.sh" --hook SessionStart "$SESSION_ID" claude 2>/dev/null)"
HEALTHY="$(printf '%s' "$HEALTH_JSON" | jq -r '.healthy // false' 2>/dev/null)"
HEALTH_NOTIFY="$(printf '%s' "$HEALTH_JSON" | jq -r 'if has("notify") then .notify else true end' 2>/dev/null)"
HEALTH_MESSAGE="$(printf '%s' "$HEALTH_JSON" | jq -r '.message // empty' 2>/dev/null)"

if [ "$HEALTHY" != "true" ]; then
  [ -n "$HEALTH_MESSAGE" ] && echo "⚠️ $HEALTH_MESSAGE"
elif [ "$HEALTH_NOTIFY" = "true" ] && [ -n "$HEALTH_MESSAGE" ]; then
  echo "$HEALTH_MESSAGE"
fi

GLOBAL="${HOME}/Engram"
INBOX="${HOME}/Engram/inbox"

# Not set up yet → say nothing.
[ -f "${HOME}/Engram/INDEX.md" ] || exit 0

echo "🧠 Engram memory is active. Treat this project's tier as its operational encyclopedia and maintain it AUTOMATICALLY. Before non-trivial work, search this project first and read only the best routing notes before expanding as needed. Capture verified product and technical knowledge, decisions, runbooks, gotchas, and authoritative code pointers immediately. Notes are concept-scoped but must be precise, not vague: include paths/symbols, contracts, data flow, commands, constraints, edge cases, and sources where relevant. Keep a live procedure checkpoint separate from permanent topic notes. Stage unverified research under research/, then promote validated conclusions or discard it. Durable memory is the graph, never CLAUDE.md/MEMORY.md. See the 'using-the-graph' skill for the full contract."

if [ -d "$INBOX" ]; then
  n=$(find "$INBOX" -type f \( -name '*.md' -o -name '*.txt' \) 2>/dev/null | wc -l | tr -d ' ')
  if [ "${n:-0}" -gt 0 ]; then
    echo "📥 You have ${n} uncaptured thought(s) in the Engram inbox — run /engram:triage to file them into the graph."
  fi
fi

# Route signal: everything lives in the ONE ~/Engram store, split into two
# buckets — global/<domain>/ for reusable knowledge, projects/<name>/ per project.
# Also: if this project has NO knowledge base yet, prompt the agent to OFFER a scan.
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
  # kebab-case the repo folder name so the path matches the skills' convention
  # (lowercase + spaces/underscores → hyphens) — avoids a forked projects/ folder
  # on case-sensitive filesystems and keeps permalinks consistent.
  PROJ="$(basename "$ROOT" 2>/dev/null | tr '[:upper:]' '[:lower:]' | tr ' _' '--')"
  if [ -n "$PROJ" ]; then
    PDIR="${HOME}/Engram/projects/${PROJ}"
    notes=0
    [ -d "$PDIR" ] && notes=$(find "$PDIR" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    if [ "${notes:-0}" -eq 0 ]; then
      echo "🆕 Project '${PROJ}' has NO Engram knowledge base yet. OFFER ONCE (do NOT run unprompted) to build one with /engram:scan — it surveys the project and captures a comprehensive KB (product/PM overview, systems, screens, architecture, technical details) into ~/Engram/projects/${PROJ}/. Ask the user first; if they decline, work normally and just capture durable facts ad hoc as you learn them."
    else
      echo "📁 Working in project '${PROJ}' (${notes} KB note(s) on file). Recall them before non-trivial work. Route new project-specific facts to ~/Engram/projects/${PROJ}/; reusable knowledge to ~/Engram/global/<domain>/ (global/workflow/, global/kmp/, global/ios/, ...). One store → cross-project recall is a single search."
    fi
  fi
fi
