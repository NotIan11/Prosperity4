"""
Plot historical price data for each product with bot trading activity overlaid.
Outputs one image per product, 3 subplots (one per day), saved to notebooks/r4_plots/.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

DATA_DIR = "data/round4"
OUT_DIR = "notebooks/r4_plots"
os.makedirs(OUT_DIR, exist_ok=True)

# Load prices
prices = {}
for day in [1, 2, 3]:
    df = pd.read_csv(f"{DATA_DIR}/prices_round_4_day_{day}.csv", sep=";")
    prices[day] = df

# Load trades
trades = {}
for day in [1, 2, 3]:
    df = pd.read_csv(f"{DATA_DIR}/trades_round_4_day_{day}.csv", sep=";")
    trades[day] = df

# All bots (7 total — fits in a single 5-10 group)
all_bots = sorted(
    set(
        b
        for day in [1, 2, 3]
        for b in list(trades[day]["buyer"].unique()) + list(trades[day]["seller"].unique())
    )
)

# Colors per bot
COLORS = [
    "#e41a1c", "#377eb8", "#4daf4a", "#984ea3",
    "#ff7f00", "#a65628", "#f781bf",
]
bot_color = {bot: COLORS[i % len(COLORS)] for i, bot in enumerate(all_bots)}

products = sorted(
    set(
        p
        for day in [1, 2, 3]
        for p in prices[day]["product"].unique()
    )
)

# Build a day offset map so timestamps increase across days on x-axis
# (each day is 1_000_000 ticks long)
DAY_LEN = 1_000_000

def make_product_plot(product: str):
    fig, axes = plt.subplots(3, 1, figsize=(18, 15), sharex=False)
    fig.suptitle(f"Product: {product} — Bot Activity by Day", fontsize=14, fontweight="bold")

    for ax_idx, day in enumerate([1, 2, 3]):
        ax = axes[ax_idx]

        # Price line
        price_df = prices[day][prices[day]["product"] == product].copy()
        price_df = price_df.sort_values("timestamp")
        if not price_df.empty:
            ax.plot(
                price_df["timestamp"],
                price_df["mid_price"],
                color="black",
                lw=1.0,
                alpha=0.8,
                label="mid price",
                zorder=2,
            )

        # Bot trades
        day_trades = trades[day][trades[day]["symbol"] == product].copy()

        for bot in all_bots:
            color = bot_color[bot]

            # Buys: bot appears as buyer
            buys = day_trades[day_trades["buyer"] == bot]
            if not buys.empty:
                ax.scatter(
                    buys["timestamp"],
                    buys["price"],
                    color=color,
                    marker="^",
                    s=60,
                    alpha=0.85,
                    zorder=3,
                    label=f"{bot} buy",
                )

            # Sells: bot appears as seller
            sells = day_trades[day_trades["seller"] == bot]
            if not sells.empty:
                ax.scatter(
                    sells["timestamp"],
                    sells["price"],
                    color=color,
                    marker="v",
                    s=60,
                    alpha=0.85,
                    zorder=3,
                    label=f"{bot} sell",
                )

        ax.set_title(f"Day {day}", fontsize=11)
        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Price")
        ax.grid(True, alpha=0.3)

    # Unified legend: one entry per bot (color), plus shape legend for buy/sell
    bot_patches = [
        mpatches.Patch(color=bot_color[b], label=b) for b in all_bots
    ]
    buy_marker = plt.Line2D(
        [], [], color="gray", marker="^", linestyle="None", markersize=8, label="buy"
    )
    sell_marker = plt.Line2D(
        [], [], color="gray", marker="v", linestyle="None", markersize=8, label="sell"
    )
    price_line = plt.Line2D([], [], color="black", lw=1.5, label="mid price")

    fig.legend(
        handles=bot_patches + [buy_marker, sell_marker, price_line],
        loc="lower center",
        ncol=len(all_bots) + 3,
        bbox_to_anchor=(0.5, -0.01),
        fontsize=9,
        framealpha=0.9,
    )

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    safe_name = product.replace("/", "_")
    out_path = os.path.join(OUT_DIR, f"{safe_name}.png")
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


for product in products:
    make_product_plot(product)

print(f"\nDone. {len(products)} images saved to {OUT_DIR}/")
