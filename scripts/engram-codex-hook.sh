#!/usr/bin/env bash
# Codex lifecycle adapter for Engram.
#
# This deliberately stores no transcript content. It watches Codex's persisted
# rollout sizes, injects bounded recall instructions, requires compact Engram
# checkpoints as a task grows, and blocks unchecked growth at hard limits.
set -uo pipefail

ROOT="${PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
RECOVERY_COMMAND="$(sh "$ROOT/scripts/engram-recovery-command.sh" 2>/dev/null || true)"
RECOVERY_COMMAND="${RECOVERY_COMMAND:-restart the configured Engram shared MCP service}"

ACTION="${1:-hook}"
case "$ACTION" in
  --status|--rebaseline-after-cleanup|--checkpoints-enabled) INPUT='{}' ;;
  *) INPUT="$(cat)" ;;
esac

# Codex uses the same verified per-chat recovery path on every platform. Keep
# shell-only status/settings helpers for existing integrations, but do not run
# the old size-bucket acknowledgement path when the portable runtime is present.
if [ "$ACTION" = hook ]; then
  event="$(printf '%s' "$INPUT" | jq -r '.hook_event_name // empty' 2>/dev/null)"
  recovery_command="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // .tool_input.cmd // empty' 2>/dev/null)"
  if [ "$event" = PreToolUse ] && [ "$recovery_command" = 'uv python install 3.12' ]; then
    printf '%s\n' '{}'
    exit 0
  fi
  if [ -f "$ROOT/scripts/engram_portable.py" ] && command -v uv >/dev/null 2>&1; then
    runtime_output="$(printf '%s' "$INPUT" | uv run --no-project --offline --python 3.12 python "$ROOT/scripts/engram_portable.py" hook)"
    runtime_status=$?
    if [ "$runtime_status" -eq 0 ]; then
      printf '%s\n' "$runtime_output"
      exit 0
    fi
  fi
  # Failed interpreter startup must not silently permit checkpoint-dependent
  # compaction. Normal sessions remain usable to repair the installation.
  event="$(printf '%s' "$INPUT" | jq -r '.hook_event_name // empty' 2>/dev/null)"
  fallback_checkpoints="$(bash "$ROOT/scripts/engram-codex-hook.sh" --checkpoints-enabled 2>/dev/null)" || fallback_checkpoints=true
  if [ ! -d "${ENGRAM_CODEX_STATE_DIR:-${CODEX_HOME:-$HOME/.codex}/engram}/continuity" ] && [ ! -f "${ENGRAM_STORE_PATH:-$HOME/Engram}/INDEX.md" ]; then
    case "$event" in
      SessionStart|UserPromptSubmit|PreToolUse)
        printf '%s\n' '{"systemMessage":"Engram setup is incomplete. Install its cached Python 3.12 runtime and shared memory service before relying on progress checkpoints."}'
        exit 0
        ;;
    esac
  fi
  if [ "$event" = PreToolUse ] && [ "$fallback_checkpoints" != false ]; then
    printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Engram could not record recovery state before this tool. Repair the cached Python 3.12 runtime."},"systemMessage":"Chat progress protection could not be verified."}'
  elif [ "$event" = PreCompact ] && [ "$fallback_checkpoints" != false ]; then
    printf '%s\n' '{"continue":false,"stopReason":"Engram could not run its recovery checker. Preserve native context and repair the Python runtime before compaction.","systemMessage":"Run Engram setup to restore the cached Python 3.12 runtime; progress protection was not verified."}'
  elif [ "$fallback_checkpoints" != false ]; then
    printf '%s\n' '{"continue":false,"stopReason":"Engram could not verify chat recovery because its runtime failed.","systemMessage":"Progress was not confirmed in Engram. Preserve native history and repair the cached Python 3.12 runtime."}'
  else
    printf '%s\n' '{"continue":true,"systemMessage":"Engram could not run its verified checkpoint checker. Preserve native chat history and repair the cached Python 3.12 runtime; no durable save was confirmed.","suppressOutput":false}'
  fi
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  if [ "$ACTION" = "--checkpoints-enabled" ]; then
    echo "Engram settings: jq is required to read checkpoint settings." >&2
    exit 2
  fi
  [ "$ACTION" = "--status" ] && echo "Engram Codex guard requires jq."
  exit 0
fi

# Keep this parser aligned with engram_settings.py without requiring Python on
# existing macOS/Linux installations. No guard state or health checks run when
# another hook asks only for the setting.
SETTINGS_FILE="${ENGRAM_CONFIG_PATH-${HOME}/.engram/settings.json}"
if [ -z "${SETTINGS_FILE//[[:space:]]/}" ]; then
  echo "Engram settings: ENGRAM_CONFIG_PATH must not be empty." >&2
  exit 2
fi
case "$SETTINGS_FILE" in
  '~') SETTINGS_FILE="$HOME" ;;
  '~/'*) SETTINGS_FILE="${HOME}/${SETTINGS_FILE#\~/}" ;;
esac
CHECKPOINTS_ENABLED=true
if [ -e "$SETTINGS_FILE" ]; then
  if [ ! -f "$SETTINGS_FILE" ] || [ ! -r "$SETTINGS_FILE" ]; then
    echo "Engram settings: cannot read settings file $SETTINGS_FILE." >&2
    exit 2
  fi
  CHECKPOINTS_ENABLED="$(jq -r -s '
    if length != 1 then error("settings must contain one JSON object")
    else .[0] | if type != "object" then error("settings must be a JSON object")
      elif has("checkpoints_enabled") and (.checkpoints_enabled | type) != "boolean"
      then error("checkpoints_enabled must be a JSON boolean")
      elif has("checkpoints_enabled") then .checkpoints_enabled else true end
    end' "$SETTINGS_FILE")" || {
      echo "Engram settings: invalid settings file $SETTINGS_FILE." >&2
      exit 2
    }
fi
if [ "${ENGRAM_CHECKPOINTS_ENABLED+x}" = x ]; then
  checkpoint_override="$(jq -nr --arg value "$ENGRAM_CHECKPOINTS_ENABLED" '$value | ascii_downcase | gsub("^\\s+|\\s+$"; "")')"
  case "$checkpoint_override" in
    true|on|1) CHECKPOINTS_ENABLED=true ;;
    false|off|0) CHECKPOINTS_ENABLED=false ;;
    *)
      echo "Engram settings: ENGRAM_CHECKPOINTS_ENABLED must be true/false, on/off, or 1/0." >&2
      exit 2
      ;;
  esac
fi
if [ "$ACTION" = "--checkpoints-enabled" ]; then
  printf '%s\n' "$CHECKPOINTS_ENABLED"
  exit 0
fi

CODEX_DIR="${CODEX_HOME:-${HOME}/.codex}"
SESSIONS_DIR="${ENGRAM_CODEX_SESSIONS_DIR:-${CODEX_DIR}/sessions}"
STATE_DIR="${ENGRAM_CODEX_STATE_DIR:-${CODEX_DIR}/engram}"
MODE_FILE="${STATE_DIR}/history-guard-mode"
BASELINE_FILE="${STATE_DIR}/history-guard-legacy-baseline-bytes"
CLEAN_FILE="${STATE_DIR}/history-guard-clean-achieved"
SESSION_BASELINE_DIR="${STATE_DIR}/history-guard-session-baselines"

SESSION_SOFT_MIB="${ENGRAM_CODEX_SESSION_SOFT_MIB:-256}"
SESSION_HARD_MIB="${ENGRAM_CODEX_SESSION_HARD_MIB:-2048}"
TOTAL_SOFT_GIB="${ENGRAM_CODEX_TOTAL_SOFT_GIB:-40}"
TOTAL_HARD_GIB="${ENGRAM_CODEX_TOTAL_HARD_GIB:-50}"
LEGACY_GROWTH_MIB="${ENGRAM_CODEX_LEGACY_GROWTH_MIB:-512}"
SESSION_LEGACY_GROWTH_MIB="${ENGRAM_CODEX_SESSION_LEGACY_GROWTH_MIB:-256}"

is_uint() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

for value in "$SESSION_SOFT_MIB" "$SESSION_HARD_MIB" "$TOTAL_SOFT_GIB" "$TOTAL_HARD_GIB" "$LEGACY_GROWTH_MIB" "$SESSION_LEGACY_GROWTH_MIB"; do
  is_uint "$value" || exit 0
done

SESSION_SOFT_BYTES=$((SESSION_SOFT_MIB * 1024 * 1024))
SESSION_HARD_BYTES=$((SESSION_HARD_MIB * 1024 * 1024))
TOTAL_SOFT_BYTES=$((TOTAL_SOFT_GIB * 1024 * 1024 * 1024))
TOTAL_HARD_BYTES=$((TOTAL_HARD_GIB * 1024 * 1024 * 1024))
LEGACY_GROWTH_BYTES=$((LEGACY_GROWTH_MIB * 1024 * 1024))
SESSION_LEGACY_GROWTH_BYTES=$((SESSION_LEGACY_GROWTH_MIB * 1024 * 1024))

EVENT="$(printf '%s' "$INPUT" | jq -r '.hook_event_name // empty' 2>/dev/null)"
SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)"
TRANSCRIPT_PATH="$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)"
PROMPT="$(printf '%s' "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)"
STOP_ACTIVE="$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)"
SAFE_SESSION_ID="$(printf '%s' "$SESSION_ID" | tr -cd '[:alnum:]._-')"
[ -n "$SAFE_SESSION_ID" ] || SAFE_SESSION_ID="unknown"

file_size() {
  target="$1"
  [ -f "$target" ] || { echo 0; return; }
  stat -f '%z' "$target" 2>/dev/null || stat -c '%s' "$target" 2>/dev/null || echo 0
}

directory_size() {
  target="$1"
  [ -d "$target" ] || { echo 0; return; }
  size_kib="$(du -sk "$target" 2>/dev/null | awk 'NR == 1 {print $1}')"
  is_uint "${size_kib:-}" || size_kib=0
  echo $((size_kib * 1024))
}

atomic_write() {
  target="$1"
  value="$2"
  mkdir -p "$STATE_DIR" 2>/dev/null || return 0
  tmp="${target}.tmp.$$"
  umask 077
  printf '%s\n' "$value" > "$tmp" 2>/dev/null || return 0
  mv -f "$tmp" "$target" 2>/dev/null || true
}

human_bytes() {
  bytes="$1"
  awk -v bytes="$bytes" 'BEGIN {
    if (bytes >= 1073741824) printf "%.1f GiB", bytes / 1073741824;
    else if (bytes >= 1048576) printf "%.1f MiB", bytes / 1048576;
    else printf "%.1f KiB", bytes / 1024;
  }'
}

json_context() {
  context="$1"
  system_message="${2:-}"
  jq -n --arg event "$EVENT" --arg context "$context" --arg systemMessage "$system_message" '{
    hookSpecificOutput: {
      hookEventName: $event,
      additionalContext: $context
    }
  } + (if $systemMessage == "" then {} else {
    systemMessage: $systemMessage,
    suppressOutput: false
  } end)'
}

json_system_message() {
  message="$1"
  jq -n --arg message "$message" '{
    continue: true,
    systemMessage: $message,
    suppressOutput: false
  }'
}

json_block_prompt() {
  reason="$1"
  jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
}

json_stop() {
  reason="$1"
  warning="$2"
  jq -n --arg reason "$reason" --arg warning "$warning" '{
    continue: false,
    stopReason: $reason,
    systemMessage: $warning
  }'
}

SESSION_BYTES="$(file_size "$TRANSCRIPT_PATH")"
TOTAL_BYTES="$(directory_size "$SESSIONS_DIR")"
is_uint "$SESSION_BYTES" || SESSION_BYTES=0
is_uint "$TOTAL_BYTES" || TOTAL_BYTES=0

EFFECTIVE_SESSION_HARD="$SESSION_HARD_BYTES"
SESSION_LEGACY_BASELINE=""
SESSION_BASELINE_FILE="${SESSION_BASELINE_DIR}/${SAFE_SESSION_ID}"
if [ -f "$SESSION_BASELINE_FILE" ]; then
  SESSION_LEGACY_BASELINE="$(sed -n '1p' "$SESSION_BASELINE_FILE" 2>/dev/null)"
  if is_uint "$SESSION_LEGACY_BASELINE" && [ "$SESSION_LEGACY_BASELINE" -ge "$SESSION_HARD_BYTES" ]; then
    EFFECTIVE_SESSION_HARD=$((SESSION_LEGACY_BASELINE + SESSION_LEGACY_GROWTH_BYTES))
  else
    SESSION_LEGACY_BASELINE=""
  fi
fi

HEALTHY=false
HEALTH_NOTIFY=true
HEALTH_MESSAGE="ENGRAM UNAVAILABLE: the shared MCP health checker could not run. Recall and capture are not durable; do not claim anything was saved to Engram, and do not perform history consolidation. Recovery: $RECOVERY_COMMAND"
if [ "$ACTION" != "--status" ] && [ "$EVENT" != "Stop" ] && [ -x "$ROOT/scripts/engram-mcp-health.sh" ]; then
  HEALTH_JSON="$(bash "$ROOT/scripts/engram-mcp-health.sh" --hook "$EVENT" "$SESSION_ID" codex 2>/dev/null)"
  parsed_healthy="$(printf '%s' "$HEALTH_JSON" | jq -r '.healthy // false' 2>/dev/null)"
  parsed_notify="$(printf '%s' "$HEALTH_JSON" | jq -r 'if has("notify") then .notify else true end' 2>/dev/null)"
  parsed_message="$(printf '%s' "$HEALTH_JSON" | jq -r '.message // empty' 2>/dev/null)"
  [ "$parsed_healthy" = "true" ] && HEALTHY=true
  [ "$parsed_notify" = "false" ] && HEALTH_NOTIFY=false
  [ -n "$parsed_message" ] && HEALTH_MESSAGE="$parsed_message"
fi
HEALTH_POLICY=""
if [ "$HEALTHY" != true ]; then
  HEALTH_POLICY="ENGRAM IS OFFLINE. Do not claim durable recall or capture succeeded. Do not consolidate, prune, or rewrite native Codex history until the MCP health check recovers. Preserve the current native context. Recovery: $RECOVERY_COMMAND"
fi

# The first activation on a machine that is already over the clean hard cap
# records one legacy baseline. That prevents immediate lockout while still
# allowing only a small, fixed amount of additional growth. Once cleanup drops
# below the hard cap, the guard permanently switches to absolute-cap mode.
MODE=""
[ -f "$MODE_FILE" ] && MODE="$(sed -n '1p' "$MODE_FILE" 2>/dev/null)"
if [ "$MODE" != "legacy" ] && [ "$MODE" != "absolute" ]; then
  if [ "$TOTAL_BYTES" -ge "$TOTAL_HARD_BYTES" ]; then
    MODE="legacy"
    atomic_write "$BASELINE_FILE" "$TOTAL_BYTES"
  else
    MODE="absolute"
    atomic_write "$CLEAN_FILE" "true"
  fi
  atomic_write "$MODE_FILE" "$MODE"
fi

# Repair an older guard state that marked this already-bloated installation
# absolute before the legacy allowance was introduced. The one-time allowance
# can never return after the sessions directory has actually reached the clean
# cap; CLEAN_FILE records that irreversible transition.
if [ "$MODE" = "absolute" ] && [ "$TOTAL_BYTES" -ge "$TOTAL_HARD_BYTES" ] && [ ! -f "$CLEAN_FILE" ]; then
  legacy_candidate=""
  [ -f "$BASELINE_FILE" ] && legacy_candidate="$(sed -n '1p' "$BASELINE_FILE" 2>/dev/null)"
  if is_uint "$legacy_candidate" && [ "$legacy_candidate" -ge "$TOTAL_HARD_BYTES" ]; then
    MODE="legacy"
    atomic_write "$MODE_FILE" "$MODE"
  fi
fi

if [ "$MODE" = "legacy" ] && [ "$TOTAL_BYTES" -lt "$TOTAL_HARD_BYTES" ]; then
  MODE="absolute"
  atomic_write "$MODE_FILE" "$MODE"
  atomic_write "$CLEAN_FILE" "true"
fi

if [ "$MODE" = "legacy" ]; then
  LEGACY_BASELINE=""
  [ -f "$BASELINE_FILE" ] && LEGACY_BASELINE="$(sed -n '1p' "$BASELINE_FILE" 2>/dev/null)"
  if ! is_uint "$LEGACY_BASELINE"; then
    LEGACY_BASELINE="$TOTAL_BYTES"
    atomic_write "$BASELINE_FILE" "$LEGACY_BASELINE"
  fi
  EFFECTIVE_TOTAL_SOFT=$((LEGACY_BASELINE + (LEGACY_GROWTH_BYTES / 2)))
  EFFECTIVE_TOTAL_HARD=$((LEGACY_BASELINE + LEGACY_GROWTH_BYTES))
else
  EFFECTIVE_TOTAL_SOFT="$TOTAL_SOFT_BYTES"
  EFFECTIVE_TOTAL_HARD="$TOTAL_HARD_BYTES"
fi

if [ "$ACTION" = "--rebaseline-after-cleanup" ]; then
  previous_baseline=""
  [ -f "$BASELINE_FILE" ] && previous_baseline="$(sed -n '1p' "$BASELINE_FILE" 2>/dev/null)"
  if [ "$MODE" != "legacy" ]; then
    echo "Refusing cleanup rebaseline: history guard is already in absolute-cap mode." >&2
    exit 2
  fi
  if ! is_uint "$previous_baseline" || [ "$TOTAL_BYTES" -ge "$previous_baseline" ]; then
    echo "Refusing cleanup rebaseline: current history must be smaller than the recorded legacy baseline." >&2
    exit 2
  fi

  atomic_write "$BASELINE_FILE" "$TOTAL_BYTES"
  mkdir -p "$SESSION_BASELINE_DIR" 2>/dev/null || exit 2
  seeded_sessions=0
  STATE_DB="${CODEX_DIR}/state_5.sqlite"
  if command -v sqlite3 >/dev/null 2>&1 && [ -f "$STATE_DB" ]; then
    while IFS='|' read -r thread_id rollout_file; do
      safe_thread_id="$(printf '%s' "$thread_id" | tr -cd '[:alnum:]._-')"
      [ -n "$safe_thread_id" ] || continue
      rollout_bytes="$(file_size "$rollout_file")"
      is_uint "$rollout_bytes" || continue
      if [ "$rollout_bytes" -ge "$SESSION_HARD_BYTES" ]; then
        atomic_write "${SESSION_BASELINE_DIR}/${safe_thread_id}" "$rollout_bytes"
        seeded_sessions=$((seeded_sessions + 1))
      fi
    done < <(sqlite3 -separator '|' "$STATE_DB" \
      "SELECT id, rollout_path FROM threads WHERE NOT (json_valid(source) AND json_type(source, '$.subagent') IS NOT NULL);" 2>/dev/null)
  fi

  audit_file="${STATE_DIR}/history-guard-cleanup-rebaseline.json"
  audit_tmp="${audit_file}.tmp.$$"
  jq -n \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --argjson previous "$previous_baseline" \
    --argjson current "$TOTAL_BYTES" \
    --argjson globalGrowth "$LEGACY_GROWTH_BYTES" \
    --argjson sessionGrowth "$SESSION_LEGACY_GROWTH_BYTES" \
    --argjson seededSessions "$seeded_sessions" \
    '{timestamp:$timestamp, previous_legacy_baseline_bytes:$previous, cleaned_legacy_baseline_bytes:$current, global_growth_allowance_bytes:$globalGrowth, per_session_growth_allowance_bytes:$sessionGrowth, seeded_oversized_user_sessions:$seededSessions}' \
    > "$audit_tmp" && mv -f "$audit_tmp" "$audit_file"

  echo "Engram Codex history guard rebaselined after verified cleanup"
  echo "  previous baseline: $(human_bytes "$previous_baseline")"
  echo "  cleaned baseline: $(human_bytes "$TOTAL_BYTES")"
  echo "  global hard stop: $(human_bytes $((TOTAL_BYTES + LEGACY_GROWTH_BYTES)))"
  echo "  oversized user-task baselines seeded: ${seeded_sessions}"
  echo "  per-task legacy growth allowance: $(human_bytes "$SESSION_LEGACY_GROWTH_BYTES")"
  exit 0
fi

if [ "$ACTION" = "--status" ]; then
  bash "$ROOT/scripts/engram-mcp-health.sh" --status 2>/dev/null || true
  echo "Engram Codex history guard"
  echo "  automatic checkpoints: $CHECKPOINTS_ENABLED"
  echo "  settings: $SETTINGS_FILE"
  echo "  mode: ${MODE}"
  echo "  sessions total: $(human_bytes "$TOTAL_BYTES")"
  echo "  total warning: $(human_bytes "$EFFECTIVE_TOTAL_SOFT")"
  echo "  total hard stop: $(human_bytes "$EFFECTIVE_TOTAL_HARD")"
  if [ "$CHECKPOINTS_ENABLED" = true ]; then
    echo "  task checkpoint: verified each turn (separate continuity status reports receipts)"
  else
    echo "  task checkpoint: disabled"
  fi
  echo "  task hard stop: $(human_bytes "$SESSION_HARD_BYTES")"
  echo "  oversized legacy task allowance: $(human_bytes "$SESSION_LEGACY_GROWTH_BYTES")"
  exit 0
fi

# Lifecycle events are handled by the shared portable adapter above.
echo "Unknown Engram guard action: $ACTION" >&2
exit 64
