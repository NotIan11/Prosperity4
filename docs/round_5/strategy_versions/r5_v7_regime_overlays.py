"""IMC Prosperity 4 — Round 5 trader (v7: regime-tuned MM + adaptive overlays).

v6 (passive MM on 46 products): BT $271k, monotone-up live curve.
v7 keeps that structural core and adds three robust adaptive overlays
(no directional bets, no capsule-drift fitting):

1. **Regime-tuned MM**: each product uses one of 5 PassiveMM tuples
   (skew, soft_cap, stop_loss_ticks) selected by structural features
   (spread, abs_ret, day_stdev, AR(1), step). 5 regimes, no per-product
   overfitting.
2. **PEBBLES outlier suppression**: skip new pebble quotes when
   |basket_dev| > 8 (deep in the tri-modal gap). Avoids inventory pickup
   during NPC repricing events.
3. **SNACKPACK group inventory balance**: skew CHOC/VAN and STRAW/RASP
   quotes against their pair-net inventory, exploiting the structurally
   stable 2+2+1 anti-corr architecture.
4. **Step-product cooldown**: for step_mr products (ROBOT_IRONING,
   OXYGEN_SHAKE_EVENING_BREATH, OXYGEN_SHAKE_CHOCOLATE), widen quotes to
   touch (not penny-inside) for 3 ticks after a |Δmid| ≥ 8 step event.

All overlays have bounded downside: failure mode is reduced fill rate or
no-op, never adverse inventory accumulation.

Active products: 46 (4 consistent BT+live bleeders dropped from v6).
Triage: docs/round_5/research/EDA_FINAL_TRIAGE.md
Regime: docs/round_5/research/regime_analysis_v7.md
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
STEP_COOLDOWN_TICKS = 3
STEP_THRESHOLD = 8.0


def _mid(depth: OrderDepth) -> float | None:
    if not depth or not depth.buy_orders or not depth.sell_orders:
        return None
    return (max(depth.buy_orders) + min(depth.sell_orders)) / 2.0


def _best_bid(depth: OrderDepth) -> int | None:
    return max(depth.buy_orders) if depth and depth.buy_orders else None


def _best_ask(depth: OrderDepth) -> int | None:
    return min(depth.sell_orders) if depth and depth.sell_orders else None


# ----------------------------------------------------------------------
# PassiveMM core
# ----------------------------------------------------------------------

class PassiveMM:
    """Penny-inside-touch quote with position skew + rolling-mean stop-loss.

    Two new flags in v7:
      step_mode: enables post-step cooldown (widens to touch for N ticks
        after a |Δmid| ≥ STEP_THRESHOLD event). Good for step_mr regime.
      external_quote_suppress: caller-driven (per-tick) flag that suppresses
        new quotes; existing position is held. Used by PEBBLES outlier gate.
    """

    def __init__(
        self,
        symbol: str,
        skew: float = 0.4,
        soft_cap: int = 7,
        window: int = 500,
        stop_loss_ticks: float = 60.0,
        step_mode: bool = False,
    ) -> None:
        self.symbol = symbol
        self.skew = skew
        self.soft_cap = soft_cap
        self.window = window
        self.stop_loss_ticks = stop_loss_ticks
        self.step_mode = step_mode
        self.mids: deque[float] = deque(maxlen=window)
        self.cooldown_left = 0  # post-step ticks remaining

    def save(self) -> dict[str, Any]:
        return {"mids": list(self.mids), "cooldown_left": self.cooldown_left}

    def load(self, d: dict[str, Any]) -> None:
        self.mids = deque(d.get("mids", [])[-self.window:], maxlen=self.window)
        self.cooldown_left = int(d.get("cooldown_left", 0))

    def act(
        self,
        state: TradingState,
        extra_skew: float = 0.0,
        suppress: bool = False,
    ) -> list[Order]:
        depth = state.order_depths.get(self.symbol)
        bb, ba = _best_bid(depth), _best_ask(depth)
        if bb is None or ba is None:
            return []
        m = (bb + ba) / 2.0

        # step detection (compare to last mid)
        if self.step_mode and self.mids:
            if abs(m - self.mids[-1]) >= STEP_THRESHOLD:
                self.cooldown_left = STEP_COOLDOWN_TICKS

        self.mids.append(m)
        pos = state.position.get(self.symbol, 0)

        # stop-loss
        if pos != 0 and len(self.mids) >= 100:
            mean = sum(self.mids) / len(self.mids)
            adverse = (m - mean) if pos > 0 else (mean - m)
            if adverse > self.stop_loss_ticks:
                if pos > 0:
                    return [Order(self.symbol, bb, -pos)]
                return [Order(self.symbol, ba, -pos)]

        if suppress:
            # cooldown still ticks down so we don't get stuck wide forever
            if self.cooldown_left > 0:
                self.cooldown_left -= 1
            return []

        # determine inside-touch offset: penny-inside default, AT touch
        # during step cooldown for step_mr products
        if self.cooldown_left > 0:
            bid_offset, ask_offset = 0, 0  # quote AT touch
            self.cooldown_left -= 1
        else:
            bid_offset, ask_offset = 1, -1  # penny inside

        total_skew = self.skew * pos + extra_skew
        bid_px = bb + bid_offset - total_skew
        ask_px = ba + ask_offset - total_skew
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
# PEBBLES coordinator (with outlier-state suppression)
# ----------------------------------------------------------------------

class PebblesCoordinator:
    """MM each PEBBLE. Two overlays:
      - residual-skew vs rolling per-product mean (basket_constraint signal)
      - outlier suppression: skip new quotes when |basket_dev| > GATE
    """

    SYMBOLS = ("PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL")
    TARGET_SUM = 50000
    BETA = 0.6  # residual->skew gain
    OUTLIER_GATE = 8.0  # tri-modal gap is 1.5–14; threshold deep inside
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

        # outlier gate
        suppress = False
        if len(mids) == len(self.SYMBOLS):
            basket_dev = sum(mids.values()) - self.TARGET_SUM
            if abs(basket_dev) > self.OUTLIER_GATE:
                suppress = True

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
            orders = self.makers[s].act(state, extra_skew=extra, suppress=suppress)
            if orders:
                result.setdefault(s, []).extend(orders)
        return result


# ----------------------------------------------------------------------
# SNACKPACK group coordinator (2+2+1 inventory balance)
# ----------------------------------------------------------------------

class SnackpackCoordinator:
    """Skew CHOC/VAN and STRAW/RASP quotes against group net inventory.

    Group A: CHOC + VAN (anti-corr -0.92)
    Group B: STRAW + RASP (anti-corr -0.92), PIST co-moves with STRAW
    Cross-group |corr| ≤ 0.04 — fully decoupled.
    """

    GROUP_A = ("SNACKPACK_CHOCOLATE", "SNACKPACK_VANILLA")
    GROUP_B = ("SNACKPACK_STRAWBERRY", "SNACKPACK_RASPBERRY")
    PIST = "SNACKPACK_PISTACHIO"
    GROUP_SKEW = 0.3  # bounded: max contribution = 0.3 * 20 / 2 = 3 ticks

    def __init__(self) -> None:
        cfg = {"skew": 0.5, "soft_cap": 7, "window": 500, "stop_loss_ticks": 80.0}
        self.makers: dict[str, PassiveMM] = {
            s: PassiveMM(s, **cfg)
            for s in self.GROUP_A + self.GROUP_B + (self.PIST,)
        }

    def save(self) -> dict[str, Any]:
        return {"makers": {s: m.save() for s, m in self.makers.items()}}

    def load(self, d: dict[str, Any]) -> None:
        for s, sub in d.get("makers", {}).items():
            if s in self.makers and isinstance(sub, dict):
                self.makers[s].load(sub)

    def act(self, state: TradingState) -> dict[str, list[Order]]:
        result: dict[str, list[Order]] = {}
        a_net = sum(state.position.get(s, 0) for s in self.GROUP_A)
        b_net = sum(state.position.get(s, 0) for s in self.GROUP_B)
        a_skew = self.GROUP_SKEW * a_net / 2.0
        b_skew = self.GROUP_SKEW * b_net / 2.0
        for s in self.GROUP_A:
            o = self.makers[s].act(state, extra_skew=a_skew)
            if o:
                result.setdefault(s, []).extend(o)
        for s in self.GROUP_B:
            o = self.makers[s].act(state, extra_skew=b_skew)
            if o:
                result.setdefault(s, []).extend(o)
        # PIST: handled independently (its inventory pairs with STRAW
        # via the +0.913 co-move, but STRAW already counter-skewed by GROUP_B)
        o = self.makers[self.PIST].act(state)
        if o:
            result.setdefault(self.PIST, []).extend(o)
        return result


# ----------------------------------------------------------------------
# Regime-tuned configurations
# ----------------------------------------------------------------------

# Regime tuples (skew, soft_cap, stop_loss_ticks). Step-mr products also
# get step_mode=True so the post-step cooldown widens quotes to touch.
REGIME_TUPLES: dict[str, dict[str, Any]] = {
    "narrow_quiet_mm":   {"skew": 0.4, "soft_cap": 7, "stop_loss_ticks": 60.0},
    "wide_drifty_mm":    {"skew": 0.5, "soft_cap": 7, "stop_loss_ticks": 50.0},
    "narrow_volatile_mm":{"skew": 0.6, "soft_cap": 6, "stop_loss_ticks": 45.0},
    "step_mr":           {"skew": 0.6, "soft_cap": 8, "stop_loss_ticks": 40.0, "step_mode": True},
}

# Per-product regime assignment (from regime_analysis_v7.md, derived
# from price-data features only). 4 BT+live consistent bleeders dropped:
# ROBOT_DISHES, OXYGEN_SHAKE_MINT, MICROCHIP_TRIANGLE, OXYGEN_SHAKE_MORNING_BREATH.
REGIME_BY_PRODUCT: dict[str, str] = {
    # narrow_quiet_mm (16 active, 18 originally — 2 dropped)
    "MICROCHIP_CIRCLE":          "narrow_quiet_mm",
    "PANEL_1X2":                 "narrow_quiet_mm",
    "PANEL_1X4":                 "narrow_quiet_mm",
    "PANEL_2X2":                 "narrow_quiet_mm",
    "PANEL_4X4":                 "narrow_quiet_mm",
    "ROBOT_LAUNDRY":             "narrow_quiet_mm",
    "ROBOT_MOPPING":             "narrow_quiet_mm",
    "ROBOT_VACUUMING":           "narrow_quiet_mm",
    "SLEEP_POD_COTTON":          "narrow_quiet_mm",
    "SLEEP_POD_LAMB_WOOL":       "narrow_quiet_mm",
    "SLEEP_POD_NYLON":           "narrow_quiet_mm",
    "SLEEP_POD_POLYESTER":       "narrow_quiet_mm",
    "SLEEP_POD_SUEDE":           "narrow_quiet_mm",
    "TRANSLATOR_ASTRO_BLACK":    "narrow_quiet_mm",
    "TRANSLATOR_ECLIPSE_CHARCOAL":"narrow_quiet_mm",
    "TRANSLATOR_GRAPHITE_MIST":  "narrow_quiet_mm",
    "TRANSLATOR_SPACE_GRAY":     "narrow_quiet_mm",
    "TRANSLATOR_VOID_BLUE":      "narrow_quiet_mm",
    # wide_drifty_mm (9 active, 11 originally)
    "GALAXY_SOUNDS_BLACK_HOLES": "wide_drifty_mm",
    "GALAXY_SOUNDS_DARK_MATTER": "wide_drifty_mm",
    "GALAXY_SOUNDS_PLANETARY_RINGS":"wide_drifty_mm",
    "GALAXY_SOUNDS_SOLAR_FLAMES":"wide_drifty_mm",
    "GALAXY_SOUNDS_SOLAR_WINDS": "wide_drifty_mm",
    "OXYGEN_SHAKE_GARLIC":       "wide_drifty_mm",
    "UV_VISOR_AMBER":            "wide_drifty_mm",
    "UV_VISOR_MAGENTA":          "wide_drifty_mm",
    "UV_VISOR_ORANGE":           "wide_drifty_mm",
    "UV_VISOR_RED":              "wide_drifty_mm",
    "UV_VISOR_YELLOW":           "wide_drifty_mm",
    # narrow_volatile_mm (4 active)
    "MICROCHIP_OVAL":            "narrow_volatile_mm",
    "MICROCHIP_RECTANGLE":       "narrow_volatile_mm",
    "MICROCHIP_SQUARE":          "narrow_volatile_mm",
    "PANEL_2X4":                 "narrow_volatile_mm",
    # step_mr (2 active)
    "OXYGEN_SHAKE_CHOCOLATE":    "step_mr",
    "OXYGEN_SHAKE_EVENING_BREATH":"step_mr",
    "ROBOT_IRONING":             "step_mr",
}

PEBBLES_SET = {"PEBBLES_XS", "PEBBLES_S", "PEBBLES_M", "PEBBLES_L", "PEBBLES_XL"}
SNACKPACK_SET = {
    "SNACKPACK_CHOCOLATE", "SNACKPACK_VANILLA", "SNACKPACK_STRAWBERRY",
    "SNACKPACK_RASPBERRY", "SNACKPACK_PISTACHIO",
}


class Trader:
    def __init__(self) -> None:
        self.pebbles = PebblesCoordinator()
        self.snackpack = SnackpackCoordinator()
        self.mm: dict[str, PassiveMM] = {}
        for sym, regime in REGIME_BY_PRODUCT.items():
            cfg = dict(REGIME_TUPLES[regime])
            self.mm[sym] = PassiveMM(sym, **cfg)

    def _save_state(self) -> str:
        try:
            return json.dumps({
                "pebbles": self.pebbles.save(),
                "snackpack": self.snackpack.save(),
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
        if isinstance(payload.get("snackpack"), dict):
            self.snackpack.load(payload["snackpack"])
        for sym, sub in payload.get("mm", {}).items():
            if sym in self.mm and isinstance(sub, dict):
                self.mm[sym].load(sub)

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        self._load_state(state.traderData or "")

        result: dict[str, list[Order]] = {}

        for sym, orders in self.pebbles.act(state).items():
            if orders:
                result.setdefault(sym, []).extend(orders)

        for sym, orders in self.snackpack.act(state).items():
            if orders:
                result.setdefault(sym, []).extend(orders)

        for sym, strat in self.mm.items():
            orders = strat.act(state)
            if orders:
                result.setdefault(sym, []).extend(orders)

        return result, 0, self._save_state()
