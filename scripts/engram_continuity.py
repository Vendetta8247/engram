#!/usr/bin/env python3
"""Verified, per-chat semantic recovery checkpoints over the Basic Memory MCP."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Any, Mapping
import urllib.request
import urllib.error
import uuid


MAX_INPUT_BYTES = 32 * 1024
MAX_RESPONSE_BYTES = 256 * 1024
ENDPOINT = "http://127.0.0.1:18765/mcp"


class ContinuityError(ValueError):
    """Checkpoint persistence or validation could not be confirmed."""


def session_key(session_id: str) -> str:
    if not isinstance(session_id, str) or not session_id.strip() or session_id.strip().lower() == "unknown":
        raise ContinuityError("A real, nonempty session_id is required")
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:24]


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ContinuityError(f"Checkpoint data is not valid JSON: {exc}") from exc


def _checkpoint(value: Any) -> dict:
    fields = {"objective", "progress", "next_action", "decisions", "references", "blockers", "verification"}
    if not isinstance(value, dict) or set(value) != fields:
        raise ContinuityError("Checkpoint must contain only objective, progress, next_action, decisions, references, blockers, and verification")
    for name in ("objective", "progress", "next_action"):
        if not isinstance(value[name], str) or not value[name].strip():
            raise ContinuityError(f"Checkpoint {name} must be a nonempty string")
    if not isinstance(value["verification"], str):
        raise ContinuityError("Checkpoint verification must be a string (empty is allowed when nothing was verified)")
    for name in ("decisions", "references", "blockers"):
        if not isinstance(value[name], list) or any(not isinstance(item, str) for item in value[name]):
            raise ContinuityError(f"Checkpoint {name} must be a list of strings")
    if len(_canonical(value).encode("utf-8")) > MAX_INPUT_BYTES:
        raise ContinuityError("Checkpoint exceeds the 32 KiB input limit")
    # Return an independent JSON value rather than mutable caller-owned lists.
    return json.loads(_canonical(value))


def _directory(value: str | None) -> str:
    if value is None or value == "global/workflow":
        return "global/workflow"
    if not isinstance(value, str) or not re.fullmatch(r"projects/[^\W_]+(?:-[^\W_]+)*", value, re.UNICODE):
        raise ContinuityError("Project directory must be projects/<safe-slug> or global/workflow")
    return value


def _normalize(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"


def _digest(payload: dict) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _render(payload: dict) -> str:
    return (
        "# Engram chat recovery checkpoint\n\n"
        f"<!-- engram-session-key: {payload['session_key']} -->\n"
        f"<!-- engram-generation: {payload['generation']} -->\n"
        f"<!-- engram-sha256: {_digest(payload)} -->\n\n"
        "```json\n" + json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n```\n"
    )


def _parse(content: str, expected_key: str) -> dict:
    match = re.fullmatch(
        r"# Engram chat recovery checkpoint\n\n"
        r"<!-- engram-session-key: ([a-f0-9]{24}) -->\n"
        r"<!-- engram-generation: ([1-9][0-9]*) -->\n"
        r"<!-- engram-sha256: ([a-f0-9]{64}) -->\n\n```json\n(.*)\n```\n",
        _normalize(content), re.DOTALL,
    )
    if not match or match[1] != expected_key:
        raise ContinuityError("Checkpoint identity markers are missing or belong to another chat")
    try:
        payload = json.loads(match[4])
    except ValueError as exc:
        raise ContinuityError("Checkpoint payload is not valid JSON") from exc
    _validate_payload(payload, expected_key)
    if payload["generation"] != int(match[2]) or _digest(payload) != match[3]:
        raise ContinuityError("Checkpoint generation or content digest does not match its markers")
    if _normalize(_render(payload)) != _normalize(content):
        raise ContinuityError("Checkpoint full content differs from its canonical representation")
    return payload


def _validate_payload(payload: Any, key: str) -> None:
    if not isinstance(payload, dict) or set(payload) != {"schema", "session_key", "generation", "captured_at", "checkpoint"}:
        raise ContinuityError("Checkpoint envelope is malformed")
    if type(payload["schema"]) is not int or payload["schema"] != 1 or payload["session_key"] != key:
        raise ContinuityError("Checkpoint schema or chat identity does not match")
    if type(payload["generation"]) is not int or payload["generation"] < 1:
        raise ContinuityError("Checkpoint generation must be a positive integer")
    if type(payload["captured_at"]) not in (int, float) or not math.isfinite(payload["captured_at"]) or payload["captured_at"] <= 0:
        raise ContinuityError("Checkpoint capture time is invalid")
    _checkpoint(payload["checkpoint"])


def _atomic_json(path: Path, value: dict) -> None:
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(_canonical(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        if hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except OSError as exc:
        raise ContinuityError(f"Cannot atomically persist {path}: {exc}") from exc
    finally:
        if temporary is not None:
            try:
                Path(temporary).unlink()
            except OSError:
                pass


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ContinuityError(f"Cannot read continuity data {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContinuityError(f"Expected a JSON object in {path}")
    return value


def _tool_data(result: dict) -> Any:
    value = result.get("structuredContent")
    if isinstance(value, dict):
        return value.get("result", value)
    for item in result.get("content", []):
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text", "")
            try:
                value = json.loads(text)
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict):
                return value.get("result", value)
    return None


def _note_content(result: dict) -> str:
    value = _tool_data(result)
    if isinstance(value, dict) and isinstance(value.get("content"), str):
        return value["content"]
    if isinstance(value, str):
        return value
    for item in result.get("content", []):
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
            if item["text"].lstrip().startswith("# Engram chat recovery checkpoint"):
                return item["text"]
    raise ContinuityError("MCP read_note did not return checkpoint content")


def _graph_note(result: dict, key: str) -> tuple[dict | None, str | None]:
    """Distinguish an absent note from malformed content; trust MCP path metadata."""
    value = _tool_data(result)
    if isinstance(value, dict) and "content" in value and "title" in value and value["content"] is None and value["title"] is None and not value.get("error"):
        return None, None
    payload = _parse(_note_content(result), key)
    directory = None
    if isinstance(value, dict) and isinstance(value.get("file_path"), str):
        match = re.fullmatch(r"(.+)/live/chats/[^/]+", value["file_path"])
        if not match:
            raise ContinuityError("Graph checkpoint is outside a recognized chat checkpoint directory")
        directory = _directory(match[1])
    return payload, directory


class MCPClient:
    def __init__(self, environ: Mapping[str, str]):
        self.endpoint = environ.get("ENGRAM_MCP_URL", ENDPOINT)
        self.project = environ.get("ENGRAM_MCP_PROJECT", "engram")
        self.headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.session = None
        self.next_id = 0
        self.deadline = time.monotonic() + 20

    def _request(self, method: str, params: dict | None = None, notification: bool = False) -> dict:
        self.next_id += 1
        identifier = self.next_id
        payload = {"jsonrpc": "2.0", "method": method}
        if not notification:
            payload["id"] = identifier
        if params is not None:
            payload["params"] = params
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ContinuityError("MCP checkpoint operation exceeded its 20 second deadline")
        try:
            request = urllib.request.Request(self.endpoint, data=_canonical(payload).encode("utf-8"), headers=self.headers)
            with self.opener.open(request, timeout=min(3, remaining)) as response:
                if method == "initialize":
                    self.session = response.headers.get("Mcp-Session-Id")
                    if self.session:
                        self.headers["Mcp-Session-Id"] = self.session
                chunks, size = [], 0
                while True:
                    if time.monotonic() > self.deadline:
                        raise ContinuityError("MCP checkpoint operation exceeded its deadline")
                    chunk = response.read1(min(65536, MAX_RESPONSE_BYTES + 1 - size))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        raise ContinuityError("MCP response exceeded the checkpoint response limit")
                body = b"".join(chunks).decode("utf-8-sig")
        except urllib.error.HTTPError as exc:
            exc.close()
            raise ContinuityError(f"MCP {method} failed: {exc}") from exc
        except (OSError, UnicodeError, http.client.HTTPException) as exc:
            raise ContinuityError(f"MCP {method} failed: {exc}") from exc
        if notification:
            return {}
        try:
            messages = [json.loads(body)]
        except ValueError:
            messages = []
            try:
                for event in re.split(r"\r?\n\r?\n", body):
                    data = "\n".join(line[5:].lstrip() for line in event.splitlines() if line.startswith("data:"))
                    if data:
                        messages.append(json.loads(data))
            except ValueError as exc:
                raise ContinuityError("MCP returned malformed JSON/SSE") from exc
        for message in messages:
            if isinstance(message, dict) and message.get("id") == identifier:
                if "error" in message:
                    raise ContinuityError("MCP error: " + str(message["error"])[:240])
                if not isinstance(message.get("result"), dict):
                    raise ContinuityError("MCP response result is missing or malformed")
                return message["result"]
        raise ContinuityError("MCP response did not contain the requested result")

    def __enter__(self):
        try:
            initialized = self._request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "engram-continuity", "version": "1"}})
            if not initialized.get("serverInfo"):
                raise ContinuityError("MCP initialize did not identify a server")
            self.headers["MCP-Protocol-Version"] = initialized.get("protocolVersion", "2025-06-18")
            self._request("notifications/initialized", notification=True)
            projects = _tool_data(self.call("list_memory_projects", {"output_format": "json"}, project=False))
            if not isinstance(projects, dict) or projects.get("constrained_project") != self.project:
                raise ContinuityError(f"MCP server is not constrained to {self.project}")
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def call(self, name: str, arguments: dict, project: bool = True) -> dict:
        args = dict(arguments)
        if project:
            args["project"] = self.project
        result = self._request("tools/call", {"name": name, "arguments": args})
        if result.get("isError"):
            raise ContinuityError(f"MCP {name} reported a tool error")
        return result

    def __exit__(self, *_args):
        if self.session:
            try:
                request = urllib.request.Request(self.endpoint, method="DELETE", headers=self.headers)
                with self.opener.open(request, timeout=1):
                    pass
            except OSError as exc:
                if isinstance(exc, urllib.error.HTTPError):
                    exc.close()


class Continuity:
    def __init__(self, session_id: str, environ: Mapping[str, str] | None = None):
        self.session_key = session_key(session_id)
        self.session_id = session_id
        self.identifier = "Chat checkpoint " + self.session_key
        self.environ = dict(os.environ if environ is None else environ)
        codex = Path(self.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
        state = Path(self.environ.get("ENGRAM_CODEX_STATE_DIR", str(codex / "engram"))).expanduser()
        self.directory = state / "continuity" / self.session_key
        self.state_path = self.directory / "state.json"

    @contextmanager
    def _lock(self, name: str = "state.lock"):
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / name
        deadline = time.monotonic() + 3
        # OS advisory locks release automatically after a process crash. A lock
        # file stays in place so another process never locks an unlinked inode.
        with path.open("a+b") as stream:
            if path.stat().st_size == 0:
                stream.write(b"\0")
                stream.flush()
            while True:
                try:
                    if os.name == "nt":
                        import msvcrt
                        stream.seek(0)
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise ContinuityError(f"Continuity state is busy at {path}; retry after the other operation finishes")
                    time.sleep(0.02)
            try:
                yield
            finally:
                if os.name == "nt":
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def read_state(self) -> dict:
        if not self.state_path.exists():
            return {"schema": 1, "session_key": self.session_key, "generation": 1}
        state = _read_json(self.state_path)
        if type(state.get("schema")) is not int or state["schema"] != 1 or state.get("session_key") != self.session_key or type(state.get("generation")) is not int or state["generation"] < 1:
            raise ContinuityError("Continuity state identity or generation is invalid")
        return state

    def begin_turn(self) -> dict:
        with self._lock():
            state = self.read_state()
            state["generation"] += 1
            _atomic_json(self.state_path, state)
        return self.status()

    def _snapshot(self, relative: str) -> dict:
        if not isinstance(relative, str):
            raise ContinuityError("Local snapshot path is invalid")
        path = self.directory / relative
        try:
            path.resolve().relative_to(self.directory.resolve())
        except ValueError as exc:
            raise ContinuityError("Local snapshot path escapes the chat state directory") from exc
        snapshot = _read_json(path)
        _validate_payload(snapshot.get("payload"), self.session_key)
        if snapshot.get("digest") != _digest(snapshot["payload"]):
            raise ContinuityError("Local snapshot digest is invalid")
        _directory(snapshot.get("project_directory"))
        return snapshot

    def _receipt(self, state: dict) -> tuple[dict | None, dict | None]:
        receipt = state.get("receipt")
        if receipt is None:
            return None, None
        if not isinstance(receipt, dict) or receipt.get("session_key") != self.session_key or receipt.get("identifier") != self.identifier:
            raise ContinuityError("Verified receipt identity is invalid")
        snapshot = self._snapshot(receipt.get("snapshot"))
        if type(receipt.get("generation")) is not int or receipt["generation"] != snapshot["payload"]["generation"] or receipt.get("digest") != snapshot["digest"] or receipt["generation"] > state["generation"]:
            raise ContinuityError("Verified receipt does not match its local snapshot")
        if type(receipt.get("verified_at")) not in (int, float) or not math.isfinite(receipt["verified_at"]) or receipt["verified_at"] <= 0:
            raise ContinuityError("Verified receipt time is invalid")
        return receipt, snapshot

    def _pending(self, state: dict, verified_generation: int) -> list[dict]:
        pending = []
        for path in sorted((self.directory / "attempts").glob("*.json"), reverse=True):
            relative = str(path.relative_to(self.directory))
            snapshot = self._snapshot(relative)
            payload = snapshot["payload"]
            if payload["generation"] > verified_generation or relative == state.get("pending_snapshot"):
                pending.append({"path": str(path), "generation": payload["generation"], "captured_at": payload["captured_at"], "digest": snapshot["digest"]})
        return pending

    def status(self) -> dict:
        state = self.read_state()
        receipt, snapshot = self._receipt(state)
        verified_generation = receipt["generation"] if receipt else 0
        pending = self._pending(state, verified_generation)
        return {"session_key": self.session_key, "identifier": self.identifier,
                "generation": state["generation"], "verified_generation": verified_generation,
                "verified_at": float(receipt["verified_at"]) if receipt else None,
                "needs_checkpoint": state["generation"] > verified_generation or bool(state.get("pending_snapshot")),
                "local_snapshot": str(self.directory / receipt["snapshot"]) if receipt else None,
                "pending_attempts": pending, "project_directory": state.get("project_directory"),
                "last_error": state.get("last_error")}

    def save(self, checkpoint: dict, project_directory: str | None = None) -> dict:
        checkpoint = _checkpoint(checkpoint)
        with self._lock():
            state = self.read_state()
            directory = _directory(project_directory or state.get("project_directory"))
            if state.get("project_directory") and state["project_directory"] != directory:
                raise ContinuityError(f"This chat's checkpoint route is already {state['project_directory']}; reuse that route")
            payload = {"schema": 1, "session_key": self.session_key, "generation": state["generation"], "captured_at": time.time(), "checkpoint": checkpoint}
            relative = f"attempts/{time.time_ns()}-{uuid.uuid4().hex}.json"
            attempt = self.directory / relative
            snapshot = {"payload": payload, "digest": _digest(payload), "project_directory": directory}
            _atomic_json(attempt, snapshot)
            state.update(project_directory=directory, pending_snapshot=relative)
            state.pop("last_error", None)
            _atomic_json(self.state_path, state)
        try:
            content = _render(payload)
            with self._lock("save.lock"):
                with self._lock():
                    current = self.read_state()
                    previous, previous_snapshot = self._receipt(current)
                    if previous_snapshot and previous_snapshot["payload"]["captured_at"] > payload["captured_at"]:
                        raise ContinuityError("A newer checkpoint was already verified; this older candidate will not overwrite it")
                with MCPClient(self.environ) as client:
                    # A restored graph can outlive this machine's local receipt.
                    # Require explicit recovery before replacing such a record,
                    # preserving its route and monotonically increasing revision.
                    if previous is None:
                        result = client.call("read_note", {"identifier": self.identifier, "output_format": "json", "include_frontmatter": False})
                        remote, remote_directory = _graph_note(result, self.session_key)
                        if remote is not None:
                            observation = current.get("graph_observation", {})
                            if observation.get("digest") != _digest(remote) or payload["generation"] <= remote["generation"]:
                                raise ContinuityError("An existing graph checkpoint must be recovered before this save can replace it; run recover, reconcile its progress, then save again")
                            if remote_directory is None or remote_directory != directory:
                                raise ContinuityError("The existing graph checkpoint's route could not be confirmed; preserve it and recover its original directory before saving")
                    client.call("write_note", {"title": self.identifier, "directory": directory + "/live/chats", "content": content, "overwrite": True, "tags": ["engram-continuity", "live-checkpoint"], "output_format": "json"})
                    result = client.call("read_note", {"identifier": self.identifier, "output_format": "json", "include_frontmatter": False})
                    readback = _note_content(result)
                    _parse(readback, self.session_key)
                    if _normalize(readback) != _normalize(content):
                        raise ContinuityError("MCP readback differs from the complete checkpoint that was written")
                with self._lock():
                    current = self.read_state()
                    receipt = {"session_key": self.session_key, "identifier": self.identifier,
                               "generation": payload["generation"], "verified_at": time.time(),
                               "snapshot": relative, "digest": snapshot["digest"]}
                    current["receipt"] = receipt
                    if current.get("pending_snapshot") == relative:
                        current.pop("pending_snapshot", None)
                        current.pop("last_error", None)
                    _atomic_json(self.state_path, current)
            return {"verified": True, "generation": payload["generation"], "identifier": self.identifier, "session_key": self.session_key, "verified_at": receipt["verified_at"], "local_attempt": str(attempt)}
        except (OSError, ValueError) as exc:
            try:
                with self._lock():
                    current = self.read_state()
                    if current.get("pending_snapshot") == relative:
                        current["last_error"] = str(exc)[:500]
                        _atomic_json(self.state_path, current)
            except (OSError, ValueError):
                pass  # Keep the original failure and the independently journaled candidate.
            raise ContinuityError(f"Checkpoint not acknowledged: {exc}. Semantic candidate preserved at {attempt}") from exc

    def recover(self, allow_missing: bool = False) -> dict:
        state = self.read_state()
        receipt, local = self._receipt(state)
        pending = self._pending(state, receipt["generation"] if receipt else 0)
        try:
            with MCPClient(self.environ) as client:
                result = client.call("read_note", {"identifier": self.identifier, "output_format": "json", "include_frontmatter": False})
                payload, directory = _graph_note(result, self.session_key)
            if payload is None:
                if allow_missing and receipt is None:
                    return {"source": "none", "graph_validated": False, "identifier": self.identifier,
                            "session_key": self.session_key, "pending_attempts": pending}
                raise ContinuityError("No graph checkpoint exists for this chat")
            if receipt and (payload["generation"] < receipt["generation"] or (payload["generation"] == receipt["generation"] and _digest(payload) != receipt["digest"])):
                raise ContinuityError("Graph checkpoint conflicts with the last verified local receipt")
            if receipt is None:
                # This is a recovery observation, never a save receipt. Stop and
                # compaction still require a subsequent write plus exact readback.
                with self._lock():
                    current = self.read_state()
                    current["generation"] = max(current["generation"], payload["generation"] + 1)
                    current["graph_observation"] = {"generation": payload["generation"], "digest": _digest(payload)}
                    if directory is not None:
                        current["project_directory"] = directory
                    _atomic_json(self.state_path, current)
            return {"checkpoint": payload["checkpoint"], "generation": payload["generation"],
                    "source": "graph", "graph_validated": True, "identifier": self.identifier,
                    "session_key": self.session_key, "pending_attempts": pending}
        except (OSError, ValueError) as exc:
            if local is None:
                raise ContinuityError(f"No verified checkpoint could be recovered: {exc}; pending semantic attempts: {len(pending)}") from exc
            return {"checkpoint": local["payload"]["checkpoint"], "generation": local["payload"]["generation"],
                    "source": "local_snapshot", "graph_validated": False, "identifier": self.identifier,
                    "session_key": self.session_key, "graph_error": str(exc)[:500], "pending_attempts": pending}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("save", "status", "recover"):
        command = commands.add_parser(name)
        command.add_argument("--session-id", required=True)
        if name == "save":
            command.add_argument("--file", type=Path, required=True)
            command.add_argument("--project", help="Project name or projects/<safe-slug>")
    args = parser.parse_args(argv)
    try:
        continuity = Continuity(args.session_id)
        if args.command == "save":
            with args.file.open("rb") as stream:
                raw = stream.read(MAX_INPUT_BYTES + 1)
            if len(raw) > MAX_INPUT_BYTES:
                raise ContinuityError("Checkpoint input file exceeds 32 KiB")
            checkpoint = json.loads(raw.decode("utf-8-sig"))
            project = args.project
            if project and not project.startswith("projects/") and project != "global/workflow":
                slug = re.sub(r"[\W_]+", "-", project.casefold(), flags=re.UNICODE).strip("-")
                project = "projects/" + slug
            result = continuity.save(checkpoint, project)
        elif args.command == "status":
            result = continuity.status()
        else:
            result = continuity.recover()
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        return 0
    except (OSError, ValueError) as exc:
        print(f"Engram continuity: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
