#!/usr/bin/env python3
"""Grid search for HydrogelStrategy parameters."""

import itertools
import re
import subprocess
import sys
from pathlib import Path

TRADER_PATH = Path("src/trader.py")
BACKTESTER = Path.home() / ".cargo/bin/rust_backtester"
DATASET = Path.home() / "Desktop/Programming/prosperity_rust_backtester/datasets/round3"

original = TRADER_PATH.read_text()

PARAM_RE = {
    key: re.compile(rf"(    {key}\s*=\s*)[^\n]+")
    for key in [
        "TAKE_EDGE",
        "LARGE_DEV_THR",
        "LARGE_DEV_EXTRA",
        "EXTREME_DEV_THR",
        "EXTREME_DEV_EXTRA",
        "PASSIVE_SPREAD",
        "SOFT_LIMIT_FRAC",
    ]
}


def run_backtest(params: dict) -> float:
    code = original
    for key, val in params.items():
        code = PARAM_RE[key].sub(rf"\g<1>{val}", code)
    TRADER_PATH.write_text(code)

    result = subprocess.run(
        [str(BACKTESTER), "--trader", str(TRADER_PATH), "--dataset", str(DATASET)],
        capture_output=True,
        text=True,
    )
    # Parse TOTAL row: "TOTAL  -  30000  1495  70971.00  -"
    m = re.search(r"^TOTAL\s+\S+\s+\d+\s+\d+\s+([\d.]+)", result.stdout, re.MULTILINE)
    return float(m.group(1)) if m else 0.0


# -------------------------------------------------------------------
# Parameter grid
# -------------------------------------------------------------------
GRID = {
    "PASSIVE_SPREAD": [30, 35, 38, 40, 42, 45, 50],
    "TAKE_EDGE":      [15, 18, 20, 22, 25, 30],
    "SOFT_LIMIT_FRAC": [0.8, 0.85, 0.9, 0.95, 1.0],
}

# Fixed params (not swept — extras proven irrelevant)
FIXED = {
    "LARGE_DEV_THR":     30,
    "LARGE_DEV_EXTRA":   0,
    "EXTREME_DEV_THR":   60,
    "EXTREME_DEV_EXTRA": 0,
}

keys = list(GRID.keys())
combos = list(itertools.product(*[GRID[k] for k in keys]))
total = len(combos)

print(f"Sweeping {total} combinations...\n")

results = []
try:
    for i, combo in enumerate(combos):
        params = {**FIXED, **dict(zip(keys, combo))}
        pnl = run_backtest(params)
        results.append((pnl, params))

        if (i + 1) % 20 == 0 or i == 0:
            best_so_far = max(results, key=lambda x: x[0])
            print(
                f"  [{i+1:3d}/{total}]  best={best_so_far[0]:,.0f}  "
                + "  ".join(f"{k}={v}" for k, v in best_so_far[1].items() if k in GRID)
            )
            sys.stdout.flush()
finally:
    TRADER_PATH.write_text(original)

results.sort(key=lambda x: x[0], reverse=True)

print("\n" + "=" * 70)
print(f"{'Rank':<5} {'PNL':>10}  {'PASSIVE_SPREAD':>14}  {'TAKE_EDGE':>9}  {'LG_EXTRA':>8}  {'EX_EXTRA':>8}")
print("-" * 70)
for rank, (pnl, p) in enumerate(results[:15], 1):
    print(
        f"{rank:<5} {pnl:>10,.0f}  {p['PASSIVE_SPREAD']:>14}  {p['TAKE_EDGE']:>9}  "
        f"{p['LARGE_DEV_EXTRA']:>8}  {p['EXTREME_DEV_EXTRA']:>8}"
    )

best_pnl, best_params = results[0]
print(f"\nBest PNL: {best_pnl:,.0f}")
print(f"Best params: {best_params}")
