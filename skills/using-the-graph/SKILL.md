---
name: using-the-graph
description: How the Engram knowledge graph works and how to maintain it AUTOMATICALLY. Memory is ambient — proactively recall relevant knowledge before work and capture durable learnings as you go, without being asked. Read this at session start and whenever storing/recalling. Engram (the basic-memory MCP) is the durable memory; never write learnings into CLAUDE.md or MEMORY.md.
---

# Using the Engram knowledge graph

Engram is the durable memory and each project's **operational encyclopedia**.
It is a graph of markdown notes, served by the **basic-memory** MCP. A developed
project tier should contain the key product, architecture, subsystem, data,
integration, runbook, convention, decision, and gotcha knowledge needed to work
effectively without reconstructing the project from old chats. Use it instead
of `CLAUDE.md` / `MEMORY.md` (those are thin pointers to this graph).

## Two buckets — decide where a fact lives

The store has exactly two top-level buckets — **`global/`** and **`projects/`** — so you always know where to point.

| Fact | Goes to |
|---|---|
| Reusable across projects (a KMP pattern, how the user works, a general gotcha) | a domain folder under **`~/Engram/global/`** — `global/workflow/`, `global/kmp/`, `global/ios/`, `global/android/`, `global/tooling/`, … |
| Specific to ONE project/app (its config, IDs, this app's internals — e.g. a Firebase bucket name) | **`~/Engram/projects/<name>/`** |
| Routine implementation detail already obvious in code/config | **nowhere** — do not mirror code; store the authoritative pointer when it is needed for orientation |
| Raw thought to sort later | the **inbox** (`~/Engram/inbox/`), via `/engram:triage` later |
| Research or a hypothesis still being tested | temporary `projects/<name>/research/` (or `global/research/` only if truly cross-project); promote or discard when resolved |

**Promotion rule:** if a project fact turns out reusable, move it from
`projects/<name>/` up to the right `global/<domain>/` folder and leave a thin
link. One fact, one home — never duplicate.

**A well-developed project folder has structure.** Ad-hoc facts can sit flat in
`projects/<name>/`, but a *comprehensive* knowledge base (built by `/engram:scan`)
organizes into sub-folders: `product/` (PM/overview/business/roadmap), `systems/`
(each subsystem), `screens/` (each user-facing surface), `architecture/`
(modules, data model, boundaries), `runbooks/` (repeatable operations), and
temporary `research/`. When a repo has **no** `projects/<name>/` notes
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

**Be precise and complete for the concept — structured, not artificially
short.** One concept per note still retrieves better than an omnibus document,
but compactness must never create vague or incomplete knowledge. A technical
note includes the exact details a future agent needs to act correctly: paths and
symbols, boundaries and contracts, schemas/data flow, commands, constraints,
edge cases, failure modes, decisions and why, plus sources or verification dates
where relevant. Do not copy routine source code; record authoritative pointers
and explain how the pieces fit. Split genuinely distinct concerns into linked
notes, but keep all necessary detail for the concept in its canonical note.

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
unscoped query blends every project's notes together. Start with compact
`search`, select and `fetch`/`read` the 1–3 best routing notes under
`projects/<current>/` and linked `global/`, then expand with targeted reads as
the task requires. Do not dump the whole encyclopedia into context. Only widen
to other projects when the local pass misses or the question is explicitly
cross-project. Follow typed relations instead of re-deriving known structure.

## Encyclopedia, live checkpoint, and research are different layers

- **Permanent encyclopedia:** canonical topic notes that explain the project
  precisely enough to work on it. Update these in place as verified reality
  changes.
- **Live checkpoint:** one small mutable handoff for a long active procedure:
  objective, current status, decisions and why, exact refs/commits, verification,
  blockers/safety, and next action. It is not a substitute for topic notes.
- **Temporary research:** evidence and hypotheses still being evaluated. Follow
  [the research lifecycle](references/research-lifecycle.md). When research is
  validated, migrate the stable conclusions into permanent canonical notes and
  remove or reduce the temporary note. Do not let successful research rot in a
  scratch folder.

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
- **Auto-capture** — the moment you learn something durable or verify key
  project knowledge, write it to the graph immediately, mid-task, without being
  asked: product behavior, architecture, subsystem contracts, data flow,
  integrations, runbooks, conventions, user preferences, corrections, gotchas,
  decisions-and-why, and reusable patterns.
  Don't batch it to "later" and don't wait for a command.

**The worth-keeping bar** (so the encyclopedia stays useful, not noisy) — store
knowledge a future task needs to orient, decide, operate, or avoid a known
failure. It must be verified or clearly marked as temporary research. Skip
conversation-local trivia and routine code restatement, but retain exact
authoritative pointers and non-obvious relationships even when the code is the
ultimate source of truth. Prefer a precise pointer over duplicated code and a
specific complete note over a vague terse one.

**Write the truth, not its history.** Record the fact as it stands now — never
meta-commentary about what some earlier source (native memory, a prior note, a
wrong assumption) *used* to say. "Native memory claimed X but it's actually Y"
is noise — just write "Y". The graph holds current reality, not a changelog of
corrections.

- When a stored fact changes: supersede in place — overwrite the old value and
  delete it. Recency wins; never leave two copies.
