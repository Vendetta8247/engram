# Portable Markdown and native-memory snapshots

Use this for `/engram:backup` on native Windows or a portable graph snapshot on
any OS. It requires only Python (uv can provide it); no Git, Bash, tar or jq.
This snapshots Markdown and config, not a running Basic Memory SQLite database.
Service/runtime upgrades use the installer's consistent database backup path.

Resolve the actual configured store before running. Write the following
standard-library program to a temporary `.py` outside the store, set `store` to
that path (default shown), then run `uv run --no-project --python 3.12 python
<temporary-script.py>` with native shell quoting. Delete the temporary script
after verification. For a real, explicitly requested Claude memory migration,
set `include_claude = True`; Codex-only backup/adoption leaves it false.

```python
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
import zipfile

store = Path.home() / "Engram"  # substitute the actual configured store
include_claude = False
if not store.is_dir():
    raise SystemExit(f"Engram store not found: {store}")
stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%fZ")
destination = store / "backups" / stamp
destination.mkdir(parents=True, exist_ok=False)
pairs = []
for source in store.rglob("*"):
    relative = source.relative_to(store)
    if any(part in {"backups", ".git"} for part in relative.parts):
        continue
    if source.is_file() and not source.is_symlink():
        if source.suffix.lower() in {".md", ".txt"} or source.name == ".bmignore":
            pairs.append((source, Path("engram") / relative))
settings = Path.home() / ".engram" / "settings.json"
if settings.is_file():
    pairs.append((settings, Path("engram-settings") / "settings.json"))
if include_claude:
    claude = Path.home() / ".claude"
    for name in ("CLAUDE.md", "settings.json", "settings.local.json"):
        source = claude / name
        if source.is_file() and not source.is_symlink():
            pairs.append((source, Path(name)))
    projects = claude / "projects"
    if projects.is_dir():
        for project in projects.iterdir():
            if not project.is_dir() or project.is_symlink():
                continue
            candidates = list((project / "memory").rglob("*"))
            candidates.append(project / "MEMORY.md")
            for source in candidates:
                if source.is_file() and not source.is_symlink():
                    pairs.append((source, source.relative_to(claude)))
manifest = [f"Engram snapshot (UTC): {stamp}", f"Store: {store}"]
for source, relative in sorted(pairs, key=lambda pair: str(pair[1])):
    target = destination / "tree" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest.append(f"{digest}  {target.stat().st_size}  tree/{relative.as_posix()}")
(destination / "manifest.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
with zipfile.ZipFile(destination / "backup.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for source in (destination / "tree").rglob("*"):
        if source.is_file():
            archive.write(source, source.relative_to(destination))
    archive.write(destination / "manifest.txt", "manifest.txt")
with zipfile.ZipFile(destination / "backup.zip") as archive:
    if archive.testzip() is not None:
        raise SystemExit("Snapshot ZIP verification failed; preserve files for inspection")
print(destination)
print((destination / "manifest.txt").read_text(encoding="utf-8"))
```

When `ENGRAM_CONFIG_PATH` overrides settings, snapshot that file instead of the
default `~/.engram/settings.json`. Verify manifest hashes from the copied files
and report skipped/missing sources; a partial failed snapshot is not success.
The snapshot never changes source notes or creates Git commits.

Restore only the requested files: `tree/engram/<relative>` goes to the configured
store, `tree/engram-settings/settings.json` to its original settings path, and
Claude migration `tree/CLAUDE.md`, `tree/settings*.json`, or `tree/projects/...`
to the corresponding `~/.claude/` paths. Show conflicts before overwriting.
Claude migration/revert must retain their explicit confirmation step. Keep
videos, audio, project binaries and rendered exports in their production folders;
this graph snapshot is not a media backup.
