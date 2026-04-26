"""Dual backtest runner: full 3-day + portal-slice (day 2, ticks 0-99900).

Usage:
    venv/bin/python scripts/bt_dual.py [trader_path]

Default trader_path is src/trader.py. Prints two PnL numbers + the
calibration ratio (live ≈ portal-slice / 1.37 based on v4 calibration).
"""
import io
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_bt(trader: str, day_arg: str) -> tuple[float, str]:
    """Run prosperity4btest, return (final_pnl, log_path_or_empty)."""
    out = subprocess.run(
        [str(ROOT / "venv/bin/prosperity4btest"), "cli", trader, day_arg, "--merge-pnl"],
        capture_output=True, text=True, cwd=ROOT,
    ).stdout
    pnl = float(re.search(r"final_pnl: ([\d,]+)", out).group(1).replace(",", ""))
    log_match = re.search(r"Successfully saved backtest results to (\S+\.log)", out)
    return pnl, (log_match.group(1) if log_match else "")


def portal_slice_pnl(log_path: str) -> float:
    """Sum profit_and_loss across products at tick 99900 (last portal tick)."""
    import pandas as pd
    text = (ROOT / log_path).read_text()
    csv_part = text.split("Activities log:")[1].split("Trade History:")[0].strip()
    df = pd.read_csv(io.StringIO(csv_part), sep=";", on_bad_lines="skip")
    return float(df[df.timestamp == 99900]["profit_and_loss"].sum())


def main(argv: list[str]) -> None:
    trader = argv[0] if argv else "src/trader.py"
    full_pnl, _ = run_bt(trader, "3")
    day2_pnl, day2_log = run_bt(trader, "3-2")
    slice_pnl = portal_slice_pnl(day2_log) if day2_log else float("nan")
    est_live = slice_pnl / 1.37  # v4-calibrated factor; refine as more data arrives
    print(f"\n=== Dual BT for {trader} ===")
    print(f"Full 3-day BT total:           {full_pnl:>10,.0f}")
    print(f"BT day-2 only:                 {day2_pnl:>10,.0f}")
    print(f"BT day-2 first-1000-tick PnL:  {slice_pnl:>10,.0f}   <- matches portal slice")
    print(f"Estimated live portal PnL:     {est_live:>10,.0f}   (slice / 1.37)")
    print(f"Calibration: live/BT_slice ratio is ~0.73 (from v4 baseline)")


if __name__ == "__main__":
    main(sys.argv[1:])
