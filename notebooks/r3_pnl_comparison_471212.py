"""
Three-panel PnL comparison centered on production run 471212.

Panel 1:
  New production run (471212)

Panel 2:
  Historical production runs overlaid

Panel 3:
  Latest local round-3 backtest from src/trader.py

Each panel plots HYDROGEL, VELVETFRUIT, VEV-options combined, and Net PnL.
"""

import json
from io import StringIO
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
RUNS_DIR = ROOT / "runs"

NEW_LOG_ID = "471212"
HIST_LOG_IDS = ["446230", "451894", "454537", "455790", "460222", "462153", "464669"]
HIST_COLORS = ["#9ecae1", "#74c476", "#fdae6b", "#fd8d3c", "#e6550d", "#a63603", "#756bb1"]
BACKTEST_ID = "backtest-1777190830322"
BACKTEST_DAYS = ("day-0", "day+1", "day+2")

C_HYDROGEL = "#2171b5"
C_VELVET = "#238b45"
C_VOUCHER = "#d94801"
C_NET = "#6a3d9a"


def load_log_json(path: Path) -> pd.DataFrame:
    with path.open() as f:
        data = json.load(f)
    return pd.read_csv(StringIO(data["activitiesLog"]), sep=";")


def load_log_bundle(log_id: str) -> pd.DataFrame:
    log_dir = LOGS_DIR / log_id
    for suffix in (".json", ".log"):
        path = log_dir / f"{log_id}{suffix}"
        if path.exists():
            return load_log_json(path)
    raise FileNotFoundError(f"No JSON-style log found for {log_id}")


def load_backtest(run_id: str, days: tuple[str, ...]) -> pd.DataFrame:
    dfs: list[pd.DataFrame] = []
    for day in days:
        path = RUNS_DIR / f"{run_id}-round3-{day}" / "submission.log"
        if path.exists():
            dfs.append(load_log_json(path))
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def extract_pnl(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_vev"] = df["product"].str.startswith("VEV_")

    rows = []
    for (day, ts), grp in df.groupby(["day", "timestamp"], sort=True):
        hydrogel = grp.loc[grp["product"] == "HYDROGEL_PACK", "profit_and_loss"]
        velvet = grp.loc[grp["product"] == "VELVETFRUIT_EXTRACT", "profit_and_loss"]
        vev = grp.loc[grp["is_vev"], "profit_and_loss"]
        rows.append(
            {
                "day": day,
                "timestamp": ts,
                "hydrogel": hydrogel.iloc[0] if len(hydrogel) else np.nan,
                "velvet": velvet.iloc[0] if len(velvet) else np.nan,
                "voucher": vev.sum() if len(vev) else np.nan,
            }
        )

    out = pd.DataFrame(rows).sort_values(["day", "timestamp"]).reset_index(drop=True)
    out["net"] = out[["hydrogel", "velvet", "voucher"]].sum(axis=1)

    day_order = {day: idx for idx, day in enumerate(sorted(out["day"].unique()))}
    stride = int(out.groupby("day")["timestamp"].max().max()) + 100
    out["t"] = out["day"].map(day_order) * stride + out["timestamp"]
    return out


def plot_pnl_panel(
    ax: plt.Axes,
    pnl: pd.DataFrame,
    title: str,
    hydrogel_kw: dict | None = None,
    velvet_kw: dict | None = None,
    voucher_kw: dict | None = None,
    net_kw: dict | None = None,
) -> None:
    hkw = dict(color=C_HYDROGEL, linewidth=1.4, label="HYDROGEL")
    vkw = dict(color=C_VELVET, linewidth=1.4, label="VELVETFRUIT")
    okw = dict(color=C_VOUCHER, linewidth=1.4, label="VEV Options")
    nkw = dict(color=C_NET, linewidth=2.0, label="Net", linestyle="--")
    if hydrogel_kw:
        hkw.update(hydrogel_kw)
    if velvet_kw:
        vkw.update(velvet_kw)
    if voucher_kw:
        okw.update(voucher_kw)
    if net_kw:
        nkw.update(net_kw)

    ax.plot(pnl["t"], pnl["hydrogel"], **hkw)
    ax.plot(pnl["t"], pnl["velvet"], **vkw)
    ax.plot(pnl["t"], pnl["voucher"], **okw)
    ax.plot(pnl["t"], pnl["net"], **nkw)
    ax.axhline(0, color="black", linewidth=0.6, linestyle=":")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_ylabel("PnL (seashells)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(True, alpha=0.25)


fig, axes = plt.subplots(3, 1, figsize=(14, 16))
fig.suptitle(
    "Round 3 PnL — HYDROGEL / VELVETFRUIT / VEV Options / Net",
    fontsize=13,
    fontweight="bold",
    y=0.995,
)
plt.subplots_adjust(hspace=0.45)

# Panel 1 — new production run.
df_new = load_log_bundle(NEW_LOG_ID)
pnl_new = extract_pnl(df_new)
plot_pnl_panel(axes[0], pnl_new, f"Production run {NEW_LOG_ID} (latest)")
final_new = pnl_new.iloc[-1]
axes[0].annotate(
    f"Final: HYD={final_new['hydrogel']:,.0f}  VF={final_new['velvet']:,.0f}"
    f"  VEV={final_new['voucher']:,.0f}  Net={final_new['net']:,.0f}",
    xy=(0.01, 0.03),
    xycoords="axes fraction",
    fontsize=8,
    color="dimgray",
)
axes[0].legend(loc="upper left", fontsize=9)

# Panel 2 — historical production logs.
ax_hist = axes[1]
for log_id, color in zip(HIST_LOG_IDS, HIST_COLORS):
    try:
        df_hist = load_log_bundle(log_id)
    except FileNotFoundError:
        continue
    pnl_hist = extract_pnl(df_hist)
    ax_hist.plot(pnl_hist["t"], pnl_hist["net"], color=color, linewidth=1.3, label=f"{log_id} (net)", linestyle="--")
    ax_hist.plot(pnl_hist["t"], pnl_hist["hydrogel"], color=color, linewidth=0.8, alpha=0.6)
    ax_hist.plot(pnl_hist["t"], pnl_hist["velvet"], color=color, linewidth=0.8, alpha=0.6)
    ax_hist.plot(pnl_hist["t"], pnl_hist["voucher"], color=color, linewidth=0.8, alpha=0.6)

legend_elements = [
    Line2D([0], [0], color="gray", linewidth=1.4, linestyle="-", label="HYDROGEL / VELVET / VEV (thin)"),
    Line2D([0], [0], color="gray", linewidth=1.4, linestyle="--", label="Net (dashed)"),
] + [Line2D([0], [0], color=color, linewidth=1.4, label=log_id) for log_id, color in zip(HIST_LOG_IDS, HIST_COLORS)]
ax_hist.legend(handles=legend_elements, fontsize=8, loc="upper left", ncol=2)
ax_hist.axhline(0, color="black", linewidth=0.6, linestyle=":")
ax_hist.set_title("Historical production runs (overlaid)", fontsize=11, fontweight="bold")
ax_hist.set_ylabel("PnL (seashells)")
ax_hist.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax_hist.grid(True, alpha=0.25)

# Panel 3 — latest local backtest.
df_backtest = load_backtest(BACKTEST_ID, BACKTEST_DAYS)
if not df_backtest.empty:
    pnl_backtest = extract_pnl(df_backtest)
    plot_pnl_panel(axes[2], pnl_backtest, f"Backtest {BACKTEST_ID} (round 3, all 3 days)")
    final_bt = pnl_backtest.iloc[-1]
    axes[2].annotate(
        f"Final: HYD={final_bt['hydrogel']:,.0f}  VF={final_bt['velvet']:,.0f}"
        f"  VEV={final_bt['voucher']:,.0f}  Net={final_bt['net']:,.0f}",
        xy=(0.01, 0.03),
        xycoords="axes fraction",
        fontsize=8,
        color="dimgray",
    )
    axes[2].legend(loc="upper left", fontsize=9)
else:
    axes[2].text(0.5, 0.5, "Backtest data not found", ha="center", va="center", transform=axes[2].transAxes)

axes[2].set_xlabel("Tick (monotonic across days)", fontsize=9)

out_path = ROOT / "notebooks" / "r3_plots" / "471212_pnl_comparison.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Saved -> {out_path}")
