# Verified continuity for each Codex chat

Use this when saving current progress, resuming after restart/compaction, or
checking recovery. The aim is to restore the work state: objective, completed
progress, decisions and why, exact file/asset references, verification, blockers,
and next action. This is a semantic handoff, not a full chat archive. Keep the
same chat; Engram does not delete, rewrite or clean native Codex history.

## Save during the turn

Consult effective `engram_settings.py status`. Checkpoints default on. When on,
save at meaningful milestones, before long actions, and at the end of each user
turn before the final reply, including short chats. A new prompt marks the chat
dirty; PreToolUse also marks a new work revision before local tools execute, so
work after a milestone save invalidates that older receipt. The final save tool
verifies its own current revision. Some hosted/specialized tools do not expose
these hooks; continue saving after milestones rather than relying only on the
gate. A receipt from an earlier revision does not cover new work. Use the actual
session ID supplied by the lifecycle hook's capture prompt, never a new random
ID or only the project name. Two chats in one project must remain independent.

Read the previous checkpoint before replacing it. Carry forward still-relevant
goals, constraints, accepted decisions, saved artifacts, asset references and
unfinished work. Update the wider work state rather than summarizing only the
latest message. Move lasting knowledge into canonical topic notes as well.

Write a UTF-8 JSON file, at most 32 KiB, with these required fields:

```json
{
  "objective": "Deliver the approved 60-second channel trailer",
  "progress": "Rough cut v3 and caption edits are saved; final mix is pending",
  "decisions": ["Keep the opening shot for audience recognition"],
  "references": ["D:\\Videos\\Trailer\\edit.prproj", "Main sequence v3"],
  "verification": "Reviewed caption timing; final audio and export remain unchecked",
  "blockers": [],
  "next_action": "Check the final mix, then export the review copy"
}
```

`objective`, `progress` and `next_action` must be nonempty strings;
`decisions`, `references` and `blockers` must be lists, and `verification` must
be a string. Record what is actually checked, including checks not yet run.
Keep media and source projects in their production folders. Never include the
full chat, footage, audio, base64 media or bulky tool output in a checkpoint.

Resolve the plugin path, session ID and JSON path before executing:

```sh
uv run --no-project --offline --python 3.12 python "<resolved-plugin-root>/scripts/engram_continuity.py" save --session-id "<actual-session-id>" --file "<checkpoint.json>" --project channel-trailer
```

The installing Codex warms Python with `uv python install 3.12` on every OS.
The quoted CLI works in PowerShell and POSIX shells once placeholders are
resolved. `--project` is optional: it routes to `projects/<name>/live/chats/`;
without a project the helper uses `global/workflow/live/chats/`. The helper
chooses a unique canonical note for the session. Do not replace it with one
shared project checkpoint or a direct unverified `write_note` call.

The helper journals each semantic attempt locally under
`$CODEX_HOME/engram/continuity/<sha-session>/attempts/` (default
`~/.codex/engram/continuity/...`) before contacting MCP. It then writes the
canonical graph note and reads it back exactly. Only a successful readback
produces a verified receipt. Earlier local versions remain available; a failed
save does not replace the previous verified recovery snapshot. Inspect the
result before saying progress is saved. A locally journaled attempt after a
network failure is not a verified graph save; retain it for inspection/retry.

## Verify before ending or compacting

```sh
uv run --no-project --offline --python 3.12 python "<resolved-plugin-root>/scripts/engram_continuity.py" status --session-id "<actual-session-id>"
```

Inspect whether the current generation has a verified, fresh receipt. The
default age limit is 300 seconds (`ENGRAM_CHECKPOINT_MAX_AGE_SECONDS` can change
it). With checkpoints enabled, Stop requires a current-turn checkpoint, and
PreCompact freshly revalidates the remote note. Missing, stale or failed
verification blocks compaction. There is no remaining-token-budget input and
PreCompact cannot ask the model to write a checkpoint; save earlier and use the
Stop continuation to complete/verify the save. If that recovery continuation
still cannot save, report the visible failure and stop rather than claim
success or loop indefinitely.

## Restore after restart or compaction

```sh
uv run --no-project --offline --python 3.12 python "<resolved-plugin-root>/scripts/engram_continuity.py" recover --session-id "<actual-session-id>"
```

Follow the restoration pointer injected on resume. Recover from the validated
graph checkpoint; if the graph is unavailable, use only the last verified local
snapshot, clearly identified as offline and potentially behind any later
unverified attempts. Read its objective, progress, references and next action,
then inspect the referenced production files before continuing. If no verified
snapshot exists, state that recovery is unavailable; do not invent restored
progress. Retain unverified local attempts for inspection and retry rather than
calling them restored/verified. Canonical project knowledge is still recalled
selectively from 1–3 routing notes as needed.

If local continuity files are missing, recovery still checks the graph for this
chat. It preserves the graph note's project route and advances the local revision
without creating a save receipt. Reconcile the recovered progress before saving
again; a direct save cannot replace an existing graph checkpoint until recovery
has confirmed its content and route. Stop and compaction still require a new
verified save. Legacy responses without file-path metadata can restore content,
but cannot safely authorize a replacement after local state loss.

Turning checkpoints off intentionally disables automatic saves and checkpoint
gates; ordinary memory capture/recall and storage protection continue. Explicit
manual saves and access to earlier recovery notes still work. Do not silently
turn the setting back on.

This protects the progress that reached a checked checkpoint; unsaved work and
full conversation wording are not guaranteed recoverable. Local snapshots and
the local graph share the machine's storage: protecting against a lost drive
requires an independently configured backup. Do not add one without the user's
choice.
