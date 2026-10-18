---
name: setup
description: Install or repair Engram's single supervised Basic Memory service, shared Codex/Claude MCP connection, project store, and health hooks without migrating native memory. Idempotent and backup-first when upgrading an existing database.
allowed-tools: Bash Read AskUserQuestion
---

# /engram:setup — bootstrap Engram

Set up Engram on this machine. macOS includes a supervised-service installer.
On native Windows and Linux, configure the shared service for the actual machine
as part of this skill; there is no separate Windows installer. **Idempotent** — preserve
existing notes/configuration and skip already-correct steps. This installs
memory for software and creative projects; Git and Claude are optional.

Resolve the installed plugin root from client metadata or its known install
path. Commands below use `PLUGIN_ROOT` as shorthand; substitute its resolved
absolute path when the variable is unavailable. `~/Engram` is the default store;
respect an existing configured store path.

## Native Windows — agent-run setup

Use native PowerShell. Another Codex can perform these steps for the user;
there is no standalone Windows installer or required task/wrapper identity.
Native Windows setup has not been tested end to end locally. Complete the
read/write and recovery checks on the target machine before reporting success.

1. Inspect existing Codex MCP settings, Basic Memory configuration/store, and
   the listener on port 18765. Reuse a healthy Engram service and its configured
   store. Preserve unrelated config and data; do not repoint an existing store,
   migrate an unrelated database, or terminate an unrelated listener. Back up
   files before changing their existing configuration.
2. Check Codex, `uv` and `uvx` on PATH. Install missing prerequisites using their
   official instructions; uv's Windows instructions are at
   https://docs.astral.sh/uv/getting-started/installation/. Run
   `uv python install 3.12` so native hooks can use cached Python with `--offline`.
   Do not require Bash, WSL, jq, Git, Claude, or a system Python installation.
3. For a new installation, default the store to `$env:USERPROFILE/Engram` and
   Basic Memory config/database to `$env:LOCALAPPDATA/Engram/basic-memory`.
   Respect an existing configured path. Run the resolved plugin helper:

   ```powershell
   uv run --no-project --python 3.12 python "$env:PLUGIN_ROOT/scripts/engram_portable.py" init-store --store $engramStore --config-dir $engramConfig
   ```

   Set `$engramStore` and `$engramConfig` to the chosen absolute paths first.
   `init-store` creates only missing layout/index and ignore rules; it does not
   install Basic Memory, register a project, or start a service.
4. Register the one Basic Memory project in the scoped config. Run `project add`
   only when `engram` is absent; if present, verify that its path is the chosen
   store. Preserve the caller's environment with `try`/`finally`:

   ```powershell
   $engramPreviousConfig = $env:BASIC_MEMORY_CONFIG_DIR
   try {
       $env:BASIC_MEMORY_CONFIG_DIR = $engramConfig
       uvx --python 3.12 --prerelease=allow --from basic-memory==0.23.2 basic-memory project add engram $engramStore --local --default
       if ($LASTEXITCODE -ne 0) { throw "Engram project registration failed" }
       uvx --python 3.12 --prerelease=allow --from basic-memory==0.23.2 basic-memory project default engram --local
       if ($LASTEXITCODE -ne 0) { throw "Engram default project registration failed" }
   } finally {
       $env:BASIC_MEMORY_CONFIG_DIR = $engramPreviousConfig
   }
   ```

   Check each native command's exit status before continuing. Never run unattended
   `basic-memory reindex` on 0.23.2; service startup sync is the supported path.
5. Start one shared service with `BASIC_MEMORY_CONFIG_DIR` set to the chosen
   directory in that service's own process:

   ```powershell
   uvx --python 3.12 --prerelease=allow --from basic-memory==0.23.2 basic-memory mcp --transport streamable-http --host 127.0.0.1 --port 18765 --path /mcp --project engram
   ```

   Configure appropriate current-user background supervision and logs on the
   actual machine, for example a native scheduled task. Use resolved executable
   paths, correctly quoted arguments, and a startup command that sets its own
   config environment. Verify background survival and restart behavior; record
   the actual supervisor identity, log paths, and exact recovery command in the
   installation's Engram runbook. No fixed task name or shipped wrapper is
   required. The service must remain loopback-only.
6. Merge only Codex's `mcp_servers.engram` table in its existing `config.toml`
   (`CODEX_HOME` when set, otherwise `~/.codex`): URL
   `http://127.0.0.1:18765/mcp`, `enabled = true`, `required = true`,
   `startup_timeout_sec = 15`. Preserve unrelated TOML and remove incompatible
   stdio fields only from the Engram entry being migrated. Merge the marked
   global routing block below, review/trust the plugin hooks, remove duplicate
   Engram hook registrations if present, and restart Codex. Plugin installation
   alone does not start the MCP service.
7. Run the portable helper's `health` and `status` commands through the same uv
   invocation. Require MCP initialize, diagnostics confirming Basic Memory
   0.23.2, and the exact `engram` project constraint. In a fresh Codex chat,
   verify a temporary note can be written, read, updated, recalled and removed
   through MCP. Exercise the recorded service recovery command, then repeat
   health/read verification and check there is only one listener.
8. Complete the verified chat-continuity checks below on this Windows machine,
   including restart/compaction recovery, two chats in the same project and an
   offline failure. Report the actual store, config/log paths, recovery command,
   MCP read/write and continuity results, and effective checkpoint setting.
   Checkpoints default on; normal memory remains active when disabled. A video production folder is a valid
   workspace without Git. Stop here; do not run the POSIX steps or inspect
   Claude memory unless migration was explicitly requested.

## Verify chat continuity in Codex (all platforms)

After ordinary service read/write verification, follow
[chat continuity](../using-the-graph/references/chat-continuity.md) with actual
hook session IDs. Save a small JSON checkpoint, verify its graph readback and
receipt, then restart/resume and exercise compaction recovery. Confirm the
objective/progress/next action are restored and source files still match.
Two chats in one project must have separate graph notes and local snapshots.
Exercise a service outage: failed saves must not claim success or replace the
last verified local snapshot, and enabled PreCompact must block until remote
verification succeeds. Verify a recovered local snapshot is labelled offline.
Turn checkpoints off/on for the check and restore the user's chosen preference;
off must skip automatic saves/gates while normal memory continues. Record what
was actually verified. Local unit tests do not establish native Windows
restart/compaction recovery; the installing Codex must check the target machine.

## Codex global routing instructions (all platforms)

Use `$CODEX_HOME/AGENTS.md` when configured, otherwise `~/.codex/AGENTS.md`.
Preserve existing instructions and replace only the Engram-marked block if it
already exists; do not put project facts in that file. Include this short block
for Codex setup/adoption:

> <!-- engram:start -->
> ## Engram memory
> Use the Engram MCP for durable knowledge. Before non-trivial work, search the
> current project and read only 1–3 relevant routing notes; fall back from
> `search` to bounded `search_notes` if the compact API is unsupported. Capture
> verified durable facts in canonical notes, editing existing notes to dedupe.
> Projects can be ordinary creative folders; Git is optional. Consult effective
> `scripts/engram_settings.py status` before automatic live checkpoints (default
> on). When enabled, follow the plugin's chat-continuity reference: use
> `engram_continuity.py` with the actual hook session ID to save after milestones,
> before long actions and at each turn's end; require verified graph readback.
> Restore the checkpoint pointer on resume. When `checkpoints_enabled` is false,
> skip automatic saves/gates; normal recall/capture and manual saves continue.
> Keep unverified research temporary and promote validated findings.
> <!-- engram:end -->

## macOS/Linux steps

## 1. Prerequisites
- Check `uv` (`command -v uv`). If missing, install via the official installer: `curl -LsSf https://astral.sh/uv/install.sh | sh` — works on macOS and Linux (on Linux it installs to `~/.local/bin`; make sure that's on `PATH`). Re-check after install.
- Run `uv python install 3.12` to warm the interpreter used by continuity hooks with `--offline`, including on macOS/Linux.
- Git is optional; do not install it just to use Engram.
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
- **Keep `backups/` and `inbox/` out of the search index.** Run `BASIC_MEMORY_CONFIG_DIR="$HOME/Library/Application Support/Engram/basic-memory" bash "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/engram-bmignore.sh"` on macOS. Backups are snapshots that would otherwise outrank real notes; the inbox is raw capture that `/engram:triage` reads from disk, not through search.
- Seed `~/Engram/INDEX.md` — a short map-of-content listing the `global/` domains + a `projects/` section. (This file is also the "Engram is set up" sentinel the hooks check.)

## 4. Register and serve the single project

- In the Engram-owned config, add exactly one operational project named `engram` pointing at `~/Engram` and make it the default. A legacy `main` entry may remain, but the MCP server must start with `--project engram`.
- Bind streamable HTTP to loopback only: `http://127.0.0.1:18765/mcp`. Never use `0.0.0.0` for the local memory service.
- On macOS run `bash "${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/engram-install-service.sh"`. It discovers the current user's home directory and `uvx`, stages the runtime script, generates and validates the user LaunchAgent, and backs up a changed existing plist before replacing it. Never hand-copy another machine's plist.
- Point Codex's `mcp_servers.engram` at the HTTP URL with `enabled = true`, `required = true`, a 15-second startup timeout, and no stdio-only `env` table. The Claude plugin's `.mcp.json` already declares the same HTTP URL.
- Install the Engram lifecycle hooks. They must check SessionStart and PreCompact immediately and UserPromptSubmit with a five-minute per-chat cache.
- Restart each configured client after switching its configuration. Existing tasks retain their old stdio MCP process until restart; do not kill those processes mid-task.

## 5. Inbox + sync note
- Confirm `~/Engram/inbox/` exists. Tell the user: drop raw thoughts here as markdown from anywhere; `/engram:triage` files them into the graph. To capture from a phone, point Obsidian (or any sync — iCloud/Dropbox/git) at `~/Engram` so the inbox syncs to mobile. Engram mandates no sync provider.

## 6. Verify and report

- Run `scripts/engram-mcp-health.sh --status`. Success requires MCP initialize, diagnostics reporting Basic Memory 0.23.2, and an exact `engram` project constraint; a listening port alone is not success.
- Print the platform-specific recovery command with `scripts/engram-recovery-command.sh`, run it, then repeat the health check and confirm the service PID changed.
- For each installed client, confirm `codex mcp get engram` or `claude mcp list` resolves the shared URL; do not require Claude for Codex-only setup. After the applications restart, verify there is one shared HTTP Basic Memory service and no remaining per-chat stdio Basic Memory processes.
- Complete the verified chat-continuity checks above for Codex. Summarize the store, runtime, logs, backup/rollback paths, MCP and continuity status, inbox, and any old clients still awaiting restart.
- For Codex, merge the global routing block above. Report effective checkpoint settings (default on); `/engram:checkpoints off` disables automatic checkpoints while normal memory continues. `/engram:adopt` also supports Codex-only onboarding; actual Claude memory migration is an explicit separate mode with backup/confirmation. No per-repo init is required: project folders auto-create in the central store.

Do NOT migrate or modify native Claude memory here — that's `/engram:adopt`. Do not delete the legacy Basic Memory database until all clients have restarted and the shared service has passed post-restart read/write verification.
