# Changelog

## 0.5.1 — 2026-10-18

- Fix a Codex recovery deadlock when context compaction was required before the
  agent could save a fresh checkpoint. Missing, stale or unverified checkpoints
  now produce a recovery warning without blocking native compaction.
- Preserve native history and staged attempts, require reconciliation and a
  verified save after compaction, and retain the verified-save requirement at
  the end of each turn. Automatic checkpoints remain enabled.
- Apply the same recovery behavior when checkpoint storage or the hook runtime
  is unavailable, and add regression coverage for repeated resume attempts.

## 0.5.0 — 2026-10-18

- Add optional automatic checkpoints, enabled by default. Use
  `/engram:checkpoints on|off|status`; ordinary memory remains active when off.
- Add verified, separate recovery records for each Codex chat. Journal semantic
  attempts locally before saving, require exact MCP readback before acknowledging
  a save, and retain prior verified snapshots and failed attempts.
- Recover graph checkpoints when local continuity files are missing, preserving
  their project route and revision before allowing a replacement save.
- Track new prompts and supported local tool activity. Require a current verified
  checkpoint before finishing a turn or compacting, and restore saved progress
  after restart or compaction. Native chat history is preserved.
- Add native Windows Codex hooks using portable Python and PowerShell commands.
  `/engram:setup` guides the installing Codex through machine-specific setup;
  no standalone Windows installer is required.
- Support video production and other creative folders without Git, including
  briefs, scripts, asset references, editing decisions and export settings.
- Keep Unicode project names consistent between Codex and Claude Code.
- Add portable backup guidance and CI checks for Windows, macOS and Linux.

Windows setup and trusted Codex hook behavior still require the target-machine
checks in [the Windows guide](docs/windows.md). Recovery covers verified saved
state; unsaved work, full conversation wording and drive failure are not
guaranteed recoverable. See [chat continuity](skills/using-the-graph/references/chat-continuity.md).
