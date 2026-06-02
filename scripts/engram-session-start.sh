#!/usr/bin/env bash
# Engram SessionStart hook — reminds the agent the graph exists and flags an
# unprocessed capture inbox. Stays silent if Engram isn't set up yet.
set -uo pipefail

GLOBAL="${HOME}/Engram"
INBOX="${HOME}/Engram/inbox"

# Not set up yet → say nothing.
[ -f "${HOME}/Engram/INDEX.md" ] || exit 0

echo "🧠 Engram memory is active. Maintain it AUTOMATICALLY — the user should not have to ask. (1) AUTO-RECALL: before non-trivial work, search the store (both global/ and projects/) via the basic-memory MCP and lead with what's already known. (2) AUTO-CAPTURE: the moment you learn something durable/reusable (a preference, correction, gotcha, decision+why, reusable pattern), write it to the graph immediately, mid-task, without being asked. Apply the worth-keeping bar so it stays curated. Durable memory is the graph, never CLAUDE.md/MEMORY.md. See the 'using-the-graph' skill for tiering + conventions."

if [ -d "$INBOX" ]; then
  n=$(find "$INBOX" -type f \( -name '*.md' -o -name '*.txt' \) 2>/dev/null | wc -l | tr -d ' ')
  if [ "${n:-0}" -gt 0 ]; then
    echo "📥 You have ${n} uncaptured thought(s) in the Engram inbox — run /engram:triage to file them into the graph."
  fi
fi

# Route signal: everything lives in the ONE ~/Engram store, split into two
# buckets — global/<domain>/ for reusable knowledge, projects/<name>/ per project.
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
  PROJ="$(basename "$ROOT" 2>/dev/null)"
  if [ -n "$PROJ" ]; then
    echo "📁 Working in project '${PROJ}'. Route project-specific facts (config, this app's internals) to ~/Engram/projects/${PROJ}/ (auto-create that folder if needed). Reusable knowledge (patterns, working rules) goes to ~/Engram/global/<domain>/ (global/workflow/, global/kmp/, global/ios/, ...). One store → cross-project recall is a single search."
  fi
fi
