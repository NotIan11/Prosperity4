"""
Plot PnL vs mid-price for every product in the latest round-5 backtest.

One PNG per product family saved to notebooks/r5_plots/.
Each figure: 5 columns (one per variant) × 1 row.
Left axis = cumulative PnL, right axis = mid price.
Days are plotted separately in each panel, separated by vertical lines.
X-axis shows timestamp (0–1,000,000) with day labels.
"""

import json
from io import StringIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ── config ────────────────────────────────────────────────────────────────────
RUN_ID = "1777440854215"
DAYS = [
    ("day+2", 2),
    ("day+3", 3),
    ("day+4", 4),
]
ROUND = 5

FAMILIES = {
    "GALAXY_SOUNDS": [
        "GALAXY_SOUNDS_BLACK_HOLES",
        "GALAXY_SOUNDS_DARK_MATTER",
        "GALAXY_SOUNDS_PLANETARY_RINGS",
        "GALAXY_SOUNDS_SOLAR_FLAMES",
        "GALAXY_SOUNDS_SOLAR_WINDS",
    ],
    "MICROCHIP": [
        "MICROCHIP_CIRCLE",
        "MICROCHIP_OVAL",
        "MICROCHIP_RECTANGLE",
        "MICROCHIP_SQUARE",
        "MICROCHIP_TRIANGLE",
    ],
    "OXYGEN_SHAKE": [
        "OXYGEN_SHAKE_CHOCOLATE",
        "OXYGEN_SHAKE_EVENING_BREATH",
        "OXYGEN_SHAKE_GARLIC",
        "OXYGEN_SHAKE_MINT",
        "OXYGEN_SHAKE_MORNING_BREATH",
    ],
    "PANEL": [
        "PANEL_1X2",
        "PANEL_1X4",
        "PANEL_2X2",
        "PANEL_2X4",
        "PANEL_4X4",
    ],
    "PEBBLES": [
        "PEBBLES_L",
        "PEBBLES_M",
        "PEBBLES_S",
        "PEBBLES_XL",
        "PEBBLES_XS",
    ],
    "ROBOT": [
        "ROBOT_DISHES",
        "ROBOT_IRONING",
        "ROBOT_LAUNDRY",
        "ROBOT_MOPPING",
        "ROBOT_VACUUMING",
    ],
    "SLEEP_POD": [
        "SLEEP_POD_COTTON",
        "SLEEP_POD_LAMB_WOOL",
        "SLEEP_POD_NYLON",
        "SLEEP_POD_POLYESTER",
        "SLEEP_POD_SUEDE",
    ],
    "SNACKPACK": [
        "SNACKPACK_CHOCOLATE",
        "SNACKPACK_PISTACHIO",
        "SNACKPACK_RASPBERRY",
        "SNACKPACK_STRAWBERRY",
        "SNACKPACK_VANILLA",
    ],
    "TRANSLATOR": [
        "TRANSLATOR_ASTRO_BLACK",
        "TRANSLATOR_ECLIPSE_CHARCOAL",
        "TRANSLATOR_GRAPHITE_MIST",
        "TRANSLATOR_SPACE_GRAY",
        "TRANSLATOR_VOID_BLUE",
    ],
    "UV_VISOR": [
        "UV_VISOR_AMBER",
        "UV_VISOR_MAGENTA",
        "UV_VISOR_ORANGE",
        "UV_VISOR_RED",
        "UV_VISOR_YELLOW",
    ],
}

OUT_DIR = Path("notebooks/r5_plots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── load data ─────────────────────────────────────────────────────────────────
frames = []
for day_tag, day_num in DAYS:
    path = Path(f"runs/backtest-{RUN_ID}-round{ROUND}-{day_tag}/submission.log")
    if not path.exists():
        print(f"[warn] missing {path}")
        continue
    with open(path) as fh:
        data = json.load(fh)
    df = pd.read_csv(StringIO(data["activitiesLog"]), sep=";")
    # Use a simple sequential index (0 to N-1) as x so bbox_inches='tight'
    # can't blow up from million-scale tick values.
    df["day_num"] = day_num
    frames.append(df)

all_df = pd.concat(frames, ignore_index=True)
all_df.sort_values(["product", "day_num", "timestamp"], inplace=True)

# Build a compact x-axis: within each day, timestamp goes 0..999,900.
# Stitch days as 0..n_ticks across all days.
def make_x(sub: pd.DataFrame) -> np.ndarray:
    """Return a monotone integer index spanning all days."""
    xs = []
    offset = 0
    for _, grp in sub.groupby("day_num", sort=True):
        ts = grp["timestamp"].values
        xs.append(ts - ts[0] + offset)
        offset += ts[-1] - ts[0] + 100
    return np.concatenate(xs)

# Pre-compute day boundary x positions for vertical lines (one per product)
# They'll be computed inside the loop per product.

# Distinct colours for up to 5 variants
PALETTE = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd", "#ff7f0e"]

# ── plot one figure per family — all variants on shared axes ─────────────────
for family, variants in FAMILIES.items():
    fig, (ax, ax2) = plt.subplots(
        2, 1,
        figsize=(12, 6),
        sharex=True,
        gridspec_kw={"height_ratios": [2, 1]},
    )
    fig.suptitle(
        f"Round {ROUND} Backtest — {family} | PnL (top) & Mid Price (bottom)",
        fontsize=11,
    )

    day_boundaries = None  # compute once from first non-empty product

    for color, product in zip(PALETTE, variants):
        sub = all_df[all_df["product"] == product].copy()
        if sub.empty:
            continue

        sub = sub.sort_values(["day_num", "timestamp"])
        xs = make_x(sub)
        pnl = sub["profit_and_loss"].values
        mid = sub["mid_price"].values

        # Compute day boundaries once
        if day_boundaries is None:
            day_boundaries = []
            offset = 0
            for idx, (_, grp) in enumerate(sub.groupby("day_num", sort=True)):
                ts = grp["timestamp"].values
                day_len = ts[-1] - ts[0] + 100
                if idx > 0:
                    day_boundaries.append(offset)
                offset += day_len
            tick_positions = [0] + day_boundaries
            tick_labels = [f"D{d}" for _, d in DAYS]

        variant_label = product.replace(family + "_", "").replace("_", " ")
        final_pnl = pnl[-1]
        label = f"{variant_label}  ({final_pnl:+,.0f})"

        ax.plot(xs, pnl, color=color, lw=1.1, rasterized=True, label=label)
        ax2.plot(xs, mid, color=color, lw=0.8, alpha=0.7, rasterized=True, label=variant_label)

    # Day boundary lines
    for b in (day_boundaries or []):
        ax.axvline(b, color="black", lw=0.8, ls=":", alpha=0.5)
        ax2.axvline(b, color="black", lw=0.8, ls=":", alpha=0.5)

    ax.axhline(0, color="gray", lw=0.5, ls="--")
    ax.set_ylabel("PnL", fontsize=9)
    ax.legend(fontsize=7, loc="upper left", ncol=2)
    ax.grid(True, alpha=0.2, lw=0.4)

    ax2.set_ylabel("Mid Price", fontsize=9)
    ax2.set_xlabel("Day", fontsize=9)
    ax2.grid(True, alpha=0.2, lw=0.4)

    if day_boundaries is not None:
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, fontsize=8)

    fig.subplots_adjust(top=0.91, hspace=0.08)
    out_path = OUT_DIR / f"pnl_vs_price_{family.lower()}.png"
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"Saved {out_path}")

print("\nDone — all plots saved to", OUT_DIR)
