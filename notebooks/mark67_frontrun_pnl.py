"""
Simulate frontrunning Mark 67 on VELVETFRUIT_EXTRACT.

Strategy:
  - Enter long at the best ask (cross spread) in the tick JUST before his
    detected buy signal (price declining for N consecutive ticks).
  - Exit at the best bid (cross spread) M rows after his buy executes.
  - Position size: fixed units per trade (subject to limit of 200).

We simulate across multiple (lookback, hold_rows) parameter pairs to find
the realistic P&L range.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from itertools import product as iprod

DATA_DIR = "data/round4"
BOT       = "Mark 67"
PRODUCT   = "VELVETFRUIT_EXTRACT"
POS_LIMIT = 200
UNITS     = 20   # units per trade (conservative, well inside limit)

# ── Load data ──────────────────────────────────────────────────────────────────
prices_raw = {d: pd.read_csv(f"{DATA_DIR}/prices_round_4_day_{d}.csv", sep=";") for d in [1,2,3]}
trades_raw = {d: pd.read_csv(f"{DATA_DIR}/trades_round_4_day_{d}.csv", sep=";") for d in [1,2,3]}

# ── First: measure pure price impact (how much does price move after his buy?) ─
print("=" * 65)
print("PRICE RECOVERY AFTER MARK 67 BUY")
print("=" * 65)

HOLD_ROWS = [1, 2, 3, 5, 10, 20, 40]

all_returns = {h: [] for h in HOLD_ROWS}

for d in [1, 2, 3]:
    price_df = prices_raw[d][prices_raw[d]["product"] == PRODUCT].sort_values("timestamp").reset_index(drop=True)
    day_trades = trades_raw[d]
    buys = day_trades[(day_trades["symbol"] == PRODUCT) & (day_trades["buyer"] == BOT)].sort_values("timestamp")

    for _, row in buys.iterrows():
        t = row["timestamp"]
        trade_price = row["price"]

        # index in price_df at or just after trade
        idx_arr = price_df.index[price_df["timestamp"] >= t].tolist()
        if not idx_arr:
            continue
        i = idx_arr[0]

        mid_at_trade = price_df.loc[i, "mid_price"]

        for h in HOLD_ROWS:
            if i + h < len(price_df):
                mid_after = price_df.loc[i + h, "mid_price"]
                all_returns[h].append(mid_after - mid_at_trade)

print(f"{'Hold (rows)':<14} {'Mean Δ':<10} {'Median Δ':<10} {'% positive':<14} {'n'}")
print("-" * 60)
for h in HOLD_ROWS:
    arr = np.array(all_returns[h])
    print(f"{h:<14} {arr.mean():<10.3f} {np.median(arr):<10.3f} {(arr>0).mean()*100:<14.1f} {len(arr)}")

# ── Second: full P&L simulation ────────────────────────────────────────────────
print("\n" + "=" * 65)
print(f"FRONTRUN P&L SIMULATION  (units={UNITS}, pos_limit={POS_LIMIT})")
print("=" * 65)
print("Entry: buy at ask_price_1 when price has fallen N rows in a row")
print("Exit:  sell at bid_price_1 M rows after Mark 67's buy")
print()

LOOKBACKS = [1, 2, 3]   # N declining rows before entry
HOLDS     = [2, 5, 10, 20]  # M rows to hold after trade

results_table = []

for lb, hold in iprod(LOOKBACKS, HOLDS):
    total_pnl = 0
    trade_pnls = []

    for d in [1, 2, 3]:
        price_df = prices_raw[d][prices_raw[d]["product"] == PRODUCT].sort_values("timestamp").reset_index(drop=True)
        day_trades = trades_raw[d]

        for _, row in day_trades[(day_trades["symbol"] == PRODUCT) &
                                  (day_trades["buyer"] == BOT)].sort_values("timestamp").iterrows():
            t = row["timestamp"]

            # Find the price row just before the trade
            before_idx = price_df.index[price_df["timestamp"] <= t].tolist()
            if len(before_idx) < lb + 1:
                continue
            i = before_idx[-1]

            # Check: N consecutive declining mid prices (mids[0]=most recent, mids[1]=one row ago)
            # Declining means each newer row is LOWER than the one before it
            mids = [price_df.loc[i - k, "mid_price"] for k in range(lb + 1)]
            declining = all(mids[k] < mids[k + 1] for k in range(lb))
            if not declining:
                continue

            # Entry: buy at ask_price_1 (worst case — crossing the spread)
            entry_ask = price_df.loc[i, "ask_price_1"]
            if pd.isna(entry_ask) or entry_ask == 0:
                entry_ask = price_df.loc[i, "mid_price"] + 3  # fallback: mid+3

            # Mark 67 trade row
            trade_idx_arr = price_df.index[price_df["timestamp"] >= t].tolist()
            if not trade_idx_arr:
                continue
            trade_i = trade_idx_arr[0]

            # Exit: sell at bid_price_1, M rows after his buy
            exit_i = trade_i + hold
            if exit_i >= len(price_df):
                exit_i = len(price_df) - 1

            exit_bid = price_df.loc[exit_i, "bid_price_1"]
            if pd.isna(exit_bid) or exit_bid == 0:
                exit_bid = price_df.loc[exit_i, "mid_price"] - 3  # fallback

            pnl_per_unit = exit_bid - entry_ask
            trade_pnls.append(pnl_per_unit)

    if not trade_pnls:
        continue

    arr = np.array(trade_pnls)
    n = len(arr)
    total = arr.sum() * UNITS
    per_trade = arr.mean() * UNITS
    win_rate = (arr > 0).mean() * 100
    results_table.append({
        "lookback": lb, "hold": hold,
        "n_trades": n,
        "win_rate": win_rate,
        "pnl_per_unit_mean": arr.mean(),
        "total_pnl": total,
        "per_trade_pnl": per_trade,
    })
    print(f"lb={lb} rows, hold={hold:>2} rows | n={n:>3} | win={win_rate:.0f}% | "
          f"avg per unit: {arr.mean():+.2f} | total ({UNITS}u): {total:+,.0f}")

# ── Plot: P&L distribution for best combo ─────────────────────────────────────
# Pick the combo with best total P&L
best = max(results_table, key=lambda x: x["total_pnl"])
lb_best, hold_best = best["lookback"], best["hold"]

def collect_trades(lb, hold):
    """Collect per-unit P&L for a given lookback/hold, returns (with_spread, frictionless) arrays."""
    pnls_spread = []
    pnls_friction = []
    for d in [1, 2, 3]:
        price_df = prices_raw[d][prices_raw[d]["product"] == PRODUCT].sort_values("timestamp").reset_index(drop=True)
        day_trades = trades_raw[d]
        for _, row in day_trades[(day_trades["symbol"] == PRODUCT) &
                                  (day_trades["buyer"] == BOT)].sort_values("timestamp").iterrows():
            t = row["timestamp"]
            before_idx = price_df.index[price_df["timestamp"] <= t].tolist()
            if len(before_idx) < lb + 1:
                continue
            i = before_idx[-1]
            mids = [price_df.loc[i - k, "mid_price"] for k in range(lb + 1)]
            if not all(mids[k] < mids[k + 1] for k in range(lb)):
                continue
            entry_ask = price_df.loc[i, "ask_price_1"]
            if pd.isna(entry_ask) or entry_ask == 0:
                entry_ask = price_df.loc[i, "mid_price"] + 3
            entry_mid = price_df.loc[i, "mid_price"]
            trade_idx_arr = price_df.index[price_df["timestamp"] >= t].tolist()
            if not trade_idx_arr:
                continue
            trade_i = trade_idx_arr[0]
            exit_i = min(trade_i + hold, len(price_df) - 1)
            exit_bid = price_df.loc[exit_i, "bid_price_1"]
            if pd.isna(exit_bid) or exit_bid == 0:
                exit_bid = price_df.loc[exit_i, "mid_price"] - 3
            exit_mid = price_df.loc[exit_i, "mid_price"]
            pnls_spread.append(exit_bid - entry_ask)
            pnls_friction.append(exit_mid - entry_mid)
    return np.array(pnls_spread), np.array(pnls_friction)

trade_pnls_best_spread, trade_pnls_best_friction = collect_trades(lb_best, hold_best)

arr_best = trade_pnls_best_spread
arr_best_fric = trade_pnls_best_friction

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle(
    f"Frontrunning Mark 67 — P&L Simulation\n"
    f"Entry: when price falls {lb_best} row(s), Exit: {hold_best} rows after his buy, {UNITS} units/trade",
    fontsize=12, fontweight="bold")

ax1, ax2, ax3 = axes

# Histogram: with-spread vs frictionless
ax1.hist(arr_best * UNITS, bins=20, color="#d62728", edgecolor="white", alpha=0.7, label="With spread (bid/ask)")
ax1.hist(arr_best_fric * UNITS, bins=20, color="#1f77b4", edgecolor="white", alpha=0.7, label="Frictionless (mid/mid)")
ax1.axvline(0, color="black", lw=1.2, ls="--")
ax1.axvline(arr_best.mean() * UNITS, color="red", lw=1.5, ls="--",
            label=f"spread mean={arr_best.mean()*UNITS:+.1f}")
ax1.axvline(arr_best_fric.mean() * UNITS, color="blue", lw=1.5, ls="--",
            label=f"friction mean={arr_best_fric.mean()*UNITS:+.1f}")
ax1.set_xlabel(f"P&L per trade ({UNITS} units)")
ax1.set_ylabel("Count")
ax1.set_title(f"Trade P&L — n={len(arr_best)} trades\n"
              f"spread win%={(arr_best>0).mean()*100:.0f}%  frictionless win%={(arr_best_fric>0).mean()*100:.0f}%")
ax1.legend(fontsize=8)

# Equity curves
cum = np.cumsum(arr_best * UNITS)
cum_fric = np.cumsum(arr_best_fric * UNITS)
ax2.plot(cum, color="#d62728", lw=1.5, label="With spread")
ax2.plot(cum_fric, color="#1f77b4", lw=1.5, label="Frictionless")
ax2.axhline(0, color="black", lw=0.8, ls="--")
ax2.set_xlabel("Trade #")
ax2.set_ylabel("Cumulative P&L (seashells)")
ax2.set_title(f"Equity curve\nSpread total: {cum[-1]:+,.0f}  |  Frictionless: {cum_fric[-1]:+,.0f}")
ax2.legend()

# Spread cost breakdown
spread_cost_per_unit = arr_best_fric - arr_best
ax3.bar(["Gross\n(frictionless)", "Spread\ncost", "Net\n(with spread)"],
        [arr_best_fric.mean() * UNITS, -spread_cost_per_unit.mean() * UNITS, arr_best.mean() * UNITS],
        color=["#1f77b4", "#ff7f0e", "#d62728"], alpha=0.85, edgecolor="white")
ax3.axhline(0, color="black", lw=0.8)
ax3.set_ylabel("Mean P&L per trade (seashells)")
ax3.set_title(f"Average P&L breakdown\n({UNITS} units/trade)")

plt.tight_layout()
plt.savefig("notebooks/r4_plots/mark67_frontrun_pnl.png", dpi=140, bbox_inches="tight")
plt.show()
print(f"\nSaved: notebooks/r4_plots/mark67_frontrun_pnl.png")

# ── Summary ──────────────────────────────────────────────────────────────────
avg_spread_cost = spread_cost_per_unit.mean()
print("\n" + "=" * 65)
print(f"SUMMARY (lb={lb_best}, hold={hold_best}, {UNITS} units/trade)")
print("=" * 65)
print(f"  Trades:                    {len(arr_best)}")
print(f"  Frictionless P&L (mid):    {arr_best_fric.sum()*UNITS:+,.0f}  ({arr_best_fric.mean()*UNITS:+.2f}/trade)")
print(f"  Avg spread cost/unit:      {avg_spread_cost:.2f}  (~{avg_spread_cost*UNITS:.1f}/trade)")
print(f"  Net P&L with spread:       {arr_best.sum()*UNITS:+,.0f}  ({arr_best.mean()*UNITS:+.2f}/trade)")
print(f"  Win rate (with spread):    {(arr_best>0).mean()*100:.0f}%")
print(f"  Win rate (frictionless):   {(arr_best_fric>0).mean()*100:.0f}%")
print(f"\n  VERDICT: Gross edge = {arr_best_fric.mean():.2f} ticks/unit  |  spread cost = ~{avg_spread_cost:.1f} ticks/unit")
print(f"  Net: {'NEGATIVE' if arr_best.mean()<0 else 'POSITIVE'} edge after spread ({arr_best.mean():+.2f} ticks/unit)")
