---
name: recall
description: Use when the user asks what's known / remembered / decided about something, or to look it up in memory. Queries + traverses the Engram knowledge graph (basic-memory MCP) across project + global tiers — not Claude's native memory. (The agent also auto-recalls before non-trivial work per the using-the-graph skill.)
when_to_use: Trigger phrases like "what do you know about", "do you remember", "did we decide", "have we hit this before", "look it up", "recall", "what's our convention for".
argument-hint: "<what to recall>"
allowed-tools: Read
---

# /engram:recall — query the graph

Query: **$ARGUMENTS**

1. Use the basic-memory MCP `search` (semantic + full-text) across the whole `~/Engram` store — global domains AND every `projects/<name>/` — since a fact from any project is one search away.
2. For the most relevant hits, `build_context` to pull the note plus its linked neighborhood — follow typed relations rather than re-deriving facts.
3. Synthesize a concise answer, citing the note titles you drew from. If nothing relevant exists, say so plainly (don't invent) and offer to `/engram:remember` it once known.
