"""
Verify whether Mark 67 buys at local price dips.

For each Mark 67 buy trade, we check the mid_price in a symmetric window
around the trade timestamp and determine if the trade happened at a local minimum.

Multiple window sizes are tested to see how robust the pattern is.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines

DATA_DIR = "data/round4"
BOT = "Mark 67"

# ── Load data ──────────────────────────────────────────────────────────────────
prices = {d: pd.read_csv(f"{DATA_DIR}/prices_round_4_day_{d}.csv", sep=";") for d in [1,2,3]}
trades = {d: pd.read_csv(f"{DATA_DIR}/trades_round_4_day_{d}.csv", sep=";") for d in [1,2,3]}

# ── Helper: for each buy, compute price percentile within a rolling window ─────
def dip_stats(day, product, window_ticks=20_000):
    """
    For every Mark 67 buy on `day` for `product`:
      - Find all mid_price rows within ±window_ticks of the trade timestamp
      - Compute the percentile of the trade price within that window
        (0 = absolute low of the window, 100 = absolute high)
    Returns a list of percentile values.
    """
    price_df = prices[day][prices[day]["product"] == product].sort_values("timestamp")
    times = price_df["timestamp"].values
    mids  = price_df["mid_price"].values

    day_trades = trades[day]
    buys = day_trades[(day_trades["symbol"] == product) & (day_trades["buyer"] == BOT)].copy()

    results = []
    for _, row in buys.iterrows():
        t = row["timestamp"]
        p = row["price"]
        mask = (times >= t - window_ticks) & (times <= t + window_ticks)
        window_prices = mids[mask]
        if len(window_prices) < 2:
            continue
        lo, hi = window_prices.min(), window_prices.max()
        pct = (p - lo) / (hi - lo) * 100 if hi > lo else 50.0
        results.append({
            "timestamp": t,
            "price": p,
            "window_min": lo,
            "window_max": hi,
            "percentile": pct,
        })
    return pd.DataFrame(results)


# ── Run for multiple window sizes ──────────────────────────────────────────────
WINDOWS = [5_000, 10_000, 20_000, 40_000]
product = "VELVETFRUIT_EXTRACT"

print(f"Mark 67 — {product}")
print(f"{'Window (ticks)':<18} {'N trades':<12} {'Median pct':<14} {'% in bottom 33%':<18} {'% in bottom 20%'}")
print("-" * 80)

all_pcts = {}
for w in WINDOWS:
    frames = [dip_stats(d, product, w) for d in [1, 2, 3]]
    combined = pd.concat(frames, ignore_index=True)
    pcts = combined["percentile"]
    n = len(pcts)
    median = pcts.median()
    bot33 = (pcts <= 33).mean() * 100
    bot20 = (pcts <= 20).mean() * 100
    all_pcts[w] = combined
    print(f"{w:<18,} {n:<12} {median:<14.1f} {bot33:<18.1f} {bot20:.1f}")

# ── Visual: histogram of percentile + cumulative distribution ──────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle(f"{BOT} — Buy price percentile within ±window (VELVETFRUIT_EXTRACT, all days)", fontsize=13)

ax1, ax2 = axes

COLORS_W = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
for i, w in enumerate(WINDOWS):
    pcts = all_pcts[w]["percentile"]
    ax1.hist(pcts, bins=20, range=(0, 100), alpha=0.5, color=COLORS_W[i], label=f"±{w//1000}k ticks")
    # CDF
    sorted_pcts = np.sort(pcts)
    cdf = np.arange(1, len(sorted_pcts)+1) / len(sorted_pcts)
    ax2.plot(sorted_pcts, cdf, color=COLORS_W[i], lw=2, label=f"±{w//1000}k ticks")

# Reference: uniform distribution
ax1.axvline(33, color="gray", lw=1.2, ls="--", alpha=0.7, label="33rd pct")
ax1.axvline(50, color="black", lw=1, ls=":", alpha=0.7, label="50th pct (random)")
ax1.set_xlabel("Price percentile in window (0=low, 100=high)")
ax1.set_ylabel("# trades")
ax1.set_title("Distribution of buy price within window")
ax1.legend(fontsize=9)

ax2.axvline(33, color="gray", lw=1.2, ls="--", alpha=0.7)
ax2.plot([0,100], [0,1], color="black", lw=1, ls=":", alpha=0.5, label="uniform (random)")
ax2.set_xlabel("Price percentile in window")
ax2.set_ylabel("CDF")
ax2.set_title("CDF of buy price percentile")
ax2.legend(fontsize=9)

plt.tight_layout()
plt.savefig("notebooks/r4_plots/mark67_dip_analysis.png", dpi=140, bbox_inches="tight")
plt.show()
print("Saved: notebooks/r4_plots/mark67_dip_analysis.png")

# ── Day-by-day breakdown ───────────────────────────────────────────────────────
print("\nPer-day breakdown (±20k window):")
w = 20_000
for d in [1, 2, 3]:
    df = dip_stats(d, product, w)
    pcts = df["percentile"]
    print(f"  Day {d}: n={len(pcts)}, median={pcts.median():.1f}pct, "
          f"bottom-33%={( pcts<=33).mean()*100:.0f}%, bottom-20%={(pcts<=20).mean()*100:.0f}%")
