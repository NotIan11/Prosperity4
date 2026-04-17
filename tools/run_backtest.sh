#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
VENV="$ROOT/.venv/bin/prosperity4btest"
TRADER="$ROOT/src/trader.py"

export PYTHONPATH="${PYTHONPATH:-}" # Initialize PYTHONPATH if unbound
export PYTHONPATH="$ROOT:$PYTHONPATH"

# If no arguments provided, default to round 1 (all days)
if [ $# -eq 0 ]; then
    exec "$VENV" "$TRADER" "1"
else
    exec "$VENV" "$TRADER" "$@"
fi
