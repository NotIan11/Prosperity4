"""IMC Prosperity 4 — Round 5 trader (v3: tuned passive MM).

Triage source: docs/round_5/research/EDA_FINAL_TRIAGE.md

v1 (taker MR) lost -$395k across 3 days. Spreads of 10-17 ticks vs MR edge of
~3-5 ticks made taker round-trips structurally negative. v2 inverts: passive
maker quotes inside-the-spread, captures spread on passive fills, lets the
EDA-found mean-reversion mechanics return inventory to flat.

Active products (13):
- PEBBLES_{XS,S,M,L,XL}: passive MM with basket-tilt (skew quotes by residual
  from sum=50000 constraint). NB09 sum constraint is the strongest signal.
- SNACKPACK_{CHOC,VAN,STRAW,RASP,PIST}: passive MM. Wide ~17-tick spreads make
  this an MM opportunity even without alpha; 2+2+1 anti-corr provides MR.
- ROBOT_IRONING, OXYGEN_SHAKE_EVENING_BREATH: passive MM. Step-fn ±10 grid.

Skipped: OXYGEN_SHAKE_CHOCOLATE (jump risk), 37 noise products.

Position limit = 10/product.
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


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def _mid(depth: OrderDepth) -> float | None:
    if not depth or not depth.buy_orders or not depth.sell_orders:
        return None
    return (max(depth.buy_orders) + min(depth.sell_orders)) / 2.0


def _best_bid(depth: OrderDepth) -> int | None:
    return max(depth.buy_orders) if depth and depth.buy_orders else None


def _best_ask(depth: OrderDepth) -> int | None:
    return min(depth.sell_orders) if depth and depth.sell_orders else None


# ----------------------------------------------------------------------
# Passive MM core
# ----------------------------------------------------------------------

class PassiveMM:
    """Generic passive market maker for one product.

    Posts bid at best_bid+1 and ask at best_ask-1 (penny-inside the touch),
    with a position-skew that pulls quotes back toward flat inventory:
        bid_px -= skew * position
        ask_px -= skew * position

    Soft inventory cap stops adding when |pos| reaches soft_cap.
    Hard stop-loss flatten when adverse_move from rolling-mean fair exceeds
    stop_loss_ticks (defends against regime breaks like the day-4 ROBOT_DISHES
    spike that fooled NB06).
    """

    def __init__(
        self,
        symbol: str,
        skew: float = 0.4,
        soft_cap: int = 8,
        window: int = 500,
        stop_loss_ticks: float = 40.0,
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

        # Stop-loss: if mid has moved adversely vs rolling fair, flatten.
        if pos != 0 and len(self.mids) >= 100:
            mean = sum(self.mids) / len(self.mids)
            adverse = (m - mean) if pos > 0 else (mean - m)
            # adverse > stop_loss => mark-to-market deep loss; go flat at touch
            if adverse > self.stop_loss_ticks:
                if pos > 0:
                    return [Order(self.symbol, bb, -pos)]
                else:
                    return [Order(self.symbol, ba, -pos)]

        # Quote prices: penny inside the touch, with combined skew.
        total_skew = self.skew * pos + extra_skew
        bid_px = bb + 1 - total_skew
        ask_px = ba - 1 - total_skew
        bid_px_i = int(math.floor(bid_px))
        ask_px_i = int(math.ceil(ask_px))
        # Don't cross or invert
        if bid_px_i >= ba:
            bid_px_i = ba - 1
        if ask_px_i <= bb:
            ask_px_i = bb + 1
        if bid_px_i >= ask_px_i:
            # spread too tight to fit two quotes: just quote at touch
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
# PEBBLES basket coordinator
# ----------------------------------------------------------------------

class PebblesCoordinator:
    """MM each PEBBLE plus a basket-tilt overlay.

    Basket signal: sum(mids) - 50000. Tri-modal at {0, +14-16, -17-18} (NB09).
    Each pebble's residual = mid - rolling_mean (window=200).
    extra_skew per pebble = beta * residual (pulls quotes against the deviation).
    Larger beta where the basket constraint is tighter.
    """

    SYMBOLS = (
        "PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL",
    )
    TARGET_SUM = 50000
    BETA = 0.6  # residual->skew gain
    ROLL_WINDOW = 200

    def __init__(self) -> None:
        # Pebbles drift across days (NB08): means shift up to 30%. Loose stop_loss.
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
        # collect mids for residual computation
        mids: dict[str, float] = {}
        for s in self.SYMBOLS:
            depth = state.order_depths.get(s)
            m = _mid(depth)
            if m is not None:
                mids[s] = m
                self.basket_hist[s].append(m)

        # residuals (only if we have enough history)
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
# Trader
# ----------------------------------------------------------------------

# Per-product MM config
PER_PRODUCT_CFG: dict[str, dict[str, Any]] = {
    # SNACKPACK (wide ~17 spreads, strong MM opportunity)
    "SNACKPACK_CHOCOLATE":  {"skew": 0.5, "soft_cap": 7, "stop_loss_ticks": 80.0},
    "SNACKPACK_VANILLA":    {"skew": 0.5, "soft_cap": 7, "stop_loss_ticks": 80.0},
    "SNACKPACK_STRAWBERRY": {"skew": 0.5, "soft_cap": 7, "stop_loss_ticks": 80.0},
    "SNACKPACK_RASPBERRY":  {"skew": 0.5, "soft_cap": 7, "stop_loss_ticks": 80.0},
    "SNACKPACK_PISTACHIO":  {"skew": 0.5, "soft_cap": 7, "stop_loss_ticks": 80.0},
    # Step-fn products: tighter skew, smaller stop (step=10 grid)
    "ROBOT_IRONING":               {"skew": 0.6, "soft_cap": 8, "stop_loss_ticks": 40.0},
    "OXYGEN_SHAKE_EVENING_BREATH": {"skew": 0.6, "soft_cap": 8, "stop_loss_ticks": 40.0},
}


class Trader:
    def __init__(self) -> None:
        self.pebbles = PebblesCoordinator()
        self.per_product: dict[str, PassiveMM] = {
            sym: PassiveMM(sym, **cfg) for sym, cfg in PER_PRODUCT_CFG.items()
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
