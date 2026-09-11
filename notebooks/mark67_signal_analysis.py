"""
Find the strongest combination of features that predicts Mark 67's next buy.
Goal: maximize precision (we post a passive ask — false positives waste nothing but
      missed positives cost us a trade). We want a signal that fires ~1 row ahead.

Features tested:
  - N consecutive declining price rows
  - Magnitude of price drop over N rows
  - Price level vs rolling mean (deviation from FV ~5250)
  - Time since last Mark 67 buy
  - Bid-ask spread width
  - Velocity of decline (acceleration)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

DATA_DIR = "data/round4"
PRODUCT  = "VELVETFRUIT_EXTRACT"
BOT      = "Mark 67"
FV       = 5250.0  # known fair value

prices_raw = {d: pd.read_csv(f"{DATA_DIR}/prices_round_4_day_{d}.csv", sep=";") for d in [1,2,3]}
trades_raw = {d: pd.read_csv(f"{DATA_DIR}/trades_round_4_day_{d}.csv", sep=";") for d in [1,2,3]}

# ── Build feature matrix ───────────────────────────────────────────────────────
rows = []

for d in [1, 2, 3]:
    price_df = prices_raw[d][prices_raw[d]["product"] == PRODUCT].sort_values("timestamp").reset_index(drop=True)
    day_trades = trades_raw[d]
    buys_ts = set(day_trades[(day_trades["symbol"] == PRODUCT) & (day_trades["buyer"] == BOT)]["timestamp"].values)

    # Track last Mark 67 buy time
    last_buy_t = None

    for i in range(5, len(price_df)):
        t      = price_df.loc[i, "timestamp"]
        mid    = price_df.loc[i, "mid_price"]
        bid    = price_df.loc[i, "bid_price_1"]
        ask    = price_df.loc[i, "ask_price_1"]
        spread = ask - bid

        # Price momentum / consecutive declines
        mids = price_df.loc[i-4:i, "mid_price"].values  # [i-4, i-3, i-2, i-1, i]

        consec_decline_1 = int(mids[4] < mids[3])
        consec_decline_2 = int(mids[4] < mids[3] < mids[2])
        consec_decline_3 = int(mids[4] < mids[3] < mids[2] < mids[1])
        consec_decline_4 = int(mids[4] < mids[3] < mids[2] < mids[1] < mids[0])

        drop_1  = mids[4] - mids[3]    # negative = declining
        drop_2  = mids[4] - mids[2]
        drop_3  = mids[4] - mids[1]
        drop_5  = mids[4] - mids[0]
        accel   = drop_1 - (mids[3] - mids[2])  # is decline accelerating?

        # Price level vs FV
        dev_from_fv = mid - FV        # negative = below FV (cheap)
        
        # Rolling mean deviation (50 rows)
        if i >= 50:
            roll_mean = price_df.loc[i-50:i-1, "mid_price"].mean()
            dev_roll  = mid - roll_mean
        else:
            dev_roll = 0.0

        # Time since last buy
        if last_buy_t is not None:
            ticks_since_buy = t - last_buy_t
        else:
            ticks_since_buy = 999999  # very large = no recent buy

        # Target: does Mark 67 buy in THIS row or next 1 row?
        target_now  = int(t in buys_ts)
        target_next = int(
            t in buys_ts or
            (i + 1 < len(price_df) and price_df.loc[i+1, "timestamp"] in buys_ts)
        )

        if t in buys_ts:
            last_buy_t = t

        rows.append({
            "day": d, "timestamp": t, "mid": mid, "spread": spread,
            "consec1": consec_decline_1,
            "consec2": consec_decline_2,
            "consec3": consec_decline_3,
            "consec4": consec_decline_4,
            "drop1": drop_1, "drop2": drop_2, "drop3": drop_3, "drop5": drop_5,
            "accel": accel,
            "dev_fv": dev_from_fv,
            "dev_roll": dev_roll,
            "ticks_since_buy": ticks_since_buy,
            "target": target_now,
            "target_next": target_next,
        })

df = pd.DataFrame(rows)

total = len(df)
total_buys = df["target"].sum()
base_precision = total_buys / total

print(f"Dataset: {total:,} rows, {total_buys} buy events")
print(f"Base precision (random): {base_precision*100:.2f}%\n")

# ── Single feature precision/recall ──────────────────────────────────────────
print("=" * 70)
print("SINGLE FEATURE PRECISION vs RECALL  (target = buy in this row)")
print("=" * 70)
print(f"{'Filter':<45} {'N rows':<10} {'Precision':<12} {'Recall':<10} {'F1'}")
print("-" * 70)

def stats(mask):
    n       = mask.sum()
    tp      = df.loc[mask, "target"].sum()
    prec    = tp / n if n > 0 else 0
    rec     = tp / total_buys if total_buys > 0 else 0
    f1      = 2*prec*rec/(prec+rec) if prec+rec > 0 else 0
    return n, prec, rec, f1

filters = [
    ("consec1==1",          df["consec1"] == 1),
    ("consec2==1",          df["consec2"] == 1),
    ("consec3==1",          df["consec3"] == 1),
    ("consec4==1",          df["consec4"] == 1),
    ("drop1 < -1",          df["drop1"] < -1),
    ("drop1 < -2",          df["drop1"] < -2),
    ("drop2 < -2",          df["drop2"] < -2),
    ("drop3 < -3",          df["drop3"] < -3),
    ("drop5 < -5",          df["drop5"] < -5),
    ("dev_fv < -5",         df["dev_fv"] < -5),
    ("dev_fv < -10",        df["dev_fv"] < -10),
    ("dev_fv < -15",        df["dev_fv"] < -15),
    ("dev_roll < -2",       df["dev_roll"] < -2),
    ("dev_roll < -5",       df["dev_roll"] < -5),
    ("ticks_since <8000",   df["ticks_since_buy"] < 8_000),
    ("ticks_since <15000",  df["ticks_since_buy"] < 15_000),
    ("ticks_since >15000",  df["ticks_since_buy"] > 15_000),
    ("spread==5",           df["spread"] == 5),
    ("accel < -1",          df["accel"] < -1),
]

for name, mask in filters:
    n, p, r, f1 = stats(mask)
    flag = "  ***" if p > base_precision * 3 else ("  **" if p > base_precision * 2 else "")
    print(f"  {name:<43} {n:<10,} {p*100:<12.2f} {r*100:<10.1f} {f1*100:.1f}{flag}")

# ── Two-feature combinations ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("TWO-FEATURE COMBINATIONS (top by F1)")
print("=" * 70)
print(f"{'Filter combination':<55} {'N':<8} {'Prec%':<10} {'Rec%':<8} {'F1%'}")
print("-" * 70)

candidates = []
key_filters = [
    ("consec2",   df["consec2"] == 1),
    ("consec3",   df["consec3"] == 1),
    ("drop2<-2",  df["drop2"] < -2),
    ("drop3<-3",  df["drop3"] < -3),
    ("dev_fv<-5", df["dev_fv"] < -5),
    ("dev_fv<-10",df["dev_fv"] < -10),
    ("dev_roll<-2",df["dev_roll"] < -2),
    ("dev_roll<-5",df["dev_roll"] < -5),
    ("since<15k", df["ticks_since_buy"] < 15_000),
    ("since>15k", df["ticks_since_buy"] > 15_000),
    ("accel<-1",  df["accel"] < -1),
]

combos = []
for i, (n1, m1) in enumerate(key_filters):
    for j, (n2, m2) in enumerate(key_filters):
        if j <= i:
            continue
        mask = m1 & m2
        n, p, r, f1 = stats(mask)
        if n >= 5:
            combos.append((f"{n1} & {n2}", n, p, r, f1))

combos.sort(key=lambda x: -x[4])
for name, n, p, r, f1 in combos[:20]:
    print(f"  {name:<55} {n:<8,} {p*100:<10.2f} {r*100:<8.1f} {f1*100:.1f}")

# ── Best combo: visualize threshold sweep ─────────────────────────────────────
print("\n" + "=" * 70)
print("THRESHOLD SWEEP: ticks_since_buy x min_consecutive_declines")
print("=" * 70)
print(f"{'since_buy range':<25} {'consec':<10} {'N':<8} {'Precision%':<14} {'Recall%'}")
print("-" * 70)
for since_lo, since_hi in [(0,5000),(5000,10000),(10000,20000),(20000,50000),(50000,999999)]:
    for consec in [1, 2, 3]:
        col = f"consec{consec}"
        mask = (df["ticks_since_buy"] >= since_lo) & (df["ticks_since_buy"] < since_hi) & (df[col] == 1)
        n, p, r, f1 = stats(mask)
        if n > 0:
            flag = " ***" if p > base_precision * 4 else ""
            print(f"  [{since_lo:>6,} – {since_hi:>7,}) & consec>={consec}   "
                  f"{n:<8,} {p*100:<14.2f} {r*100:.1f}{flag}")

# ── Plot: precision vs recall frontier ────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle(f"Mark 67 Buy Prediction — Signal Analysis\nBase precision: {base_precision*100:.2f}%", fontsize=13)

ax1, ax2 = axes

# Scatter: all two-feature combo results
ns     = [c[1] for c in combos]
precs  = [c[2]*100 for c in combos]
recs   = [c[3]*100 for c in combos]
f1s    = [c[4]*100 for c in combos]

sc = ax1.scatter(recs, precs, c=f1s, cmap="RdYlGn", s=[max(5, n/3) for n in ns], alpha=0.7)
ax1.axhline(base_precision * 100, color="red", lw=1.2, ls="--", label=f"Base {base_precision*100:.2f}%")
ax1.set_xlabel("Recall (%)")
ax1.set_ylabel("Precision (%)")
ax1.set_title("Precision vs Recall (2-feature combos)\nColor=F1, Size∝N")
plt.colorbar(sc, ax=ax1, label="F1 (%)")
ax1.legend()

# Label top 5
top5 = sorted(combos, key=lambda x: -x[4])[:5]
for name, n, p, r, f1 in top5:
    ax1.annotate(name, (r*100, p*100), fontsize=6.5, alpha=0.85,
                 xytext=(3, 3), textcoords="offset points")

# ticks_since_buy distribution: buys vs non-buys
ax2.hist(df.loc[df["target"]==0, "ticks_since_buy"].clip(0, 100_000), bins=50,
         alpha=0.6, color="#1f77b4", density=True, label="Non-buy rows")
ax2.hist(df.loc[df["target"]==1, "ticks_since_buy"].clip(0, 100_000), bins=50,
         alpha=0.7, color="#d62728", density=True, label="Buy rows")
ax2.set_xlabel("Ticks since last Mark 67 buy (clipped at 100k)")
ax2.set_ylabel("Density")
ax2.set_title("Time since last buy: buys vs non-buys")
ax2.legend()

plt.tight_layout()
plt.savefig("notebooks/r4_plots/mark67_signal_analysis.png", dpi=140, bbox_inches="tight")
plt.show()
print("Saved: notebooks/r4_plots/mark67_signal_analysis.png")
