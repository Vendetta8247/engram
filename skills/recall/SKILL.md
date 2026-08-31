---
name: recall
description: Use when the user asks what's known / remembered / decided about something, or to look it up in memory. Queries + traverses the Engram knowledge graph (basic-memory MCP) across project + global tiers — not Claude's native memory. (The agent also auto-recalls before non-trivial work per the using-the-graph skill.)
allowed-tools: Read
---

# /engram:recall — query the graph

Query: **$ARGUMENTS**

1. **Current project first.** Determine the current project (`projects/<name>/`, from the git repo folder). Run the basic-memory MCP `search` (semantic + full-text), then lead with the hits whose permalink sits under `projects/<name>/` or `global/` — answer from those if they cover it. Only widen to the rest of the store (other `projects/*`) when the local pass comes up short or the question is explicitly cross-project. A fact from any project is still one search away — it's just ranked after home.
2. For the most relevant hits, `build_context` to pull the note plus its linked neighborhood — follow typed relations rather than re-deriving facts.
3. Synthesize a concise answer, citing the note titles you drew from. If nothing relevant exists, say so plainly (don't invent) and offer to `/engram:remember` it once known.
