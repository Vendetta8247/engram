#!/usr/bin/env bash
# Install Engram's per-user macOS LaunchAgent without embedding one developer's paths.
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Engram's bundled service installer currently supports macOS only." >&2
  exit 69
fi

ROOT="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
LABEL="com.yegor.engram.basic-memory"
USER_HOME="${HOME:?HOME must be set}"
RUNTIME_DIR="${ENGRAM_RUNTIME_DIR:-${USER_HOME}/Library/Application Support/Engram}"
CONFIG_DIR="${ENGRAM_BASIC_MEMORY_CONFIG_DIR:-${RUNTIME_DIR}/basic-memory}"
LOG_DIR="${ENGRAM_LOG_DIR:-${USER_HOME}/Library/Logs/Engram}"
AGENT_DIR="${ENGRAM_LAUNCH_AGENT_DIR:-${USER_HOME}/Library/LaunchAgents}"
AGENT_PATH="${AGENT_DIR}/${LABEL}.plist"
SERVICE_PATH="${RUNTIME_DIR}/bin/engram-mcp-service.sh"
NO_LOAD=false

if [ "${1:-}" = "--no-load" ]; then
  NO_LOAD=true
elif [ "$#" -ne 0 ]; then
  echo "usage: $0 [--no-load]" >&2
  exit 64
fi

UVX_BIN="${ENGRAM_UVX:-}"
if [ -z "$UVX_BIN" ]; then
  UVX_BIN="$(command -v uvx 2>/dev/null || true)"
fi
if [ -z "$UVX_BIN" ] || [ ! -x "$UVX_BIN" ]; then
  echo "Engram service installer: uvx was not found; install uv or set ENGRAM_UVX." >&2
  exit 69
fi
UVX_BIN="$(cd "$(dirname "$UVX_BIN")" && pwd)/$(basename "$UVX_BIN")"
UVX_DIR="$(dirname "$UVX_BIN")"
SERVICE_PATH_VALUE="${UVX_DIR}:${USER_HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

xml_escape() {
  printf '%s' "$1" | sed \
    -e 's/&/\&amp;/g' \
    -e 's/</\&lt;/g' \
    -e 's/>/\&gt;/g' \
    -e 's/"/\&quot;/g' \
    -e "s/'/\&apos;/g"
}

mkdir -p "${RUNTIME_DIR}/bin" "$CONFIG_DIR" "$LOG_DIR" "$AGENT_DIR"
chmod 700 "$RUNTIME_DIR" "$CONFIG_DIR" "$LOG_DIR" 2>/dev/null || true
install -m 755 "$ROOT/scripts/engram-mcp-service.sh" "$SERVICE_PATH"

tmp_plist="$(mktemp "${AGENT_DIR}/.${LABEL}.XXXXXX")"
trap 'rm -f "$tmp_plist"' EXIT
cat > "$tmp_plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$(xml_escape "$SERVICE_PATH")</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>$(xml_escape "$USER_HOME")</string>
    <key>PATH</key>
    <string>$(xml_escape "$SERVICE_PATH_VALUE")</string>
    <key>ENGRAM_UVX</key>
    <string>$(xml_escape "$UVX_BIN")</string>
    <key>ENGRAM_BASIC_MEMORY_CONFIG_DIR</key>
    <string>$(xml_escape "$CONFIG_DIR")</string>
  </dict>
  <key>WorkingDirectory</key>
  <string>$(xml_escape "$CONFIG_DIR")</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ThrottleInterval</key>
  <integer>5</integer>
  <key>ProcessType</key>
  <string>Background</string>
  <key>StandardOutPath</key>
  <string>$(xml_escape "${LOG_DIR}/basic-memory.stdout.log")</string>
  <key>StandardErrorPath</key>
  <string>$(xml_escape "${LOG_DIR}/basic-memory.stderr.log")</string>
</dict>
</plist>
EOF

plutil -lint "$tmp_plist" >/dev/null
if [ -f "$AGENT_PATH" ] && ! cmp -s "$tmp_plist" "$AGENT_PATH"; then
  backup_path="${AGENT_PATH}.backup.$(date -u +%Y%m%dT%H%M%SZ)"
  cp -p "$AGENT_PATH" "$backup_path"
  echo "Backed up previous LaunchAgent to $backup_path"
fi
if [ ! -f "$AGENT_PATH" ] || ! cmp -s "$tmp_plist" "$AGENT_PATH"; then
  chmod 600 "$tmp_plist"
  mv -f "$tmp_plist" "$AGENT_PATH"
  trap - EXIT
fi

if [ "$NO_LOAD" = false ]; then
  domain="gui/$(id -u)"
  launchctl bootout "$domain/$LABEL" >/dev/null 2>&1 || true
  launchctl bootstrap "$domain" "$AGENT_PATH"
  launchctl enable "$domain/$LABEL"
  launchctl kickstart -k "$domain/$LABEL"
fi

echo "Engram LaunchAgent: $AGENT_PATH"
echo "Engram runtime: $RUNTIME_DIR"
echo "Basic Memory config: $CONFIG_DIR"
echo "uvx: $UVX_BIN"
