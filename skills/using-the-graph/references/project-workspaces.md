# Project workspaces, including video production

Engram does not require a Git repository or source code. A folder containing a
video brief, scripts, source assets and an editing project is a valid workspace.
The store path shown as `~/Engram` in skills is the default; when an installation
uses a custom store, use the configured path reported by portable `status`.

Resolve the project name in this order:

1. An explicit project name in the user's request or command arguments.
2. The selected/open workspace folder supplied by the client.
3. The Git root, when one exists and no workspace was selected.
4. The current working folder.

Normalize the name to a single safe kebab-case folder component; never allow
`..`, drive prefixes, or directory separators in a project name. Reuse an
existing canonical name when it already identifies this project. An explicit
name wins even when the working directory is elsewhere. Ask for a name/folder
only when no meaningful project can be inferred. Home, the Engram memory store,
and the Engram plugin/cache directory are not implicitly creative projects;
recognize them before the cwd fallback. Explicit work on Engram itself can use
`projects/engram/`.

Create only `projects/<name>/` in the central store, not `.engram`, `.git`, a new
Basic Memory project, or a per-workspace MCP config. One Basic Memory project
named `engram` indexes all `global/` and `projects/` notes. The creative project
name is a tier within it, not the MCP `project` parameter.

For video work, capture verified information a future collaborator needs:

- `brief/`: objective, audience, channel, style references, key message,
  storyboard/script, approvals and decisions with rationale.
- `production/`: editing workflow and timeline/sequence names, audio choices and
  levels, color space/grade, captions/subtitles, tools and reproducible commands.
- `assets/`: source asset paths or IDs, provenance, usage rights/licenses,
  restrictions, version and missing/relink requirements.
- `delivery/`: export codec/container, frame size/rate, aspect ratio, audio and
  caption requirements, destinations, review criteria and delivery state.

Store Markdown notes with file paths/IDs and relevant metadata. Keep videos,
audio, image sequences, source footage, editor binaries and rendered exports in
the production folders. Do not copy or encode them into Engram notes or backups.
Use Windows paths as paths (e.g. `D:\Videos\Launch\edit.prproj`), not shell
commands to execute; quote resolved paths in native commands.

Normal recall stays selective: compact search, then read 1–3 routing notes and
specific links required for the task. [Verified chat continuity](chat-continuity.md)
keeps each chat's active sequence, asset IDs, last export and next edit in its own
checkpoint under `projects/<name>/live/chats/`. Use the actual session ID so two
chats on one video project do not overwrite each other. The checkpoint setting
controls automatic save/verification gates without changing durable capture.
