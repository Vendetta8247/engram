---
name: using-the-graph
description: How the Engram knowledge graph works and how to maintain it AUTOMATICALLY. Memory is ambient — proactively recall relevant knowledge before work and capture durable learnings as you go, without being asked. Read this at session start and whenever storing/recalling. Engram (the basic-memory MCP) is the durable memory; never write learnings into CLAUDE.md or MEMORY.md.
user-invocable: false
---

# Using the Engram knowledge graph

Engram is the durable memory. It is a graph of markdown notes, served by the
**basic-memory** MCP. When you learn something worth keeping, or need prior
knowledge, you go here — **not** to `CLAUDE.md` / `MEMORY.md` (those are now
thin pointers to this graph).

## Two tiers — decide where a fact lives

| Fact | Goes to |
|---|---|
| Reusable across projects (e.g. a KMP localization pattern, a Firebase stage/live rule, how the user likes to work) | **global** brain |
| Specific to this one project/app | **project** brain (the pinned project for this repo) |
| Derivable cheaply from code/config at point of need | **nowhere** — keep a pointer, re-derive |
| Raw thought to sort later | the **inbox** (`global/inbox/`), via `/engram:triage` later |

**Promotion rule:** if a project fact turns out reusable, move it to global and
leave the project note as a thin link. One fact, one home — never duplicate.

**Project brains auto-create — the user never runs `/engram:init`.** When you are
about to store project-specific knowledge while working in a repo that has no
Engram project brain yet, **create one first, automatically, without being
asked**: do the `/engram:init` steps (make `<repo>/.engram/`, register the
basic-memory project, write/merge the `.mcp.json` pin, seed an index note that
`applies_to` the global index), then write the note. Do this lazily — only when
there's actually project knowledge to store, so repos you merely browse don't
get an empty brain. `/engram:init` remains as a manual option for deliberately
setting a repo up (and committing the `.mcp.json` pin) ahead of time.

## How to write (basic-memory MCP tools)

Use `write_note` / `edit_note`. Before writing, `search` the graph — if the
note exists, **edit it in place**; never fork a duplicate.

A note = one entity (one concept per file). Use this grammar inside the body so
the graph has real edges:

- **Observations** — categorized facts as list items:
  - `- [fact] habit_entry timestamps are epoch millis`
  - `- [rule] never touch live Firebase without explicit approval`
  - `- [gotcha] SKIE bridges Kotlin List<String?> as [Any] on iOS`
  - `- [cmd] ./gradlew :shared:compileKotlinIosArm64`
- **Typed relations** — wikilinks with a verb:
  - `- uses [[SQLDelight]]`
  - `- applies_to [[kmp/theming]]`
  - `- supersedes [[avatar-system-v1]]`
  - bare `[[X]]` = generic link
- **Frontmatter:** `title`, `type`, `tier` (global|project), `tags`. For volatile
  facts (versions, SKUs, pricing) add an inline `verify before quoting — last
  checked YYYY-MM-DD` line; omit for evergreen rules.

Project notes should `- applies_to [[...]]` the relevant global note rather than
restating it.

## How to read

Use `search` (semantic + full-text) and `build_context` to traverse a note plus
its linked neighborhood. Prefer following typed relations over re-deriving facts.

## Engram OWNS the "remember" verb — never native memory

When the user says **"remember", "note that", "save this", "keep in mind",
"don't forget", "make a note", "for future reference", "log that"** — or
anything that means *store this* — that goes into the **Engram graph** (the
basic-memory MCP), and **never** into Claude's built-in/native memory. Engram
is the single durable store; native memory is superseded. If you ever feel the
native-memory reflex, redirect it to Engram. (A UserPromptSubmit hook also
detects these phrasings and reminds you — but the rule holds with or without it.)

The same applies to recall: "what do you know about…", "did we decide…",
"have we hit this before…" → query the Engram graph, not native memory.

## Automatic, not on-demand (this is the core behavior)

Memory is **ambient** — you maintain it on your own. The user does NOT have to
ask you to remember or recall. `/engram:remember` and `/engram:recall` are
manual overrides; the default is that you do this proactively:

- **Auto-recall** — at session start and before any non-trivial work on a
  project, `search`/`build_context` the project brain + its linked global
  knowledge *without being asked*. Lead with what's already known.
- **Auto-capture** — the moment you learn something durable, write it to the
  graph immediately, mid-task, without being asked: a user preference, a
  correction, a gotcha, a decision-and-its-why, a reusable pattern, a runbook.
  Don't batch it to "later" and don't wait for a command.

**The worth-keeping bar** (so auto-capture stays curated, not noisy) — write it
only if it is **durable** (still true next week), **reusable** (you'd want it on
a future task), and **not trivially derivable** from code/config at the moment
you'd need it. Skip one-off trivia, restated-from-code values, and
conversation-local detail. When in doubt, a terse note beats none — but a
pointer beats a duplicated value.

- When a stored fact changes: supersede in place — overwrite the old value and
  delete it. Recency wins; never leave two copies.
