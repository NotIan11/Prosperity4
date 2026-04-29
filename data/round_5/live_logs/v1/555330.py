"""IMC Prosperity 4 — Round 5 trader (v1: taker MR — RECONSTRUCTED).

Reconstructed from session transcript. NOT the running version.

v1 was the first R5 strategy: take liquidity on mean-reversion signals.
BT result on R5 days 2/3/4: -$395,220 total. Lost on every active product.
Root cause: with R5 spreads of 10-17 ticks and position limit 10, taker
round-trips paid more in spread than they captured in MR edge. v2 inverts
this by becoming a passive maker (capture spread on passive fills).

Triage source: docs/round_5/research/EDA_FINAL_TRIAGE.md
"""

from __future__ import annotations

import json
import math
from collections import deque
from typing import Any

try:
    from datamodel import Order, OrderDepth, TradingState
except ImportError:
    from prosperity4bt.datamodel import Order, OrderDepth, TradingState


POSITION_LIMIT = 10


def _mid(depth: OrderDepth) -> float | None:
    if not depth or not depth.buy_orders or not depth.sell_orders:
        return None
    return (max(depth.buy_orders) + min(depth.sell_orders)) / 2.0


def _best_bid(depth: OrderDepth) -> int | None:
    return max(depth.buy_orders) if depth and depth.buy_orders else None


def _best_ask(depth: OrderDepth) -> int | None:
    return min(depth.sell_orders) if depth and depth.sell_orders else None


class PebblesBasket:
    """Take-side basket arbitrage on PEBBLES sum=50000 (NB09)."""

    SYMBOLS = (
        "PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL",
    )
    TARGET_SUM = 50000
    ENTRY_THRESH = 2.0
    EXIT_THRESH = 0.5
    WINDOW = 200
    MAX_HOLD_TICKS = 300

    def __init__(self) -> None:
        self.mid_hist: dict[str, deque[float]] = {s: deque(maxlen=self.WINDOW) for s in self.SYMBOLS}
        self.entry_ts: dict[str, int] = {}

    def save(self) -> dict[str, Any]:
        return {
            "mid_hist": {s: list(v) for s, v in self.mid_hist.items()},
            "entry_ts": dict(self.entry_ts),
        }

    def load(self, d: dict[str, Any]) -> None:
        for s in self.SYMBOLS:
            v = d.get("mid_hist", {}).get(s, [])
            self.mid_hist[s] = deque(v[-self.WINDOW:], maxlen=self.WINDOW)
        self.entry_ts = dict(d.get("entry_ts", {}))

    def _flatten(self, sym: str, pos: int, depth: OrderDepth) -> list[Order]:
        if pos > 0:
            bb = _best_bid(depth)
            return [Order(sym, bb, -pos)] if bb is not None else []
        ba = _best_ask(depth)
        return [Order(sym, ba, -pos)] if ba is not None else []

    def act(self, state: TradingState) -> dict[str, list[Order]]:
        result: dict[str, list[Order]] = {}
        mids: dict[str, float] = {}
        for s in self.SYMBOLS:
            depth = state.order_depths.get(s)
            m = _mid(depth)
            if m is None:
                return result
            mids[s] = m
            self.mid_hist[s].append(m)

        if any(len(self.mid_hist[s]) < 30 for s in self.SYMBOLS):
            return result

        roll_mean = {s: sum(self.mid_hist[s]) / len(self.mid_hist[s]) for s in self.SYMBOLS}
        residuals = {s: mids[s] - roll_mean[s] for s in self.SYMBOLS}
        basket_dev = sum(mids.values()) - self.TARGET_SUM

        for s in self.SYMBOLS:
            pos = state.position.get(s, 0)
            if pos == 0:
                self.entry_ts.pop(s, None)
                continue
            if s not in self.entry_ts:
                self.entry_ts[s] = state.timestamp
            elif state.timestamp - self.entry_ts[s] > self.MAX_HOLD_TICKS * 100:
                result.setdefault(s, []).extend(self._flatten(s, pos, state.order_depths[s]))

        if abs(basket_dev) < self.EXIT_THRESH:
            for s in self.SYMBOLS:
                pos = state.position.get(s, 0)
                if pos != 0:
                    result.setdefault(s, []).extend(self._flatten(s, pos, state.order_depths[s]))
            return result

        if basket_dev > self.ENTRY_THRESH:
            target = max(self.SYMBOLS, key=lambda s: residuals[s])
            if residuals[target] > 0:
                pos = state.position.get(target, 0)
                room = POSITION_LIMIT + pos
                if room > 0:
                    bb = _best_bid(state.order_depths[target])
                    if bb is not None:
                        size = max(1, min(room, math.ceil(abs(basket_dev))))
                        result.setdefault(target, []).append(Order(target, bb, -size))
        elif basket_dev < -self.ENTRY_THRESH:
            target = min(self.SYMBOLS, key=lambda s: residuals[s])
            if residuals[target] < 0:
                pos = state.position.get(target, 0)
                room = POSITION_LIMIT - pos
                if room > 0:
                    ba = _best_ask(state.order_depths[target])
                    if ba is not None:
                        size = max(1, min(room, math.ceil(abs(basket_dev))))
                        result.setdefault(target, []).append(Order(target, ba, size))

        return result


class PerProductMR:
    """Take-side rolling-mean MR for one product."""

    def __init__(
        self,
        symbol: str,
        window: int = 500,
        k_entry: float = 1.5,
        k_exit: float = 0.4,
        min_dev_floor: float = 4.0,
        stop_loss_ticks: float = 25.0,
        max_hold_ticks: int = 500,
    ) -> None:
        self.symbol = symbol
        self.window = window
        self.k_entry = k_entry
        self.k_exit = k_exit
        self.min_dev_floor = min_dev_floor
        self.stop_loss_ticks = stop_loss_ticks
        self.max_hold_ticks = max_hold_ticks
        self.mids: deque[float] = deque(maxlen=window)
        self.entry_mid: float | None = None
        self.entry_ts: int | None = None

    def save(self) -> dict[str, Any]:
        return {"mids": list(self.mids), "entry_mid": self.entry_mid, "entry_ts": self.entry_ts}

    def load(self, d: dict[str, Any]) -> None:
        self.mids = deque(d.get("mids", [])[-self.window:], maxlen=self.window)
        self.entry_mid = d.get("entry_mid")
        self.entry_ts = d.get("entry_ts")

    def act(self, state: TradingState) -> list[Order]:
        depth = state.order_depths.get(self.symbol)
        m = _mid(depth)
        if m is None:
            return []
        self.mids.append(m)
        pos = state.position.get(self.symbol, 0)

        if pos == 0:
            self.entry_mid = None
            self.entry_ts = None

        if len(self.mids) < 50:
            return []

        mean = sum(self.mids) / len(self.mids)
        var = sum((x - mean) ** 2 for x in self.mids) / max(1, len(self.mids) - 1)
        std = math.sqrt(var) if var > 0 else 1.0
        dev = m - mean

        orders: list[Order] = []

        if pos != 0 and self.entry_mid is not None:
            adverse = (m - self.entry_mid) if pos > 0 else (self.entry_mid - m)
            held_too_long = (
                self.entry_ts is not None
                and state.timestamp - self.entry_ts > self.max_hold_ticks * 100
            )
            if adverse < -self.stop_loss_ticks or held_too_long:
                if pos > 0:
                    bb = _best_bid(depth)
                    if bb is not None:
                        orders.append(Order(self.symbol, bb, -pos))
                else:
                    ba = _best_ask(depth)
                    if ba is not None:
                        orders.append(Order(self.symbol, ba, -pos))
                return orders

        if pos != 0 and abs(dev) < self.k_exit * std:
            if pos > 0:
                bb = _best_bid(depth)
                if bb is not None:
                    orders.append(Order(self.symbol, bb, -pos))
            else:
                ba = _best_ask(depth)
                if ba is not None:
                    orders.append(Order(self.symbol, ba, -pos))
            return orders

        z = dev / std if std > 0 else 0.0
        if z > self.k_entry and dev > self.min_dev_floor:
            room = POSITION_LIMIT + pos
            if room > 0:
                bb = _best_bid(depth)
                if bb is not None:
                    size = min(room, max(1, int(round(abs(z)))))
                    orders.append(Order(self.symbol, bb, -size))
                    if pos == 0:
                        self.entry_mid = m
                        self.entry_ts = state.timestamp
        elif z < -self.k_entry and dev < -self.min_dev_floor:
            room = POSITION_LIMIT - pos
            if room > 0:
                ba = _best_ask(depth)
                if ba is not None:
                    size = min(room, max(1, int(round(abs(z)))))
                    orders.append(Order(self.symbol, ba, size))
                    if pos == 0:
                        self.entry_mid = m
                        self.entry_ts = state.timestamp

        return orders


PER_PRODUCT_CFG: dict[str, dict[str, Any]] = {
    "SNACKPACK_CHOCOLATE":  {"window": 500, "k_entry": 1.5, "min_dev_floor": 4.0,  "stop_loss_ticks": 20.0},
    "SNACKPACK_VANILLA":    {"window": 500, "k_entry": 1.5, "min_dev_floor": 4.0,  "stop_loss_ticks": 20.0},
    "SNACKPACK_STRAWBERRY": {"window": 500, "k_entry": 1.5, "min_dev_floor": 4.0,  "stop_loss_ticks": 20.0},
    "SNACKPACK_RASPBERRY":  {"window": 500, "k_entry": 1.5, "min_dev_floor": 4.0,  "stop_loss_ticks": 20.0},
    "SNACKPACK_PISTACHIO":  {"window": 500, "k_entry": 1.5, "min_dev_floor": 4.0,  "stop_loss_ticks": 20.0},
    "ROBOT_IRONING":               {"window": 500, "k_entry": 1.0, "min_dev_floor": 10.0, "stop_loss_ticks": 30.0},
    "OXYGEN_SHAKE_EVENING_BREATH": {"window": 500, "k_entry": 1.0, "min_dev_floor": 10.0, "stop_loss_ticks": 30.0},
}


class Trader:
    def __init__(self) -> None:
        self.pebbles = PebblesBasket()
        self.per_product: dict[str, PerProductMR] = {
            sym: PerProductMR(sym, **cfg) for sym, cfg in PER_PRODUCT_CFG.items()
        }

    def _save_state(self) -> str:
        try:
            return json.dumps({
                "pebbles": self.pebbles.save(),
                "per_product": {sym: s.save() for sym, s in self.per_product.items()},
            }, separators=(",", ":"))
        except Exception:
            return ""

    def _load_state(self, td: str) -> None:
        if not td:
            return
        try:
            payload = json.loads(td)
        except Exception:
            return
        if isinstance(payload.get("pebbles"), dict):
            self.pebbles.load(payload["pebbles"])
        for sym, sub in payload.get("per_product", {}).items():
            if sym in self.per_product and isinstance(sub, dict):
                self.per_product[sym].load(sub)

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        self._load_state(state.traderData or "")
        result: dict[str, list[Order]] = {}
        for sym, orders in self.pebbles.act(state).items():
            if orders:
                result.setdefault(sym, []).extend(orders)
        for sym, strat in self.per_product.items():
            orders = strat.act(state)
            if orders:
                result.setdefault(sym, []).extend(orders)
        return result, 0, self._save_state()