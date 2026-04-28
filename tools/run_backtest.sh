#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
TRADER="$ROOT/src/trader.py"
RUST_BT="$HOME/.cargo/bin/rust_backtester"
RUST_BT_DATA="$HOME/Desktop/Programming/prosperity_rust_backtester/datasets"

export PYTHONPATH="${PYTHONPATH:-}"
export PYTHONPATH="$ROOT:$PYTHONPATH"

usage() {
    echo "Usage: $0 [round] [day] [--carry] [--persist]"
    echo "  round   Round number (default: 2). Accepts 1-8 or 'tutorial'."
    echo "  day     Day number, e.g. -1, 0, 1 (default: all days)."
    echo "  --carry Carry state across days."
    echo "  --persist Write full artifact set."
    echo ""
    echo "Examples:"
    echo "  $0              # round 2, all days"
    echo "  $0 2 1          # round 2, day 1 only"
    echo "  $0 1            # round 1, all days"
    echo "  $0 2 --carry    # round 2, carry mode"
}

ROUND=""
DAY=""
EXTRA_ARGS=()

for arg in "$@"; do
    case "$arg" in
        --carry|--persist|--flat)
            EXTRA_ARGS+=("$arg")
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            if [ -z "$ROUND" ]; then
                ROUND="$arg"
            elif [ -z "$DAY" ]; then
                DAY="$arg"
            else
                EXTRA_ARGS+=("$arg")
            fi
            ;;
    esac
done

# Default to round 2
ROUND="${ROUND:-2}"

DATASET="${RUST_BT_DATA}/round${ROUND}"
if [ "$ROUND" = "tutorial" ]; then
    DATASET="${RUST_BT_DATA}/tutorial"
fi
# Fall back to local data/ directory if the bundled dataset doesn't exist
if [ ! -d "$DATASET" ] && [ -d "$ROOT/data/round${ROUND}" ]; then
    DATASET="$ROOT/data/round${ROUND}"
fi

CMD=("$RUST_BT" --trader "$TRADER" --dataset "$DATASET")

if [ -n "$DAY" ]; then
    CMD+=(--day "$DAY")
fi

CMD+=("${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}")

exec "${CMD[@]}"
