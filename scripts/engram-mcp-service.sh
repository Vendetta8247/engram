#!/usr/bin/env bash
# One shared Basic Memory process for every Codex and Claude task.
set -euo pipefail

readonly BASIC_MEMORY_VERSION="${ENGRAM_BASIC_MEMORY_VERSION:-0.23.2}"
readonly HOST="${ENGRAM_MCP_HOST:-127.0.0.1}"
readonly PORT="${ENGRAM_MCP_PORT:-18765}"
readonly PATH_PREFIX="${ENGRAM_MCP_PATH:-/mcp}"

if [ -n "${ENGRAM_BASIC_MEMORY_CONFIG_DIR:-}" ]; then
  CONFIG_DIR="$ENGRAM_BASIC_MEMORY_CONFIG_DIR"
elif [ "$(uname -s)" = "Darwin" ]; then
  CONFIG_DIR="${HOME}/Library/Application Support/Engram/basic-memory"
else
  CONFIG_DIR="${XDG_STATE_HOME:-${HOME}/.local/state}/engram/basic-memory"
fi
readonly CONFIG_DIR

UVX="${ENGRAM_UVX:-}"
if [ -z "$UVX" ]; then
  UVX="$(command -v uvx 2>/dev/null || true)"
fi
readonly UVX

if [ -z "$UVX" ] || [ ! -x "$UVX" ]; then
  echo "Engram MCP service: uvx was not found; install uv or set ENGRAM_UVX" >&2
  exit 69
fi

if [ ! -f "$CONFIG_DIR/config.json" ] || [ ! -f "$CONFIG_DIR/memory.db" ]; then
  echo "Engram MCP service: runtime is incomplete at $CONFIG_DIR" >&2
  exit 78
fi

export BASIC_MEMORY_CONFIG_DIR="$CONFIG_DIR"
export BASIC_MEMORY_NO_PROMOS=true

exec "$UVX" --prerelease=allow --from "basic-memory==${BASIC_MEMORY_VERSION}" \
  basic-memory mcp \
  --transport streamable-http \
  --host "$HOST" \
  --port "$PORT" \
  --path "$PATH_PREFIX" \
  --project engram
