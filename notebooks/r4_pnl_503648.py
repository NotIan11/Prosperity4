"""
Plot PnL breakdown for live run 503648 (Round 4, Day 3).
- HG (HYDROGEL_PACK) PnL
- VFE (VELVETFRUIT_EXTRACT) PnL
- VEV (sum of all VEV_* vouchers) PnL
- Net PnL
Overlaid with HG mid_price (right y-axis) and VFE mid_price (right y-axis).
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from io import StringIO

LOG_PATH = "logs/503648/503648.json"
OUT_PATH = "notebooks/r4_plots/live_503648_pnl.png"

# ── load ────────────────────────────────────────────────────────────────────

with open(LOG_PATH) as f:
    raw = json.load(f)

df = pd.read_csv(StringIO(raw["activitiesLog"]), sep=";")

# ── build per-tick PnL series ────────────────────────────────────────────────

rows = []
for (day, ts), grp in df.groupby(["day", "timestamp"]):
    hg   = grp.loc[grp["product"] == "HYDROGEL_PACK",         "profit_and_loss"]
    vfe  = grp.loc[grp["product"] == "VELVETFRUIT_EXTRACT",   "profit_and_loss"]
    vev  = grp.loc[grp["product"].str.startswith("VEV_"),     "profit_and_loss"]
    hg_p = grp.loc[grp["product"] == "HYDROGEL_PACK",         "mid_price"]
    vfe_p= grp.loc[grp["product"] == "VELVETFRUIT_EXTRACT",   "mid_price"]
    rows.append({
        "day":       day,
        "timestamp": ts,
        "hg_pnl":    hg.iloc[0]   if len(hg)  else np.nan,
        "vfe_pnl":   vfe.iloc[0]  if len(vfe) else np.nan,
        "vev_pnl":   vev.sum()    if len(vev) else np.nan,
        "hg_price":  hg_p.iloc[0] if len(hg_p)  else np.nan,
        "vfe_price": vfe_p.iloc[0]if len(vfe_p) else np.nan,
    })

pnl = pd.DataFrame(rows).sort_values(["day", "timestamp"]).reset_index(drop=True)

# Build monotonic x across days
stride = pnl.groupby("day")["timestamp"].max().max() + 100
pnl["t"] = (pnl["day"].rank(method="dense").astype(int) - 1) * stride + pnl["timestamp"]

pnl["net_pnl"] = pnl[["hg_pnl", "vfe_pnl", "vev_pnl"]].sum(axis=1, min_count=1)

# ── colour palette ───────────────────────────────────────────────────────────

C_HG  = "#2171b5"   # blue
C_VFE = "#238b45"   # green
C_VEV = "#d94801"   # orange-red
C_NET = "#6a3d9a"   # purple
C_HG_PRICE  = "#9ecae1"  # light blue
C_VFE_PRICE = "#74c476"  # light green

# ── plot ─────────────────────────────────────────────────────────────────────

days = sorted(pnl["day"].unique())
n = len(days)

fig, axes = plt.subplots(n, 1, figsize=(16, 5 * n), squeeze=False)
fig.suptitle("Live Run 503648 — PnL Breakdown with Prices", fontsize=14, fontweight="bold")

for ax_idx, day in enumerate(days):
    sub = pnl[pnl["day"] == day].copy()
    t   = sub["t"]

    ax = axes[ax_idx][0]
    ax2 = ax.twinx()

    # ── prices on right axis (faint) ────────────────────────────────────────
    if sub["hg_price"].notna().any():
        ax2.plot(t, sub["hg_price"],  color=C_HG_PRICE,  lw=1.2, alpha=0.55, label="HG price")
    if sub["vfe_price"].notna().any():
        ax2.plot(t, sub["vfe_price"], color=C_VFE_PRICE, lw=1.2, alpha=0.55, ls="--", label="VFE price")
    ax2.set_ylabel("Mid Price", fontsize=9)
    ax2.tick_params(axis="y", labelsize=8)

    # ── PnL on left axis ────────────────────────────────────────────────────
    ax.plot(t, sub["hg_pnl"],  color=C_HG,  lw=1.5, label="HG PnL")
    ax.plot(t, sub["vfe_pnl"], color=C_VFE, lw=1.5, label="VFE PnL")
    ax.plot(t, sub["vev_pnl"], color=C_VEV, lw=1.5, label="VEV PnL")
    ax.plot(t, sub["net_pnl"], color=C_NET, lw=2.2, ls="--", label="Net PnL")

    ax.axhline(0, color="gray", lw=0.5, ls=":")
    ax.set_title(f"Day {day}", fontsize=11)
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("PnL (seashells)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.tick_params(axis="both", labelsize=8)

    # combined legend
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8, framealpha=0.7)

    # final net PnL annotation
    final_net = sub["net_pnl"].dropna().iloc[-1] if sub["net_pnl"].notna().any() else np.nan
    if not np.isnan(final_net):
        ax.annotate(
            f"Net: {final_net:,.0f}",
            xy=(t.iloc[-1], final_net),
            xytext=(-60, 10),
            textcoords="offset points",
            fontsize=9,
            color=C_NET,
            fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C_NET, lw=0.8),
        )

plt.tight_layout()
plt.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
print(f"Saved to {OUT_PATH}")
plt.show()
