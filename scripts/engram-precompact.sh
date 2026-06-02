#!/usr/bin/env bash
# Engram PreCompact hook — fires before the context window is compacted. Last
# chance to persist anything durable from this session before it's summarized
# away. Silent if Engram isn't set up.
set -uo pipefail
[ -d "${HOME}/.engram/global" ] || exit 0
echo "🧠 Engram checkpoint (pre-compaction): before this context is compacted, sweep the session for durable, reusable learnings not yet in the graph — user preferences, corrections, gotchas, decisions+why, reusable patterns — and write them now to the basic-memory MCP (right tier, worth-keeping bar, dedupe-then-write). Anything not captured here is lost on compaction."
