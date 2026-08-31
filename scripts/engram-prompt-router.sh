#!/usr/bin/env bash
# Engram UserPromptSubmit router. When the user's prompt looks like a memory
# request ("remember X", "note that…", "save this", …), inject a hard
# instruction to route it through Engram (basic-memory MCP) instead of Claude's
# native memory. This is the deterministic layer that makes Engram OWN the
# "remember" verb — it fires on the actual words, every prompt, regardless of
# whether the model would have picked the skill on its own.
#
# Silent when: Engram isn't set up, no prompt, or no memory-intent match.
# Output: the documented UserPromptSubmit additionalContext envelope.
set -uo pipefail

ROOT="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
if [ "${ENGRAM_HOST:-}" = "codex" ] || [ -n "${PLUGIN_ROOT:-}" ]; then
  exec bash "${ROOT}/scripts/engram-codex-hook.sh"
fi

INPUT="$(cat)"   # hook input JSON on stdin
PROMPT="$(printf '%s' "$INPUT" | jq -r '.prompt // .user_prompt // empty' 2>/dev/null)"
SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)"
HEALTH_JSON="$(bash "${ROOT}/scripts/engram-mcp-health.sh" --hook UserPromptSubmit "$SESSION_ID" claude 2>/dev/null)"
HEALTHY="$(printf '%s' "$HEALTH_JSON" | jq -r '.healthy // false' 2>/dev/null)"
HEALTH_NOTIFY="$(printf '%s' "$HEALTH_JSON" | jq -r 'if has("notify") then .notify else true end' 2>/dev/null)"
HEALTH_MESSAGE="$(printf '%s' "$HEALTH_JSON" | jq -r '.message // empty' 2>/dev/null)"
CONTEXT=""
SYSTEM_MESSAGE=""

if [ "$HEALTHY" != "true" ]; then
  CONTEXT="ENGRAM IS OFFLINE. Do not claim durable recall or capture succeeded. Do not consolidate or prune native chat history. Preserve native context until the shared MCP service recovers."
  [ "$HEALTH_NOTIFY" = "true" ] && SYSTEM_MESSAGE="$HEALTH_MESSAGE"
elif [ "$HEALTH_NOTIFY" = "true" ] && [ -n "$HEALTH_MESSAGE" ]; then
  CONTEXT="$HEALTH_MESSAGE"
  SYSTEM_MESSAGE="$HEALTH_MESSAGE"
fi

# Memory-intent detection (case-insensitive). Kept broad on purpose; the
# injected instruction is phrased conditionally so a false positive is a
# harmless no-op nudge rather than a wrong action.
if [ -f "${HOME}/Engram/INDEX.md" ] && printf '%s' "$PROMPT" | grep -iqE '(remember|memori[sz]e|make a note|take note|note that|note this|jot (this|that|it|down)|keep (this|that|it)?[[:space:]]*in mind|don.?t forget|for (future|later) reference|save (this|that|it)|store (this|that)|log (this|that)|write (this|that) down)'; then
  CONTEXT="${CONTEXT} ENGRAM ROUTING: this prompt looks like a request to remember/save information. If it is, capture it into the ENGRAM knowledge graph via the basic-memory MCP — route to the right tier (global vs project) per the using-the-graph skill, search-then-write to dedupe, and tell the user what you stored and where. Do NOT use Claude native memory for this; Engram is the durable store. If Engram is offline, do not claim the save succeeded."
fi

if [ -n "$CONTEXT" ]; then
  jq -n --arg context "$CONTEXT" --arg systemMessage "$SYSTEM_MESSAGE" '{
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: $context
    }
  } + (if $systemMessage == "" then {} else {systemMessage:$systemMessage} end)'
fi
exit 0
