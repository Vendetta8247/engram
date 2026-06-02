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

INPUT="$(cat)"   # hook input JSON on stdin
[ -d "${HOME}/Engram/global" ] || exit 0

PROMPT="$(printf '%s' "$INPUT" | jq -r '.prompt // .user_prompt // empty' 2>/dev/null)"
[ -n "$PROMPT" ] || exit 0

# Memory-intent detection (case-insensitive). Kept broad on purpose; the
# injected instruction is phrased conditionally so a false positive is a
# harmless no-op nudge rather than a wrong action.
if printf '%s' "$PROMPT" | grep -iqE '(remember|memori[sz]e|make a note|take note|note that|note this|jot (this|that|it|down)|keep (this|that|it)?[[:space:]]*in mind|don.?t forget|for (future|later) reference|save (this|that|it)|store (this|that)|log (this|that)|write (this|that) down)'; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: "ENGRAM ROUTING: this prompt looks like a request to remember/save information. If it is, capture it into the ENGRAM knowledge graph via the basic-memory MCP — route to the right tier (global vs project) per the using-the-graph skill, search-then-write to dedupe, and tell the user what you stored and where. Do NOT use Claude native memory for this; Engram is the durable store. (If the prompt is not actually a save request — e.g. \"I don'\''t remember…\" — ignore this.)"
    }
  }'
fi
exit 0
