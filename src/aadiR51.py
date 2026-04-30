"""
IMC Prosperity Round 5 — Trading Algorithm v3

Changes from v2:
  - Added DirectionalStrategy: 11 products with 3/3-day consistent drift
      → hold at ±POS_LIMIT all day (take liquidity once to fill, then done)
  - Added SNACKPACK_CHOCOLATE/VANILLA as 3rd pair (sum locked ~19,941 σ=76)
  - Dropped MICROCHIP_CIRCLE/OVAL pair → OVAL now directional short
      (3/3 days negative, ~+15k/day directional >> ~+2.4k/day from pair)
  - MICROCHIP_CIRCLE stays as EMA MM

Strategy layout:
  Pairs (2)    : PEBBLES_M/XL, SNACKPACK_CHOCOLATE/VANILLA
  Dir Long (6) : BLACK_HOLES, GARLIC, PANEL_2X4, UV_RED, LAMB_WOOL, STRAWBERRY
  Dir Short (5): PEBBLES_XS, PEBBLES_S, MICROCHIP_OVAL, UV_AMBER, PISTACHIO
  MM (37)      : everything else — EMA-trend-filtered spread capture
"""

import json
import numpy as np
from datamodel import Order, OrderDepth, TradingState
from typing import Dict, List, Optional, Tuple

# ── Global ─────────────────────────────────────────────────────────────────────
POS_LIMIT = 10

# ── Pairs: z-score mean-reversion ─────────────────────────────────────────────
WINDOW   = 500
ENTRY_Z  = 1.5
EXIT_Z   = 0.3
MIN_HIST = 200

PAIRS: List[Tuple[str, str]] = [
    ("PEBBLES_M",           "PEBBLES_XL"),        # live: +8246, dominant pair
    ("SNACKPACK_CHOCOLATE", "SNACKPACK_VANILLA"),  # sum locked ~19,941 σ=76
]

PAIR_PRODUCTS: frozenset = frozenset(p for pair in PAIRS for p in pair)

# ── Directional: hold at ±POS_LIMIT — all 3 training days same sign ─────────
# Long: drift consistently positive across days 2, 3, 4
DIRECTIONAL_LONG: List[str] = [
    "GALAXY_SOUNDS_BLACK_HOLES",  # +1446 / +688 / +1320  avg +1152
    "OXYGEN_SHAKE_GARLIC",        # +1828 / +111 / +1958  avg +1299
    "PANEL_2X4",                  # +738  / +738 / +894   avg  +790
    "UV_VISOR_RED",               # +842  / +182 / +698   avg  +574
    "SLEEP_POD_LAMB_WOOL",        # +404  / +396 / +16    avg  +272
    "SNACKPACK_STRAWBERRY",       # +436  / +358 / +98    avg  +297
]

# Short: drift consistently negative across days 2, 3, 4
DIRECTIONAL_SHORT: List[str] = [
    "PEBBLES_XS",        # -1952 / -1204 / -824   avg -1326
    "MICROCHIP_OVAL",    # -744  / -1824 / -1898  avg -1488
    "UV_VISOR_AMBER",    # -1500 / -1109 / -255   avg  -954
    "PEBBLES_S",         # -840  / -177  / -937   avg  -651
    "SNACKPACK_PISTACHIO",# -489 / -124  / -282   avg  -298
]

DIRECTIONAL_PRODUCTS: frozenset = frozenset(DIRECTIONAL_LONG + DIRECTIONAL_SHORT)

# ── All 50 products ────────────────────────────────────────────────────────────
ALL_PRODUCTS: List[str] = [
    "GALAXY_SOUNDS_DARK_MATTER","GALAXY_SOUNDS_BLACK_HOLES","GALAXY_SOUNDS_PLANETARY_RINGS",
    "GALAXY_SOUNDS_SOLAR_WINDS","GALAXY_SOUNDS_SOLAR_FLAMES",
    "SLEEP_POD_SUEDE","SLEEP_POD_LAMB_WOOL","SLEEP_POD_POLYESTER","SLEEP_POD_NYLON","SLEEP_POD_COTTON",
    "MICROCHIP_CIRCLE","MICROCHIP_OVAL","MICROCHIP_SQUARE","MICROCHIP_RECTANGLE","MICROCHIP_TRIANGLE",
    "PEBBLES_XS","PEBBLES_S","PEBBLES_M","PEBBLES_L","PEBBLES_XL",
    "ROBOT_VACUUMING","ROBOT_MOPPING","ROBOT_DISHES","ROBOT_LAUNDRY","ROBOT_IRONING",
    "UV_VISOR_YELLOW","UV_VISOR_AMBER","UV_VISOR_ORANGE","UV_VISOR_RED","UV_VISOR_MAGENTA",
    "TRANSLATOR_SPACE_GRAY","TRANSLATOR_ASTRO_BLACK","TRANSLATOR_ECLIPSE_CHARCOAL",
    "TRANSLATOR_GRAPHITE_MIST","TRANSLATOR_VOID_BLUE",
    "PANEL_1X2","PANEL_2X2","PANEL_1X4","PANEL_2X4","PANEL_4X4",
    "OXYGEN_SHAKE_MORNING_BREATH","OXYGEN_SHAKE_EVENING_BREATH","OXYGEN_SHAKE_MINT",
    "OXYGEN_SHAKE_CHOCOLATE","OXYGEN_SHAKE_GARLIC",
    "SNACKPACK_CHOCOLATE","SNACKPACK_VANILLA","SNACKPACK_PISTACHIO",
    "SNACKPACK_STRAWBERRY","SNACKPACK_RASPBERRY",
]

# MM gets everything not claimed by pairs or directional
MM_PRODUCTS: List[str] = [
    p for p in ALL_PRODUCTS
    if p not in PAIR_PRODUCTS and p not in DIRECTIONAL_PRODUCTS
]

# ── MM parameters ──────────────────────────────────────────────────────────────
EMA_ALPHA     = 0.02   # ~50-tick smoothing
TREND_THRESH  = 0.002  # 0.2% from EMA = "trending"
SKEW_MULT     = 5      # max inventory skew in ticks
TREND_QTY_CAP = 3      # max units to build against trend direction


def _best_bid_ask(od: OrderDepth) -> Tuple[Optional[int], Optional[int]]:
    bb = max(od.buy_orders)  if od.buy_orders  else None
    ba = min(od.sell_orders) if od.sell_orders else None
    return bb, ba


class Trader:

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:

        try:
            saved = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            saved = {}

        spread_hist: Dict[str, List[float]] = saved.get("sh", {})
        emas: Dict[str, float]              = saved.get("em", {})

        result: Dict[str, List[Order]] = {}

        # ── Mid-price map ──────────────────────────────────────────────────────
        mids: Dict[str, float] = {}
        for sym, od in state.order_depths.items():
            bb, ba = _best_bid_ask(od)
            if bb is not None and ba is not None:
                mids[sym] = (bb + ba) / 2.0

        # ══════════════════════════════════════════════════════════════════════
        # STRATEGY 1 — Z-score pairs trading
        # PEBBLES_M/XL: confirmed mean-reverting in live run (+8246 realized)
        # SNACKPACK_CHOC/VAN: structural sum constraint (σ=76 on sum ~19,941)
        # ══════════════════════════════════════════════════════════════════════
        for prod_a, prod_b in PAIRS:
            if prod_a not in mids or prod_b not in mids:
                continue

            key  = f"{prod_a}|{prod_b}"
            hist = spread_hist.setdefault(key, [])
            hist.append(mids[prod_a] - mids[prod_b])
            if len(hist) > WINDOW:
                hist.pop(0)

            if len(hist) < MIN_HIST:
                continue

            arr = np.asarray(hist, dtype=np.float64)
            std = float(arr.std()) + 1e-9
            z   = float((arr[-1] - arr.mean()) / std)

            pos_a = state.position.get(prod_a, 0)
            pos_b = state.position.get(prod_b, 0)

            od_a = state.order_depths.get(prod_a)
            od_b = state.order_depths.get(prod_b)
            if od_a is None or od_b is None:
                continue

            bb_a, ba_a = _best_bid_ask(od_a)
            bb_b, ba_b = _best_bid_ask(od_b)
            if None in (bb_a, ba_a, bb_b, ba_b):
                continue

            if z > ENTRY_Z:
                tgt_a, tgt_b = -POS_LIMIT, +POS_LIMIT   # A expensive → short A / long B
            elif z < -ENTRY_Z:
                tgt_a, tgt_b = +POS_LIMIT, -POS_LIMIT   # B expensive → long A / short B
            elif abs(z) < EXIT_Z:
                tgt_a, tgt_b = 0, 0                      # reverted → flatten
            else:
                continue                                  # hold zone

            delta_a = tgt_a - pos_a
            delta_b = tgt_b - pos_b

            ords_a = result.setdefault(prod_a, [])
            ords_b = result.setdefault(prod_b, [])

            if delta_a > 0:
                ords_a.append(Order(prod_a, ba_a,  delta_a))
            elif delta_a < 0:
                ords_a.append(Order(prod_a, bb_a,  delta_a))

            if delta_b > 0:
                ords_b.append(Order(prod_b, ba_b,  delta_b))
            elif delta_b < 0:
                ords_b.append(Order(prod_b, bb_b,  delta_b))

        # ══════════════════════════════════════════════════════════════════════
        # STRATEGY 2 — Directional: hold at ±POS_LIMIT in drift direction
        # Products with 3/3 consistent day-over-day drift direction.
        # Take liquidity aggressively until target reached; no orders once flat.
        # ══════════════════════════════════════════════════════════════════════
        for direction, products in ((+1, DIRECTIONAL_LONG), (-1, DIRECTIONAL_SHORT)):
            for product in products:
                od = state.order_depths.get(product)
                if od is None:
                    continue
                bb, ba = _best_bid_ask(od)
                if bb is None or ba is None:
                    continue

                pos    = state.position.get(product, 0)
                target = direction * POS_LIMIT
                delta  = target - pos

                if delta == 0:
                    continue

                ords = result.setdefault(product, [])
                if delta > 0:
                    ords.append(Order(product, ba,  delta))   # buy at ask
                else:
                    ords.append(Order(product, bb,  delta))   # sell at bid

        # ══════════════════════════════════════════════════════════════════════
        # STRATEGY 3 — EMA-trend-filtered market making (37 neutral products)
        # Captures bid-ask spread; trend filter prevents inventory against drift;
        # high skew (5 ticks) flushes inventory faster.
        # ══════════════════════════════════════════════════════════════════════
        for product in MM_PRODUCTS:
            od = state.order_depths.get(product)
            if od is None:
                continue
            bb, ba = _best_bid_ask(od)
            if bb is None or ba is None:
                continue

            mid = mids.get(product)
            if mid is None:
                continue

            ema = emas.get(product, mid)
            ema = EMA_ALPHA * mid + (1.0 - EMA_ALPHA) * ema
            emas[product] = ema

            trend = (mid - ema) / ema   # + = trending up, - = trending down

            pos      = state.position.get(product, 0)
            skew     = round(pos / POS_LIMIT * SKEW_MULT)
            our_bid  = bb + 1 - skew
            our_ask  = ba - 1 - skew
            if our_bid >= our_ask:
                our_bid, our_ask = bb, ba

            buy_qty  = POS_LIMIT - pos
            sell_qty = POS_LIMIT + pos

            # Cap position build in the direction the market is already running
            if trend > TREND_THRESH and pos <= 0:
                sell_qty = min(sell_qty, TREND_QTY_CAP)
            elif trend < -TREND_THRESH and pos >= 0:
                buy_qty  = min(buy_qty,  TREND_QTY_CAP)

            ords = result.setdefault(product, [])
            if buy_qty > 0:
                ords.append(Order(product, our_bid,  +buy_qty))
            if sell_qty > 0:
                ords.append(Order(product, our_ask, -sell_qty))

        # ── Persist state ──────────────────────────────────────────────────────
        new_state = json.dumps({"sh": spread_hist, "em": emas}, separators=(",", ":"))
        return result, 0, new_state