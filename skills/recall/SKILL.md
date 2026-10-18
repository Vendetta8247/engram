---
name: recall
description: Use when the user asks what's known / remembered / decided about something, or to look it up in memory. Queries + traverses the Engram knowledge graph (basic-memory MCP) across project + global tiers — not Claude's native memory. (The agent also auto-recalls before non-trivial work per the using-the-graph skill.)
allowed-tools: Read
---

# /engram:recall — query the graph

Query: **$ARGUMENTS**

1. **Current project first.** Resolve an explicit project name in the request, then selected workspace, Git root if present, then current folder, following [project workspaces](../using-the-graph/references/project-workspaces.md). `$ARGUMENTS` is the recall query; do not turn the whole query into a project name. Git is optional. Run compact basic-memory MCP `search`; if it returns `Unsupported MCP client`, use `search_notes` with `project: "engram"`, a targeted query and `page_size: 3` (at most 5), without automatic pagination. Here `engram` is the shared store project. Lead with hits under `projects/<name>/` and linked `global/`; only widen to other projects when local recall misses or the question is explicitly cross-project.
2. Fetch/read the 1–3 most relevant routing notes, then expand only into specific linked notes needed for the question. Follow typed relations without loading a broad neighborhood.
3. Synthesize a concise answer, citing the note titles you drew from. If nothing relevant exists, say so plainly (don't invent) and offer to `/engram:remember` it once known.
