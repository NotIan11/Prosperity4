"""R3 Voucher Chain EDA — IV surface, smile drift, static-vs-rolling, residuals.

Run: venv/bin/python notebooks/03_voucher_chain_eda.py

Outputs:
  - docs/round_3/research/plots/03_*.png
  - findings printed at the bottom (### FINDINGS) and mirrored to
    docs/round_3/research/05_voucher_chain.md (separately).

Conventions:
  - moneyness m = log(K/S)/sqrt(TTE_years), TTE_years = TTE_days/365
  - Historical day0/1/2 → TTE = 8/7/6 days respectively (per brief)
  - Smile parameterisation: iv = a*m^2 + b*m + c (CMU convention)
  - Position limit per voucher: 300; VFE: 200
  - Skip vouchers with mid==0.5 (deep-OTM pinned floor) when fitting
"""
from __future__ import annotations
import os
import sys
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from utils.black_scholes import BlackScholes  # noqa: E402

PLOTS = os.path.join(ROOT, "docs/round_3/research/plots")
os.makedirs(PLOTS, exist_ok=True)

VOUCHERS = ["VEV_4000", "VEV_4500", "VEV_5000", "VEV_5100", "VEV_5200",
            "VEV_5300", "VEV_5400", "VEV_5500", "VEV_6000", "VEV_6500"]
STRIKES = {v: int(v.split("_")[1]) for v in VOUCHERS}
DEAD = {"VEV_6000", "VEV_6500"}
UND = "VELVETFRUIT_EXTRACT"
TTE_DAYS_BY_DAY = {0: 8, 1: 7, 2: 6}  # historical TTE per brief

# ---------------------------------------------------------------- load
def load() -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(ROOT, "data/round_3/prices_round_3_day_*.csv")))
    df = pd.concat([pd.read_csv(f, sep=";") for f in files], ignore_index=True)
    df["t"] = df.day * 1_000_000 + df.timestamp
    return df

print("Loading data ...")
raw = load()
print("rows:", len(raw), "products:", raw["product"].nunique())

# Wide table: per-(day,timestamp) one row with mid for each product
wide = raw.pivot_table(index=["day", "timestamp"], columns="product",
                       values="mid_price").reset_index()
wide = wide.dropna(subset=[UND]).copy()
wide["S"] = wide[UND]
wide["tte_days"] = wide["day"].map(TTE_DAYS_BY_DAY)
wide["tte_y"] = wide["tte_days"] / 365.0

print("\nVFE summary by day:")
print(wide.groupby("day")["S"].agg(["mean", "std", "min", "max"]).round(2))

# ---------------------------------------------------------------- IV solve
print("\nSolving IV per (timestamp, voucher) ...")
records = []
for _, row in wide.iterrows():
    S = row["S"]; T = row["tte_y"]
    for v in VOUCHERS:
        mid = row.get(v, np.nan)
        if pd.isna(mid) or mid <= 0:
            continue
        K = STRIKES[v]
        intrinsic = max(S - K, 0.0)
        # Filter: cannot solve IV if mid below intrinsic or essentially 0
        if mid < intrinsic + 1e-6 or mid <= 0.5 + 1e-9 and v in DEAD:
            iv = np.nan
        else:
            try:
                iv = BlackScholes.implied_vol(mid, S, K, T)
                # bisection bounds 0.001..1.0; treat hit-bound as bad
                if iv <= 0.0015 or iv >= 0.999:
                    iv = np.nan
            except Exception:
                iv = np.nan
        m = np.log(K / S) / np.sqrt(T)
        if not np.isnan(iv):
            vega = BlackScholes.vega(S, K, T, iv)
            delta = BlackScholes.delta(S, K, T, iv)
        else:
            vega = np.nan; delta = np.nan
        records.append((row["day"], row["timestamp"], v, K, S, T, mid, m, iv, vega, delta))

iv_df = pd.DataFrame(records, columns=["day", "timestamp", "voucher", "K", "S",
                                       "T", "mid", "m", "iv", "vega", "delta"])
print("IV rows:", len(iv_df), "non-null IV:", iv_df["iv"].notna().sum())

# ---------------------------------------------------------------- Q1: per-voucher IV stats
print("\n=== Q1: per-voucher IV summary ===")
summary = iv_df.groupby("voucher")["iv"].agg(["count", "mean", "std", "min", "max"]).round(4)
print(summary)

# Plot: IV distribution and time series per voucher
fig, axes = plt.subplots(2, 5, figsize=(20, 8), sharey=False)
for ax, v in zip(axes.flat, VOUCHERS):
    sub = iv_df[iv_df.voucher == v].dropna(subset=["iv"])
    if len(sub) == 0:
        ax.set_title(f"{v} (no IV)"); continue
    for d, g in sub.groupby("day"):
        ax.plot(g["timestamp"], g["iv"], lw=0.4, label=f"d{d}")
    ax.set_title(v); ax.set_xlabel("ts"); ax.set_ylabel("iv"); ax.legend(fontsize=6)
plt.tight_layout(); plt.savefig(f"{PLOTS}/03_iv_timeseries.png", dpi=110); plt.close()

# IV surface: mean IV per (day, voucher) heatmap
piv = iv_df.dropna(subset=["iv"]).groupby(["day", "voucher"])["iv"].mean().unstack()
fig, ax = plt.subplots(figsize=(10, 3))
im = ax.imshow(piv.values, aspect="auto", cmap="viridis")
ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels(piv.columns, rotation=45)
ax.set_yticks(range(len(piv.index))); ax.set_yticklabels([f"day{d}" for d in piv.index])
ax.set_title("Mean implied vol — IV surface")
plt.colorbar(im, ax=ax); plt.tight_layout()
plt.savefig(f"{PLOTS}/03_iv_surface.png", dpi=110); plt.close()
print("\nMean IV per (day, voucher):"); print(piv.round(4))

# ---------------------------------------------------------------- Q2: per-timestamp smile fit
print("\n=== Q2: per-timestamp quadratic smile fit ===")
fit_df = iv_df.dropna(subset=["iv"]).copy()
# exclude DEAD strikes from fitting (no real market)
fit_df = fit_df[~fit_df.voucher.isin(DEAD)]

def fit_quadratic(g):
    if len(g) < 4:
        return pd.Series({"a": np.nan, "b": np.nan, "c": np.nan, "n": len(g)})
    x = g["m"].values; y = g["iv"].values
    coef = np.polyfit(x, y, 2)  # returns [a, b, c]
    return pd.Series({"a": coef[0], "b": coef[1], "c": coef[2], "n": len(g)})

smile = fit_df.groupby(["day", "timestamp"]).apply(fit_quadratic).reset_index()
print("Smile fits:", len(smile), "valid:", smile["a"].notna().sum())
print("\nSmile coefficient stats by day:")
print(smile.groupby("day")[["a", "b", "c"]].agg(["mean", "std", "min", "max"]).round(4))

# Plot a(t), b(t), c(t) per day
fig, axes = plt.subplots(3, 3, figsize=(15, 9), sharex="col")
for col, d in enumerate(sorted(smile["day"].unique())):
    sub = smile[smile.day == d]
    for row, k in enumerate(["a", "b", "c"]):
        ax = axes[row, col]
        ax.plot(sub["timestamp"], sub[k], lw=0.5)
        ax.axhline(sub[k].mean(), color="red", ls="--", lw=0.7,
                   label=f"mean={sub[k].mean():.3f}")
        ax.set_title(f"day{d} — {k}(t)")
        ax.legend(fontsize=7)
plt.tight_layout(); plt.savefig(f"{PLOTS}/03_smile_drift.png", dpi=110); plt.close()

# Quantify drift: stdev / mean ratio per day
drift = (smile.groupby("day")[["a", "b", "c"]].std()
         / smile.groupby("day")[["a", "b", "c"]].mean().abs()).round(3)
print("\nIntraday |std/mean| per day (drift signature):")
print(drift)

# ---------------------------------------------------------------- Q3: static smile validation
print("\n=== Q3: static (day-0 fit) vs out-of-sample days 1,2 ===")
day0 = fit_df[fit_df.day == 0]
coef0 = np.polyfit(day0["m"].values, day0["iv"].values, 2)
print(f"Day-0 pooled smile: a={coef0[0]:.4f}, b={coef0[1]:.4f}, c={coef0[2]:.4f}")

def predict_iv(m, coef):
    return coef[0]*m*m + coef[1]*m + coef[2]

def bs_price_safe(S, K, T, iv):
    if not np.isfinite(iv) or iv <= 0:
        return np.nan
    return BlackScholes.call_price(S, K, T, iv)

# residual = market_mid - theo on each day using static day-0 smile
fit_df["iv_static"] = predict_iv(fit_df["m"].values, coef0)
# NOTE: fit_df.T is the DataFrame transpose; use fit_df["T"] for the TTE column.
fit_df["theo_static"] = [bs_price_safe(s, k, t, iv) for s, k, t, iv
                         in zip(fit_df["S"], fit_df["K"], fit_df["T"], fit_df["iv_static"])]
fit_df["resid_static"] = fit_df["mid"] - fit_df["theo_static"]
print("\nStatic-smile residual (mid - theo) by day, voucher:")
print(fit_df.groupby(["day", "voucher"])["resid_static"]
        .agg(["mean", "std"]).round(3))

# ---------------------------------------------------------------- Q4: rolling smile
print("\n=== Q4: rolling smile (window=100 ticks) ===")
WINDOW = 100
# Build per-tick rolling smile by reusing per-tick fits → take rolling mean coefs
smile_sorted = smile.sort_values(["day", "timestamp"]).reset_index(drop=True)
smile_sorted[["a_roll", "b_roll", "c_roll"]] = (
    smile_sorted[["a", "b", "c"]].rolling(WINDOW, min_periods=20).mean())

# Residuals using rolling smile (predicting next tick's voucher mid)
fit_df = fit_df.merge(smile_sorted[["day", "timestamp", "a_roll", "b_roll", "c_roll"]],
                      on=["day", "timestamp"], how="left")
fit_df["iv_roll"] = (fit_df["a_roll"]*fit_df["m"]**2
                     + fit_df["b_roll"]*fit_df["m"]
                     + fit_df["c_roll"])
fit_df["theo_roll"] = [bs_price_safe(s, k, t, iv) for s, k, t, iv
                       in zip(fit_df["S"], fit_df["K"], fit_df["T"], fit_df["iv_roll"])]
fit_df["resid_roll"] = fit_df["mid"] - fit_df["theo_roll"]

cmp = pd.DataFrame({
    "static_rmse": fit_df.groupby("voucher")["resid_static"].apply(lambda s: np.sqrt((s**2).mean())),
    "rolling_rmse": fit_df.groupby("voucher")["resid_roll"].apply(lambda s: np.sqrt((s**2).mean())),
})
cmp["improvement_%"] = (1 - cmp.rolling_rmse / cmp.static_rmse) * 100
print("\nRMSE per voucher (lower=better):")
print(cmp.round(3))

overall_static = np.sqrt((fit_df["resid_static"]**2).mean())
overall_roll = np.sqrt((fit_df["resid_roll"]**2).mean())
print(f"\nOverall RMSE: static={overall_static:.3f}, rolling={overall_roll:.3f}, "
      f"improvement={(1-overall_roll/overall_static)*100:.1f}%")

# ---------------------------------------------------------------- Q5: residuals
print("\n=== Q5: residual stationarity / mean-reversion ===")
from statsmodels.tsa.stattools import adfuller
adf_rows = []
for v in [v for v in VOUCHERS if v not in DEAD]:
    s = fit_df[fit_df.voucher == v]["resid_roll"].dropna()
    if len(s) < 50:
        continue
    try:
        stat, pval, *_ = adfuller(s.values, maxlag=10)
        adf_rows.append((v, len(s), stat, pval, s.mean(), s.std()))
    except Exception as e:
        adf_rows.append((v, len(s), np.nan, np.nan, s.mean(), s.std()))
adf_df = pd.DataFrame(adf_rows, columns=["voucher", "n", "adf_stat", "pval", "mean", "std"])
print(adf_df.round(4))

# Plot residuals per strike (rolling smile)
fig, axes = plt.subplots(2, 4, figsize=(18, 7), sharey=False)
live = [v for v in VOUCHERS if v not in DEAD]
for ax, v in zip(axes.flat, live):
    sub = fit_df[fit_df.voucher == v].dropna(subset=["resid_roll"])
    for d, g in sub.groupby("day"):
        ax.plot(g["timestamp"], g["resid_roll"], lw=0.4, label=f"d{d}")
    ax.axhline(0, color="k", lw=0.4)
    ax.set_title(f"{v} resid (mid-theo, rolling smile)")
    ax.legend(fontsize=6)
plt.tight_layout(); plt.savefig(f"{PLOTS}/03_residuals_per_strike.png", dpi=110); plt.close()

# ---------------------------------------------------------------- Q6: cross-strike cointegration
print("\n=== Q6: pairwise cointegration (Engle-Granger) on voucher mids ===")
from statsmodels.tsa.stattools import coint
mid_wide = (raw[raw["product"].isin(live)]
            .pivot_table(index=["day", "timestamp"], columns="product",
                         values="mid_price").dropna())
coint_rows = []
pairs = [(a, b) for i, a in enumerate(live) for b in live[i+1:]]
for a, b in pairs:
    if a not in mid_wide or b not in mid_wide:
        continue
    x = mid_wide[a].values; y = mid_wide[b].values
    if np.std(x) == 0 or np.std(y) == 0:
        continue
    try:
        t, p, _ = coint(x, y)
        coint_rows.append((a, b, t, p))
    except Exception:
        pass
coint_df = pd.DataFrame(coint_rows, columns=["a", "b", "t", "p"]).sort_values("p")
print(coint_df.head(15).round(4))
print(f"\nPairs with p<0.05: {(coint_df.p < 0.05).sum()} / {len(coint_df)}")

# ---------------------------------------------------------------- Q7: vega-weighted residuals
print("\n=== Q7: vega-weighted residuals (Frankfurt threshold candidates) ===")
fit_df["resid_per_vega"] = fit_df["resid_roll"] / fit_df["vega"]
vw = fit_df.groupby("voucher")[["vega", "resid_roll", "resid_per_vega"]].agg(
    {"vega": "mean", "resid_roll": ["mean", "std"], "resid_per_vega": ["mean", "std"]})
print(vw.round(4))

# ---------------------------------------------------------------- Q8: implied vs realized
print("\n=== Q8: implied vs realized vol of VFE ===")
vfe = wide[["day", "timestamp", "S"]].sort_values(["day", "timestamp"]).copy()
vfe["ret"] = vfe.groupby("day")["S"].pct_change()
# realized vol over horizons (annualised, 100 ticks/sec assumption: timestamp step=100)
# 1 day = 1e6 ts/100 = 10000 ticks; we approximate as 10000 ticks/day, 7 days/yr (TTE basis)
TICKS_PER_DAY = 10000
TRADING_DAYS_YEAR = 252
def ann_vol(s, h):
    rolling = s.rolling(h).std() * np.sqrt(TICKS_PER_DAY * TRADING_DAYS_YEAR)
    return rolling.mean()
rv = {h: ann_vol(vfe["ret"], h) for h in (10, 50, 200, 500)}
print("Realized vol (annualised, mean over series):", {k: round(v, 4) for k, v in rv.items()})
mean_iv = iv_df.dropna(subset=["iv"]).groupby("day")["iv"].mean()
print("Mean implied vol per day:"); print(mean_iv.round(4))

# ---------------------------------------------------------------- Q9: dead OTM
print("\n=== Q9: VEV_6000 / VEV_6500 deep-OTM check ===")
for v in DEAD:
    sub = raw[raw["product"] == v]["mid_price"].dropna()
    print(f"{v}: rows={len(sub)} mean={sub.mean():.3f} min={sub.min()} "
          f"max={sub.max()} unique<=3={sub.value_counts().head(3).to_dict()}")
    trades_files = sorted(glob.glob(os.path.join(ROOT, "data/round_3/trades_round_3_day_*.csv")))
tr = pd.concat([pd.read_csv(f, sep=";") for f in trades_files], ignore_index=True)
for v in DEAD:
    sub = tr[tr["symbol"] == v]
    print(f"{v} trades: n={len(sub)} price_range=[{sub.price.min() if len(sub) else 'n/a'}, "
          f"{sub.price.max() if len(sub) else 'n/a'}]")

# ---------------------------------------------------------------- Q10: lead-lag (brief)
print("\n=== Q10: brief voucher-vs-VFE lead-lag (corr at lags) ===")
# Use most-ATM voucher as proxy
proxy = "VEV_5200"
ll = (raw[raw["product"].isin([proxy, UND])]
      .pivot_table(index=["day", "timestamp"], columns="product", values="mid_price")
      .dropna()
      .sort_index())
ll["dS"] = ll[UND].pct_change()
ll["dV"] = ll[proxy].pct_change()
for lag in (-3, -2, -1, 0, 1, 2, 3):
    c = ll["dV"].corr(ll["dS"].shift(lag))
    sign = "VFE leads V" if lag > 0 else ("V leads VFE" if lag < 0 else "concurrent")
    print(f"  lag={lag:+d} ({sign}): corr={c:.4f}")

# ---------------------------------------------------------------- FINDINGS
print(r"""

### FINDINGS

(See header docstring + sections above for the cited numbers — the printed
output IS the source of truth; this block only summarises.)

Q1 — IV per voucher: see summary table; near-ATM strikes (5000-5500) give
clean IV solutions; deep-ITM (4000) is intrinsic-pinned and IV is unstable;
deep-OTM (6000/6500) bid is 0.5 floor, IV unsolvable.

Q2 — Smile drift: a(t)/b(t)/c(t) refit every tick. See plot
03_smile_drift.png and the |std/mean| ratio table — c (level) is the most
stable, a (curvature) drifts the most. This is the CMU smoking gun.

Q3 — Static day-0 smile residual mean by day: if day 1, 2 means are ~0
the static fit generalises; if biased ⇒ Frankfurt's hardcoded approach
needs day-specific recalibration.

Q4 — Rolling smile beats static? See per-voucher RMSE table and the
overall improvement %. >5% RMSE reduction → ship rolling.

Q5 — Residual ADF p-values: low p ⇒ stationary/mean-reverting ⇒
residual is exploitable as alpha (mid - theo as a contrarian signal).

Q6 — Cointegration: count of p<0.05 pairs. If high, cross-strike
relative-value trades are viable independent of underlying direction.

Q7 — Vega gating: residual/vega gives strike-comparable signal scale.

Q8 — Implied vs realized: mean IV vs realised at multiple horizons —
gap = vol-risk-premium estimate.

Q9 — VEV_6000/6500: confirm pinned at 0.5; exclude from fitting and
trading (no actionable market).

Q10 — Lead-lag: lag-0 correlation is the dominant term ⇒ no exploitable
intra-product lead-lag at the 100-ts grid.
""")
