#!/bin/bash
# KSPR CLI - Bash wrapper
# Usage: ./kspr.sh [args]  or  kspr [args] (after install)

# Resolve script directory relative to working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Handle case where script is invoked via symlink or from different cwd
if [ ! -f "$SCRIPT_DIR/cli/kspr.py" ]; then
  # Try relative to project root
  SCRIPT_DIR="$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")/cli"
fi

PYTHON_SCRIPT="$SCRIPT_DIR/kspr.py"

exec python3 "$PYTHON_SCRIPT" "$@"