#!/bin/bash
# KSPR CLI - Bash wrapper.
# Usage: ./bin/kspr.sh [args]  or  kspr [args] (after install)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_SCRIPT="$REPO_ROOT/cli/kspr.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
  echo "[!] No se encontró cli/kspr.py en $REPO_ROOT" >&2
  exit 1
fi

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  exec "$REPO_ROOT/.venv/bin/python" "$PYTHON_SCRIPT" "$@"
fi
exec python3 "$PYTHON_SCRIPT" "$@"
