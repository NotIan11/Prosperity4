"""
Compare VelvetfruitStrategy vs Mark01CopyStrategy on round 4 data.
Simulates order execution directly against the prices/trades CSVs.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import matplotlib.pyplot as plt
from collections import deque
from typing import Optional, List, Dict
from src.datamodel import Order, OrderDepth, TradingState, Trade, Listing, Observation

DATA_DIR = "data/round4"
SYMBOL = "VELVETFRUIT_EXTRACT"
POS_LIMIT = 200
DAYS = [1, 2, 3]
BOT = "Mark 01"

# ---------------------------------------------------------------------------
# Build mock TradingState from a single prices row
# ---------------------------------------------------------------------------

def build_order_depth(row) -> OrderDepth:
    od = OrderDepth()
    for i in [1, 2, 3]:
        bp = row.get(f"bid_price_{i}")
        bv = row.get(f"bid_volume_{i}")
        ap = row.get(f"ask_price_{i}")
        av = row.get(f"ask_volume_{i}")
        if pd.notna(bp) and pd.notna(bv) and int(bv) > 0:
            od.buy_orders[int(bp)] = int(bv)
        if pd.notna(ap) and pd.notna(av) and int(av) > 0:
            od.sell_orders[int(ap)] = -int(av)
    return od


def build_state(row, position: int, mark01_signal: Optional[str],
                trader_data: str = "") -> TradingState:
    od = build_order_depth(row)
    mock_trade = []
    if mark01_signal == "buy":
        mock_trade = [Trade(SYMBOL, 0, 1, buyer=BOT, seller="other", timestamp=row["timestamp"])]
    elif mark01_signal == "sell":
        mock_trade = [Trade(SYMBOL, 0, 1, buyer="other", seller=BOT, timestamp=row["timestamp"])]

    return TradingState(
        traderData=trader_data,
        timestamp=int(row["timestamp"]),
        listings={SYMBOL: Listing(SYMBOL, SYMBOL, 1)},
        order_depths={SYMBOL: od},
        own_trades={},
        market_trades={SYMBOL: mock_trade} if mock_trade else {},
        position={SYMBOL: position} if position != 0 else {},
        observations=Observation({}, {}),
    )


# ---------------------------------------------------------------------------
# Order fill simulation (aggressive orders cross the spread)
# ---------------------------------------------------------------------------

def fill_orders(orders: List[Order], od: OrderDepth, position: int) -> tuple:
    """Returns (cash_delta, position_delta). Modifies od in place."""
    cash = 0.0
    pos_delta = 0
    for o in orders:
        if o.quantity > 0:  # buy
            for ask in sorted(od.sell_orders.keys()):
                if ask > o.price:
                    break
                avail = -od.sell_orders[ask]
                fill = min(o.quantity - pos_delta, avail, POS_LIMIT - position - pos_delta)
                if fill <= 0:
                    break
                cash -= ask * fill
                pos_delta += fill
                od.sell_orders[ask] += fill
        elif o.quantity < 0:  # sell
            want = -o.quantity
            filled = 0
            for bid in sorted(od.buy_orders.keys(), reverse=True):
                if bid < o.price:
                    break
                avail = od.buy_orders[bid]
                fill = min(want - filled, avail, POS_LIMIT + position - pos_delta)
                if fill <= 0:
                    break
                cash += bid * fill
                pos_delta -= fill
                od.buy_orders[bid] -= fill
                filled += fill
    return cash, pos_delta


# ---------------------------------------------------------------------------
# Simulation loop
# ---------------------------------------------------------------------------

def simulate(strategy_class, strategy_kwargs: dict,
             use_mark01_signal: bool = False) -> Dict[int, pd.Series]:
    """
    Returns dict of {day: pd.Series of cumulative PNL indexed by timestamp}.
    """
    from src.trader import VelvetfruitStrategy, Mark01CopyStrategy
    import json

    pnl_by_day = {}

    for day in DAYS:
        prices = pd.read_csv(f"{DATA_DIR}/prices_round_4_day_{day}.csv", sep=";")
        trades = pd.read_csv(f"{DATA_DIR}/trades_round_4_day_{day}.csv", sep=";")

        vfe_prices = prices[prices["product"] == SYMBOL].sort_values("timestamp").reset_index(drop=True)
        vfe_trades = trades[trades["symbol"] == SYMBOL].copy()

        # Group Mark 01 trades by timestamp → net direction
        mark01_by_ts: Dict[int, str] = {}
        for ts, grp in vfe_trades.groupby("timestamp"):
            net_buy = grp[grp["buyer"] == BOT]["quantity"].sum()
            net_sell = grp[grp["seller"] == BOT]["quantity"].sum()
            if net_buy > net_sell:
                mark01_by_ts[int(ts)] = "buy"
            elif net_sell > net_buy:
                mark01_by_ts[int(ts)] = "sell"

        strategy = strategy_class(**strategy_kwargs)
        position = 0
        cash = 0.0
        trader_data = ""
        pnl_series = []

        # pending Mark 01 signal (detected last tick, fire this tick)
        pending_signal: Optional[str] = None

        for _, row in vfe_prices.iterrows():
            ts = int(row["timestamp"])
            od = build_order_depth(row)
            mid = float(row["mid_price"])

            state = build_state(row, position, pending_signal, trader_data)

            # Inject market_trades for strategies that use them
            if pending_signal:
                state.market_trades[SYMBOL] = [
                    Trade(SYMBOL, int(mid), 1,
                          buyer=BOT if pending_signal == "buy" else "other",
                          seller=BOT if pending_signal == "sell" else "other",
                          timestamp=ts)
                ]

            orders = strategy.run(state)
            trader_data = json.dumps(strategy.save_state())

            if orders:
                cash_delta, pos_delta = fill_orders(orders, od, position)
                cash += cash_delta
                position += pos_delta

            mark_pnl = cash + position * mid
            pnl_series.append((ts, mark_pnl))

            # Update pending signal from current tick's Mark 01 trades
            pending_signal = mark01_by_ts.get(ts)

        pnl_by_day[day] = pd.Series(
            [p for _, p in pnl_series],
            index=[t for t, _ in pnl_series],
            name=f"day{day}",
        )

    return pnl_by_day


# ---------------------------------------------------------------------------
# Run both strategies and plot
# ---------------------------------------------------------------------------

from src.trader import VelvetfruitStrategy, Mark01CopyStrategy

print("Simulating VelvetfruitStrategy (baseline)...")
baseline = simulate(VelvetfruitStrategy, {"symbol": SYMBOL, "position_limit": POS_LIMIT})

print("Simulating Mark01CopyStrategy...")
copy = simulate(Mark01CopyStrategy, {"symbol": SYMBOL, "position_limit": POS_LIMIT},
                use_mark01_signal=True)

# Print final PNL comparison
print(f"\n{'Day':<6} {'Baseline':>12} {'Mark01 Copy':>12} {'Delta':>12}")
total_base = total_copy = 0
for day in DAYS:
    b = baseline[day].iloc[-1]
    c = copy[day].iloc[-1]
    print(f"D+{day:<4} {b:>12,.1f} {c:>12,.1f} {c - b:>+12,.1f}")
    total_base += b
    total_copy += c
print(f"{'TOTAL':<6} {total_base:>12,.1f} {total_copy:>12,.1f} {total_copy - total_base:>+12,.1f}")

# Plot
fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=False)
fig.suptitle(f"{SYMBOL}: VelvetfruitStrategy vs Mark 01 Copy", fontsize=13, fontweight="bold")

for ax_idx, day in enumerate(DAYS):
    ax = axes[ax_idx]
    ax.plot(baseline[day].index, baseline[day].values, label="Baseline (MR)", color="#377eb8", lw=1.4)
    ax.plot(copy[day].index, copy[day].values, label="Mark 01 Copy", color="#e41a1c", lw=1.4)
    ax.axhline(0, color="black", lw=0.6, ls="--", alpha=0.4)
    ax.set_title(f"Day {day}  |  Baseline: {baseline[day].iloc[-1]:+,.0f}  |  Copy: {copy[day].iloc[-1]:+,.0f}", fontsize=10)
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Cumulative PnL")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

plt.tight_layout()
out = "notebooks/r4_plots/vfe_strategy_comparison.png"
fig.savefig(out, dpi=130, bbox_inches="tight")
plt.close()
print(f"\nPlot saved: {out}")
