"""
Investigate whether Mark 67's buy timing is predictable from price data alone.
Testing multiple hypotheses:
  1. Fixed/periodic interval between trades
  2. Price momentum before trade (does he buy after a drop?)
  3. Price level relative to recent range (does he buy near a rolling low?)
  4. Whether a simple rule can predict his next trade
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

DATA_DIR = "data/round4"
BOT = "Mark 67"
PRODUCT = "VELVETFRUIT_EXTRACT"

# ── Load data ──────────────────────────────────────────────────────────────────
prices = {d: pd.read_csv(f"{DATA_DIR}/prices_round_4_day_{d}.csv", sep=";") for d in [1,2,3]}
trades = {d: pd.read_csv(f"{DATA_DIR}/trades_round_4_day_{d}.csv", sep=";") for d in [1,2,3]}

# Compile all Mark 67 buys with their trade price AND nearest mid_price at time of trade
all_buys = []
for d in [1, 2, 3]:
    price_df = prices[d][prices[d]["product"] == PRODUCT].sort_values("timestamp").reset_index(drop=True)
    day_trades = trades[d]
    buys = day_trades[(day_trades["symbol"] == PRODUCT) & (day_trades["buyer"] == BOT)].copy()
    buys = buys.sort_values("timestamp").reset_index(drop=True)
    buys["day"] = d

    # Nearest mid price before the trade
    for idx, row in buys.iterrows():
        t = row["timestamp"]
        before = price_df[price_df["timestamp"] <= t]
        after  = price_df[price_df["timestamp"] >= t]
        buys.loc[idx, "mid_before"] = before["mid_price"].iloc[-1] if not before.empty else np.nan
        buys.loc[idx, "mid_after"]  = after["mid_price"].iloc[0]  if not after.empty  else np.nan

    all_buys.append(buys)

buys_df = pd.concat(all_buys, ignore_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1. INTER-TRADE INTERVAL DISTRIBUTION
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("1. INTER-TRADE INTERVALS")
print("=" * 60)
for d in [1, 2, 3]:
    day_buys = buys_df[buys_df["day"] == d]["timestamp"].values
    gaps = np.diff(day_buys)
    print(f"  Day {d}: n={len(day_buys)}, gaps median={np.median(gaps):.0f}, "
          f"mean={np.mean(gaps):.0f}, std={np.std(gaps):.0f}, "
          f"min={gaps.min():.0f}, max={gaps.max():.0f}")

all_gaps = []
for d in [1, 2, 3]:
    day_buys = buys_df[buys_df["day"] == d]["timestamp"].values
    all_gaps.extend(np.diff(day_buys))
all_gaps = np.array(all_gaps)
print(f"\n  All days combined: n={len(all_gaps)}, median={np.median(all_gaps):.0f}, "
      f"mode≈{all_gaps[np.argmin(np.abs(all_gaps - np.median(all_gaps)))]:,.0f}")

# Check for multiples of a base interval
base = np.gcd.reduce(all_gaps.astype(int))
print(f"  GCD of all gaps: {base}")
print(f"  Gaps as multiples of {base}: {sorted(set((all_gaps/base).astype(int)))[:20]}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. PRICE MOMENTUM BEFORE TRADE
# Check price change over N ticks before each buy
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. PRICE CHANGE BEFORE EACH BUY")
print("=" * 60)

LOOKBACKS = [2, 5, 10, 20]  # in price rows (each row = 100 ticks)

for d in [1, 2, 3]:
    price_df = prices[d][prices[d]["product"] == PRODUCT].sort_values("timestamp").reset_index(drop=True)
    day_buys_ts = buys_df[buys_df["day"] == d]["timestamp"].values
    
    for lb in LOOKBACKS:
        changes = []
        for t in day_buys_ts:
            idx = price_df[price_df["timestamp"] <= t].index
            if len(idx) < lb + 1:
                continue
            i = idx[-1]
            chg = price_df.loc[i, "mid_price"] - price_df.loc[i - lb, "mid_price"]
            changes.append(chg)
        if changes:
            arr = np.array(changes)
            pct_neg = (arr < 0).mean() * 100
            print(f"  Day {d}, lb={lb:2d} rows ({lb*100} ticks): "
                  f"mean chg={arr.mean():.2f}, median={np.median(arr):.2f}, "
                  f"% declining={pct_neg:.1f}%")

# ─────────────────────────────────────────────────────────────────────────────
# 3. IS TRADE TIMING PREDICTABLE FROM LAST TRADE TIME?
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("3. NEXT TRADE PREDICTION: is gap since last trade predictive?")
print("=" * 60)

# Check the distribution of gaps more carefully — are most gaps multiples of 100?
print(f"  Gaps divisible by 100: {(all_gaps % 100 == 0).mean()*100:.0f}%")
print(f"  Gaps divisible by 200: {(all_gaps % 200 == 0).mean()*100:.0f}%")
print(f"  Gaps divisible by 6100: {(all_gaps % 6100 == 0).mean()*100:.0f}%")

# How often is the gap exactly 6100, 6200, 6300 etc?
from collections import Counter
gap_counts = Counter(all_gaps.astype(int))
print("\n  Most common gaps:")
for gap, count in sorted(gap_counts.items(), key=lambda x: -x[1])[:15]:
    print(f"    {gap:>8,} ticks  x{count}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. PLOTS
# ─────────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(16, 11))
fig.suptitle(f"{BOT} — Buy Timing Predictability Analysis", fontsize=14, fontweight="bold")

# 4a. Gap histogram
ax = axes[0, 0]
ax.hist(all_gaps, bins=60, color="#1f77b4", edgecolor="white", alpha=0.85)
ax.axvline(np.median(all_gaps), color="red", lw=1.5, ls="--", label=f"median={np.median(all_gaps):.0f}")
ax.set_xlabel("Gap to next Mark 67 buy (ticks)")
ax.set_ylabel("Count")
ax.set_title("Inter-trade gap distribution")
ax.legend()

# 4b. Gap autocorrelation — is gap[i+1] correlated with gap[i]?
ax = axes[0, 1]
g1 = all_gaps[:-1]
g2 = all_gaps[1:]
ax.scatter(g1, g2, alpha=0.4, s=20, color="#2ca02c")
r, pval = stats.pearsonr(g1, g2)
ax.set_xlabel("Gap[i] (ticks)")
ax.set_ylabel("Gap[i+1] (ticks)")
ax.set_title(f"Gap autocorrelation (r={r:.3f}, p={pval:.3f})")
# Regression line
m, b = np.polyfit(g1, g2, 1)
x_line = np.linspace(g1.min(), g1.max(), 100)
ax.plot(x_line, m*x_line + b, color="red", lw=1.5)

# 4c. Price change N rows before buy (lb=5)
ax = axes[1, 0]
lb = 5
all_changes = []
for d in [1, 2, 3]:
    price_df = prices[d][prices[d]["product"] == PRODUCT].sort_values("timestamp").reset_index(drop=True)
    day_buys_ts = buys_df[buys_df["day"] == d]["timestamp"].values
    for t in day_buys_ts:
        idx = price_df[price_df["timestamp"] <= t].index
        if len(idx) < lb + 1:
            continue
        i = idx[-1]
        chg = price_df.loc[i, "mid_price"] - price_df.loc[i - lb, "mid_price"]
        all_changes.append(chg)

all_changes = np.array(all_changes)
ax.hist(all_changes, bins=30, color="#ff7f0e", edgecolor="white", alpha=0.85)
ax.axvline(0, color="black", lw=1.2, ls="--")
ax.axvline(np.median(all_changes), color="red", lw=1.5, ls="--",
           label=f"median={np.median(all_changes):.1f}")
ax.set_xlabel("Price change in 5 rows (500 ticks) before buy")
ax.set_ylabel("Count")
ax.set_title(f"Price momentum before buy\n"
             f"(declining={( all_changes<0).mean()*100:.0f}%, t-test p={stats.ttest_1samp(all_changes,0).pvalue:.3f})")
ax.legend()

# 4d. Cumulative trade count vs time (day 1) — regular schedule?
ax = axes[1, 1]
for d in [1, 2, 3]:
    day_buys_ts = buys_df[buys_df["day"] == d]["timestamp"].values
    ax.step(day_buys_ts, np.arange(1, len(day_buys_ts)+1), label=f"Day {d}", lw=1.5)
    # What a perfectly uniform schedule would look like
    if d == 1:
        n = len(day_buys_ts)
        t_end = day_buys_ts[-1]
        uniform_t = np.linspace(day_buys_ts[0], t_end, n)
        ax.plot(uniform_t, np.arange(1, n+1), "k--", lw=1, alpha=0.5, label="uniform reference")
ax.set_xlabel("Timestamp")
ax.set_ylabel("Cumulative buys")
ax.set_title("Cumulative buy count (uniform = dashed)")
ax.legend()

plt.tight_layout()
plt.savefig("notebooks/r4_plots/mark67_timing_analysis.png", dpi=140, bbox_inches="tight")
plt.show()
print("\nSaved: notebooks/r4_plots/mark67_timing_analysis.png")
