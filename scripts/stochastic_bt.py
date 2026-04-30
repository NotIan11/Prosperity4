"""
Stochastic backtest wrapper — simulates IMC's ~20% NPC order randomization.

For each seed, randomly drops ~20% of order-book price levels before each tick
is presented to the trader. This approximates the platform's per-submission
randomization that causes the same code to vary 4x+ in live PnL.

Usage:
    venv/bin/python scripts/stochastic_bt.py

Outputs per-version statistics to stdout.
"""

from __future__ import annotations

import importlib
import importlib.util
import multiprocessing
import random
import sys
import os
from collections import defaultdict
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

# ── project root on sys.path ──────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "venv" / "lib" / "python3.13" / "site-packages"))

from prosperity4bt.data import BacktestData, read_day_data
from prosperity4bt.datamodel import (
    Listing,
    Observation,
    Order,
    OrderDepth,
    Symbol,
    Trade,
    TradingState,
)
from prosperity4bt.file_reader import FileSystemReader
from prosperity4bt.models import (
    ActivityLogRow,
    BacktestResult,
    MarketTrade,
    SandboxLogRow,
    TradeRow,
    TradeMatchingMode,
)

# ── constants ─────────────────────────────────────────────────────────────────
DATA_ROOT = ROOT / "data" / "bt_resources"
ROUND = 5
DAYS = [3, 4]             # scoring-relevant days only (skip day 2 warmup)
DROP_PROB = 0.20          # probability to drop each price level
N_SEEDS = 20              # seeds per version
N_WORKERS = 4             # parallel workers for seed runs
TRADE_MODE = TradeMatchingMode.all

STRATEGY_FILES = {
    "v4": ROOT / "docs" / "round_5" / "strategy_versions" / "r5_v4_all50_mm.py",
    "v7": ROOT / "docs" / "round_5" / "strategy_versions" / "r5_v7_regime_overlays.py",
    "v8": ROOT / "docs" / "round_5" / "strategy_versions" / "r5_v8_robot_settled_gate.py",
}

LIMITS = {
    "EMERALDS": 80, "TOMATOES": 80, "INTARIAN_PEPPER_ROOT": 80,
    "ASH_COATED_OSMIUM": 80, "HYDROGEL_PACK": 200, "VELVETFRUIT_EXTRACT": 200,
    "VELVETFRUIT_EXTRACT_VOUCHER": 300, "VEV_4000": 300, "VEV_4500": 300,
    "VEV_5000": 300, "VEV_5100": 300, "VEV_5200": 300, "VEV_5300": 300,
    "VEV_5400": 300, "VEV_5500": 300, "VEV_6000": 300, "VEV_6500": 300,
}
for suffix in ["DARK_MATTER","BLACK_HOLES","PLANETARY_RINGS","SOLAR_WINDS","SOLAR_FLAMES"]:
    LIMITS[f"GALAXY_SOUNDS_{suffix}"] = 10
for suffix in ["SUEDE","LAMB_WOOL","POLYESTER","NYLON","COTTON"]:
    LIMITS[f"SLEEP_POD_{suffix}"] = 10
for suffix in ["CIRCLE","OVAL","SQUARE","RECTANGLE","TRIANGLE"]:
    LIMITS[f"MICROCHIP_{suffix}"] = 10
for suffix in ["XS","S","M","L","XL"]:
    LIMITS[f"PEBBLES_{suffix}"] = 10
for suffix in ["VACUUMING","MOPPING","DISHES","LAUNDRY","IRONING"]:
    LIMITS[f"ROBOT_{suffix}"] = 10
for suffix in ["YELLOW","AMBER","ORANGE","RED","MAGENTA"]:
    LIMITS[f"UV_VISOR_{suffix}"] = 10
for suffix in ["SPACE_GRAY","ASTRO_BLACK","ECLIPSE_CHARCOAL","GRAPHITE_MIST","VOID_BLUE"]:
    LIMITS[f"TRANSLATOR_{suffix}"] = 10
for suffix in ["1X2","2X2","1X4","2X4","4X4"]:
    LIMITS[f"PANEL_{suffix}"] = 10
for suffix in ["MORNING_BREATH","EVENING_BREATH","MINT","CHOCOLATE","GARLIC"]:
    LIMITS[f"OXYGEN_SHAKE_{suffix}"] = 10
for suffix in ["CHOCOLATE","VANILLA","PISTACHIO","STRAWBERRY","RASPBERRY"]:
    LIMITS[f"SNACKPACK_{suffix}"] = 10


# ── helpers ───────────────────────────────────────────────────────────────────

def load_trader(path: Path):
    """Load a Trader class from a standalone .py file."""
    spec = importlib.util.spec_from_file_location("_trader_module", path)
    mod = importlib.util.module_from_spec(spec)
    # Provide the datamodel shim so strategy imports work
    sys.modules["datamodel"] = importlib.import_module("prosperity4bt.datamodel")
    spec.loader.exec_module(mod)
    return mod.Trader


def drop_levels(prices: list[int], volumes: list[int], rng: random.Random, drop_prob: float):
    """Return filtered (prices, volumes) after randomly dropping levels."""
    out_p, out_v = [], []
    for p, v in zip(prices, volumes):
        if rng.random() >= drop_prob:
            out_p.append(p)
            out_v.append(v)
    return out_p, out_v


def prepare_state_stochastic(state: TradingState, data: BacktestData, rng: random.Random, drop_prob: float) -> None:
    """Like runner.prepare_state but randomly drops order levels."""
    for product in data.products:
        order_depth = OrderDepth()
        row = data.prices[state.timestamp][product]

        bid_p, bid_v = drop_levels(row.bid_prices, row.bid_volumes, rng, drop_prob)
        ask_p, ask_v = drop_levels(row.ask_prices, row.ask_volumes, rng, drop_prob)

        for price, volume in zip(bid_p, bid_v):
            order_depth.buy_orders[price] = volume
        for price, volume in zip(ask_p, ask_v):
            order_depth.sell_orders[price] = -volume

        state.order_depths[product] = order_depth
        state.listings[product] = Listing(product, product, 1)

    observation_row = data.observations.get(state.timestamp)
    if observation_row is None:
        state.observations = Observation(plainValueObservations={}, conversionObservations={})
    else:
        state.observations = Observation(plainValueObservations={}, conversionObservations={})


def type_check_orders(orders: dict[Symbol, list[Order]]) -> None:
    for key, value in orders.items():
        if not isinstance(key, str):
            raise ValueError(f"Orders key '{key}' is of type {type(key)}, expected a str")
        for order in value:
            if not isinstance(order.symbol, str):
                raise ValueError(f"Order symbol '{order}' not str")
            if not isinstance(order.price, int):
                raise ValueError(f"Order price '{order}' not int")
            if not isinstance(order.quantity, int):
                raise ValueError(f"Order qty '{order}' not int")


def enforce_limits(state, data, orders, sandbox_row):
    for product in data.products:
        product_orders = orders.get(product, [])
        product_position = state.position.get(product, 0)
        limit = LIMITS.get(product, 10)
        total_long = sum(o.quantity for o in product_orders if o.quantity > 0)
        total_short = sum(abs(o.quantity) for o in product_orders if o.quantity < 0)
        if product_position + total_long > limit or product_position - total_short < -limit:
            orders.pop(product, None)


def match_buy_order(state, data, order, market_trades, mode):
    trades = []
    order_depth = state.order_depths[order.symbol]
    price_matches = sorted(p for p in order_depth.sell_orders if p <= order.price)
    for price in price_matches:
        volume = min(order.quantity, abs(order_depth.sell_orders[price]))
        trades.append(Trade(order.symbol, price, volume, "SUBMISSION", "", state.timestamp))
        state.position[order.symbol] = state.position.get(order.symbol, 0) + volume
        data.profit_loss[order.symbol] -= price * volume
        order_depth.sell_orders[price] += volume
        if order_depth.sell_orders[price] == 0:
            order_depth.sell_orders.pop(price)
        order.quantity -= volume
        if order.quantity == 0:
            return trades
    if mode == TradeMatchingMode.none:
        return trades
    for mt in market_trades:
        if mt.sell_quantity == 0 or mt.trade.price > order.price:
            continue
        if mt.trade.price == order.price and mode == TradeMatchingMode.worse:
            continue
        volume = min(order.quantity, mt.sell_quantity)
        trades.append(Trade(order.symbol, order.price, volume, "SUBMISSION", mt.trade.seller, state.timestamp))
        state.position[order.symbol] = state.position.get(order.symbol, 0) + volume
        data.profit_loss[order.symbol] -= order.price * volume
        mt.sell_quantity -= volume
        order.quantity -= volume
        if order.quantity == 0:
            return trades
    return trades


def match_sell_order(state, data, order, market_trades, mode):
    trades = []
    order_depth = state.order_depths[order.symbol]
    price_matches = sorted((p for p in order_depth.buy_orders if p >= order.price), reverse=True)
    for price in price_matches:
        volume = min(abs(order.quantity), order_depth.buy_orders[price])
        trades.append(Trade(order.symbol, price, volume, "", "SUBMISSION", state.timestamp))
        state.position[order.symbol] = state.position.get(order.symbol, 0) - volume
        data.profit_loss[order.symbol] += price * volume
        order_depth.buy_orders[price] -= volume
        if order_depth.buy_orders[price] == 0:
            order_depth.buy_orders.pop(price)
        order.quantity += volume
        if order.quantity == 0:
            return trades
    if mode == TradeMatchingMode.none:
        return trades
    for mt in market_trades:
        if mt.buy_quantity == 0 or mt.trade.price < order.price:
            continue
        if mt.trade.price == order.price and mode == TradeMatchingMode.worse:
            continue
        volume = min(abs(order.quantity), mt.buy_quantity)
        trades.append(Trade(order.symbol, order.price, volume, mt.trade.buyer, "SUBMISSION", state.timestamp))
        state.position[order.symbol] = state.position.get(order.symbol, 0) - volume
        data.profit_loss[order.symbol] += order.price * volume
        mt.buy_quantity -= volume
        order.quantity += volume
        if order.quantity == 0:
            return trades
    return trades


def match_orders(state, data, orders, result, mode):
    market_trades = {
        product: [MarketTrade(t, t.quantity, t.quantity) for t in trades]
        for product, trades in data.trades[state.timestamp].items()
    }
    for product in data.products:
        new_trades = []
        for order in orders.get(product, []):
            if order.quantity > 0:
                new_trades.extend(match_buy_order(state, data, order, market_trades.get(product, []), mode))
            elif order.quantity < 0:
                new_trades.extend(match_sell_order(state, data, order, market_trades.get(product, []), mode))
        if new_trades:
            state.own_trades[product] = new_trades
            result.trades.extend([TradeRow(t) for t in new_trades])
    for product, trades in market_trades.items():
        for t in trades:
            t.trade.quantity = min(t.buy_quantity, t.sell_quantity)
        remaining = [t.trade for t in trades if t.trade.quantity > 0]
        state.market_trades[product] = remaining
        result.trades.extend([TradeRow(t) for t in remaining])


def run_stochastic_backtest(
    TraderClass,
    file_reader,
    round_num: int,
    day_num: int,
    seed: int,
    drop_prob: float = DROP_PROB,
) -> tuple[float, dict[str, float]]:
    """
    Run one backtest with NPC order randomization using the given seed.
    Returns (total_pnl, {product: pnl}).
    """
    rng = random.Random(seed)
    data = read_day_data(file_reader, round_num, day_num, no_names=True)

    os.environ["PROSPERITY4BT_ROUND"] = str(round_num)
    os.environ["PROSPERITY4BT_DAY"] = str(day_num)

    trader = TraderClass()
    trader_data = ""
    state = TradingState(
        traderData=trader_data,
        timestamp=0,
        listings={},
        order_depths={},
        own_trades={},
        market_trades={},
        position={},
        observations=Observation({}, {}),
    )
    result = BacktestResult(round_num=round_num, day_num=day_num, sandbox_logs=[], activity_logs=[], trades=[])

    timestamps = sorted(data.prices.keys())
    for timestamp in timestamps:
        state.timestamp = timestamp
        state.traderData = trader_data
        state.own_trades = {}
        state.market_trades = {}

        prepare_state_stochastic(state, data, rng, drop_prob)

        stdout = StringIO()
        stdout.close = lambda: None  # type: ignore

        with redirect_stdout(stdout):
            try:
                orders, conversions, trader_data = trader.run(state)
            except Exception:
                orders, conversions, trader_data = {}, 0, trader_data

        sandbox_row = SandboxLogRow(timestamp=timestamp, sandbox_log="", lambda_log="")

        type_check_orders(orders)
        enforce_limits(state, data, orders, sandbox_row)
        match_orders(state, data, orders, result, TRADE_MODE)

    # compute final per-product PnL: realized P&L + mark-to-market of open position
    last_ts = timestamps[-1]
    product_pnl: dict[str, float] = {}
    for product in data.products:
        realized = data.profit_loss[product]
        position = state.position.get(product, 0)
        if position != 0:
            mid = data.prices[last_ts][product].mid_price
            realized += position * mid
        product_pnl[product] = realized

    total_pnl = sum(product_pnl.values())
    return total_pnl, product_pnl


def run_deterministic_backtest(
    TraderClass,
    file_reader,
    round_num: int,
    day_num: int,
) -> tuple[float, dict[str, float]]:
    """Run without any order dropping (drop_prob=0) as baseline."""
    return run_stochastic_backtest(TraderClass, file_reader, round_num, day_num, seed=0, drop_prob=0.0)


# ── main ──────────────────────────────────────────────────────────────────────

def percentile(data: list[float], p: float) -> float:
    """Simple percentile using linear interpolation."""
    if not data:
        return float("nan")
    sorted_data = sorted(data)
    n = len(sorted_data)
    idx = p / 100 * (n - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return sorted_data[lo]
    frac = idx - lo
    return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac


def format_hist(values: list[float], bins: int = 10) -> str:
    """ASCII histogram of values."""
    if not values:
        return "(no data)"
    mn, mx = min(values), max(values)
    if mn == mx:
        return f"all values = {mn:,.0f}"
    width = (mx - mn) / bins
    counts = [0] * bins
    for v in values:
        idx = min(int((v - mn) / width), bins - 1)
        counts[idx] += 1
    max_count = max(counts)
    lines = []
    for i, c in enumerate(counts):
        lo = mn + i * width
        hi = lo + width
        bar = "#" * (c * 20 // max_count if max_count > 0 else 0)
        lines.append(f"  [{lo:>8,.0f}, {hi:>8,.0f}) | {bar:<20} {c}")
    return "\n".join(lines)


def _worker_run_seed(args: tuple) -> tuple[int, float, dict[str, float]]:
    """Worker function for multiprocessing. Returns (seed, total_pnl, product_pnl)."""
    strategy_path_str, seed, round_num, days, drop_prob = args
    strategy_path = Path(strategy_path_str)
    # Each worker must set up its own sys.path and load the trader
    if str(ROOT / "venv" / "lib" / "python3.13" / "site-packages") not in sys.path:
        sys.path.insert(0, str(ROOT / "venv" / "lib" / "python3.13" / "site-packages"))
    TraderClass = load_trader(strategy_path)
    file_reader = FileSystemReader(DATA_ROOT)
    run_total = 0.0
    run_prod: dict[str, float] = {}
    for day in days:
        day_seed = seed * 100 + day
        t, p = run_stochastic_backtest(TraderClass, file_reader, round_num, day, seed=day_seed, drop_prob=drop_prob)
        run_total += t
        for prod, pnl in p.items():
            run_prod[prod] = run_prod.get(prod, 0.0) + pnl
    return seed, run_total, run_prod


def main():
    file_reader = FileSystemReader(DATA_ROOT)

    # results[version][seed] = total_pnl_across_days
    version_results: dict[str, list[float]] = {}
    # product_results[version][product][seed] = pnl
    product_results: dict[str, dict[str, list[float]]] = {}
    # deterministic baseline per version
    det_results: dict[str, float] = {}
    det_product_results: dict[str, dict[str, float]] = {}

    for version, strategy_path in STRATEGY_FILES.items():
        print(f"\n{'='*60}")
        print(f"Version: {version}  ({strategy_path.name})")
        print(f"{'='*60}")
        sys.stdout.flush()

        TraderClass = load_trader(strategy_path)

        # deterministic baseline (no drops)
        det_total = 0.0
        det_prod: dict[str, float] = {}
        for day in DAYS:
            t, p = run_deterministic_backtest(TraderClass, file_reader, ROUND, day)
            det_total += t
            for prod, pnl in p.items():
                det_prod[prod] = det_prod.get(prod, 0.0) + pnl
        det_results[version] = det_total
        det_product_results[version] = det_prod
        print(f"  Deterministic BT (no drops): ${det_total:,.0f}")
        sys.stdout.flush()

        # stochastic runs with multiprocessing
        seed_totals: list[float] = []
        seed_product: dict[str, list[float]] = defaultdict(list)

        worker_args = [(str(strategy_path), seed, ROUND, DAYS, DROP_PROB) for seed in range(N_SEEDS)]

        with multiprocessing.Pool(processes=N_WORKERS) as pool:
            completed = 0
            for seed, run_total, run_prod in pool.imap_unordered(_worker_run_seed, worker_args):
                seed_totals.append(run_total)
                for prod, pnl in run_prod.items():
                    seed_product[prod].append(pnl)
                completed += 1
                if completed % 5 == 0:
                    print(f"    Seeds done: {completed}/{N_SEEDS}")
                    sys.stdout.flush()

        version_results[version] = seed_totals
        product_results[version] = dict(seed_product)

        mn = min(seed_totals)
        mx = max(seed_totals)
        mean = sum(seed_totals) / len(seed_totals)
        median = percentile(seed_totals, 50)
        p5 = percentile(seed_totals, 5)
        p95 = percentile(seed_totals, 95)
        print(f"\n  Stochastic stats ({N_SEEDS} seeds, 20% drop/level):")
        print(f"    Mean:   ${mean:>10,.0f}")
        print(f"    Median: ${median:>10,.0f}")
        print(f"    P5:     ${p5:>10,.0f}")
        print(f"    P95:    ${p95:>10,.0f}")
        print(f"    Min:    ${mn:>10,.0f}")
        print(f"    Max:    ${mx:>10,.0f}")
        if det_total != 0:
            print(f"    Det→Mean ratio: {mean / det_total:.3f}")
        sys.stdout.flush()

    # --- product fragility analysis ---
    print(f"\n{'='*60}")
    print("PRODUCT FRAGILITY ANALYSIS (across all versions)")
    print(f"{'='*60}")

    # For each product, compute CV (std/|mean|) averaged across versions
    all_products = set()
    for v in product_results.values():
        all_products.update(v.keys())

    fragility: list[tuple[str, float, float, float]] = []  # (product, mean, std, cv)
    for prod in sorted(all_products):
        all_pnls: list[float] = []
        for v in product_results.values():
            if prod in v:
                all_pnls.extend(v[prod])
        if not all_pnls or len(all_pnls) < 2:
            continue
        mn = sum(all_pnls) / len(all_pnls)
        var = sum((x - mn) ** 2 for x in all_pnls) / (len(all_pnls) - 1)
        std = var ** 0.5
        cv = std / abs(mn) if mn != 0 else float("inf")
        fragility.append((prod, mn, std, cv))

    fragility.sort(key=lambda x: -x[3])
    print("\nMost fragile (highest CV = std / |mean|):")
    for prod, mn, std, cv in fragility[:15]:
        print(f"  {prod:<45} mean={mn:>8,.0f}  std={std:>7,.0f}  CV={cv:.3f}")

    fragility_stable = sorted(fragility, key=lambda x: x[3])
    print("\nMost stable (lowest CV, positive mean only):")
    stable = [(p, m, s, c) for p, m, s, c in fragility_stable if m > 0][:15]
    for prod, mn, std, cv in stable:
        print(f"  {prod:<45} mean={mn:>8,.0f}  std={std:>7,.0f}  CV={cv:.3f}")

    sys.stdout.flush()
    return version_results, product_results, det_results, det_product_results, fragility


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    results = main()
