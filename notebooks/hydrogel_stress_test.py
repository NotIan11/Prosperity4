"""
HYDROGEL Stress Test
====================
Simulates "live-day-like" regimes by shifting HYDROGEL_PACK prices by a constant
offset, then running the strategy logic directly in Python.

This exposes the strategy to regimes not seen in the 3 training days — specifically
the upward drift scenario that killed the fixed-FV approach on submission 523325
(live day mean = +33 ticks above 10000, never seen in training).

Two strategies compared:
  EMA  — current production strategy (tracks local fair value via EMA)
  FV   — fixed FV=10000 alternative (overfit to training days)

Usage:
    .venv/bin/python3 notebooks/hydrogel_stress_test.py

Output:
    Table + plot of HYDROGEL P&L vs shift offset for both strategies.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data", "round4")

# Regime shifts to test (ticks added to HYDROGEL mid/bid/ask)
# Training days sat near 0; live submission 523325 was ~+33
SHIFTS = [-60, -40, -20, -10, 0, +10, +20, +30, +40, +50, +60]
TEST_DAYS = [1, 2, 3]


# --------------------------------------------------------------------------- #
# Strategy simulators (replicate Layer 1 logic from HydrogelStrategy)
# --------------------------------------------------------------------------- #

def _simulate(prices_shifted: pd.DataFrame, strategy: str) -> float:
    """
    Simulate Layer 1 P&L on a single day's shifted price data.

    strategy: "ema"  → entry when mid deviates > TAKE_EDGE from EMA
              "fv"   → entry when mid deviates > TAKE_EDGE from fixed FV=10000
    """
    # Strategy parameters (match src/trader.py HydrogelStrategy)
    EMA_ALPHA = 0.015
    TAKE_EDGE = 18.0   # EMA mode
    FV_EDGE = 8.0      # fixed-FV mode uses tighter threshold (optimal from sweep)
    FV = 10_000.0
    ER_CAP = 150
    MAX_TAKE = 20

    pos = 0
    pnl = 0.0
    ema = None

    for _, row in prices_shifted.iterrows():
        bid = row["bid_price_1"]
        ask = row["ask_price_1"]
        mid = (bid + ask) / 2.0

        if strategy == "ema":
            ema = mid if ema is None else (1.0 - EMA_ALPHA) * ema + EMA_ALPHA * mid
            ref = ema
            edge = TAKE_EDGE
        else:  # fv
            ref = FV
            edge = FV_EDGE

        bought = sold = 0

        # Buy when ask is cheap
        if ask < ref - edge and pos + bought < ER_CAP:
            cap = min(ER_CAP - pos - bought, MAX_TAKE)
            vol = int(row.get("ask_volume_1", 10) or 10)
            qty = min(cap, vol)
            if qty > 0:
                pnl -= ask * qty
                bought += qty

        # Sell when bid is rich
        if bid > ref + edge and pos + bought - sold > -ER_CAP:
            cap = min(ER_CAP + pos + bought - sold, MAX_TAKE)
            vol = int(row.get("bid_volume_1", 10) or 10)
            qty = min(cap, vol)
            if qty > 0:
                pnl += bid * qty
                sold += qty

        pos += bought - sold

    # Mark-to-market at end of day
    last_mid = prices_shifted["mid_price"].iloc[-1]
    pnl += pos * last_mid
    return pnl


def simulate_day(day: int, shift: float, strategy: str) -> float:
    prices = pd.read_csv(
        os.path.join(DATA_DIR, f"prices_round_4_day_{day}.csv"), sep=";"
    )
    hg = prices[prices["product"] == "HYDROGEL_PACK"].copy().reset_index(drop=True)

    # Apply shift: all bid/ask/mid columns
    price_cols = [c for c in hg.columns if "bid_price" in c or "ask_price" in c or c == "mid_price"]
    for col in price_cols:
        hg[col] = hg[col] + shift

    return _simulate(hg, strategy)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    results = []

    print(f"{'Shift':>6}  {'EMA_D1':>8} {'EMA_D2':>8} {'EMA_D3':>8} {'EMA_TOT':>9}  "
          f"{'FV_D1':>8} {'FV_D2':>8} {'FV_D3':>8} {'FV_TOT':>9}")
    print("-" * 84)

    for shift in SHIFTS:
        row = {"shift": shift}
        for strat in ["ema", "fv"]:
            day_pnls = [simulate_day(d, shift, strat) for d in TEST_DAYS]
            for d, p in zip(TEST_DAYS, day_pnls):
                row[f"{strat}_d{d}"] = p
            row[f"{strat}_total"] = sum(day_pnls)

        print(
            f"{shift:>+6}  "
            f"{row['ema_d1']:>8,.0f} {row['ema_d2']:>8,.0f} {row['ema_d3']:>8,.0f} {row['ema_total']:>9,.0f}  "
            f"{row['fv_d1']:>8,.0f} {row['fv_d2']:>8,.0f} {row['fv_d3']:>8,.0f} {row['fv_total']:>9,.0f}"
        )
        results.append(row)

    df = pd.DataFrame(results)

    # Plot P&L vs shift for both strategies
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(df["shift"], df["ema_total"], marker="o", label="EMA (production)")
    ax.plot(df["shift"], df["fv_total"],  marker="s", label="Fixed FV=10000 (TE=8)")
    ax.axvline(0,  color="gray", linestyle="--", alpha=0.5, label="training mean")
    ax.axvline(33, color="red",  linestyle="--", alpha=0.7, label="live day 523325 (+33)")
    ax.axhline(0,  color="black", linewidth=0.5)
    ax.fill_betweenx(
        [ax.get_ylim()[0] if ax.get_ylim()[0] < -5000 else -5000,
         ax.get_ylim()[1] if ax.get_ylim()[1] > 40000 else 40000],
        -12, 12, alpha=0.08, color="green", label="training regime (approx)"
    )
    ax.set_xlabel("HYDROGEL structural price offset from 10000 (ticks)")
    ax.set_ylabel("Layer-1 P&L (3-day total)")
    ax.set_title("HYDROGEL strategy robustness under regime shift\n"
                 "(Layer 1 only; Layer 2 Mark-38 intercept is regime-neutral)")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    out = os.path.join(ROOT, "notebooks", "hydrogel_stress_test.png")
    plt.savefig(out, dpi=120)
    print(f"\nPlot saved to {out}")


if __name__ == "__main__":
    main()
