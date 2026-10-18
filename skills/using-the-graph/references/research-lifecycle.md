# Research lifecycle

Use this only for knowledge that is not yet established enough for the permanent
project encyclopedia.

## Stage

Write project research under `projects/<name>/research/`; use `global/research/`
only when the question genuinely spans projects. Mark the note with:

- `status: active | validated | rejected | abandoned`
- `temporary: true`
- the question or decision the research must resolve
- dated sources/evidence and exact experiment or verification steps
- hypotheses, contradictions, confidence, and open questions
- the owner/next action and a review date when research may linger

Keep raw excerpts or bulky generated artifacts outside permanent topic notes;
link to their source or file instead of flooding the graph.

## Resolve

When the research reaches a conclusion:

1. Verify it against authoritative sources, code, or a reproducible experiment.
2. Migrate stable facts, decisions and rationale into the canonical permanent
   notes under `product/`, `systems/`, `screens/`, `architecture/`, `runbooks/`,
   creative `brief/`, `production/`, `assets/`, `delivery/`, or the appropriate
   global domain. Include exact sources and verification date
   where the claim can change.
3. Update the project `INDEX.md` or relations so the canonical knowledge is
   discoverable.
4. Confirm that no unique actionable knowledge remains only in the temporary
   note.
5. Remove the temporary note, or reduce it to a short pointer when provenance is
   genuinely useful. MCP writes update the index; direct file changes use the
   supervised service startup sync, then a bounded search to verify. Never run
   unattended `basic-memory reindex` on 0.23.2 (it can fail to exit).

Rejected research is not automatically permanent. Preserve only a reusable
negative finding—what was tested, why it failed, and the conditions—otherwise
discard it. Abandoned research must retain a next action/review date or be
removed; do not maintain an indefinite scratch archive.
