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

## Two buckets — decide where a fact lives

The store has exactly two top-level buckets — **`global/`** and **`projects/`** — so you always know where to point.

| Fact | Goes to |
|---|---|
| Reusable across projects (a KMP pattern, how the user works, a general gotcha) | a domain folder under **`~/Engram/global/`** — `global/workflow/`, `global/kmp/`, `global/ios/`, `global/android/`, `global/tooling/`, … |
| Specific to ONE project/app (its config, IDs, this app's internals — e.g. a Firebase bucket name) | **`~/Engram/projects/<name>/`** |
| Derivable cheaply from code/config at point of need | **nowhere** — keep a pointer, re-derive |
| Raw thought to sort later | the **inbox** (`~/Engram/inbox/`), via `/engram:triage` later |

**Promotion rule:** if a project fact turns out reusable, move it from
`projects/<name>/` up to the right `global/<domain>/` folder and leave a thin
link. One fact, one home — never duplicate.

**A well-developed project folder has structure.** Ad-hoc facts can sit flat in
`projects/<name>/`, but a *comprehensive* knowledge base (built by `/engram:scan`)
organizes into sub-folders: `product/` (PM/overview/business/roadmap), `systems/`
(each subsystem), `screens/` (each user-facing surface), `architecture/`
(modules, data model, boundaries). When a repo has **no** `projects/<name>/` notes
yet, OFFER to `/engram:scan` it (ask first) — that surveys the project and builds
this KB in one pass.

**It is ONE store — `~/Engram` — not per-repo brains.** Everything lives under
two sibling buckets: `~/Engram/global/` (reusable knowledge, organized into
domain folders) and `~/Engram/projects/` (one folder per project). That's why
cross-project recall is a single search. Project-specific facts go in
`~/Engram/projects/<project-name>/`, where `<project-name>` is the current git
repo's folder name — create that subfolder automatically the first time you
store project knowledge there (no `/engram:init`, no per-repo files, no
`.mcp.json` pin; memory is never scattered into the repos themselves). When
recalling, search the whole store — a fact from another project is one query
away.

## How to write (basic-memory MCP tools)

Use `write_note` / `edit_note`. Before writing, `search` the graph — if the
note exists, **edit it in place**; never fork a duplicate.

**Keep notes compact — many small nodes beat a few big ones.** This graph is
operational memory for *you* (the agent), not documentation for a human: write
the least that lets a future session act correctly. One concept per note, a
handful of observation lines, no prose paragraphs, no restating code. If you
can't act on a line, don't write it. Compact notes also retrieve better — a
tight note embeds to a sharper vector and surfaces *itself* rather than being
buried inside an essay. When a topic grows, split it into linked notes instead
of letting one balloon.

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

**Search the current project first.** The store is one flat index, so an
unscoped query blends every project's notes together. Lead with what's local:
filter the hits to those under `projects/<current>/` and `global/` (by permalink
prefix) and answer from those first; only widen to a full cross-store search when
the local pass comes up short or the question is explicitly cross-project. Then
use `build_context` to traverse a note plus its linked neighborhood — follow
typed relations over re-deriving facts.

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
  project, `search`/`build_context` the store for this project's notes
  (`projects/<name>/`) + their linked global knowledge *without being asked*.
  Lead with what's already known. Widen to other projects' notes only if the
  local pass misses or the task is explicitly cross-project.
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

**Write the truth, not its history.** Record the fact as it stands now — never
meta-commentary about what some earlier source (native memory, a prior note, a
wrong assumption) *used* to say. "Native memory claimed X but it's actually Y"
is noise — just write "Y". The graph holds current reality, not a changelog of
corrections.

- When a stored fact changes: supersede in place — overwrite the old value and
  delete it. Recency wins; never leave two copies.
