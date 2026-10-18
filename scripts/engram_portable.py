#!/usr/bin/env python3
"""Native Windows Codex adapter. Standard library only; no Bash, jq, or Git needed."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile
import time
import urllib.request

from engram_settings import SettingsError, load_settings, settings_path
from engram_continuity import Continuity, ContinuityError

VERSION = "0.23.2"
ENDPOINT = "http://127.0.0.1:18765/mcp"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
MEMORY_POLICY = (
    "ENGRAM MEMORY: Maintain this project's operational encyclopedia. Before non-trivial work, "
    "use compact search and read only 1-3 relevant routing notes; expand with targeted reads. "
    "If compact search reports Unsupported MCP client, use search_notes with page_size=3. "
    "Capture verified knowledge, preferences, decisions and why, source/asset paths, contracts, "
    "workflow settings, commands, constraints, and gotchas in precise canonical topic notes. "
    "Search before writing and update existing notes. Keep unverified research temporary, then "
    "promote or discard it. Never copy transcripts or media binaries into the memory store. "
    "Projects may be software, video, or other creative work; Git is optional."
)
CHECKPOINT_POLICY = (
    "Preserve chat progress before finishing each turn and after material milestones. "
    "Save a per-chat recovery checkpoint with objective, progress, decisions and why, "
    "exact source/asset references, verification, blockers, and next action. A save is confirmed "
    "only after the continuity helper reads the same content back from Engram. Keep permanent "
    "knowledge in canonical topic notes and native chat history intact. Never paste the chat transcript."
)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return {} if default is None else default
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def human_bytes(value: int) -> str:
    if value >= 1024**3:
        return f"{value / 1024**3:.1f} GiB"
    return f"{value / 1024**2:.1f} MiB"


def positive_int(environ: dict, name: str, default: int) -> int:
    raw = str(environ.get(name, default))
    if not raw.isdecimal() or int(raw) <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(raw)


def decode_rpc(body: bytes, request_id: int) -> dict:
    text = body.decode("utf-8-sig")
    messages = []
    try:
        messages.append(json.loads(text))
    except json.JSONDecodeError:
        # Streamable HTTP may return SSE rather than a single JSON response.
        for event in re.split(r"\r?\n\r?\n", text):
            data = "\n".join(line[5:].lstrip() for line in event.splitlines() if line.startswith("data:"))
            if data:
                messages.append(json.loads(data))
    for message in messages:
        if isinstance(message, dict) and message.get("id") == request_id:
            if "error" in message:
                raise ValueError(f"MCP request failed: {message['error'].get('message', 'unknown error')}")
            return message.get("result", {})
    raise ValueError("MCP response did not contain the requested result")


def probe(environ: dict | None = None) -> dict:
    env = os.environ if environ is None else environ
    endpoint = env.get("ENGRAM_MCP_URL", ENDPOINT)
    expected_version = env.get("ENGRAM_BASIC_MEMORY_VERSION", VERSION)
    expected_project = env.get("ENGRAM_MCP_PROJECT", "engram")
    session = None
    # Local memory never needs HTTP proxies, including on corporate Windows hosts.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

    def request(payload: dict, request_id: int | None = None) -> tuple[dict, object]:
        req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers=headers)
        with opener.open(req, timeout=3) as response:
            body = response.read()
            return (decode_rpc(body, request_id) if request_id is not None else {}), response.headers

    result = {"healthy": False, "endpoint": endpoint, "expectedVersion": expected_version,
              "expectedProject": expected_project}
    try:
        initialized, response_headers = request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "engram-portable-health", "version": "1"}}}, 1)
        if not initialized.get("serverInfo"):
            raise ValueError("MCP initialize did not identify a server")
        session = response_headers.get("Mcp-Session-Id")
        if session:
            headers["Mcp-Session-Id"] = session
        headers["MCP-Protocol-Version"] = initialized.get("protocolVersion", "2025-06-18")
        request({"jsonrpc": "2.0", "method": "notifications/initialized"})
        diagnostic, _ = request({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "basic_memory_diagnostics", "arguments": {}}}, 2)
        diagnostic_text = "\n".join(item.get("text", "") for item in diagnostic.get("content", []) if item.get("type") == "text")
        if diagnostic.get("isError") or not re.search(r"basic-memory:\s*" + re.escape(expected_version) + r"(?:\s|$)", diagnostic_text):
            raise ValueError(f"Diagnostics did not confirm Basic Memory {expected_version}")
        projects, _ = request({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "list_memory_projects", "arguments": {"output_format": "json"}}}, 3)
        data = projects.get("structuredContent", {}).get("result")
        if data is None:
            for item in projects.get("content", []):
                if item.get("type") == "text":
                    try:
                        data = json.loads(item["text"])
                        break
                    except (ValueError, KeyError):
                        continue
        if projects.get("isError") or not isinstance(data, dict) or data.get("constrained_project") != expected_project:
            raise ValueError(f"Server is not constrained to project {expected_project}")
        for project in data.get("projects", []):
            if project.get("name") == expected_project:
                result["store_path"] = project.get("local_path") or project.get("path")
                break
        result.update(healthy=True, detail=f"Basic Memory {expected_version}; project {expected_project}")
    except (OSError, ValueError, KeyError) as error:
        result["detail"] = str(error)[:240]
    finally:
        if session:
            try:
                req = urllib.request.Request(endpoint, method="DELETE", headers=headers)
                with opener.open(req, timeout=1):
                    pass
            except OSError:
                pass
    return result


def health_for_hook(event: str, session_id: str, environ: dict) -> dict:
    codex_dir = Path(environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    state_dir = Path(environ.get("ENGRAM_HEALTH_STATE_DIR", str(codex_dir / "engram" / "health")))
    key = hashlib.sha256(session_id.encode()).hexdigest()[:24]
    path = state_dir / f"codex-{key}.json"
    previous = read_json(path)
    now = time.time()
    cache_seconds = positive_int(environ, "ENGRAM_HEALTH_CACHE_SECONDS", 300)
    if event not in ("SessionStart", "PreCompact") and 0 <= now - previous.get("checkedAt", 0) < cache_seconds:
        if isinstance(previous.get("healthy"), bool):
            return dict(previous, notify=False, message="")
    result = probe(environ)
    if not result.get("store_path") and previous.get("store_path"):
        result["store_path"] = previous["store_path"]
    result["checkedAt"] = now
    result["notify"] = previous.get("healthy") is not result["healthy"]
    if result["healthy"]:
        result["message"] = "ENGRAM RECOVERED: durable recall and capture are available again." if previous.get("healthy") is False else ""
    else:
        result["message"] = "ENGRAM UNAVAILABLE: " + result["detail"] + ". Restart the configured Engram Basic Memory service. Do not claim durable saves or prune native history."
    atomic_text(path, json.dumps(result))
    return result


def resolve_project(cwd: str | None = None, name: str | None = None, workspace: str | None = None,
                    environ: dict | None = None, store_path: str | None = None) -> dict:
    env = os.environ if environ is None else environ
    explicit = name or env.get("ENGRAM_PROJECT_NAME")
    root = Path(workspace or cwd).expanduser().resolve() if (workspace or cwd) else None
    if not explicit and root:
        excluded = {Path.home().resolve(), (Path.home() / "Engram").resolve()}
        configured_store = store_path or env.get("ENGRAM_STORE_PATH")
        if configured_store:
            excluded.add(Path(configured_store).expanduser().resolve())
        if not (PLUGIN_ROOT / ".git").exists():
            excluded.add(PLUGIN_ROOT)
        is_memory_store = (root / "INDEX.md").is_file() and all((root / child).is_dir() for child in ("global", "projects", "inbox"))
        if root in excluded or root == Path(root.anchor) or is_memory_store:
            root = None
        elif not workspace:
            # Discover a repository without requiring Git to be installed.
            for candidate in (root, *root.parents):
                if (candidate / ".git").exists():
                    root = candidate
                    break
        # A subdirectory can discover an excluded repository/store root.
        # Recheck after Git-root discovery as well as before it. Home itself is
        # excluded, but ordinary workspaces below Home remain valid projects.
        if root is not None:
            is_memory_store = (root / "INDEX.md").is_file() and all((root / child).is_dir() for child in ("global", "projects", "inbox"))
            if root in excluded or is_memory_store or any(parent in excluded - {Path.home().resolve()} for parent in root.parents):
                root = None
    raw_name = explicit or (root.name if root else "")
    slug = re.sub(r"[\W_]+", "-", raw_name.casefold(), flags=re.UNICODE).strip("-")
    if explicit and not slug:
        raise ValueError("Project name must contain letters or numbers")
    return {"name": slug or None, "directory": f"projects/{slug}" if slug else "global",
            "root": str(root) if root else None}


class HistoryGuard:
    def __init__(self, payload: dict, environ: dict, persist: bool = True):
        codex_dir = Path(environ.get("CODEX_HOME", str(Path.home() / ".codex")))
        self.state = Path(environ.get("ENGRAM_CODEX_STATE_DIR", str(codex_dir / "engram")))
        sessions = Path(environ.get("ENGRAM_CODEX_SESSIONS_DIR", str(codex_dir / "sessions")))
        self.session_bytes = Path(payload["transcript_path"]).stat().st_size if payload.get("transcript_path") and Path(payload["transcript_path"]).is_file() else 0
        self.total_bytes = 0
        if sessions.exists():
            for directory, children, files in os.walk(sessions):
                children[:] = [child for child in children if not (Path(directory) / child).is_symlink()]
                for filename in files:
                    path = Path(directory) / filename
                    if not path.is_symlink():
                        try:
                            self.total_bytes += path.stat().st_size
                        except FileNotFoundError:
                            pass  # A concurrently archived session is no longer retained.
        self.soft = positive_int(environ, "ENGRAM_CODEX_SESSION_SOFT_MIB", 256) * 1024**2
        self.hard = positive_int(environ, "ENGRAM_CODEX_SESSION_HARD_MIB", 2048) * 1024**2
        total_soft = positive_int(environ, "ENGRAM_CODEX_TOTAL_SOFT_GIB", 40) * 1024**3
        total_hard = positive_int(environ, "ENGRAM_CODEX_TOTAL_HARD_GIB", 50) * 1024**3
        if self.soft > self.hard or total_soft > total_hard:
            raise ValueError("History warning boundaries must not exceed hard boundaries")
        mode_path = self.state / "history-guard-mode"
        baseline_path = self.state / "history-guard-legacy-baseline-bytes"
        self.mode = mode_path.read_text().strip() if mode_path.exists() else ""
        if self.mode not in ("legacy", "absolute"):
            self.mode = "legacy" if self.total_bytes >= total_hard else "absolute"
            if persist:
                if self.mode == "legacy":
                    atomic_text(baseline_path, str(self.total_bytes))
                atomic_text(mode_path, self.mode)
        if self.mode == "legacy" and self.total_bytes < total_hard:
            self.mode = "absolute"
            if persist:
                atomic_text(mode_path, self.mode)
        if self.mode == "legacy":
            baseline = int(baseline_path.read_text()) if baseline_path.exists() else self.total_bytes
            if persist and not baseline_path.exists():
                atomic_text(baseline_path, str(baseline))
            growth = positive_int(environ, "ENGRAM_CODEX_LEGACY_GROWTH_MIB", 512) * 1024**2
            self.total_soft, self.total_hard = baseline + growth // 2, baseline + growth
        else:
            self.total_soft, self.total_hard = total_soft, total_hard
            if persist:
                atomic_text(self.state / "history-guard-clean-achieved", "true")
        safe_id = re.sub(r"[^a-zA-Z0-9._-]", "", str(payload.get("session_id", "unknown"))) or "unknown"
        legacy_session = self.state / "history-guard-session-baselines" / safe_id
        if legacy_session.exists():
            baseline = int(legacy_session.read_text())
            if baseline >= self.hard:
                self.hard = baseline + positive_int(environ, "ENGRAM_CODEX_SESSION_LEGACY_GROWTH_MIB", 256) * 1024**2

    def summary(self) -> dict:
        return {"mode": self.mode, "total_bytes": self.total_bytes, "session_bytes": self.session_bytes,
                "checkpoint_bytes": self.soft, "session_hard_bytes": self.hard,
                "total_warning_bytes": self.total_soft, "total_hard_bytes": self.total_hard}


def context_output(event: str, context: str, message: str = "") -> dict:
    result = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": context.strip()}}
    if message:
        result.update(systemMessage=message, suppressOutput=False)
    return result


def settings_maintenance(payload: dict) -> bool:
    """Permit the preference switch itself even when continuity state needs repair."""
    value = payload.get("tool_input", {})
    command = value.get("command", value.get("cmd", "")) if isinstance(value, dict) else ""
    if not isinstance(command, str) or any(token in command for token in ("\n", "\r", ";", "|", "`", "$(")):
        return False
    try:
        tokens = [token.strip('"\'') for token in shlex.split(command, posix=os.name != "nt")]
    except ValueError:
        return False
    script = str(PLUGIN_ROOT / "scripts" / "engram_settings.py")
    for index, token in enumerate(tokens):
        if os.path.normcase(token) != os.path.normcase(script):
            continue
        suffix = tokens[index + 1:]
        prefix = tokens[:index]
        return suffix in (["status"], ["checkpoints", "on"], ["checkpoints", "off"]) and prefix in (
            ["uv", "run", "--no-project", "--offline", "--python", "3.12", "python"],
            ["uv", "run", "--no-project", "--python", "3.12", "python"],
            ["python"], ["python3"],
        )
    return False


def capture_instruction(session_id: str) -> str:
    # JSON quoting represents an argument for the agent to pass via its native
    # shell; this text is never interpolated into a shell command by the hook.
    argument = json.dumps(session_id, ensure_ascii=True)
    return (
        CHECKPOINT_POLICY + " Current Codex session_id=" + argument + ". "
        "Read the previous checkpoint first and carry forward still-relevant goals, constraints, "
        "accepted decisions, saved artifacts, asset references, and unfinished work. Do not replace "
        "the wider work state with a summary of only the latest message. "
        "Write a UTF-8 JSON file with nonempty objective, progress, next_action strings, "
        "decisions/references/blockers lists of strings, and a verification string. Run the "
        "installed scripts/engram_continuity.py using uv run --no-project --offline --python 3.12 python "
        "with arguments save --session-id " + argument + " --file <absolute-checkpoint-json-path> "
        "[--project <current-project-name>]. Use the real current session ID. Inspect verified:true "
        "in the successful result; a local staged attempt or failed command is not a confirmed graph save. "
        "If a save fails, preserve staged data and report the failure explicitly."
    )


def restore_context(continuity: Continuity, state: dict) -> str:
    context = ""
    if state.get("pending_attempts"):
        context += " Newer unverified local checkpoint attempts exist; inspect and reconcile them before discarding any progress: "
        context += json.dumps(state["pending_attempts"], ensure_ascii=True)[:1800] + "."
    recovered = continuity.recover(allow_missing=not state.get("verified_generation"))
    if recovered.get("source") == "none":
        return context
    checkpoint = recovered.get("checkpoint", {})
    source = recovered.get("source", "unknown")
    context += " ENGRAM CHAT RECOVERY: source=" + source + ", graph_validated=" + str(recovered.get("graph_validated", False)).lower() + ". "
    if source == "local_snapshot":
        context += "This is the last previously verified local snapshot; graph access is currently unconfirmed. "
    # Keep startup context bounded. The complete record remains retrievable.
    summary = {key: str(checkpoint.get(key, ""))[:1600] for key in ("objective", "progress", "next_action")}
    context += json.dumps(summary, ensure_ascii=True)
    context += " Before continuing substantive work, load the complete record (decisions, asset references, verification, blockers) with "
    context += "scripts/engram_continuity.py recover --session-id " + json.dumps(continuity.session_id, ensure_ascii=True) + "."
    return context


def deferred_compaction_checkpoint(reason: str, session_id: str = "") -> dict:
    # At the context limit, model execution cannot resume until compaction
    # finishes. Requiring the model to save first creates a permanent loop.
    # Native history is retained; this warning does not mint a save receipt.
    message = (
        "ENGRAM CHECKPOINT WARNING: " + reason + " No fresh checkpoint save was confirmed. "
        "Allow native compaction to continue; preserve native history and staged checkpoint attempts. "
        "After compaction, reconcile the last saved checkpoint with newer conversation progress "
        "and save/verify the current state before finishing the turn. An older checkpoint does not "
        "cover unsaved work. "
    )
    if session_id:
        message += capture_instruction(session_id)
    return {"continue": True, "systemMessage": message.strip(), "suppressOutput": False}


def handle_hook(payload: dict, environ: dict | None = None, health: dict | None = None) -> dict:
    env = dict(os.environ if environ is None else environ)
    event = payload.get("hook_event_name", "")
    if event not in ("SessionStart", "UserPromptSubmit", "PreToolUse", "PreCompact", "Stop"):
        return {}
    if event == "PreToolUse" and settings_maintenance(payload):
        return {}
    enabled = load_settings(environ=env)["checkpoints_enabled"]
    session_id = str(payload.get("session_id", ""))
    continuity = Continuity(session_id, env) if enabled else None
    if event == "PreToolUse":
        # Mark work dirty before it can change files or reveal new information.
        # A checkpoint-save tool then verifies this latest revision itself; no
        # fragile shell-command exemptions or post-save invalidation are needed.
        if continuity:
            continuity.begin_turn()
        return {}
    guard = HistoryGuard(payload, env)
    if event == "UserPromptSubmit" and continuity:
        continuity.begin_turn()
    state = continuity.status() if continuity else {}
    max_age = positive_int(env, "ENGRAM_CHECKPOINT_MAX_AGE_SECONDS", 300) if enabled else 300
    stale = not state.get("verified_at") or time.time() - float(state.get("verified_at", 0)) > max_age
    needs_checkpoint = bool(state.get("needs_checkpoint", True) or stale) if enabled else False
    prompt = payload.get("prompt", "")
    maintenance = re.search(r"engram|checkpoint|codex[ -]+history|session[ -]+history|disk[ -]+cleanup|free[ -]+space|recover", prompt, re.I)
    keep_task = "Keep this same responsibility chat. Only memory recovery and verified history maintenance may continue at the emergency boundary."
    checkpoint = capture_instruction(session_id) if enabled else "Automatic Engram checkpoints are disabled. Continue normal durable fact capture."
    if event == "Stop":
        if enabled and needs_checkpoint:
            if payload.get("stop_hook_active"):
                return {"continue": False, "stopReason": "Engram could not verify this turn's checkpoint. Keep native chat history and staged attempts; recover memory before claiming progress is saved.",
                        "systemMessage": "Chat progress was not confirmed in Engram. The previous verified checkpoint and local attempts remain available. " + checkpoint}
            return {"decision": "block", "reason": "ENGRAM CHECKPOINT REQUIRED: this turn has no fresh verified recovery record. " + checkpoint}
        if guard.total_bytes >= guard.total_hard:
            return {"continue": False, "stopReason": "Engram history ceiling reached. " + keep_task,
                    "systemMessage": "Engram stopped further native-history growth."}
        return {}
    status = health if health is not None else health_for_hook(event, str(payload.get("session_id", "unknown")), env)
    healthy = status.get("healthy", False)
    visible = status.get("message", "") if status.get("notify", True) else ""
    offline = "" if healthy else "ENGRAM IS OFFLINE. Do not claim durable recall or saves succeeded. Preserve native context; do not prune or rewrite native history until memory storage recovers. "
    if event == "PreCompact":
        if not healthy and enabled:
            return deferred_compaction_checkpoint(visible or offline, session_id)
        if enabled:
            if needs_checkpoint:
                return deferred_compaction_checkpoint("This chat's checkpoint is missing, stale or behind the current revision.", session_id)
            try:
                recovered = continuity.recover()
            except (OSError, ValueError) as error:
                return deferred_compaction_checkpoint("Engram could not revalidate the recovery checkpoint: " + str(error), session_id)
            if recovered.get("source") != "graph" or not recovered.get("graph_validated") or recovered.get("generation") != state.get("generation"):
                return deferred_compaction_checkpoint("Engram could not confirm the current checkpoint in the graph; a local snapshot alone is not a fresh graph save.", session_id)
        if visible:
            return {"continue": True, "systemMessage": visible, "suppressOutput": False}
        return {}
    if event == "SessionStart":
        project = resolve_project(payload.get("cwd"), payload.get("project_name"), payload.get("workspace_root"), env,
                                  store_path=status.get("store_path"))
        startup_checkpoint = checkpoint
        context = offline + MEMORY_POLICY + " Project memory: " + project["directory"] + ". " + startup_checkpoint
        if enabled:
            try:
                context += restore_context(continuity, state)
            except (OSError, ValueError) as error:
                recovery_failure = "Engram could not restore this chat's checkpoint: " + str(error) + ". Do not assume the old progress was restored; preserve native history and inspect saved recovery attempts."
                context += " " + recovery_failure
                visible = (visible + " " + recovery_failure).strip()
        return context_output(event, context, visible)
    if not maintenance and guard.total_bytes >= guard.total_hard:
        return {"decision": "block", "reason": "Engram blocked normal work at the native-history ceiling. " + keep_task}
    if not maintenance and guard.session_bytes >= guard.hard:
        return {"decision": "block", "reason": "Engram blocked normal work at this chat's emergency history boundary. " + keep_task + " " + checkpoint}
    context = offline
    if enabled:
        context += checkpoint + " "
    if re.search(r"remember|note that|save this|keep in mind|don't forget|make a note", prompt, re.I):
        context += "Route this memory request to Engram, search before writing, and report only confirmed saves. "
    if guard.total_bytes >= guard.total_soft:
        context += "Native Codex history is near its storage ceiling. Keep this turn focused. "
    return context_output(event, context, visible) if context or visible else {}


def init_store(store: Path, config_dir: Path) -> dict:
    created = []
    for relative in ("global/workflow", "global/tooling", "global/video", "projects", "inbox"):
        path = store / relative
        path.mkdir(parents=True, exist_ok=True)
    index = store / "INDEX.md"
    if not index.exists():
        index.write_text("# Engram\n\nShared memory for every project.\n\n- global/: reusable knowledge and preferences\n- projects/: project knowledge, creative briefs, and workflows\n- inbox/: thoughts waiting to be curated\n", encoding="utf-8")
        created.append(str(index))
    config_dir.mkdir(parents=True, exist_ok=True)
    ignore = config_dir / ".bmignore"
    existing = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    lines = existing.splitlines()
    additions = [rule for rule in ("backups/", "inbox/") if rule not in lines]
    if additions:
        atomic_text(ignore, existing + ("\n" if existing and not existing.endswith("\n") else "") + "\n".join(additions) + "\n")
        created.append(str(ignore))
    return {"store": str(store.resolve()), "config_dir": str(config_dir.resolve()), "created": created}


def store_summary(health: dict) -> dict:
    path = health.get("store_path") or os.environ.get("ENGRAM_STORE_PATH")
    if not path:
        return {"path": None, "note_counts": {}, "inbox_items": None}
    root = Path(path)
    counts = {}
    for tier in ("global", "projects"):
        counts[tier] = sum(1 for note in (root / tier).rglob("*.md") if note.is_file())
    inbox = root / "inbox"
    return {"path": str(root), "note_counts": counts,
            "inbox_items": sum(1 for item in inbox.iterdir() if item.is_file()) if inbox.is_dir() else 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("hook", help="Read one Codex lifecycle event from stdin")
    commands.add_parser("health", help="Verify MCP initialize, version, and project constraint")
    commands.add_parser("status", help="Show memory health, checkpoint mode, and history limits")
    project = commands.add_parser("project", help="Resolve software or creative project without Git")
    project.add_argument("--cwd")
    project.add_argument("--name")
    project.add_argument("--workspace")
    initialize = commands.add_parser("init-store", help="Create only missing store layout and ignore rules")
    initialize.add_argument("--store", type=Path, required=True)
    initialize.add_argument("--config-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "hook":
            # Hook JSON is UTF-8 regardless of Windows' active ANSI code page.
            payload = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
            if not isinstance(payload, dict):
                raise ValueError("Hook input must be a JSON object")
            result = handle_hook(payload)
        elif args.command == "health":
            result = probe()
        elif args.command == "status":
            health = probe()
            result = {"health": health, "store": store_summary(health), "settings": load_settings(), "config_path": str(settings_path()),
                      "history": HistoryGuard({}, dict(os.environ), persist=False).summary()}
        elif args.command == "project":
            result = resolve_project(args.cwd, args.name, args.workspace)
        else:
            result = init_store(args.store, args.config_dir)
        print(json.dumps(result, ensure_ascii=True))
        if args.command == "health":
            return 0 if result["healthy"] else 1
        if args.command == "status":
            return 0 if result["health"]["healthy"] else 1
        return 0
    except (OSError, ValueError, SettingsError) as error:
        message = f"Engram: {error}"
        if args.command == "hook":
            # Never strand a context-limited chat when recovery checks fail.
            # Other lifecycle gates still require verified progress.
            if isinstance(locals().get("payload"), dict) and payload.get("hook_event_name") == "PreCompact":
                print(json.dumps(deferred_compaction_checkpoint(message, str(payload.get("session_id", "")))))
                return 0
            if isinstance(locals().get("payload"), dict) and payload.get("hook_event_name") == "PreToolUse":
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": message + ". Recovery state could not be recorded before running this tool."}, "systemMessage": message}))
                return 0
            if isinstance(locals().get("payload"), dict) and payload.get("hook_event_name") in ("SessionStart", "UserPromptSubmit", "Stop"):
                print(json.dumps({"continue": False, "stopReason": message + ". Recovery protection could not be verified; preserve native context.", "systemMessage": message}))
                return 0
            print(json.dumps({"continue": True, "systemMessage": message + ". No checkpoint save was confirmed; preserve native history.", "suppressOutput": False}))
        else:
            print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
