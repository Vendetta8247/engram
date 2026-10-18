# 🧠 Engram

**Durable, graph-shaped memory for Codex and Claude Code — a second brain, shared across every project.**

Engram replaces ad-hoc agent memory with a knowledge graph stored as **plain markdown** (Obsidian-browsable, optionally versioned in Git) and queried over MCP. One store, two buckets: **`global/`** carries reusable knowledge across all your projects, and **`projects/<name>/`** is each project's operational encyclopedia. Codex and Claude recall from it before work and write to it as they learn — automatically.

> Built on [Basic Memory](https://github.com/basicmachines-co/basic-memory). Engram packages it with a two-tier layout, conventions, automatic recall/capture, optional verified per-chat checkpoints, a phone-friendly capture inbox, and a safe migration off Claude's native memory. A shared-service installer is included for **macOS**. On **native Windows Codex**, `/engram:setup` guides the installing agent through configuring the local service; Linux also needs a machine-specific user service. Software, video production, and other creative projects can share the same memory workflow; a Git repository is optional.

## Why

- **Future-proof.** Your memory is a folder of Markdown files; Git versioning is optional. No proprietary database is ever the source of truth. Readable with `cat` in 20 years; openable in Obsidian today.
- **A graph, not a list.** Entities + typed relations (`uses`, `supersedes`, `applies_to`), so knowledge is *traversable*, not grepped.
- **Two buckets, no duplication.** Reusable patterns live once in `global/`; each project's facts live in `projects/<name>/` and link up.
- **Agents actually consult it.** A session-start briefing plus read/write MCP tools mid-task — not "hope it gets recalled."
- **Precise by design.** Notes are concept-scoped and structured, but technically complete: exact entry points, contracts, data flow, commands, constraints, edge cases, decisions, and sources where needed.
- **Capture from anywhere.** A markdown inbox you can sync to your phone (Obsidian or any sync); triage curates it into the graph.
- **Safe & reversible.** Going live backs up *everything* first and waits for your explicit yes; one command puts native memory back.

## How to install

**Native Windows with Codex:** ask Codex to install this plugin and run `/engram:setup`, following [the Windows setup guide](docs/windows.md). Codex configures uv-managed Python and an appropriate background service on that machine. WSL, Git Bash, `jq`, a Git repository, and Claude Code are not required. There is no standalone Windows installer; the installing Codex must verify real memory read/write and service recovery on the target machine. Native Windows end-to-end setup has not been exercised locally.

**macOS / Linux prerequisites:** Codex and/or [Claude Code](https://claude.com/claude-code), [uv](https://docs.astral.sh/uv/), `curl`, and `jq`. Git is needed for the plugin marketplace installation below, not for the projects you work on. The macOS service installer discovers the installing user's home directory and `uvx`; no developer-specific absolute paths are shipped.

For **Codex-only** use, install the plugin and run `/engram:setup`; `/engram:adopt` also recognizes Codex-only setup and skips Claude memory migration. The adoption instructions below apply when migrating existing Claude memory.

```bash
# 1. add this repo as a plugin marketplace
/plugin marketplace add vendetta8247/engram

# 2. install the plugin
/plugin install engram@engram

# 3. go live — ONE command. Self-bootstraps (installs Basic Memory + builds your
#    store under ~/Engram), backs up all native memory, and switches memory over.
#    It backs up first and waits for your explicit confirmation before changing anything.
/engram:adopt
```

That's the whole setup. `/engram:adopt` self-bootstraps everything (you don't need `/engram:setup` first). When it finishes, it offers to **scan** the current project into a knowledge base — say yes, or do it later with `/engram:scan`.

### Codex integration

Engram includes a Codex manifest and a Codex-specific lifecycle adapter while preserving Claude compatibility. On macOS, Codex and Claude share one Basic Memory 0.23.2 streamable-HTTP process supervised by `launchd`; new chats no longer spawn one indexing process each. The service binds only to `127.0.0.1:18765` and is constrained to the `engram` project.

The macOS service is installed from the plugin source with `bash scripts/engram-install-service.sh`. The installer generates `~/Library/LaunchAgents/com.yegor.engram.basic-memory.plist` for the current account, discovers `uvx`, validates the plist, and backs up a changed existing plist before replacing it. The `com.yegor...` string is a stable service identifier, not a username or machine binding.

Every chat checks the service through a real MCP initialize + diagnostics + project handshake. `SessionStart` and `PreCompact` checks are uncached; `UserPromptSubmit` checks are cached for five minutes per chat. An outage produces one visible warning, keeps the offline policy in agent context, forbids claims of durable capture, and, when checkpoints are enabled, blocks Codex compaction until checkpoint storage recovers. Recovery is announced once. Codex also marks the MCP server `required`, so a new or resumed task cannot silently start without it.

With checkpoints enabled, each Codex chat saves a checked handoff after milestones, before long actions, and at every turn's end—even in short chats. It records the objective, progress, decisions, references, verification, blockers and next action. `engram_continuity.py` first journals the attempt locally, writes that chat's own graph note, and reads it back exactly before recording a verified receipt. Two chats working on the same project do not overwrite one another. New prompts and supported local tool calls mark the work dirty, so a mid-turn save does not cover later tool activity. Stop requires a verified checkpoint for the current revision; PreCompact freshly revalidates the remote note and blocks on a missing, stale or failed save. Receipts default to a five-minute freshness limit (`ENGRAM_CHECKPOINT_MAX_AGE_SECONDS`).

On restart or after compaction, the chat receives a restoration pointer to its validated checkpoint. If the graph is unavailable, the helper can restore the last verified local snapshot and clearly labels it offline; failed attempts remain journaled for inspection/retry. The same chat continues, and native Codex history is left untouched. See [the continuity workflow and save/status/recover commands](skills/using-the-graph/references/chat-continuity.md).

This restores progress that reached a verified checkpoint, including exact production-file references. It is not a full transcript archive or a guarantee for unsaved work. The graph and local snapshots share the machine's storage; recovery from a lost drive requires an independent backup chosen by the user.

Permanent knowledge remains in canonical encyclopedia notes. Unverified research stays temporary until validated conclusions are promoted or discarded.

**Checkpoints are optional and on by default.** Run `/engram:checkpoints off`, `/engram:checkpoints on`, or `/engram:checkpoints status`. The preference persists in `~/.engram/settings.json` (`%USERPROFILE%\.engram\settings.json` on Windows). Turning them off disables automatic checkpoint saves and verification gates, reducing automatic per-chat progress recovery. Selective recall, ordinary durable capture, availability warnings, and native-history storage limits remain active. Existing recovery notes remain accessible and explicit manual saves still work; Engram does not silently change the preference.

The setting can also be changed directly from the plugin source:

```sh
uv run --no-project --python 3.12 python scripts/engram_settings.py checkpoints off
uv run --no-project --python 3.12 python scripts/engram_settings.py status
```

`ENGRAM_CONFIG_PATH` selects another settings file. `ENGRAM_CHECKPOINTS_ENABLED=true|false` overrides the saved preference (also accepts `on|off` and `1|0`); status reports the effective value and its source. Invalid settings report an error instead of silently changing behavior. Preferences are user-wide, including future chats; hooks read them on each invocation. The plugin must be installed/enabled and its hooks trusted. A host restart may be needed after plugin updates.

Checkpoint verification applies from the first turn, independently of saved-history size. Default storage limits:
- At **2 GiB per task**, normal work is blocked at an emergency boundary. The same responsibility task is retained; only checkpoint, recovery, and verified history-maintenance work remains allowed.
- At **40 GiB total** under `~/.codex/sessions`, Codex warns that aggregate history is approaching its ceiling.
- At **50 GiB total**, normal prompts are blocked until old tasks are cleaned or archived.
- If installed while history is already over 50 GiB, Engram records a one-time legacy baseline and permits at most **512 MiB** of additional growth. Once cleanup drops below 50 GiB, it permanently switches to the absolute cap.

The guard never copies transcripts into Engram or automatically deletes, cleans, or rewrites native Codex history. These boundaries measure saved history bytes, not the model's remaining token budget. The agent saves checkpoints earlier in the turn; PreCompact cannot make the model write one during the hook, so it only allows compaction after fresh remote validation. A failed recovery continuation is reported visibly instead of being treated as a successful save.

Useful commands:

- `scripts/engram-status.sh` — full MCP, launchd, process-count, and Codex-history status.
- `scripts/engram-codex-hook.sh --status` — active history mode and thresholds.
- `scripts/engram_continuity.py save|status|recover` — verified progress for the actual current chat session ID; see the continuity workflow for arguments.
- `scripts/engram-recovery-command.sh` — print the platform-appropriate service restart command.
- `scripts/engram-install-service.sh` — install or repair the current macOS user's shared service.

Limits can be overridden with the `ENGRAM_CODEX_*` environment variables documented in the adapter.

Want to try it *alongside* native memory before committing? Run `/engram:setup` (install only, no takeover), then `/engram:adopt` when ready. Changed your mind after adopting? `/engram:revert` restores native memory exactly as it was.

## Using Engram

Once you're live, memory is **ambient** — you mostly don't run commands:

- **It recalls automatically.** Before non-trivial work, Claude searches the store (current project first, then global) and leads with what's already known.
- **It captures automatically.** The moment Claude learns something durable — a preference, a correction, a gotcha, a decision and its *why*, a reusable pattern — it writes a compact note to the graph, mid-task, without being asked.
- **You can still drive it by hand.** "Remember that…" / "what do you know about…" route to the graph (never native memory). Or use `/engram:remember` and `/engram:recall` explicitly.
- **Onboard a project** with `/engram:scan` — it builds a structured, cross-linked KB under `projects/<name>/`. For a video project, this can cover the creative brief, audience, scripts/storyboards, source assets, editing conventions, audio/color/captions, export presets, feedback, and delivery requirements. Keep media in its production folders; notes retain paths, IDs, and decisions. Start with written materials and metadata, and inspect media only as needed.
- **Capture on the go.** Drop raw notes into `~/Engram/inbox/` from anywhere (point Obsidian/iCloud/Dropbox/git at `~/Engram` to sync from your phone); `/engram:triage` files them into the graph later.
- **Browse it like a human.** Open `~/Engram` in Obsidian — it's just markdown with wikilinks.

## Commands you run

| Command | What it does |
|---|---|
| `/engram:adopt` | **Go live.** Codex-only use runs setup and installs the routing directive. An explicit Claude migration backs up first, confirms, migrates global memory, and defers per-project migration to `/engram:scan`. |
| `/engram:revert` | **Go back.** Remove Codex's marked routing block, or restore an explicitly migrated Claude memory backup. Preserve the graph. |
| `/engram:scan` | **Onboard a project.** Seeds from the project's backed-up native memory, surveys the repo, writes **compact, agent-readable** notes into `projects/<name>/`, then runs a consolidation pass that dedups and tightens them. Pick **depth** (overview / map / exhaustive — coverage, not note size) and **engine** (single agent / multiple agents / workflow). Re-run to refresh after big changes. |
| `/engram:remember <fact>` | Capture a fact into the graph (auto-routes global vs project). Mostly automatic — this is the manual override. |
| `/engram:recall <query>` | Query + traverse the graph. Mostly automatic — this is the manual override. |
| `/engram:triage` | Process the capture inbox into the curated graph. |
| `/engram:checkpoints on\|off\|status` | Control verified per-chat progress checkpoints and their gates; normal memory remains active. |
| `/engram:backup` | Snapshot graph notes/settings; include Claude memory only when requested. |
| `/engram:status` | Show service/config, current chat checkpoint verification, note counts and backups. |
| `/engram:setup` | *Optional.* Install + create the store **without** taking over native memory — to try Engram alongside native memory first. (`adopt` does this for you.) |
| `/engram:init` | *Optional / rarely needed.* A project's folder auto-creates the first time you store project knowledge. Use this only to set one up deliberately ahead of time. |

## Internal / automatic (you don't run these)

- **`using-the-graph`** — *internal skill* (not user-invocable). The behavior spec the agent loads to know how to recall, route, and write notes. It's the brain behind the automatic recall/capture; you never type it.
- **Hooks** (run by Claude Code, no action from you):
  - *SessionStart* — briefs the agent that memory is active and to recall before work.
  - *UserPromptSubmit* — when your prompt looks like "remember…", deterministically routes it to Engram (needs `jq`; a no-op if absent).
  - *PreCompact* — on Codex, remotely revalidates the current chat checkpoint before allowing compaction when enabled.
  - *Stop* — on Codex, requests a verified current-turn save before the turn completes when enabled.

## How it's laid out

```
~/Engram/                 ← ONE store (open this in Obsidian; one searchable graph)
   global/                 ← reusable knowledge, in domain folders
     workflow/ kmp/ ios/ android/ tooling/ ...
   projects/
     my-app/  api/  ...    ← each project's own facts (config, internals)
   inbox/                  ← capture inbox (sync to your phone via Obsidian/iCloud/git)
```

Two top-level buckets: **`global/`** (reusable across projects) and **`projects/`** (per project). Everything lives in `~/Engram`, so a fact from any project is one search away. No per-repo files.

## Requirements

- **Codex or Claude Code** — the host; native Windows setup targets Codex.
- **[uv](https://docs.astral.sh/uv/)** — supplies Python and runs pinned Basic Memory.
- **curl + jq** — used by macOS/Linux shell hooks; native Windows uses Python.
- **Git** *(optional)* — for versioning the store; creative workspaces do not need repositories.
- **[Obsidian](https://obsidian.md)** *(optional)* — to browse/edit the graph as a human.

## Safety

Going live never destroys anything: `/engram:adopt` backs up all native memory (a timestamped tree + tarball + manifest) *before* it touches a thing, shows you the manifest, and waits for an explicit yes. It leaves your native files in place and only flips native auto-memory off. `/engram:revert` puts it all back. Graph snapshots are available through `/engram:backup`; Git versioning is optional.

## License

MIT (Engram). [Basic Memory](https://github.com/basicmachines-co/basic-memory) is an AGPL-3.0 dependency that Engram installs and calls over MCP — it is not redistributed in this repository.
