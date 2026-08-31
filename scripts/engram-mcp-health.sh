#!/usr/bin/env bash
# End-to-end Engram MCP probe with per-chat outage/recovery transition state.
set -uo pipefail

readonly ENDPOINT="${ENGRAM_MCP_URL:-http://127.0.0.1:18765/mcp}"
readonly EXPECTED_VERSION="${ENGRAM_BASIC_MEMORY_VERSION:-0.23.2}"
readonly EXPECTED_PROJECT="${ENGRAM_MCP_PROJECT:-engram}"
readonly CACHE_SECONDS="${ENGRAM_HEALTH_CACHE_SECONDS:-300}"
ROOT="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
if [ -n "${ENGRAM_HEALTH_STATE_DIR:-}" ]; then
  STATE_DIR="$ENGRAM_HEALTH_STATE_DIR"
elif [ "$(uname -s)" = "Darwin" ]; then
  STATE_DIR="${HOME}/Library/Caches/Engram/mcp-health"
else
  STATE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/engram/mcp-health"
fi
readonly STATE_DIR
RECOVERY_COMMAND="$(sh "$ROOT/scripts/engram-recovery-command.sh" 2>/dev/null || true)"
readonly RECOVERY_COMMAND="${RECOVERY_COMMAND:-restart the configured Engram shared MCP service}"

is_uint() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

json_result() {
  healthy="$1"
  checked="$2"
  notify="$3"
  message="$4"
  detail="$5"
  jq -n \
    --argjson healthy "$healthy" \
    --argjson checked "$checked" \
    --argjson notify "$notify" \
    --arg message "$message" \
    --arg detail "$detail" \
    --arg endpoint "$ENDPOINT" \
    --arg version "$EXPECTED_VERSION" \
    --arg project "$EXPECTED_PROJECT" \
    '{healthy:$healthy,checked:$checked,notify:$notify,message:$message,detail:$detail,endpoint:$endpoint,expectedVersion:$version,expectedProject:$project}'
}

probe() {
  if ! command -v curl >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
    PROBE_DETAIL="curl and jq are required for the Engram MCP health check"
    return 1
  fi

  response="$(curl --silent --show-error --include --max-time 3 \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"engram-health","version":"1"}}}' \
    "$ENDPOINT" 2>&1)" || {
      PROBE_DETAIL="initialize failed: $(printf '%s' "$response" | head -c 240)"
      return 1
    }

  session_id="$(printf '%s\n' "$response" | awk 'tolower($1)=="mcp-session-id:" {gsub("\r", "", $2); print $2; exit}')"
  if [ -z "$session_id" ]; then
    PROBE_DETAIL="initialize returned no MCP session id"
    return 1
  fi

  curl --silent --show-error --max-time 3 -o /dev/null \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -H "Mcp-Session-Id: $session_id" \
    --data '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
    "$ENDPOINT" 2>/dev/null || {
      PROBE_DETAIL="MCP initialization acknowledgement failed"
      return 1
    }

  diagnostic_response="$(curl --silent --show-error --max-time 5 \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -H "Mcp-Session-Id: $session_id" \
    --data '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"basic_memory_diagnostics","arguments":{}}}' \
    "$ENDPOINT" 2>&1)" || {
      PROBE_DETAIL="diagnostics tool call failed"
      return 1
    }
  diagnostic="$(printf '%s\n' "$diagnostic_response" | sed -n 's/^data: //p' | jq -r 'select(.id==2 and .result.isError!=true) | [.result.content[]? | select(.type=="text") | .text] | join("\n")' 2>/dev/null)"
  if ! printf '%s\n' "$diagnostic" | grep -Fq -- "- basic-memory: $EXPECTED_VERSION"; then
    PROBE_DETAIL="expected Basic Memory $EXPECTED_VERSION; diagnostics did not confirm it"
    return 1
  fi

  project_response="$(curl --silent --show-error --max-time 5 \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -H "Mcp-Session-Id: $session_id" \
    --data '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_memory_projects","arguments":{"output_format":"json"}}}' \
    "$ENDPOINT" 2>&1)" || {
      PROBE_DETAIL="project-list tool call failed"
      return 1
    }
  constrained_project="$(printf '%s\n' "$project_response" | sed -n 's/^data: //p' | jq -r 'select(.id==3 and .result.isError!=true) | .result.structuredContent.result.constrained_project // empty' 2>/dev/null | tail -n 1)"
  if [ "$constrained_project" != "$EXPECTED_PROJECT" ]; then
    PROBE_DETAIL="server is not constrained to the $EXPECTED_PROJECT project"
    return 1
  fi

  PROBE_DETAIL="Basic Memory $EXPECTED_VERSION; project $EXPECTED_PROJECT"
  return 0
}

write_state() {
  state_file="$1"
  status="$2"
  checked_at="$3"
  mkdir -p "$STATE_DIR" 2>/dev/null || return 0
  chmod 700 "$STATE_DIR" 2>/dev/null || true
  tmp="${state_file}.tmp.$$"
  umask 077
  jq -n --arg status "$status" --argjson checkedAt "$checked_at" \
    '{status:$status,checkedAt:$checkedAt}' > "$tmp" 2>/dev/null || return 0
  mv -f "$tmp" "$state_file" 2>/dev/null || true
}

if [ "${1:-}" = "--status" ]; then
  if probe; then
    echo "Engram MCP: healthy ($PROBE_DETAIL)"
    echo "Endpoint: $ENDPOINT"
    exit 0
  fi
  echo "Engram MCP: UNAVAILABLE ($PROBE_DETAIL)"
  echo "Recovery: $RECOVERY_COMMAND"
  exit 1
fi

if [ "${1:-}" != "--hook" ]; then
  echo "usage: $0 --status | --hook EVENT SESSION_ID HOST" >&2
  exit 64
fi

event="${2:-unknown}"
session_id="${3:-unknown}"
host="${4:-unknown}"
safe_key="$(printf '%s-%s' "$host" "$session_id" | tr -cd '[:alnum:]._-')"
[ -n "$safe_key" ] || safe_key="unknown"
state_file="${STATE_DIR}/${safe_key}.json"
now="$(date +%s)"
previous_status="unknown"
previous_checked=0
if [ -f "$state_file" ]; then
  previous_status="$(jq -r '.status // "unknown"' "$state_file" 2>/dev/null)"
  previous_checked="$(jq -r '.checkedAt // 0' "$state_file" 2>/dev/null)"
fi
is_uint "$previous_checked" || previous_checked=0
cache_seconds="$CACHE_SECONDS"
is_uint "$cache_seconds" || cache_seconds=300

force=false
case "$event" in
  SessionStart|PreCompact) force=true ;;
esac

if [ "$force" = false ] && [ $((now - previous_checked)) -lt "$cache_seconds" ] && { [ "$previous_status" = "up" ] || [ "$previous_status" = "down" ]; }; then
  if [ "$previous_status" = "up" ]; then
    json_result true false false "" "cached healthy result"
  else
    json_result false false false "" "cached unavailable result"
  fi
  exit 0
fi

attempts=1
[ "$event" = "SessionStart" ] && attempts=3
healthy=false
attempt=1
while [ "$attempt" -le "$attempts" ]; do
  if probe; then
    healthy=true
    break
  fi
  if [ "$attempt" -lt "$attempts" ]; then
    sleep 0.5
  fi
  attempt=$((attempt + 1))
done

if [ "$healthy" = true ]; then
  notify=false
  message=""
  if [ "$previous_status" = "down" ]; then
    notify=true
    message="ENGRAM RECOVERED: durable recall and capture are available again through $ENDPOINT."
  fi
  write_state "$state_file" up "$now"
  json_result true true "$notify" "$message" "$PROBE_DETAIL"
  exit 0
fi

notify=false
[ "$previous_status" != "down" ] && notify=true
message="ENGRAM UNAVAILABLE: the shared memory service failed its MCP handshake ($PROBE_DETAIL). Recall and capture are not durable; do not claim anything was saved to Engram, and do not perform history consolidation while it is down. Preserve native context. Recovery: $RECOVERY_COMMAND"
write_state "$state_file" down "$now"
json_result false true "$notify" "$message" "$PROBE_DETAIL"
