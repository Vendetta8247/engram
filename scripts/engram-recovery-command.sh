#!/bin/sh
set -eu

case "$(uname -s 2>/dev/null || true)" in
  Darwin)
    echo 'launchctl kickstart -k gui/$(id -u)/com.yegor.engram.basic-memory'
    ;;
  Linux)
    echo 'systemctl --user restart engram-basic-memory.service'
    ;;
  *)
    echo 'restart the configured Engram shared MCP service'
    ;;
esac
