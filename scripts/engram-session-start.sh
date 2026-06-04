#!/usr/bin/env bash
# Engram SessionStart hook — reminds the agent the graph exists and flags an
# unprocessed capture inbox. Stays silent if Engram isn't set up yet.
set -uo pipefail

GLOBAL="${HOME}/Engram"
INBOX="${HOME}/Engram/inbox"

# Not set up yet → say nothing.
[ -f "${HOME}/Engram/INDEX.md" ] || exit 0

echo "🧠 Engram memory is active. Maintain it AUTOMATICALLY — the user should not have to ask. (1) AUTO-RECALL: before non-trivial work, search the store via the basic-memory MCP — THIS project first (projects/<name>/ + linked global/), widening to other projects only if the local pass misses — and lead with what's already known. (2) AUTO-CAPTURE: the moment you learn something durable/reusable (a preference, correction, gotcha, decision+why, reusable pattern), write it to the graph immediately, mid-task, without being asked — keep notes COMPACT (many small nodes). Apply the worth-keeping bar so it stays curated. Durable memory is the graph, never CLAUDE.md/MEMORY.md. See the 'using-the-graph' skill for tiering + conventions."

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
