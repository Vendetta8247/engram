#!/usr/bin/env bash
# Engram SessionStart hook — reminds the agent the graph exists and flags an
# unprocessed capture inbox. Stays silent if Engram isn't set up yet.
set -uo pipefail

ROOT="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
if [ "${1:-}" = --project-context ]; then
  # The Codex adapter calls only this bounded routing helper. Do not recurse into
  # its host adapter or run settings, health checks, and the full memory header.
  if ! command -v jq >/dev/null 2>&1; then
    echo "Engram project routing requires jq." >&2
    exit 2
  fi
  INPUT="$(cat)"
else
if [ "${ENGRAM_HOST:-}" = "codex" ] || [ -n "${PLUGIN_ROOT:-}" ]; then
  exec bash "${ROOT}/scripts/engram-codex-hook.sh"
fi

CHECKPOINTS_ENABLED="$(bash "${ROOT}/scripts/engram-codex-hook.sh" --checkpoints-enabled)" || exit 2

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

GLOBAL="${ENGRAM_STORE_PATH:-${HOME}/Engram}"
INBOX="${GLOBAL}/inbox"

# Not set up yet → say nothing.
[ -f "${GLOBAL}/INDEX.md" ] || exit 0

if [ "$CHECKPOINTS_ENABLED" = true ]; then
  CHECKPOINT_POLICY="Keep a live procedure checkpoint separate from permanent topic notes."
else
  CHECKPOINT_POLICY="Automatic live checkpoints are disabled. Continue selective recall and durable fact capture."
fi
echo "🧠 Engram memory is active. Treat this project's tier as its operational encyclopedia and maintain it AUTOMATICALLY. Before non-trivial work, search this project first and read only the best routing notes before expanding as needed. Capture verified product and technical knowledge, decisions, runbooks, gotchas, and authoritative code pointers immediately. Notes are concept-scoped but must be precise, not vague: include paths/symbols, contracts, data flow, commands, constraints, edge cases, and sources where relevant. ${CHECKPOINT_POLICY} Stage unverified research under research/, then promote validated conclusions or discard it. Durable memory is the graph, never CLAUDE.md/MEMORY.md. See the 'using-the-graph' skill for the full contract."

if [ -d "$INBOX" ]; then
  n=$(find "$INBOX" -type f \( -name '*.md' -o -name '*.txt' \) 2>/dev/null | wc -l | tr -d ' ')
  if [ "${n:-0}" -gt 0 ]; then
    echo "📥 You have ${n} uncaptured thought(s) in the Engram inbox — run /engram:triage to file them into the graph."
  fi
fi
fi

# Resolve software and creative workspaces without requiring Git. An explicit
# name wins; otherwise prefer a selected workspace, repository root, then cwd.
normalize_directory() {
  if [ -d "$1" ]; then
    (cd -- "$1" 2>/dev/null && pwd -P)
  else
    case "$1" in
      /*) printf '%s\n' "${1%/}" ;;
      *) printf '%s/%s\n' "$PWD" "${1%/}" ;;
    esac
  fi
}

PROJECT_CWD="$(printf '%s' "$INPUT" | jq -r 'if (.cwd | type) == "string" then .cwd else empty end' 2>/dev/null)"
[ -n "$PROJECT_CWD" ] || PROJECT_CWD="$PWD"
PROJECT_WORKSPACE="$(printf '%s' "$INPUT" | jq -r 'if (.workspace_root | type) == "string" then .workspace_root else empty end' 2>/dev/null)"
PROJECT_STORE="$(normalize_directory "${ENGRAM_STORE_PATH:-${HOME}/Engram}")"
RAW_PROJECT="${ENGRAM_PROJECT_NAME:-}"
if [ -n "$PROJECT_WORKSPACE" ]; then
  PROJECT_ROOT="$(normalize_directory "$PROJECT_WORKSPACE")"
elif PROJECT_ROOT="$(git -C "$PROJECT_CWD" rev-parse --show-toplevel 2>/dev/null)"; then
  PROJECT_ROOT="$(normalize_directory "$PROJECT_ROOT")"
else
  PROJECT_ROOT="$(normalize_directory "$PROJECT_CWD")"
fi

if [ -z "$RAW_PROJECT" ]; then
  PROJECT_HOME="$(normalize_directory "$HOME")"
  PROJECT_DEFAULT_STORE="$(normalize_directory "${HOME}/Engram")"
  PROJECT_PLUGIN="$(normalize_directory "$ROOT")"
  # Projectless chats commonly start in home, the store, or an installed plugin
  # cache. A source checkout remains a valid project for Engram development.
  if [ "$PROJECT_ROOT" = / ] || [ "$PROJECT_ROOT" = "$PROJECT_HOME" ]; then
    PROJECT_ROOT=""
  elif [ ! -e "$ROOT/.git" ]; then
    case "${PROJECT_ROOT}/" in
      "${PROJECT_PLUGIN}/"*) PROJECT_ROOT="" ;;
    esac
  fi
  case "${PROJECT_ROOT}/" in
    "${PROJECT_STORE}/"*|"${PROJECT_DEFAULT_STORE}/"*) PROJECT_ROOT="" ;;
  esac
  [ -z "$PROJECT_ROOT" ] || RAW_PROJECT="$(basename "$PROJECT_ROOT")"
fi

# jq lowercases ASCII only. Match the portable adapter's Unicode casefold so
# Claude and Codex share one tier for names such as "Моє ВІДЕО" or "Straße".
# Keep ASCII routing usable on older shell-only installations without Python.
if printf '%s' "$RAW_PROJECT" | LC_ALL=C grep -q '[^ -~]'; then
  PROJECT_NORMALIZER='import re, sys; print(re.sub(r"[\W_]+", "-", sys.argv[1].casefold(), flags=re.UNICODE).strip("-"))'
  PROJECT_NORMALIZED=false
  if command -v uv >/dev/null 2>&1; then
    if PROJ="$(uv run --no-project --offline --python 3.12 python -c "$PROJECT_NORMALIZER" "$RAW_PROJECT" 2>/dev/null)"; then
      PROJECT_NORMALIZED=true
    fi
  fi
  if [ "$PROJECT_NORMALIZED" = false ] && command -v python3 >/dev/null 2>&1; then
    if PROJ="$(python3 -c "$PROJECT_NORMALIZER" "$RAW_PROJECT" 2>/dev/null)"; then
      PROJECT_NORMALIZED=true
    fi
  fi
  if [ "$PROJECT_NORMALIZED" = false ]; then
    echo "Engram Unicode project routing requires Python. Run setup to cache Python 3.12 before routing this project." >&2
    exit 2
  fi
else
  PROJ="$(jq -nr --arg name "$RAW_PROJECT" '$name | ascii_downcase | gsub("[^\\p{L}\\p{N}]+"; "-") | sub("^-"; "") | sub("-$"; "")')"
fi
if [ -n "$PROJ" ]; then
  PDIR="${PROJECT_STORE}/projects/${PROJ}"
  notes=0
  [ -d "$PDIR" ] && notes=$(find "$PDIR" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
  if [ "${notes:-0}" -eq 0 ]; then
    echo "🆕 Project '${PROJ}' has NO Engram knowledge base yet. OFFER ONCE (do NOT run unprompted) to build one with /engram:scan — it surveys project materials (software, video, or other creative work), source/asset references, workflows, decisions, and delivery requirements into ${PDIR}/. Ask the user first; if they decline, work normally and just capture durable facts ad hoc as you learn them."
  else
    echo "📁 Working in project '${PROJ}' (${notes} KB note(s) on file). Recall them before non-trivial work. Route new project-specific facts to ${PDIR}/; reusable knowledge to ${PROJECT_STORE}/global/<domain>/ (global/workflow/, global/tooling/, global/video/, ...). One store → cross-project recall is a single search."
  fi
fi
