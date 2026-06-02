---
name: recall
description: MANUAL OVERRIDE to force a lookup in the Engram graph now. Recall is normally automatic (the agent consults the graph before non-trivial work on its own — see the using-the-graph skill); use this to explicitly query stored project + global knowledge.
argument-hint: "<what to recall>"
allowed-tools: Read
---

# /engram:recall — query the graph

Query: **$ARGUMENTS**

1. Use the basic-memory MCP `search` (semantic + full-text) across the current project brain AND the global brain.
2. For the most relevant hits, `build_context` to pull the note plus its linked neighborhood — follow typed relations rather than re-deriving facts.
3. Synthesize a concise answer, citing the note titles you drew from. If nothing relevant exists, say so plainly (don't invent) and offer to `/engram:remember` it once known.
