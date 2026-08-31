---
name: setup
description: Install or repair Engram's single supervised Basic Memory service, shared Codex/Claude MCP connection, project store, and health hooks without migrating native memory. Idempotent and backup-first when upgrading an existing database.
allowed-tools: Bash Read AskUserQuestion
---

# /engram:setup — bootstrap Engram

Set up Engram on this machine. The bundled supervised-service installer supports macOS. On Linux, the graph and plugin conventions remain compatible, but a user-level HTTP service must be configured separately; do not claim turnkey Linux service installation. **Idempotent** — re-running must not clobber existing data. Work through these steps, reporting concisely. If a step is already correct, skip it.

## 1. Prerequisites
- Check `uv` (`command -v uv`). If missing, install via the official installer: `curl -LsSf https://astral.sh/uv/install.sh | sh` — works on macOS and Linux (on Linux it installs to `~/.local/bin`; make sure that's on `PATH`). On Windows, direct the user to https://docs.astral.sh/uv/. Re-check after install.
- Check `git` is available.
- Require `curl` and `jq`: the lifecycle guard uses both for an end-to-end MCP health check. On macOS install missing `jq` with `brew install jq`.

## 2. Pin and stage Basic Memory

- The service command is version-pinned: `uvx --prerelease=allow --from basic-memory==0.23.2 basic-memory mcp`. Do not replace it with an unpinned `uvx basic-memory` invocation.
- Use an Engram-owned config/database directory (`~/Library/Application Support/Engram/basic-memory/` on macOS), not the legacy `~/.basic-memory` database still opened by existing stdio clients.
- Before an upgrade, snapshot the Markdown store, SQLite database, and config with checksums. Seed the new runtime from a consistent SQLite backup, then let 0.23.2 migrate only the copy.
- Never run unattended `basic-memory reindex` on 0.23.2: indexing completes but the CLI can fail to exit while burning a CPU core. Service startup sync is the supported setup path here.

## 3. Create the ONE store (~/Engram)
Everything lives under `~/Engram`, split into exactly two top-level buckets: **`global/`** (reusable knowledge, in domain folders) and **`projects/`** (one folder per project). There are no per-repo brains.
- Create the directory tree (only if absent — never overwrite):
  `~/Engram/global/{workflow,kmp,ios,android,tooling}`, `~/Engram/projects`, and `~/Engram/inbox`.
  (Note: project config like Firebase IDs/buckets is per-project → it lives under `projects/<name>/`, not a `global/firebase/` domain.)
- Preserve an existing Git repository and `.gitignore`, but do not create commits automatically. This user's standing Engram policy forbids agent-created commits in `~/Engram`.
- **Keep `backups/` and `inbox/` out of the search index.** Run `BASIC_MEMORY_CONFIG_DIR="$HOME/Library/Application Support/Engram/basic-memory" bash "${CLAUDE_PLUGIN_ROOT}/scripts/engram-bmignore.sh"` on macOS. Backups are snapshots that would otherwise outrank real notes; the inbox is raw capture that `/engram:triage` reads from disk, not through search.
- Seed `~/Engram/INDEX.md` — a short map-of-content listing the `global/` domains + a `projects/` section. (This file is also the "Engram is set up" sentinel the hooks check.)

## 4. Register and serve the single project

- In the Engram-owned config, add exactly one operational project named `engram` pointing at `~/Engram` and make it the default. A legacy `main` entry may remain, but the MCP server must start with `--project engram`.
- Bind streamable HTTP to loopback only: `http://127.0.0.1:18765/mcp`. Never use `0.0.0.0` for the local memory service.
- On macOS run `bash "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/engram-install-service.sh"`. It discovers the current user's home directory and `uvx`, stages the runtime script, generates and validates the user LaunchAgent, and backs up a changed existing plist before replacing it. Never hand-copy another machine's plist.
- Point Codex's `mcp_servers.engram` at the HTTP URL with `enabled = true`, `required = true`, a 15-second startup timeout, and no stdio-only `env` table. The Claude plugin's `.mcp.json` already declares the same HTTP URL.
- Install the Engram lifecycle hooks. They must check SessionStart and PreCompact immediately and UserPromptSubmit with a five-minute per-chat cache.
- Restart Codex and Claude after switching client configuration. Existing tasks retain their old stdio MCP process until restart; do not kill those processes mid-task.

## 5. Inbox + sync note
- Confirm `~/Engram/inbox/` exists. Tell the user: drop raw thoughts here as markdown from anywhere; `/engram:triage` files them into the graph. To capture from a phone, point Obsidian (or any sync — iCloud/Dropbox/git) at `~/Engram` so the inbox syncs to mobile. Engram mandates no sync provider.

## 6. Verify and report

- Run `scripts/engram-mcp-health.sh --status`. Success requires MCP initialize, diagnostics reporting Basic Memory 0.23.2, and an exact `engram` project constraint; a listening port alone is not success.
- Print the platform-specific recovery command with `scripts/engram-recovery-command.sh`, run it, then repeat the health check and confirm the service PID changed.
- Confirm `codex mcp get engram` and `claude mcp list` resolve the same URL. After the applications restart, verify there is one shared HTTP Basic Memory service and no remaining per-chat stdio Basic Memory processes.
- Summarize the store, runtime, logs, backup/rollback paths, MCP status, inbox, and any old clients still awaiting restart.
- Tell the user: `/engram:adopt` migrates existing Claude memory in (backs up first). No per-repo init is needed — project folders auto-create under `~/Engram/projects/` as you work.

Do NOT migrate or modify native Claude memory here — that's `/engram:adopt`. Do not delete the legacy Basic Memory database until all clients have restarted and the shared service has passed post-restart read/write verification.
