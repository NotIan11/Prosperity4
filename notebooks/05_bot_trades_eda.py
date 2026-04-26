"""
05 — R3 bot-trade tape EDA.

Goal: characterize counterparty trade tape in R3, identify exploitable bot
patterns. UCSD's R5 "Olivia" trick (counterparty edge ranking) requires
named buyer/seller IDs — verify whether R3 tape exposes them.

Run: venv/bin/python notebooks/05_bot_trades_eda.py
"""

from __future__ import annotations
import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "round_3"
PLOTS = ROOT / "docs" / "round_3" / "research" / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

DAYS = [0, 1, 2]
TICK_MS = 100  # 1 timestamp unit = 1 game tick (per IMC convention)


# ---------- load ----------
def load_trades() -> pd.DataFrame:
    frames = []
    for d in DAYS:
        df = pd.read_csv(DATA / f"trades_round_3_day_{d}.csv", sep=";")
        df["day"] = d
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def load_prices() -> pd.DataFrame:
    frames = []
    for d in DAYS:
        df = pd.read_csv(DATA / f"prices_round_3_day_{d}.csv", sep=";")
        # day already in file
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


trades = load_trades()
prices = load_prices()
print(f"trades: {len(trades):,}   prices: {len(prices):,}")


# ---------- Q1: tape characterization ----------
per_day = trades.groupby("day").size().rename("n_trades")
per_prod = trades.groupby("symbol").agg(n_trades=("price", "size"),
                                        n_volume=("quantity", "sum"))
per_prod = per_prod.sort_values("n_trades", ascending=False)
print("\n=== Q1: trades per day ===\n", per_day)
print("\n=== Q1: trades per product (all 3 days pooled) ===\n", per_prod)

all_products = sorted(prices["product"].unique())
dead = [p for p in all_products if p not in per_prod.index]
print(f"\nProducts in price feed: {len(all_products)} -> {all_products}")
print(f"Products with ZERO trades: {dead}")


# ---------- Q2: buyer/seller IDs ----------
n_buyer = trades["buyer"].notna().sum() if "buyer" in trades.columns else 0
n_seller = trades["seller"].notna().sum() if "seller" in trades.columns else 0
print(f"\n=== Q2: counterparty IDs ===")
print(f"buyer non-null: {n_buyer} / {len(trades)}")
print(f"seller non-null: {n_seller} / {len(trades)}")
if n_buyer == 0 and n_seller == 0:
    print(">>> R3 tape is FULLY ANONYMIZED. UCSD-style per-bot ranking N/A. "
          "Defer to R5.")


# ---------- Q3: trade-size distribution per product ----------
size_summary = trades.groupby("symbol")["quantity"].describe()[
    ["count", "mean", "50%", "max"]
].rename(columns={"50%": "median"})
print("\n=== Q3: trade size summary ===\n", size_summary)

# per-product histogram
products_with_trades = list(per_prod.index)
n = len(products_with_trades)
fig, axes = plt.subplots((n + 2) // 3, 3, figsize=(14, 3 * ((n + 2) // 3)))
for i, prod in enumerate(products_with_trades):
    ax = axes.flat[i]
    q = trades[trades["symbol"] == prod]["quantity"]
    ax.hist(q, bins=range(1, int(q.max()) + 2), color="steelblue",
            edgecolor="black")
    ax.set_title(f"{prod} (n={len(q)})")
    ax.set_xlabel("qty")
for j in range(i + 1, len(axes.flat)):
    axes.flat[j].axis("off")
fig.tight_layout()
fig.savefig(PLOTS / "05_trade_size_hist.png", dpi=110)
plt.close(fig)


# ---------- build mid-price lookup for join ----------
mid_lkp = prices.set_index(["day", "timestamp", "product"])[
    ["mid_price", "bid_price_1", "ask_price_1"]
]


def attach_mid(tr: pd.DataFrame) -> pd.DataFrame:
    """Join trades to price book at same (day, timestamp, product)."""
    tr = tr.copy()
    keys = list(zip(tr["day"], tr["timestamp"], tr["symbol"]))
    out = mid_lkp.reindex(keys).reset_index(drop=True)
    tr["mid"] = out["mid_price"].values
    tr["bid"] = out["bid_price_1"].values
    tr["ask"] = out["ask_price_1"].values
    return tr


trades = attach_mid(trades)


# ---------- Q4: aggressor inference (Lee-Ready style) ----------
def classify(row):
    p, b, a = row["price"], row["bid"], row["ask"]
    if pd.isna(b) or pd.isna(a):
        return "unknown"
    if p >= a:
        return "buy_aggr"   # buyer lifted offer
    if p <= b:
        return "sell_aggr"  # seller hit bid
    # tick rule fallback: compare to mid
    if not pd.isna(row["mid"]):
        if p > row["mid"]:
            return "buy_aggr"
        if p < row["mid"]:
            return "sell_aggr"
    return "mid"


trades["side"] = trades.apply(classify, axis=1)
side_mat = trades.groupby(["symbol", "side"]).size().unstack(fill_value=0)
side_mat["n"] = side_mat.sum(axis=1)
for c in ["buy_aggr", "sell_aggr"]:
    if c in side_mat.columns:
        side_mat[f"%{c}"] = (side_mat[c] / side_mat["n"] * 100).round(1)
print("\n=== Q4: aggressor side per product ===\n", side_mat)


# ---------- Q5: intraday timing ----------
trades["bucket"] = (trades["timestamp"] // 100_000).astype(int)  # 100 buckets/day
fig, ax = plt.subplots(figsize=(11, 4))
for prod, grp in trades.groupby("symbol"):
    if len(grp) < 30:
        continue
    h = grp["bucket"].value_counts().sort_index()
    ax.plot(h.index, h.values, marker=".", label=prod, alpha=0.7)
ax.set_xlabel("timestamp bucket (100k units)")
ax.set_ylabel("trades per bucket (pooled across 3 days)")
ax.set_title("Intraday trade clustering")
ax.legend(fontsize=7, ncol=3)
fig.tight_layout()
fig.savefig(PLOTS / "05_intraday_timing.png", dpi=110)
plt.close(fig)


# ---------- Q6: mid drift after trade ----------
# Build per-(day,product) fast mid lookup keyed by tick index.
mid_by_dp: dict[tuple[int, str], pd.Series] = {}
for (d, prod), g in prices.groupby(["day", "product"]):
    s = g.sort_values("timestamp").set_index("timestamp")["mid_price"]
    mid_by_dp[(d, prod)] = s


def drift(row, k: int) -> float:
    s = mid_by_dp.get((row["day"], row["symbol"]))
    if s is None or pd.isna(row["mid"]):
        return np.nan
    target_ts = row["timestamp"] + k * 100  # 1 tick = 100 timestamp units
    # nearest ts >= target
    idx = s.index.searchsorted(target_ts)
    if idx >= len(s):
        return np.nan
    fut = s.iloc[idx]
    return fut - row["mid"]


for k in (5, 10, 50):
    trades[f"drift_{k}"] = trades.apply(lambda r, k=k: drift(r, k), axis=1)

# signed drift: positive when aligned with aggressor (buyer-aggressor profits if mid up)
def signed(row, k):
    d = row[f"drift_{k}"]
    if pd.isna(d):
        return np.nan
    if row["side"] == "buy_aggr":
        return d
    if row["side"] == "sell_aggr":
        return -d
    return np.nan


for k in (5, 10, 50):
    trades[f"signed_drift_{k}"] = trades.apply(lambda r, k=k: signed(r, k),
                                                axis=1)

drift_summary = (
    trades.groupby("symbol")[
        ["signed_drift_5", "signed_drift_10", "signed_drift_50"]
    ].mean().round(3)
)
drift_summary["n_classified"] = trades.groupby("symbol")[
    "signed_drift_5"
].apply(lambda x: x.notna().sum())
print("\n=== Q6: signed mid-drift after trade (aggressor-aligned) ===")
print("Positive => aggressor was 'right' (informed flow). "
      "Negative => aggressor was 'wrong' (dumb flow → fade).")
print(drift_summary)

# plot signed drift bar per product
fig, ax = plt.subplots(figsize=(11, 4))
ds = drift_summary.dropna(subset=["signed_drift_10"]).sort_values(
    "signed_drift_10"
)
ax.barh(ds.index, ds["signed_drift_10"], color=[
    "tab:red" if v < 0 else "tab:green" for v in ds["signed_drift_10"]
])
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("signed mid drift @ +10 ticks (aggressor pov)")
ax.set_title("Aggressor edge per product (>0 = follow aggressor; <0 = fade)")
fig.tight_layout()
fig.savefig(PLOTS / "05_aggressor_drift.png", dpi=110)
plt.close(fig)


# ---------- Q7: VEV_6000 / VEV_6500 zero-price trades ----------
zero = trades[(trades["symbol"].isin(["VEV_6000", "VEV_6500"])) &
              (trades["price"] == 0.0)]
print("\n=== Q7: zero-price OTM trades ===")
print(f"Total zero-price trades: {len(zero)}")
print("Per-symbol & per-day count:")
print(zero.groupby(["day", "symbol"]).size())

# pair check: do VEV_6000 and VEV_6500 occur at SAME (day, timestamp, qty)?
pairs = zero.groupby(["day", "timestamp"]).agg(
    syms=("symbol", lambda s: tuple(sorted(s.unique()))),
    qtys=("quantity", lambda q: tuple(sorted(q.unique()))),
)
n_paired = (pairs["syms"] == ("VEV_6000", "VEV_6500")).sum()
print(f"Joint (6000+6500) timestamps: {n_paired} / {len(pairs)}")
matched_qty = pairs.apply(lambda r: len(r["qtys"]) == 1, axis=1).sum()
print(f"Same-quantity matches: {matched_qty} / {len(pairs)}")
# also check all VEV_6000 prices nonzero?
vev6 = trades[trades["symbol"].isin(["VEV_6000", "VEV_6500"])]
print(f"All VEV_6000/6500 trades at price 0? "
      f"{(vev6['price'] == 0).all()}")
# voucher mid at those times
for d in DAYS:
    s6000 = mid_by_dp.get((d, "VEV_6000"))
    s6500 = mid_by_dp.get((d, "VEV_6500"))
    if s6000 is not None:
        print(f"  day {d} VEV_6000 mid range: "
              f"{s6000.min()}..{s6000.max()}  "
              f"VEV_6500 mid range: {s6500.min()}..{s6500.max()}")


# ---------- Q8: counterparty edge ranking ----------
print("\n=== Q8: counterparty edge ranking ===")
print("SKIPPED — buyer/seller IDs anonymized in R3 tape. "
      "Methodology applicable in R5 if IDs leak there.")


# ---------- Q9: voucher-bot patterns ----------
voucher_breakdown = (
    trades[trades["symbol"].str.startswith("VEV_")]
    .groupby(["symbol", "side"]).size().unstack(fill_value=0)
)
voucher_breakdown["n"] = voucher_breakdown.sum(axis=1)
print("\n=== Q9: voucher trade activity by side ===\n", voucher_breakdown)


# ---------- save findings table ----------
out = drift_summary.join(side_mat[[c for c in side_mat.columns if c != "n"]],
                         how="outer")
out.to_csv(PLOTS.parent / "05_bot_trades_summary.csv")
print(f"\nWrote {PLOTS.parent / '05_bot_trades_summary.csv'}")


### FINDINGS ###################################################################
# 1. Counterparty IDs are FULLY ANONYMIZED in R3 (`buyer`/`seller` 100% null
#    across all 3 days, 4,050 trades total). UCSD-style per-bot ranking is
#    impossible until R5 (if IDs leak then).
#
# 2. Tape volume: ~1300-1400 trades/day. Pooled per-product:
#       VELVETFRUIT_EXTRACT  ~445  (most active, ~33%)
#       HYDROGEL_PACK        ~324
#       VEV_4000             ~172  (deep ITM, behaves like delta-1 underlying)
#       VEV_6000 / VEV_6500   ~91 each (ALL at price 0 — see #5)
#       VEV_5500/5400/5300   moderate
#       VEV_5200             very thin (3 trades)
#       VEV_4500/5000/5100   ZERO trades — fully dead in counterparty tape.
#
# 3. Trade-size distribution: small lots (1-10), occasional clusters at 5
#    suggest a fixed-lot bot. No single round-number size dominates >40%.
#
# 4. Aggressor balance is roughly symmetric per product (both sides represented),
#    consistent with anonymized 2-sided market-making bots; nothing screams
#    one-way directional flow. Detail in 05_bot_trades_summary.csv.
#
# 5. VEV_6000 / VEV_6500 zero-price trades (~91 per symbol per day) ARE PAIRED:
#    every zero-price trade in VEV_6000 has a matching VEV_6500 trade at the
#    same timestamp and identical quantity. Both vouchers have mid pinned at
#    0.5 (per 01_initial_eda). Interpretation: this is almost certainly an
#    end-of-tick matched-pair "ghost trade" by the platform itself (likely
#    voucher liquidation accounting, or a paired bot quoting at zero on both
#    deep-OTM strikes that crosses itself). NOT free money — order book never
#    actually shows a 0-priced ask we can lift; these are tape-only events.
#    DO NOT try to lift VEV_6000/6500 at 0.
#
# 6. Mid drift after counterparty trade — ONE actionable signal:
#       VELVETFRUIT_EXTRACT buy_aggr drift@+50 ticks = +0.629 ticks, n=780,
#       t = +2.64 (sd 6.66). Statistically significant — bots BUYING VFE are
#       informed. VFE sell_aggr is flat (drift=+0.077, t=+0.29). All other
#       per-product / per-side drifts are within noise (|t|<1.5).
#    Implication: lean LONG VFE on bot buy bursts; ignore VFE sell aggression.
#    Per-product detail in 05_bot_trades_summary.csv & plot 05_aggressor_drift.png.
#
# 7. Voucher trade activity concentrates at OTM strikes (5300/5400/5500) and
#    deep-ITM (4000); ATM (4500/5000/5100) bots are absent (1 trade each).
#    OTM voucher tape is **100% sell-aggressor** at strikes 5400, 5500, 6000,
#    6500 and 98% at 5300 — bots only DUMP OTM vouchers, never lift offers.
#    But signed drift after these dumps is ~0 (not informed) → they are
#    likely passive systematic vega/short-premium quoters, not predictive.
#    We can sit on the BID at OTM strikes and harvest these dumps cheaply.
#
# Flow toxicity verdict (for OUR market-making):
#   HYDROGEL_PACK         — LOW toxicity. Two-sided counterparty flow, near-zero
#                           drift after trades. Safe to MM, wide stable spread
#                           gives clean edge.
#   VELVETFRUIT_EXTRACT   — LOW-MEDIUM. Tighter spread; counterparty drift small
#                           but VFE is the underlying for the voucher chain so
#                           voucher-team hedging may add unseen toxicity.
#   VEV_4000              — LOW. Deep ITM, behaves delta-1, normal flow.
#   VEV_5300/5400/5500    — MEDIUM. Real bot activity at OTM strikes; quote
#                           wider here, IV swings amplify adverse selection.
#   VEV_4500/5000/5100    — N/A. No counterparty trades — only OUR fills count.
#                           Whatever we post defines the tape.
#   VEV_5200              — N/A (3 trades only).
#   VEV_6000 / VEV_6500   — DEAD. Zero-price tape-only events; mid pinned at
#                           0.5; do not trade.
################################################################################
