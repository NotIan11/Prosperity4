#!/usr/bin/env python3
"""
Informed trader analysis for HYDROGEL_PACK.

Inspired by Frankfurt Hedgehogs (2025 2nd place): an anonymous bot bought at
daily lows and sold at daily highs on Squid Ink (their Round 1 equivalent of
our HYDROGEL_PACK). This notebook checks whether a similar pattern exists here.

Usage: python notebooks/hydrogel_informed_trader.py
"""

import sys
from pathlib import Path
from collections import defaultdict

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

DATA_DIR = Path("data/round3")
DAYS = [0, 1, 2]
TICKS_PER_DAY = 1_000_000  # just a large sentinel; day field is explicit

# ------------------------------------------------------------------
# Load data
# ------------------------------------------------------------------

def load_prices(day: int) -> pd.DataFrame:
    f = DATA_DIR / f"prices_round_3_day_{day}.csv"
    df = pd.read_csv(f, sep=";")
    df = df[df["product"] == "HYDROGEL_PACK"].copy()
    df["day"] = day
    return df[["day", "timestamp", "mid_price",
               "bid_price_1", "ask_price_1"]].reset_index(drop=True)


def load_trades(day: int) -> pd.DataFrame:
    f = DATA_DIR / f"trades_round_3_day_{day}.csv"
    df = pd.read_csv(f, sep=";")
    df = df[df["symbol"] == "HYDROGEL_PACK"].copy()
    df["day"] = day
    return df[["day", "timestamp", "buyer", "seller", "price", "quantity"]].reset_index(drop=True)


prices_all = pd.concat([load_prices(d) for d in DAYS], ignore_index=True)
trades_all = pd.concat([load_trades(d) for d in DAYS], ignore_index=True)

print(f"Price rows (HYDROGEL_PACK): {len(prices_all)}")
print(f"Trade rows (HYDROGEL_PACK): {len(trades_all)}")
print(f"\nTrade quantity distribution:")
print(trades_all["quantity"].value_counts().sort_index())
print(f"\nBuyer values: {trades_all['buyer'].unique()}")
print(f"Seller values: {trades_all['seller'].unique()}")

# ------------------------------------------------------------------
# Per-day running min/max of mid_price
# ------------------------------------------------------------------

prices_all = prices_all.sort_values(["day", "timestamp"]).reset_index(drop=True)
prices_all["running_min"] = prices_all.groupby("day")["mid_price"].cummin()
prices_all["running_max"] = prices_all.groupby("day")["mid_price"].cummax()

# ------------------------------------------------------------------
# For each trade, find the running min/max at that moment
# ------------------------------------------------------------------

def get_running_extremes(trade_day: int, trade_ts: int, prices_df: pd.DataFrame):
    """Return (running_min, running_max) for the given day at or before trade_ts."""
    mask = (prices_df["day"] == trade_day) & (prices_df["timestamp"] <= trade_ts)
    subset = prices_df[mask]
    if subset.empty:
        return None, None
    last_row = subset.iloc[-1]
    return last_row["running_min"], last_row["running_max"]


running_mins = []
running_maxs = []
for _, row in trades_all.iterrows():
    rmin, rmax = get_running_extremes(int(row["day"]), int(row["timestamp"]), prices_all)
    running_mins.append(rmin)
    running_maxs.append(rmax)

trades_all["running_min"] = running_mins
trades_all["running_max"] = running_maxs

# ------------------------------------------------------------------
# Flag trades at daily extremes
# ------------------------------------------------------------------

EXTREME_TOL = 5  # within N ticks of the running extreme

trades_all["at_daily_low"] = (
    trades_all["price"] <= trades_all["running_min"] + EXTREME_TOL
)
trades_all["at_daily_high"] = (
    trades_all["price"] >= trades_all["running_max"] - EXTREME_TOL
)
trades_all["is_new_low"] = (
    trades_all["price"] <= trades_all["running_min"]
)
trades_all["is_new_high"] = (
    trades_all["price"] >= trades_all["running_max"]
)

print("\n\n=== Extreme Trade Analysis ===")
print(f"\nTolerance = ±{EXTREME_TOL} ticks from running extreme\n")
for qty in sorted(trades_all["quantity"].unique()):
    sub = trades_all[trades_all["quantity"] == qty]
    n = len(sub)
    n_low = sub["at_daily_low"].sum()
    n_high = sub["at_daily_high"].sum()
    n_new_low = sub["is_new_low"].sum()
    n_new_high = sub["is_new_high"].sum()
    print(
        f"qty={qty:2d}:  total={n:4d}  "
        f"at_low={n_low:3d} ({100*n_low/n:.0f}%)  "
        f"at_high={n_high:3d} ({100*n_high/n:.0f}%)  "
        f"new_low={n_new_low:3d}  new_high={n_new_high:3d}"
    )

# ------------------------------------------------------------------
# Strict new-extreme trades only
# ------------------------------------------------------------------

print("\n\n=== Strict New Extreme Trades (price == running min or max) ===")
new_low_trades = trades_all[trades_all["is_new_low"]]
new_high_trades = trades_all[trades_all["is_new_high"]]

print(f"\nTrades setting a new daily low  ({len(new_low_trades)} total):")
print(new_low_trades[["day", "timestamp", "price", "quantity"]].to_string(index=False))

print(f"\nTrades setting a new daily high ({len(new_high_trades)} total):")
print(new_high_trades[["day", "timestamp", "price", "quantity"]].to_string(index=False))

# ------------------------------------------------------------------
# Plot: mid price per day with all trade markers
# ------------------------------------------------------------------

fig, axes = plt.subplots(len(DAYS), 1, figsize=(16, 5 * len(DAYS)), sharex=False)
if len(DAYS) == 1:
    axes = [axes]

COLORS = {2: "tab:orange", 3: "tab:green", 4: "tab:blue",
          5: "tab:red", 6: "tab:purple", 1: "tab:gray"}
DEFAULT_COLOR = "black"

for ax, day in zip(axes, DAYS):
    p_day = prices_all[prices_all["day"] == day]
    t_day = trades_all[trades_all["day"] == day]

    ax.plot(p_day["timestamp"], p_day["mid_price"], lw=0.8, color="steelblue",
            label="mid price", zorder=1)
    ax.plot(p_day["timestamp"], p_day["running_min"], lw=0.7, color="limegreen",
            linestyle="--", alpha=0.6, label="running daily min")
    ax.plot(p_day["timestamp"], p_day["running_max"], lw=0.7, color="tomato",
            linestyle="--", alpha=0.6, label="running daily max")

    for qty, grp in t_day.groupby("quantity"):
        color = COLORS.get(qty, DEFAULT_COLOR)
        ax.scatter(grp["timestamp"], grp["price"],
                   s=50, color=color, alpha=0.8, zorder=3,
                   label=f"trade qty={qty}")

    # Highlight new-extreme trades
    nl = t_day[t_day["is_new_low"]]
    nh = t_day[t_day["is_new_high"]]
    ax.scatter(nl["timestamp"], nl["price"], s=120, marker="^",
               color="darkgreen", zorder=5, label="new daily low trade")
    ax.scatter(nh["timestamp"], nh["price"], s=120, marker="v",
               color="darkred", zorder=5, label="new daily high trade")

    ax.set_title(f"Day {day} — HYDROGEL_PACK mid price + trades by qty")
    ax.set_xlabel("timestamp")
    ax.set_ylabel("price")
    ax.legend(fontsize=7, ncol=4)
    ax.grid(alpha=0.3)

plt.tight_layout()
out_path = Path("notebooks/r1_plots")
out_path.mkdir(parents=True, exist_ok=True)
fig.savefig(out_path / "hydrogel_informed_trader.png", dpi=150)
print(f"\nPlot saved to {out_path / 'hydrogel_informed_trader.png'}")
plt.show()

# ------------------------------------------------------------------
# Plot 2: Only quantity-filtered — mimic Frankfurt Hedgehogs Figure 3b
# (show each qty independently to quickly spot systematic patterns)
# ------------------------------------------------------------------

fig2, axes2 = plt.subplots(len(DAYS), 1, figsize=(16, 5 * len(DAYS)), sharex=False)
if len(DAYS) == 1:
    axes2 = [axes2]

for ax, day in zip(axes2, DAYS):
    p_day = prices_all[prices_all["day"] == day]
    t_day = trades_all[trades_all["day"] == day]

    ax.plot(p_day["timestamp"], p_day["mid_price"], lw=0.8, color="steelblue",
            alpha=0.5, label="mid price", zorder=1)

    for qty, grp in t_day.groupby("quantity"):
        color = COLORS.get(qty, DEFAULT_COLOR)
        ax.scatter(grp["timestamp"], grp["price"],
                   s=60, color=color, alpha=0.9, zorder=3,
                   label=f"qty={qty}")
        # draw vertical lines to show where on the price series each trade is
        for _, tr in grp.iterrows():
            ax.axvline(tr["timestamp"], color=color, alpha=0.2, lw=0.5)

    ax.set_title(f"Day {day} — trades by qty (vertical lines)")
    ax.set_xlabel("timestamp")
    ax.set_ylabel("price")
    ax.legend(fontsize=8, ncol=5)
    ax.grid(alpha=0.3)

plt.tight_layout()
fig2.savefig(out_path / "hydrogel_trades_by_qty.png", dpi=150)
print(f"Plot saved to {out_path / 'hydrogel_trades_by_qty.png'}")
plt.show()

# ------------------------------------------------------------------
# Numerical summary: are trades at extremes more common than random?
# ------------------------------------------------------------------

print("\n\n=== Baseline (random) comparison ===")
print("Fraction of all price ticks that are at or within 5 of running min/max:")

for day in DAYS:
    p_day = prices_all[prices_all["day"] == day]
    frac_min = (p_day["mid_price"] <= p_day["running_min"] + EXTREME_TOL).mean()
    frac_max = (p_day["mid_price"] >= p_day["running_max"] - EXTREME_TOL).mean()
    print(f"  Day {day}: near_min={frac_min:.3f}  near_max={frac_max:.3f}")

print("\nFor each qty, if trades were random wrt price, we'd expect similar fractions.")
print("High deviation from baseline → systematic informed-trader behaviour.\n")
