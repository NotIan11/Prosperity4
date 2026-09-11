"""
Three-panel PnL comparison:
  1. New production run (462153)
  2. Historical production runs (446230, 451894, 454537, 455790, 460222)
  3. Latest backtest (backtest-1777184301555, round3 all days)

Each panel plots: HYDROGEL, VELVETFRUIT, VEV-options combined, and Net PnL
on the same axes over time.
"""
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from io import StringIO

# ── helpers ───────────────────────────────────────────────────────────────

def load_log(path: str) -> pd.DataFrame:
    with open(path) as f:
        data = json.load(f)
    df = pd.read_csv(StringIO(data["activitiesLog"]), sep=";")
    return df


def extract_pnl(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a DataFrame indexed by (day, timestamp) with columns:
      hydrogel, velvet, voucher (sum of all VEV_*), net
    Each entry is the last recorded PnL value at that timestamp.
    """
    df = df.copy()
    df["is_vev"] = df["product"].str.startswith("VEV_")

    # pivot so we get one row per (day, timestamp, product)
    # then group to compute per-category latest PnL at each tick
    rows = []
    for (day, ts), grp in df.groupby(["day", "timestamp"]):
        hydrogel = grp.loc[grp["product"] == "HYDROGEL_PACK", "profit_and_loss"]
        velvet   = grp.loc[grp["product"] == "VELVETFRUIT_EXTRACT", "profit_and_loss"]
        vev      = grp.loc[grp["is_vev"], "profit_and_loss"]
        rows.append({
            "day":       day,
            "timestamp": ts,
            "hydrogel":  hydrogel.iloc[0] if len(hydrogel) else np.nan,
            "velvet":    velvet.iloc[0]   if len(velvet)   else np.nan,
            "voucher":   vev.sum()        if len(vev)      else np.nan,
        })

    out = pd.DataFrame(rows).sort_values(["day", "timestamp"]).reset_index(drop=True)
    out["net"] = out[["hydrogel", "velvet", "voucher"]].sum(axis=1)
    # Build a monotonic x-axis by offsetting each day
    stride = out.groupby("day")["timestamp"].max().max() + 100
    out["t"] = out["day_idx"] if "day_idx" in out.columns else (
        out["day"].rank(method="dense").astype(int) - 1
    ) * stride + out["timestamp"]
    return out


def load_backtest(run_id: str, days=("day-0", "day+1", "day+2")) -> pd.DataFrame:
    dfs = []
    for d in days:
        path = f"runs/{run_id}-round3-{d}/submission.log"
        try:
            dfs.append(load_log(path))
        except FileNotFoundError:
            pass
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


# ── colour palette ────────────────────────────────────────────────────────
C_HYDROGEL = "#2171b5"
C_VELVET   = "#238b45"
C_VOUCHER  = "#d94801"
C_NET      = "#6a3d9a"

HIST_LOG_IDS = ["446230", "451894", "454537", "455790", "460222", "462153"]
HIST_COLORS  = ["#9ecae1", "#74c476", "#fdae6b", "#fd8d3c", "#e6550d", "#a63603"]

NEW_LOG_ID  = "464669"
BACKTEST_ID = "backtest-1777185929489"


def plot_pnl_panel(ax: plt.Axes, pnl: pd.DataFrame, title: str,
                   hydrogel_kw=None, velvet_kw=None, voucher_kw=None, net_kw=None):
    """Plot the four PnL lines onto ax."""
    hkw = dict(color=C_HYDROGEL, linewidth=1.4, label="HYDROGEL")
    vkw = dict(color=C_VELVET,   linewidth=1.4, label="VELVETFRUIT")
    okw = dict(color=C_VOUCHER,  linewidth=1.4, label="VEV Options")
    nkw = dict(color=C_NET,      linewidth=2.0, label="Net",  linestyle="--")
    if hydrogel_kw: hkw.update(hydrogel_kw)
    if velvet_kw:   vkw.update(velvet_kw)
    if voucher_kw:  okw.update(voucher_kw)
    if net_kw:      nkw.update(net_kw)

    ax.plot(pnl["t"], pnl["hydrogel"], **hkw)
    ax.plot(pnl["t"], pnl["velvet"],   **vkw)
    ax.plot(pnl["t"], pnl["voucher"],  **okw)
    ax.plot(pnl["t"], pnl["net"],      **nkw)
    ax.axhline(0, color="black", linewidth=0.6, linestyle=":")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_ylabel("PnL (seashells)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(True, alpha=0.25)


# ── main ──────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(14, 16))
fig.suptitle("Round 3 PnL — HYDROGEL / VELVETFRUIT / VEV Options / Net",
             fontsize=13, fontweight="bold", y=0.995)
plt.subplots_adjust(hspace=0.45)

# Panel 1 — New production run (462153)
df1  = load_log(f"logs/{NEW_LOG_ID}/{NEW_LOG_ID}.log")
pnl1 = extract_pnl(df1)
plot_pnl_panel(axes[0], pnl1, f"Production run {NEW_LOG_ID} (latest)")
final = pnl1.iloc[-1]
axes[0].annotate(
    f"Final: HYD={final['hydrogel']:,.0f}  VF={final['velvet']:,.0f}"
    f"  VEV={final['voucher']:,.0f}  Net={final['net']:,.0f}",
    xy=(0.01, 0.03), xycoords="axes fraction", fontsize=8, color="dimgray")
axes[0].legend(loc="upper left", fontsize=9)

# Panel 2 — Historical production logs (all previous runs) overlaid
ax2 = axes[1]
for lid, clr in zip(HIST_LOG_IDS, HIST_COLORS):
    try:
        dfh  = load_log(f"logs/{lid}/{lid}.log")
        pnlh = extract_pnl(dfh)
        ax2.plot(pnlh["t"], pnlh["net"], color=clr, linewidth=1.3, label=f"{lid} (net)", linestyle="--")
        ax2.plot(pnlh["t"], pnlh["hydrogel"], color=clr, linewidth=0.8, alpha=0.6, linestyle="-")
        ax2.plot(pnlh["t"], pnlh["velvet"],   color=clr, linewidth=0.8, alpha=0.6, linestyle="-")
        ax2.plot(pnlh["t"], pnlh["voucher"],  color=clr, linewidth=0.8, alpha=0.6, linestyle="-")
    except FileNotFoundError:
        pass

# Legend for products (shared across logs)
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], color="gray", linewidth=1.4, linestyle="-",  label="HYDROGEL / VELVET / VEV (thin)"),
    Line2D([0], [0], color="gray", linewidth=1.4, linestyle="--", label="Net (dashed)"),
] + [
    Line2D([0], [0], color=c, linewidth=1.4, label=lid)
    for lid, c in zip(HIST_LOG_IDS, HIST_COLORS)
]
ax2.legend(handles=legend_elements, fontsize=8, loc="upper left", ncol=2)
ax2.axhline(0, color="black", linewidth=0.6, linestyle=":")
ax2.set_title("Historical production runs (overlaid)", fontsize=11, fontweight="bold")
ax2.set_ylabel("PnL (seashells)")
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax2.grid(True, alpha=0.25)

# Panel 3 — Latest backtest
dfb  = load_backtest(BACKTEST_ID)
pnlb = extract_pnl(dfb) if not dfb.empty else pd.DataFrame()
if not pnlb.empty:
    plot_pnl_panel(axes[2], pnlb, f"Backtest {BACKTEST_ID} (round 3, all 3 days)")
    final_b = pnlb.iloc[-1]
    axes[2].annotate(
        f"Final: HYD={final_b['hydrogel']:,.0f}  VF={final_b['velvet']:,.0f}"
        f"  VEV={final_b['voucher']:,.0f}  Net={final_b['net']:,.0f}",
        xy=(0.01, 0.03), xycoords="axes fraction", fontsize=8, color="dimgray")
    axes[2].legend(loc="upper left", fontsize=9)
else:
    axes[2].text(0.5, 0.5, "Backtest data not found", ha="center", va="center",
                 transform=axes[2].transAxes)

axes[2].set_xlabel("Tick (monotonic across days)", fontsize=9)

out_path = "notebooks/r3_plots/r3_pnl_comparison.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Saved → {out_path}")
plt.show()
