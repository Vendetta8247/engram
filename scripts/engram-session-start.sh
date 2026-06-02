#!/usr/bin/env bash
# Engram SessionStart hook — reminds the agent the graph exists and flags an
# unprocessed capture inbox. Stays silent if Engram isn't set up yet.
set -uo pipefail

GLOBAL="${HOME}/.engram/global"
INBOX="${GLOBAL}/inbox"

# Not set up yet → say nothing.
[ -d "$GLOBAL" ] || exit 0

echo "🧠 Engram memory is active. Your durable memory is the knowledge graph (basic-memory MCP), not CLAUDE.md/MEMORY.md. Consult it for project + global knowledge and write learnings there — see the 'using-the-graph' skill for the two-tier routing + conventions."

if [ -d "$INBOX" ]; then
  n=$(find "$INBOX" -type f \( -name '*.md' -o -name '*.txt' \) 2>/dev/null | wc -l | tr -d ' ')
  if [ "${n:-0}" -gt 0 ]; then
    echo "📥 You have ${n} uncaptured thought(s) in the Engram inbox — run /engram:triage to file them into the graph."
  fi
fi
