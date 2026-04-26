#!/usr/bin/env python3
"""
Risk-adjusted sweep for HydrogelStrategy.

Scores each parameter set on:
  - Calmar ratio:  total_pnl / max_drawdown  (primary, penalises large dips)
  - Final PNL:     raw total for reference
  - Max drawdown:  worst peak-to-trough (absolute)

Runs all 3 days with --persist to get per-tick PNL curves.
"""

import csv
import itertools
import re
import shutil
import subprocess
import sys
from pathlib import Path

TRADER_PATH = Path("src/trader.py")
BACKTESTER = Path.home() / ".cargo/bin/rust_backtester"
DATASET = Path.home() / "Desktop/Programming/prosperity_rust_backtester/datasets/round3"
RUNS_DIR = Path("runs")

original = TRADER_PATH.read_text()

PARAM_RE = {
    key: re.compile(rf"(    {key}\s*=\s*)[^\n]+")
    for key in [
        "TAKE_EDGE", "PASSIVE_SPREAD", "SOFT_LIMIT_FRAC",
        "TREND_WINDOW", "TREND_DROP_THR",
    ]
}


def max_drawdown(pnl_series: list[float]) -> float:
    """Peak-to-trough drawdown (positive number = loss magnitude)."""
    peak = pnl_series[0]
    dd = 0.0
    for v in pnl_series:
        if v > peak:
            peak = v
        dd = max(dd, peak - v)
    return dd


def run_backtest(params: dict) -> tuple[float, float, float]:
    """Returns (calmar, total_pnl, max_dd)."""
    code = original
    for key, val in params.items():
        code = PARAM_RE[key].sub(rf"\g<1>{val}", code)
    TRADER_PATH.write_text(code)

    result = subprocess.run(
        [str(BACKTESTER), "--trader", str(TRADER_PATH),
         "--dataset", str(DATASET), "--persist"],
        capture_output=True, text=True,
    )

    # Collect per-tick HYDROGEL PNL across all 3 day run-dirs created this run
    pnl_series = []
    run_ids = re.findall(r"(backtest-\d+-round3-day[^\s]+)", result.stdout)

    for run_id in run_ids:
        pnl_file = RUNS_DIR / run_id / "pnl_by_product.csv"
        if not pnl_file.exists():
            continue
        with open(pnl_file) as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                pnl_series.append(float(row["HYDROGEL_PACK"]))

    # Clean up run dirs to avoid filling disk
    for run_id in run_ids:
        run_dir = RUNS_DIR / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)

    if not pnl_series:
        return 0.0, 0.0, 0.0

    total_pnl = pnl_series[-1]
    dd = max_drawdown(pnl_series)
    calmar = total_pnl / dd if dd > 0 else total_pnl
    return calmar, total_pnl, dd


# -------------------------------------------------------------------
# Parameter grid — balanced range to find the risk-adjusted optimum
# -------------------------------------------------------------------
GRID = {
    "TREND_WINDOW":    [10, 15, 20, 30],
    "TREND_DROP_THR":  [8, 10, 12, 15, 20, 25],
}

FIXED = {}

keys = list(GRID.keys())
combos = list(itertools.product(*[GRID[k] for k in keys]))
total = len(combos)
print(f"Sweeping {total} combinations (risk-adjusted)...\n")

results = []
try:
    for i, combo in enumerate(combos):
        params = {**FIXED, **dict(zip(keys, combo))}
        calmar, pnl, dd = run_backtest(params)
        results.append((calmar, pnl, dd, params))

        if (i + 1) % 6 == 0 or i == 0:
            best = max(results, key=lambda x: x[0])
            print(
                f"  [{i+1:3d}/{total}]  best_calmar={best[0]:.3f}"
                f"  pnl={best[1]:,.0f}  dd={best[2]:,.0f}"
                f"  TW={best[3]['TREND_WINDOW']}  TDT={best[3]['TREND_DROP_THR']}"
            )
            sys.stdout.flush()
finally:
    TRADER_PATH.write_text(original)

results.sort(key=lambda x: x[0], reverse=True)

print("\n" + "=" * 80)
print(f"{'Rank':<5} {'Calmar':>8}  {'PNL':>10}  {'MaxDD':>10}  "
      f"{'TW':>4}  {'TDT':>5}")
print("-" * 60)
for rank, (calmar, pnl, dd, p) in enumerate(results[:20], 1):
    print(
        f"{rank:<5} {calmar:>8.3f}  {pnl:>10,.0f}  {dd:>10,.0f}  "
        f"{p['TREND_WINDOW']:>4}  {p['TREND_DROP_THR']:>5}"
    )

best_calmar, best_pnl, best_dd, best_params = results[0]
print(f"\nBest Calmar: {best_calmar:.3f}  (PNL={best_pnl:,.0f}, MaxDD={best_dd:,.0f})")
print(f"Best params: {best_params}")
