#!/usr/bin/env python3
"""Shared, dependency-free Engram settings for native clients and the CLI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping


class SettingsError(ValueError):
    """The settings file or an environment override is invalid."""


def settings_path(environ: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    if "ENGRAM_CONFIG_PATH" in env:
        if not env["ENGRAM_CONFIG_PATH"].strip():
            raise SettingsError("ENGRAM_CONFIG_PATH must not be empty")
        return Path(env["ENGRAM_CONFIG_PATH"]).expanduser()
    return Path.home() / ".engram" / "settings.json"


def _read_config(path: Path) -> dict[str, Any]:
    try:
        # Accept the UTF-8 BOM emitted by older Windows text editors.
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SettingsError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SettingsError(f"{path}: settings must be a JSON object")
    if "checkpoints_enabled" in value and type(value["checkpoints_enabled"]) is not bool:
        raise SettingsError(f"{path}: checkpoints_enabled must be a JSON boolean")
    return value


def _environment_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in ("true", "on", "1"):
        return True
    if normalized in ("false", "off", "0"):
        return False
    raise SettingsError(
        "ENGRAM_CHECKPOINTS_ENABLED must be true/false, on/off, or 1/0"
    )


def load_settings(
    path: str | os.PathLike[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return validated effective settings; environment overrides saved values.

    Missing files use defaults. Invalid files remain errors even when an
    environment override exists. Unknown keys are preserved for other clients.
    """
    env = os.environ if environ is None else environ
    config_path = Path(path).expanduser() if path is not None else settings_path(env)
    result = {"checkpoints_enabled": True, **_read_config(config_path)}
    if "ENGRAM_CHECKPOINTS_ENABLED" in env:
        result["checkpoints_enabled"] = _environment_bool(env["ENGRAM_CHECKPOINTS_ENABLED"])
    return result


def set_checkpoints(
    enabled: bool,
    path: str | os.PathLike[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Atomically change the saved setting without persisting env overrides."""
    if type(enabled) is not bool:
        raise SettingsError("checkpoints_enabled must be a boolean")
    env = os.environ if environ is None else environ
    config_path = Path(path).expanduser() if path is not None else settings_path(env)
    # Validate all effective settings before changing the file.
    load_settings(config_path, env)
    config = _read_config(config_path)
    config["checkpoints_enabled"] = enabled
    temporary: str | None = None
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{config_path.name}.", dir=config_path.parent)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(config, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, config_path)
        temporary = None
    except OSError as exc:
        raise SettingsError(f"cannot save {config_path}: {exc}") from exc
    finally:
        if temporary is not None:
            try:
                Path(temporary).unlink()
            except OSError:
                pass
    return load_settings(config_path, env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect or change Engram settings")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="print effective settings as JSON")
    toggle = commands.add_parser("checkpoints", help="enable or disable automatic checkpoints")
    toggle.add_argument("mode", choices=("on", "off"))
    args = parser.parse_args(argv)
    try:
        config_path = settings_path()
        if args.command == "checkpoints":
            settings = set_checkpoints(args.mode == "on", config_path)
        else:
            settings = load_settings(config_path)
        print(json.dumps({
            **settings,
            "config_path": str(config_path),
            "checkpoints_source": (
                "environment" if "ENGRAM_CHECKPOINTS_ENABLED" in os.environ
                else "settings" if config_path.exists() else "default"
            ),
        }, indent=2))
        return 0
    except SettingsError as exc:
        parser.exit(2, f"Engram settings: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
