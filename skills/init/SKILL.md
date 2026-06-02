---
name: init
description: OPTIONAL manual setup of the current repo's project brain. Normally this happens AUTOMATICALLY — the agent auto-creates a repo's project brain the first time it stores project knowledge there (see using-the-graph), so you rarely run this. Use it to deliberately set a repo up + commit the .mcp.json pin ahead of time.
argument-hint: "[project-name]"
allowed-tools: Bash Read Write
---

# /engram:init — create this repo's project brain

Precondition: `/engram:setup` has run. If `~/Engram/global` is missing, tell the user to run `/engram:setup` first.

1. Determine the project name: use `$ARGUMENTS` if given, else the repo directory name (kebab-cased).
2. Create the project store at `<repo>/.engram/` (only if absent). Add `INDEX.md` (a short map-of-content seeded with one line: `- applies_to [[INDEX]]` pointing at the global index).
3. Register a Basic Memory project for it: `basic-memory project add <name> "$(pwd)/.engram"` (check `basic-memory project --help` for exact syntax).
4. Pin this repo to that project: write/merge a committed `.mcp.json` in the repo root that runs the basic-memory MCP with `BASIC_MEMORY_MCP_PROJECT` set to `<name>`, e.g.:
   ```json
   { "mcpServers": { "basic-memory": { "command": "uvx", "args": ["basic-memory", "mcp"], "env": { "BASIC_MEMORY_MCP_PROJECT": "<name>" } } } }
   ```
   If a `.mcp.json` already exists, merge rather than overwrite.
5. Tell the user: project-specific facts now land here and should `- applies_to [[...]]` global notes instead of restating them (see the `using-the-graph` skill). Recommend committing `.engram/` and `.mcp.json` to the repo.
