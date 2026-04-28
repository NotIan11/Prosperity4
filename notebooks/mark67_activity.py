"""
Plot Mark 67 buy/sell activity overlaid on mid price, for each asset it trades.
Round 4, days 1-3. Output saved to notebooks/r4_plots/.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines

DATA_DIR = "data/round4"
OUT_DIR = "notebooks/r4_plots"
BOT = "Mark 67"
os.makedirs(OUT_DIR, exist_ok=True)

# Load data
prices = {day: pd.read_csv(f"{DATA_DIR}/prices_round_4_day_{day}.csv", sep=";") for day in [1, 2, 3]}
trades = {day: pd.read_csv(f"{DATA_DIR}/trades_round_4_day_{day}.csv", sep=";") for day in [1, 2, 3]}

# Find all symbols Mark 67 appears in (buyer or seller)
mark67_symbols = sorted(set(
    sym
    for day in [1, 2, 3]
    for sym in pd.concat([
        trades[day][trades[day]["buyer"] == BOT]["symbol"],
        trades[day][trades[day]["seller"] == BOT]["symbol"],
    ])
))

print(f"{BOT} trades: {mark67_symbols}")

for product in mark67_symbols:
    fig, axes = plt.subplots(3, 1, figsize=(16, 13), sharex=False)
    fig.suptitle(f"{BOT} — {product}", fontsize=14, fontweight="bold")

    for ax_idx, day in enumerate([1, 2, 3]):
        ax = axes[ax_idx]

        # Mid price line
        price_df = prices[day][prices[day]["product"] == product].sort_values("timestamp")
        if not price_df.empty:
            ax.plot(
                price_df["timestamp"],
                price_df["mid_price"],
                color="black",
                lw=1.0,
                alpha=0.8,
                zorder=2,
            )

        # Mark 67 trades for this product/day
        day_trades = trades[day][trades[day]["symbol"] == product]

        buys = day_trades[day_trades["buyer"] == BOT]
        sells = day_trades[day_trades["seller"] == BOT]

        if not buys.empty:
            ax.scatter(
                buys["timestamp"],
                buys["price"],
                color="#2196F3",
                marker="^",
                s=70,
                alpha=0.9,
                zorder=4,
                label="buy",
            )

        if not sells.empty:
            ax.scatter(
                sells["timestamp"],
                sells["price"],
                color="#F44336",
                marker="v",
                s=70,
                alpha=0.9,
                zorder=4,
                label="sell",
            )

        ax.set_title(f"Day {day}", fontsize=11)
        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Price")
        ax.grid(True, alpha=0.3)

    # Shared legend
    buy_marker = mlines.Line2D([], [], color="#2196F3", marker="^", linestyle="None", markersize=8, label=f"{BOT} buy")
    sell_marker = mlines.Line2D([], [], color="#F44336", marker="v", linestyle="None", markersize=8, label=f"{BOT} sell")
    price_line = mlines.Line2D([], [], color="black", lw=1.5, label="mid price")
    fig.legend(handles=[buy_marker, sell_marker, price_line], loc="lower center", ncol=3, fontsize=11, frameon=True)

    plt.tight_layout(rect=[0, 0.05, 1, 1])

    out_path = f"{OUT_DIR}/mark67_{product.lower()}.png"
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    print(f"Saved: {out_path}")
    plt.show()
