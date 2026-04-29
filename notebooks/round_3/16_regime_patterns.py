"""Regime pattern analysis for R3 (HG/VFE/vouchers)."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

DATA = Path("/Users/bensinek/Documents/Coding/Prosperity4/data/round_3")
OUT = Path("/Users/bensinek/Documents/Coding/Prosperity4/docs/round_3/research/plots")
OUT.mkdir(exist_ok=True, parents=True)

dfs = []
for d in (0, 1, 2):
    df = pd.read_csv(DATA / f"prices_round_3_day_{d}.csv", sep=";")
    df["day"] = d
    dfs.append(df)
prices = pd.concat(dfs, ignore_index=True)

# Pivot mid by product per (day,timestamp)
pivot = prices.pivot_table(index=["day", "timestamp"], columns="product",
                           values="mid_price").reset_index()
pivot = pivot.sort_values(["day", "timestamp"]).reset_index(drop=True)

products = [c for c in pivot.columns if c not in ("day", "timestamp")]
print("products:", products)

# ------- HG regime -------
HG_FV = 9991
hg = pivot[["day", "timestamp", "HYDROGEL_PACK"]].dropna().rename(columns={"HYDROGEL_PACK": "mid"})
hg["dev"] = hg["mid"] - HG_FV
hg["abs_dev"] = hg["dev"].abs()

print("\n=== HYDROGEL ===")
for d, g in hg.groupby("day"):
    inside = (g["abs_dev"] <= 20).mean()
    drift = (g["abs_dev"] > 40).mean()
    rv = g["mid"].diff().pow(2).rolling(200).mean().pow(0.5)
    print(f"day {d}: mean dev={g['dev'].mean():.2f} std={g['dev'].std():.2f} "
          f"|dev|<=20 {inside*100:.1f}% |dev|>40 {drift*100:.1f}% "
          f"min={g['dev'].min():.0f} max={g['dev'].max():.0f} "
          f"rolling rv200 mean={rv.mean():.2f} std={rv.std():.2f}")

# rolling vol regime
hg["ret"] = hg["mid"].diff()
hg["rv200"] = hg["ret"].rolling(200).std()
hg["rv200_z"] = (hg["rv200"] - hg["rv200"].mean()) / hg["rv200"].std()

# Sub-regime analysis: low vs high vol
low_mask = hg["rv200"] < hg["rv200"].quantile(0.33)
hi_mask = hg["rv200"] > hg["rv200"].quantile(0.67)
print(f"low-vol regime: |dev|<=20 share = {(hg.loc[low_mask, 'abs_dev']<=20).mean()*100:.1f}%, "
      f"mean |dev|={hg.loc[low_mask,'abs_dev'].mean():.2f}")
print(f"hi-vol regime:  |dev|<=20 share = {(hg.loc[hi_mask, 'abs_dev']<=20).mean()*100:.1f}%, "
      f"mean |dev|={hg.loc[hi_mask,'abs_dev'].mean():.2f}")

# Excursion duration above/below FV
hg["sign"] = np.sign(hg["dev"])
runs = (hg["sign"] != hg["sign"].shift()).cumsum()
run_lengths = hg.groupby(runs).size()
print(f"HG excursion (sign-runs) median={run_lengths.median():.0f} "
      f"p90={run_lengths.quantile(0.9):.0f} max={run_lengths.max()}")

fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=False)
for i, d in enumerate((0, 1, 2)):
    g = hg[hg["day"] == d]
    axes[i].plot(g["timestamp"], g["mid"], lw=0.5)
    axes[i].axhline(HG_FV, color="r", lw=0.5)
    axes[i].axhline(HG_FV + 20, color="orange", lw=0.4, ls="--")
    axes[i].axhline(HG_FV - 20, color="orange", lw=0.4, ls="--")
    axes[i].set_title(f"HG day {d}: |dev|<=20 = {(g['mid'].sub(HG_FV).abs()<=20).mean()*100:.1f}%")
fig.tight_layout()
fig.savefig(OUT / "16_hg_regime.png", dpi=80)
plt.close(fig)

# ------- VFE regime -------
VFE_FV = 5250
vfe = pivot[["day", "timestamp", "VELVETFRUIT_EXTRACT"]].dropna().rename(columns={"VELVETFRUIT_EXTRACT": "mid"})
vfe["dev"] = vfe["mid"] - VFE_FV
vfe["abs_dev"] = vfe["dev"].abs()
print("\n=== VFE ===")
for d, g in vfe.groupby("day"):
    print(f"day {d}: mean={g['mid'].mean():.2f} dev mean={g['dev'].mean():.2f} std={g['dev'].std():.2f} "
          f"min={g['dev'].min():.0f} max={g['dev'].max():.0f} "
          f"|dev|<=20 {(g['abs_dev']<=20).mean()*100:.1f}% "
          f"|dev|>50 {(g['abs_dev']>50).mean()*100:.1f}%")

# Excursion length above/below FV
vfe["sign"] = np.sign(vfe["dev"])
vfe_runs = (vfe["sign"] != vfe["sign"].shift()).cumsum()
vrl = vfe.groupby(vfe_runs).size()
print(f"VFE sign-run median={vrl.median():.0f} p75={vrl.quantile(0.75):.0f} "
      f"p90={vrl.quantile(0.9):.0f} p99={vrl.quantile(0.99):.0f} max={vrl.max()}")
print(f"VFE share of runs > 500 ticks: {(vrl > 500).mean()*100:.2f}% "
      f"({(vrl>500).sum()} runs); share of time in those runs: "
      f"{vrl[vrl>500].sum()/vrl.sum()*100:.1f}%")

# How long VFE stays above/below FV (use 25-tick smoothing to ignore noise crossings)
vfe["mid_s"] = vfe["mid"].rolling(25, min_periods=1).mean()
vfe["sign_s"] = np.sign(vfe["mid_s"] - VFE_FV)
vfe_runs_s = (vfe["sign_s"] != vfe["sign_s"].shift()).cumsum()
vrl_s = vfe.groupby(vfe_runs_s).size()
print(f"VFE smoothed sign-run median={vrl_s.median():.0f} p75={vrl_s.quantile(0.75):.0f} "
      f"p90={vrl_s.quantile(0.9):.0f} max={vrl_s.max()}; "
      f"frac runs > 500: {(vrl_s>500).mean()*100:.1f}%; "
      f"time in runs > 500: {vrl_s[vrl_s>500].sum()/vrl_s.sum()*100:.1f}%")

fig, axes = plt.subplots(3, 1, figsize=(12, 9))
for i, d in enumerate((0, 1, 2)):
    g = vfe[vfe["day"] == d]
    axes[i].plot(g["timestamp"], g["mid"], lw=0.4)
    axes[i].axhline(VFE_FV, color="r", lw=0.5)
    axes[i].set_title(f"VFE day {d}")
fig.tight_layout()
fig.savefig(OUT / "16_vfe_regime.png", dpi=80)
plt.close(fig)

# ------- Voucher delta per strike -------
print("\n=== Voucher Δ wrt VFE ===")
vouchers = [c for c in products if c.startswith("VEV_")]
# resampling - per day, delta per 50-tick window
deltas = {}
for v in vouchers:
    sub = pivot[["day", "timestamp", "VELVETFRUIT_EXTRACT", v]].dropna()
    if len(sub) < 1000:
        continue
    rows = []
    for d, g in sub.groupby("day"):
        g = g.sort_values("timestamp")
        dvfe = g["VELVETFRUIT_EXTRACT"].diff()
        dvev = g[v].diff()
        # OLS slope (no intercept), restricted to rows where VFE moved
        m = dvfe.abs() > 0
        if m.sum() < 50:
            continue
        x, y = dvfe[m].values, dvev[m].values
        slope = (x * y).sum() / (x * x).sum()
        # also corr
        corr = np.corrcoef(x, y)[0, 1] if len(x) > 2 else np.nan
        rows.append((d, slope, corr, m.sum()))
    deltas[v] = rows
    overall = rows
    avg_slope = np.mean([r[1] for r in overall])
    avg_corr = np.mean([r[2] for r in overall])
    print(f"{v}: slope by day = " + ", ".join(f"d{r[0]}={r[1]:+.3f}" for r in overall) +
          f"  | corr avg={avg_corr:+.2f}  | n moves avg={int(np.mean([r[3] for r in overall]))}")

# Plot deltas vs strike
strikes = []
slopes_avg = []
for v in vouchers:
    if v in deltas and deltas[v]:
        K = int(v.split("_")[1])
        strikes.append(K)
        slopes_avg.append(np.mean([r[1] for r in deltas[v]]))
order = np.argsort(strikes)
strikes = np.array(strikes)[order]
slopes_avg = np.array(slopes_avg)[order]
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(strikes, slopes_avg, "o-")
ax.axhline(1.0, color="r", ls="--", lw=0.5, label="delta=1")
ax.axvline(5250, color="g", ls=":", lw=0.5, label="VFE FV")
ax.set_xlabel("Strike"); ax.set_ylabel("ΔVoucher / ΔVFE (tick-level slope)")
ax.set_title("Empirical delta per strike (avg across 3 days)")
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT / "16_voucher_delta_per_strike.png", dpi=80)
plt.close(fig)

# ------- Co-movement regimes HG vs VFE -------
print("\n=== HG vs VFE regime correlation ===")
joint = pivot[["day", "timestamp", "HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"]].dropna()
joint["hg_r"] = joint["HYDROGEL_PACK"].diff()
joint["vfe_r"] = joint["VELVETFRUIT_EXTRACT"].diff()
W = 500
joint["roll_corr"] = joint["hg_r"].rolling(W).corr(joint["vfe_r"])
print(f"rolling-{W} corr: mean={joint['roll_corr'].mean():.3f} std={joint['roll_corr'].std():.3f} "
      f"min={joint['roll_corr'].min():.2f} max={joint['roll_corr'].max():.2f}")
extreme_pos = (joint["roll_corr"] > 0.2).mean()
extreme_neg = (joint["roll_corr"] < -0.2).mean()
print(f"share with |corr|>0.2: pos={extreme_pos*100:.1f}% neg={extreme_neg*100:.1f}%")

fig, ax = plt.subplots(figsize=(12, 4))
for d, g in joint.groupby("day"):
    ax.plot(g["timestamp"], g["roll_corr"], lw=0.5, label=f"day {d}")
ax.axhline(0, color="k", lw=0.4)
ax.set_title(f"HG-VFE rolling-{W} return correlation")
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT / "16_hgvfe_rollcorr.png", dpi=80)
plt.close(fig)

# ------- Time-of-day patterns -------
print("\n=== Time-of-day patterns ===")
joint["bucket"] = (joint["timestamp"] // 100000)  # 10 buckets per day
hg2 = pivot[["day", "timestamp", "HYDROGEL_PACK"]].dropna()
hg2["bucket"] = hg2["timestamp"] // 100000
hg2["ret"] = hg2["HYDROGEL_PACK"].diff()
hg_bucket = hg2.groupby("bucket")["ret"].std()
print("HG std by intraday bucket:", hg_bucket.round(2).to_dict())

vfe2 = pivot[["day", "timestamp", "VELVETFRUIT_EXTRACT"]].dropna()
vfe2["bucket"] = vfe2["timestamp"] // 100000
vfe2["ret"] = vfe2["VELVETFRUIT_EXTRACT"].diff()
vfe_bucket = vfe2.groupby("bucket")["ret"].std()
print("VFE std by intraday bucket:", vfe_bucket.round(3).to_dict())

# Spread by bucket using bid1/ask1
prices2 = prices.copy()
prices2["spread"] = prices2["ask_price_1"] - prices2["bid_price_1"]
prices2["bucket"] = prices2["timestamp"] // 100000
for prod in ("HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"):
    sp = prices2[prices2["product"] == prod].groupby("bucket")["spread"].mean()
    print(f"{prod} spread by bucket:", sp.round(2).to_dict())

# Trade volume per bucket from trades file
tdfs = []
for d in (0, 1, 2):
    t = pd.read_csv(DATA / f"trades_round_3_day_{d}.csv", sep=";")
    t["day"] = d
    tdfs.append(t)
trades = pd.concat(tdfs, ignore_index=True)
trades["bucket"] = trades["timestamp"] // 100000
for prod in ("HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"):
    vol = trades[trades["symbol"] == prod].groupby("bucket")["quantity"].sum()
    print(f"{prod} trade volume by bucket:", vol.to_dict())

fig, axes = plt.subplots(2, 1, figsize=(10, 6))
hg_bucket.plot(ax=axes[0], marker="o", title="HG mid-return std by bucket (intraday)")
vfe_bucket.plot(ax=axes[1], marker="o", title="VFE mid-return std by bucket (intraday)")
fig.tight_layout()
fig.savefig(OUT / "16_intraday_vol.png", dpi=80)
plt.close(fig)

print("\nDONE")
