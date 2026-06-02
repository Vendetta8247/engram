---
name: remember
description: MANUAL OVERRIDE to force-save a specific fact into the Engram graph now. Routine capture is automatic (the agent writes durable learnings on its own — see the using-the-graph skill); use this only when the user explicitly wants something saved.
argument-hint: "<the fact to remember>"
allowed-tools: Read AskUserQuestion
---

# /engram:remember — capture a fact into the graph

The fact to store is: **$ARGUMENTS**

Follow the `using-the-graph` skill. Steps:

1. **Route it.** Reusable across projects → global brain. Specific to the current project → this repo's project brain. Derivable cheaply from code/config → don't store it; tell the user and stop. If the tier is genuinely ambiguous, ask (one quick question).
2. **Dedup.** `search` the graph for the topic. If a note already covers it, **edit in place** (`edit_note`) — never create a duplicate.
3. **Write** with the conventions: one concept per note; observations as `- [fact]/[rule]/[gotcha]/[cmd] …`; typed relations as `- uses/applies_to/supersedes [[…]]`; frontmatter `title/type/tier/tags`; add `verify before quoting — last checked <today>` only if the fact is volatile.
4. **Confirm** back to the user: which note, which tier, and whether it was new or an update.
