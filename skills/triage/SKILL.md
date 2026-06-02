---
name: triage
description: Process the Engram capture inbox — file each raw thought into the curated graph, park it, or drop it. The capture→curation step.
argument-hint: ""
allowed-tools: Bash Read AskUserQuestion
---

# /engram:triage — process the capture inbox

The inbox is raw, frictionless capture (often from a phone). Curating it into the graph is a separate job — this command.

1. List inbox items: files under `~/.engram/global/inbox/` (`*.md`, `*.txt`). If empty, say so and stop.
2. For EACH item, read it and surface it to the user with a proposed disposition:
   - **File it** → write a graph note (route global vs project per the `using-the-graph` skill, dedup first), then remove the inbox file.
   - **Park it** → leave in inbox (or move to an `inbox/parked/` subfolder) with a one-line note on why.
   - **Drop it** → delete with a brief reason in the summary (don't silently discard).
3. Work through them efficiently; batch obviously-similar items. Confirm ambiguous routing with the user rather than guessing.
4. Report: N filed (to which tiers/notes), N parked, N dropped. Leave the inbox empty (or only parked items).
