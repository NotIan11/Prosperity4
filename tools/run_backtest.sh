#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
VENV="$ROOT/.venv/bin/prosperity4btest"
TRADER="$ROOT/src/trader.py"

ROUND="${1:-1}"
shift || true
EXTRA_ARGS=("$@")

exec "$VENV" "$TRADER" "$ROUND" "${EXTRA_ARGS[@]}"
