---
name: remember
description: Use whenever the user asks to remember, note, save, keep in mind, don't forget, jot down, or log something. Writes it into the Engram knowledge graph (basic-memory MCP), routed to the right tier — NEVER into Claude's native memory. (Routine durable learnings are also captured automatically per the using-the-graph skill; this is the explicit path for a user's save request.)
allowed-tools: Read AskUserQuestion
---

# /engram:remember — capture a fact into the graph

The fact to store is: **$ARGUMENTS**

Follow the `using-the-graph` skill. Steps:

1. **Route it.** Reusable across projects → a domain folder under `~/Engram/global/` (`global/workflow/`, `global/kmp/`, …). Specific to one project → `~/Engram/projects/<name>/`. Unverified research/hypothesis → temporary `projects/<name>/research/`. Do not mirror routine code, but retain authoritative pointers and non-obvious structure needed to work on the project. If routing is genuinely ambiguous, ask one quick question.
2. **Dedup.** `search` the graph for the topic. If a note already covers it, **edit in place** (`edit_note`) — never create a duplicate.
3. **Write** with the conventions: one concept per note; precise and complete enough to act on; observations as `- [fact]/[rule]/[gotcha]/[cmd] …`; typed relations as `- uses/applies_to/supersedes [[…]]`; frontmatter `title/type/tier/tags`; add exact paths/symbols/contracts/commands/edge cases and sources where technically relevant. Mark temporary research explicitly and promote it after validation.
4. **Confirm** back to the user: which note, which tier, and whether it was new or an update.
