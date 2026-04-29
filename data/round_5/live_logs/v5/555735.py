"""IMC Prosperity 4 — Round 5 trader (v5: directional + MM hybrid).

Triage source: docs/round_5/research/EDA_FINAL_TRIAGE.md
Drift table source: per-product polyfit slopes across days 2/3/4.

v4 (MM on all 50): BT $265k / live $20.5k. Capped at MM premium.
v5 adds a directional layer: 13 products with sign-stable drift across all 3
capsule days are traded as `DirectionalStrategy` (max long/short, hold).
Inspired by Ian's R5 bot which earned $33k live with the same pattern.

Active strategies:
- DirectionalStrategy x13: 9 short + 4 long (drift sign-stable across d2/d3/d4)
- PebblesCoordinator x3 (M, L, XL): basket-aware MM. XS and S removed
  because they're now outright shorts; basket overlay still functions on
  the remaining 3 since XS+S deviation now expresses as our short position.
- PassiveMM x33: every other product

Pitfalls accounted for:
- traderData round-trip: kept (PassiveMM stores rolling mids; Directional is stateless)
- No PnL caps on size; respects POSITION_LIMIT=10
- Directional has no stop-loss intentionally — trends span full day; v4
  data shows MM-style stops fired against winning trends.
"""

from __future__ import annotations

import json
import math
from collections import deque
from typing import Any

try:
    from datamodel import Order, OrderDepth, TradingState  # IMC platform
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


# ----------------------------------------------------------------------
# DirectionalStrategy: max-position-and-hold
# ----------------------------------------------------------------------

class DirectionalStrategy:
    """Hold max long (+1) or max short (-1). Sweeps the touch to reach target."""

    def __init__(self, symbol: str, direction: int) -> None:
        assert direction in (-1, 1)
        self.symbol = symbol
        self.direction = direction

    def save(self) -> dict[str, Any]:
        return {}

    def load(self, d: dict[str, Any]) -> None:
        pass

    def act(self, state: TradingState) -> list[Order]:
        depth = state.order_depths.get(self.symbol)
        if depth is None:
            return []
        pos = state.position.get(self.symbol, 0)
        target = self.direction * POSITION_LIMIT
        diff = target - pos
        if diff == 0:
            return []
        if diff > 0:
            ba = _best_ask(depth)
            if ba is None:
                return []
            return [Order(self.symbol, ba, diff)]
        bb = _best_bid(depth)
        if bb is None:
            return []
        return [Order(self.symbol, bb, diff)]  # diff is negative


# ----------------------------------------------------------------------
# Passive MM core (carried from v4)
# ----------------------------------------------------------------------

class PassiveMM:
    """Penny-inside-touch quote with position skew + rolling-mean stop-loss."""

    def __init__(
        self,
        symbol: str,
        skew: float = 0.4,
        soft_cap: int = 8,
        window: int = 500,
        stop_loss_ticks: float = 60.0,
    ) -> None:
        self.symbol = symbol
        self.skew = skew
        self.soft_cap = soft_cap
        self.window = window
        self.stop_loss_ticks = stop_loss_ticks
        self.mids: deque[float] = deque(maxlen=window)

    def save(self) -> dict[str, Any]:
        return {"mids": list(self.mids)}

    def load(self, d: dict[str, Any]) -> None:
        self.mids = deque(d.get("mids", [])[-self.window:], maxlen=self.window)

    def act(self, state: TradingState, extra_skew: float = 0.0) -> list[Order]:
        depth = state.order_depths.get(self.symbol)
        bb, ba = _best_bid(depth), _best_ask(depth)
        if bb is None or ba is None:
            return []
        m = (bb + ba) / 2.0
        self.mids.append(m)
        pos = state.position.get(self.symbol, 0)

        if pos != 0 and len(self.mids) >= 100:
            mean = sum(self.mids) / len(self.mids)
            adverse = (m - mean) if pos > 0 else (mean - m)
            if adverse > self.stop_loss_ticks:
                if pos > 0:
                    return [Order(self.symbol, bb, -pos)]
                return [Order(self.symbol, ba, -pos)]

        total_skew = self.skew * pos + extra_skew
        bid_px = bb + 1 - total_skew
        ask_px = ba - 1 - total_skew
        bid_px_i = int(math.floor(bid_px))
        ask_px_i = int(math.ceil(ask_px))
        if bid_px_i >= ba:
            bid_px_i = ba - 1
        if ask_px_i <= bb:
            ask_px_i = bb + 1
        if bid_px_i >= ask_px_i:
            bid_px_i = bb
            ask_px_i = ba

        bid_size = POSITION_LIMIT - pos
        ask_size = POSITION_LIMIT + pos
        if pos >= self.soft_cap:
            bid_size = 0
        if pos <= -self.soft_cap:
            ask_size = 0

        orders: list[Order] = []
        if bid_size > 0:
            orders.append(Order(self.symbol, bid_px_i, bid_size))
        if ask_size > 0:
            orders.append(Order(self.symbol, ask_px_i, -ask_size))
        return orders


# ----------------------------------------------------------------------
# PEBBLES coordinator (M, L, XL — basket overlay on remaining 3)
# ----------------------------------------------------------------------

class PebblesCoordinator:
    """MM PEBBLES_{M,L,XL}. Residual-skew overlay anchored on the 3-product
    rolling-mean of the basket sum: when our 3-product sum is high vs its
    rolling mean, ask-aggressively the most-overpriced one."""

    SYMBOLS = ("PEBBLES_M", "PEBBLES_L", "PEBBLES_XL")
    BETA = 0.6
    ROLL_WINDOW = 200

    def __init__(self) -> None:
        self.makers: dict[str, PassiveMM] = {
            s: PassiveMM(s, skew=0.4, soft_cap=8, window=500, stop_loss_ticks=80.0)
            for s in self.SYMBOLS
        }
        self.basket_hist: dict[str, deque[float]] = {
            s: deque(maxlen=self.ROLL_WINDOW) for s in self.SYMBOLS
        }

    def save(self) -> dict[str, Any]:
        return {
            "makers": {s: m.save() for s, m in self.makers.items()},
            "basket_hist": {s: list(v) for s, v in self.basket_hist.items()},
        }

    def load(self, d: dict[str, Any]) -> None:
        for s in self.SYMBOLS:
            self.makers[s].load(d.get("makers", {}).get(s, {}))
            v = d.get("basket_hist", {}).get(s, [])
            self.basket_hist[s] = deque(v[-self.ROLL_WINDOW:], maxlen=self.ROLL_WINDOW)

    def act(self, state: TradingState) -> dict[str, list[Order]]:
        mids: dict[str, float] = {}
        for s in self.SYMBOLS:
            depth = state.order_depths.get(s)
            m = _mid(depth)
            if m is not None:
                mids[s] = m
                self.basket_hist[s].append(m)

        residuals: dict[str, float] = {}
        if len(mids) == len(self.SYMBOLS) and all(
            len(self.basket_hist[s]) >= 30 for s in self.SYMBOLS
        ):
            for s in self.SYMBOLS:
                rm = sum(self.basket_hist[s]) / len(self.basket_hist[s])
                residuals[s] = mids[s] - rm

        result: dict[str, list[Order]] = {}
        for s in self.SYMBOLS:
            extra = self.BETA * residuals.get(s, 0.0)
            orders = self.makers[s].act(state, extra_skew=extra)
            if orders:
                result.setdefault(s, []).extend(orders)
        return result


# ----------------------------------------------------------------------
# Trader registry
# ----------------------------------------------------------------------

# 13 directional products (sign-stable drift across days 2/3/4).
# Sign convention: -1 = max short, +1 = max long. Magnitude in name comments
# is the average per-day total drift in capsule.
DIRECTIONAL: dict[str, int] = {
    # Short (down-drifters)
    "PEBBLES_XS":            -1,   # avg -1760
    "MICROCHIP_OVAL":        -1,   # avg -1247
    "ROBOT_IRONING":         -1,   # avg -1027
    "PEBBLES_S":             -1,   # avg  -932
    "UV_VISOR_AMBER":        -1,   # avg  -726
    "TRANSLATOR_ASTRO_BLACK":-1,   # avg  -532
    "UV_VISOR_ORANGE":       -1,   # avg  -360
    "SNACKPACK_PISTACHIO":   -1,   # avg  -302
    "SNACKPACK_CHOCOLATE":   -1,   # avg  -232
    # Long (up-drifters)
    "SNACKPACK_VANILLA":     +1,   # avg  +258
    "GALAXY_SOUNDS_BLACK_HOLES": +1,  # avg +1095
    "PANEL_2X4":             +1,   # avg +1115
    "OXYGEN_SHAKE_GARLIC":   +1,   # avg +1482
}

# Everything else gets passive MM. PEBBLES_{M,L,XL} handled by coordinator.
PEBBLES_COORDINATOR_SYMS = {"PEBBLES_M", "PEBBLES_L", "PEBBLES_XL"}

ALL_R5_PRODUCTS = (
    "GALAXY_SOUNDS_BLACK_HOLES", "GALAXY_SOUNDS_DARK_MATTER",
    "GALAXY_SOUNDS_PLANETARY_RINGS", "GALAXY_SOUNDS_SOLAR_FLAMES",
    "GALAXY_SOUNDS_SOLAR_WINDS",
    "MICROCHIP_CIRCLE", "MICROCHIP_OVAL", "MICROCHIP_RECTANGLE",
    "MICROCHIP_SQUARE", "MICROCHIP_TRIANGLE",
    "OXYGEN_SHAKE_CHOCOLATE", "OXYGEN_SHAKE_EVENING_BREATH",
    "OXYGEN_SHAKE_GARLIC", "OXYGEN_SHAKE_MINT", "OXYGEN_SHAKE_MORNING_BREATH",
    "PANEL_1X2", "PANEL_1X4", "PANEL_2X2", "PANEL_2X4", "PANEL_4X4",
    "PEBBLES_L", "PEBBLES_M", "PEBBLES_S", "PEBBLES_XL", "PEBBLES_XS",
    "ROBOT_DISHES", "ROBOT_IRONING", "ROBOT_LAUNDRY", "ROBOT_MOPPING",
    "ROBOT_VACUUMING",
    "SLEEP_POD_COTTON", "SLEEP_POD_LAMB_WOOL", "SLEEP_POD_NYLON",
    "SLEEP_POD_POLYESTER", "SLEEP_POD_SUEDE",
    "SNACKPACK_CHOCOLATE", "SNACKPACK_PISTACHIO", "SNACKPACK_RASPBERRY",
    "SNACKPACK_STRAWBERRY", "SNACKPACK_VANILLA",
    "TRANSLATOR_ASTRO_BLACK", "TRANSLATOR_ECLIPSE_CHARCOAL",
    "TRANSLATOR_GRAPHITE_MIST", "TRANSLATOR_SPACE_GRAY",
    "TRANSLATOR_VOID_BLUE",
    "UV_VISOR_AMBER", "UV_VISOR_MAGENTA", "UV_VISOR_ORANGE",
    "UV_VISOR_RED", "UV_VISOR_YELLOW",
)

_MM_DEFAULT = {"skew": 0.4, "soft_cap": 7, "stop_loss_ticks": 60.0}
_MM_SNACKPACK = {"skew": 0.5, "soft_cap": 7, "stop_loss_ticks": 80.0}
_MM_STEP = {"skew": 0.6, "soft_cap": 8, "stop_loss_ticks": 40.0}

PER_PRODUCT_MM_CFG: dict[str, dict[str, Any]] = {}
for _p in ALL_R5_PRODUCTS:
    if _p in DIRECTIONAL or _p in PEBBLES_COORDINATOR_SYMS:
        continue
    if _p in {"SNACKPACK_RASPBERRY", "SNACKPACK_STRAWBERRY"}:
        PER_PRODUCT_MM_CFG[_p] = dict(_MM_SNACKPACK)
    elif _p in {"OXYGEN_SHAKE_EVENING_BREATH"}:
        PER_PRODUCT_MM_CFG[_p] = dict(_MM_STEP)
    else:
        PER_PRODUCT_MM_CFG[_p] = dict(_MM_DEFAULT)


class Trader:
    def __init__(self) -> None:
        self.directional = {sym: DirectionalStrategy(sym, d) for sym, d in DIRECTIONAL.items()}
        self.pebbles = PebblesCoordinator()
        self.mm = {sym: PassiveMM(sym, **cfg) for sym, cfg in PER_PRODUCT_MM_CFG.items()}

    def _save_state(self) -> str:
        try:
            return json.dumps({
                "pebbles": self.pebbles.save(),
                "mm": {sym: s.save() for sym, s in self.mm.items()},
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
        for sym, sub in payload.get("mm", {}).items():
            if sym in self.mm and isinstance(sub, dict):
                self.mm[sym].load(sub)

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        self._load_state(state.traderData or "")

        result: dict[str, list[Order]] = {}

        # Directional
        for sym, strat in self.directional.items():
            orders = strat.act(state)
            if orders:
                result.setdefault(sym, []).extend(orders)

        # PEBBLES basket-MM
        for sym, orders in self.pebbles.act(state).items():
            if orders:
                result.setdefault(sym, []).extend(orders)

        # Passive MM
        for sym, strat in self.mm.items():
            orders = strat.act(state)
            if orders:
                result.setdefault(sym, []).extend(orders)

        return result, 0, self._save_state()