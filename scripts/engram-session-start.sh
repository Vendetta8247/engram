#!/usr/bin/env bash
# Engram SessionStart hook — reminds the agent the graph exists and flags an
# unprocessed capture inbox. Stays silent if Engram isn't set up yet.
set -uo pipefail

GLOBAL="${HOME}/.engram/global"
INBOX="${GLOBAL}/inbox"

# Not set up yet → say nothing.
[ -d "$GLOBAL" ] || exit 0

echo "🧠 Engram memory is active. Maintain it AUTOMATICALLY — the user should not have to ask. (1) AUTO-RECALL: before non-trivial work, search the project + global brain via the basic-memory MCP and lead with what's already known. (2) AUTO-CAPTURE: the moment you learn something durable/reusable (a preference, correction, gotcha, decision+why, reusable pattern), write it to the graph immediately, mid-task, without being asked. Apply the worth-keeping bar so it stays curated. Durable memory is the graph, never CLAUDE.md/MEMORY.md. See the 'using-the-graph' skill for tiering + conventions."

if [ -d "$INBOX" ]; then
  n=$(find "$INBOX" -type f \( -name '*.md' -o -name '*.txt' \) 2>/dev/null | wc -l | tr -d ' ')
  if [ "${n:-0}" -gt 0 ]; then
    echo "📥 You have ${n} uncaptured thought(s) in the Engram inbox — run /engram:triage to file them into the graph."
  fi
fi
