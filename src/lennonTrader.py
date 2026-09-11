import json
import math
from typing import Dict, List, Optional, Tuple

try:
    from datamodel import Order, OrderDepth, TradingState  # type: ignore
except ImportError:
    from src.datamodel import Order, OrderDepth, TradingState  # type: ignore


UNDERLYING = "VELVETFRUIT_EXTRACT"
HYDROGEL = "HYDROGEL_PACK"

VEV_STRIKES = {
    "VEV_4000": 4000,
    "VEV_4500": 4500,
    "VEV_5000": 5000,
    "VEV_5100": 5100,
    "VEV_5200": 5200,
    "VEV_5300": 5300,
    "VEV_5400": 5400,
    "VEV_5500": 5500,
    "VEV_6000": 6000,
    "VEV_6500": 6500,
}

POSITION_LIMITS = {
    HYDROGEL: 200,
    UNDERLYING: 200,
    "VEV_4000": 200,
    "VEV_4500": 200,
    "VEV_5000": 200,
    "VEV_5100": 200,
    "VEV_5200": 200,
    "VEV_5300": 200,
    "VEV_5400": 200,
    "VEV_5500": 200,
    "VEV_6000": 200,
    "VEV_6500": 200,
}

DEFAULT_SIGMA = 0.22
DEFAULT_TTE_DAYS = 7.0
DAYS_PER_YEAR = 365.0

MAX_OPTION_TAKE_PER_TICK = 10
MAX_VEV5300_TAKE_PER_TICK = 15
MAX_HEDGE_PER_TICK = 30

DEAD_STRIKES = {"VEV_6000", "VEV_6500"}
NO_BUY_STRIKES = {"VEV_5400", "VEV_5500", "VEV_6000", "VEV_6500"}


def best_bid_ask(depth: OrderDepth) -> Tuple[Optional[int], Optional[int]]:
    bid = max(depth.buy_orders.keys()) if depth.buy_orders else None
    ask = min(depth.sell_orders.keys()) if depth.sell_orders else None
    return bid, ask


def mid_price(depth: OrderDepth) -> Optional[float]:
    bid, ask = best_bid_ask(depth)
    if bid is None or ask is None:
        return None
    return 0.5 * (bid + ask)


def spread(depth: OrderDepth) -> Optional[float]:
    bid, ask = best_bid_ask(depth)
    if bid is None or ask is None:
        return None
    return ask - bid


def get_pos(state: TradingState, symbol: str) -> int:
    return state.position.get(symbol, 0)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_call(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0:
        return max(S - K, 0.0)

    if S <= 0 or K <= 0:
        return max(S - K, 0.0)

    vol_sqrt_t = sigma * math.sqrt(T)
    if vol_sqrt_t <= 0:
        return max(S - K, 0.0)

    d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    return S * norm_cdf(d1) - K * norm_cdf(d2)


def bs_delta(S: float, K: float, T: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0:
        return 1.0 if S > K else 0.0

    vol_sqrt_t = sigma * math.sqrt(T)
    if vol_sqrt_t <= 0:
        return 1.0 if S > K else 0.0

    d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / vol_sqrt_t
    return norm_cdf(d1)


def implied_vol_bisect(price: float, S: float, K: float, T: float) -> Optional[float]:
    intrinsic = max(S - K, 0.0)

    if price < intrinsic - 0.5:
        return None

    if price <= intrinsic + 0.1:
        return 0.01

    lo, hi = 0.01, 2.00

    for _ in range(30):
        mid = 0.5 * (lo + hi)
        val = bs_call(S, K, T, mid)

        if val > price:
            hi = mid
        else:
            lo = mid

    return 0.5 * (lo + hi)


def current_tte_years(state: TradingState) -> float:
    return max(DEFAULT_TTE_DAYS / DAYS_PER_YEAR, 1.0 / DAYS_PER_YEAR)


class HydrogelStrategy:
    FAIR = 9991
    TAKE_EDGE = 18
    PASSIVE_EDGE = 20
    MAX_TAKE = 25
    MAX_PASSIVE = 25

    # Dynamic risk controls, not timestamp-based.
    EMA_ALPHA = 0.015
    RICH_MID = FAIR + 35
    VERY_RICH_MID = FAIR + 55
    TRAILING_DRAWDOWN = 22
    EMA_BREAK = 18
    MAX_DERISK_PER_TICK = 40

    def __init__(self) -> None:
        self.ema_mid: Optional[float] = None
        self.prev_mid: Optional[float] = None
        self.peak_mid_while_long: Optional[float] = None

    def save_state(self) -> dict:
        return {
            "ema_mid": self.ema_mid,
            "prev_mid": self.prev_mid,
            "peak_mid_while_long": self.peak_mid_while_long,
        }

    def load_state(self, data: dict) -> None:
        self.ema_mid = data.get("ema_mid", None)
        self.prev_mid = data.get("prev_mid", None)
        self.peak_mid_while_long = data.get("peak_mid_while_long", None)

    def update_state(self, mid: float, pos: int) -> None:
        if self.ema_mid is None:
            self.ema_mid = mid
        else:
            self.ema_mid = (1.0 - self.EMA_ALPHA) * self.ema_mid + self.EMA_ALPHA * mid

        if pos > 0:
            if self.peak_mid_while_long is None:
                self.peak_mid_while_long = mid
            else:
                self.peak_mid_while_long = max(self.peak_mid_while_long, mid)
        else:
            self.peak_mid_while_long = mid

    def should_derisk(self, mid: float, pos: int) -> bool:
        if pos <= 0:
            return False

        ema = self.ema_mid if self.ema_mid is not None else mid
        peak = self.peak_mid_while_long if self.peak_mid_while_long is not None else mid

        rolled_over_from_peak = peak - mid >= self.TRAILING_DRAWDOWN and mid > self.FAIR + 5
        rich_take_profit = mid >= self.VERY_RICH_MID
        ema_break_after_rich = mid < ema - self.EMA_BREAK and peak > self.RICH_MID

        return rich_take_profit or rolled_over_from_peak or ema_break_after_rich

    def should_block_new_buys(self, mid: float, pos: int) -> bool:
        ema = self.ema_mid if self.ema_mid is not None else mid
        peak = self.peak_mid_while_long if self.peak_mid_while_long is not None else mid

        if mid >= self.RICH_MID:
            return True

        if pos > 0 and peak - mid >= self.TRAILING_DRAWDOWN:
            return True

        if pos > 0 and mid < ema - self.EMA_BREAK:
            return True

        return False

    def run(self, state: TradingState) -> List[Order]:
        symbol = HYDROGEL
        depth = state.order_depths.get(symbol)
        if depth is None or not depth.buy_orders or not depth.sell_orders:
            return []

        mid = mid_price(depth)
        if mid is None:
            return []

        pos = get_pos(state, symbol)
        self.update_state(mid, pos)

        orders: List[Order] = []
        bought = 0
        sold = 0

        # Dynamic derisking: if Hydrogel is rich or has rolled over while we are long,
        # sell into available bids. This fixes the big giveback without memorizing time.
        if self.should_derisk(mid, pos):
            for bid, vol in sorted(depth.buy_orders.items(), reverse=True):
                if sold >= self.MAX_DERISK_PER_TICK:
                    break

                # In a panic/EMA-break, allow lower bids; otherwise require a profitable exit zone.
                ema = self.ema_mid if self.ema_mid is not None else mid
                peak = self.peak_mid_while_long if self.peak_mid_while_long is not None else mid

                if mid >= self.VERY_RICH_MID:
                    min_bid = self.FAIR + 25
                elif peak - mid >= self.TRAILING_DRAWDOWN:
                    min_bid = self.FAIR + 8
                elif mid < ema - self.EMA_BREAK:
                    min_bid = self.FAIR
                else:
                    min_bid = self.FAIR + self.TAKE_EDGE

                if bid < min_bid:
                    break

                remaining_pos = pos - sold
                if remaining_pos <= 0:
                    break

                qty = min(vol, remaining_pos, self.MAX_DERISK_PER_TICK - sold)
                if qty > 0:
                    orders.append(Order(symbol, bid, -qty))
                    sold += qty

        block_new_buys = self.should_block_new_buys(mid, pos)

        if not block_new_buys:
            for ask, vol in sorted(depth.sell_orders.items()):
                if ask > self.FAIR - self.TAKE_EDGE:
                    break

                cap = min(POSITION_LIMITS[symbol] - pos - bought, self.MAX_TAKE - bought)
                if cap <= 0:
                    break

                qty = min(-vol, cap)
                if qty > 0:
                    orders.append(Order(symbol, ask, qty))
                    bought += qty

        for bid, vol in sorted(depth.buy_orders.items(), reverse=True):
            if bid < self.FAIR + self.TAKE_EDGE:
                break

            cap = min(POSITION_LIMITS[symbol] + pos - sold, self.MAX_TAKE - sold)
            if cap <= 0:
                break

            qty = min(vol, cap)
            if qty > 0:
                orders.append(Order(symbol, bid, -qty))
                sold += qty

        effective_pos = pos + bought - sold
        inv_skew = int(round(8 * effective_pos / max(POSITION_LIMITS[symbol], 1)))

        bid_px = self.FAIR - self.PASSIVE_EDGE - inv_skew
        ask_px = self.FAIR + self.PASSIVE_EDGE - inv_skew

        buy_cap = min(POSITION_LIMITS[symbol] - pos - bought, self.MAX_PASSIVE)
        sell_cap = min(POSITION_LIMITS[symbol] + pos - sold, self.MAX_PASSIVE)

        # Avoid passive bid accumulation when dynamic risk says not to add.
        if not block_new_buys and buy_cap > 0:
            orders.append(Order(symbol, bid_px, buy_cap))

        if sell_cap > 0:
            orders.append(Order(symbol, ask_px, -sell_cap))

        self.prev_mid = mid
        return orders


class VEVOptionChainStrategy:
    def __init__(self) -> None:
        self.sigma_ema = DEFAULT_SIGMA
        self.last_S: Optional[float] = None

    def save_state(self) -> dict:
        return {
            "sigma_ema": self.sigma_ema,
            "last_S": self.last_S,
        }

    def load_state(self, data: dict) -> None:
        self.sigma_ema = float(data.get("sigma_ema", DEFAULT_SIGMA))
        self.last_S = data.get("last_S", None)

    def calibrate_sigma(self, state: TradingState, S: float, T: float) -> float:
        ivs: List[Tuple[float, float]] = []

        for symbol in ["VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_5500"]:
            depth = state.order_depths.get(symbol)
            if depth is None:
                continue

            m = mid_price(depth)
            sp = spread(depth)
            if m is None or sp is None or sp <= 0:
                continue

            K = VEV_STRIKES[symbol]
            iv = implied_vol_bisect(m, S, K, T)
            if iv is None or not (0.02 <= iv <= 1.50):
                continue

            moneyness_penalty = 1.0 + abs(S - K) / 150.0
            spread_penalty = 1.0 + sp / 3.0
            weight = 1.0 / (moneyness_penalty * spread_penalty)
            ivs.append((iv, weight))

        if not ivs:
            return self.sigma_ema

        weighted = sum(iv * w for iv, w in ivs) / sum(w for _, w in ivs)
        self.sigma_ema = 0.70 * self.sigma_ema + 0.30 * weighted
        self.sigma_ema = min(max(self.sigma_ema, 0.08), 0.80)

        return self.sigma_ema

    def option_edge_threshold(self, symbol: str, depth: OrderDepth, fair: float) -> float:
        sp = spread(depth)
        if sp is None:
            sp = 2.0

        K = VEV_STRIKES[symbol]

        if symbol in DEAD_STRIKES:
            return 999999.0

        if K in (4000, 4500):
            return max(3.0, 1.00 * sp)

        if K == 5000:
            return max(2.5, 1.00 * sp)

        if K == 5100:
            return max(2.5, 1.00 * sp)

        if K == 5200:
            return max(2.5, 1.00 * sp)

        if K == 5300:
            return max(2.0, 1.00 * sp)

        if K == 5400:
            return max(3.0, 1.50 * sp)

        if K == 5500:
            return max(3.0, 1.50 * sp)

        return max(4.0, 2.0 * sp)

    def trade_option(self, state: TradingState, symbol: str, S: float, T: float, sigma: float) -> List[Order]:
        if symbol in DEAD_STRIKES:
            return []

        depth = state.order_depths.get(symbol)
        if depth is None or not depth.buy_orders or not depth.sell_orders:
            return []

        K = VEV_STRIKES[symbol]
        fair = bs_call(S, K, T, sigma)

        # Keep this modest. It is empirical, so do not over-crank it.
        if symbol == "VEV_5300":
            fair -= 1.25
        elif symbol == "VEV_5400":
            fair -= 2.0

        orders: List[Order] = []
        pos = get_pos(state, symbol)
        bought = 0
        sold = 0

        edge_thr = self.option_edge_threshold(symbol, depth, fair)
        allow_buy = symbol not in NO_BUY_STRIKES
        allow_sell = symbol not in DEAD_STRIKES
        max_take = MAX_VEV5300_TAKE_PER_TICK if symbol == "VEV_5300" else MAX_OPTION_TAKE_PER_TICK

        if allow_buy:
            for ask, vol in sorted(depth.sell_orders.items()):
                edge = fair - ask
                if edge < edge_thr:
                    break

                cap = min(POSITION_LIMITS[symbol] - pos - bought, max_take - bought)
                if cap <= 0:
                    break

                desired = int(min(cap, max(1, edge // max(edge_thr, 1.0) * 5)))
                qty = min(-vol, desired)

                if qty > 0:
                    orders.append(Order(symbol, ask, qty))
                    bought += qty

        if allow_sell:
            for bid, vol in sorted(depth.buy_orders.items(), reverse=True):
                edge = bid - fair
                if edge < edge_thr:
                    break

                cap = min(POSITION_LIMITS[symbol] + pos - sold, max_take - sold)
                if cap <= 0:
                    break

                desired = int(min(cap, max(1, edge // max(edge_thr, 1.0) * 5)))
                qty = min(vol, desired)

                if qty > 0:
                    orders.append(Order(symbol, bid, -qty))
                    sold += qty

        return orders

    def hedge_underlying(self, state: TradingState, S: float, T: float, sigma: float) -> List[Order]:
        depth = state.order_depths.get(UNDERLYING)
        if depth is None or not depth.buy_orders or not depth.sell_orders:
            return []

        best_bid, best_ask = best_bid_ask(depth)
        if best_bid is None or best_ask is None:
            return []

        if best_ask - best_bid > 8:
            return []

        option_delta_exposure = 0.0

        for symbol, K in VEV_STRIKES.items():
            pos = get_pos(state, symbol)
            if pos == 0:
                continue
            option_delta_exposure += pos * bs_delta(S, K, T, sigma)

        current_under_pos = get_pos(state, UNDERLYING)
        target_under_pos = int(round(-option_delta_exposure))
        target_under_pos = max(
            -POSITION_LIMITS[UNDERLYING],
            min(POSITION_LIMITS[UNDERLYING], target_under_pos),
        )

        diff = target_under_pos - current_under_pos

        if abs(diff) < 8:
            return []

        orders: List[Order] = []

        if diff > 0:
            qty = min(diff, MAX_HEDGE_PER_TICK, POSITION_LIMITS[UNDERLYING] - current_under_pos)
            if qty > 0:
                px = min(best_bid + 1, best_ask - 1)
                orders.append(Order(UNDERLYING, px, qty))

        elif diff < 0:
            qty = min(-diff, MAX_HEDGE_PER_TICK, POSITION_LIMITS[UNDERLYING] + current_under_pos)
            if qty > 0:
                px = max(best_ask - 1, best_bid + 1)
                orders.append(Order(UNDERLYING, px, -qty))

        return orders

    def opportunistic_underlying_mm(self, state: TradingState) -> List[Order]:
        depth = state.order_depths.get(UNDERLYING)
        if depth is None or not depth.buy_orders or not depth.sell_orders:
            return []

        m = mid_price(depth)
        if m is None:
            return []

        if self.last_S is None:
            self.last_S = m

        fair = 0.98 * self.last_S + 0.02 * m
        self.last_S = fair

        best_bid, best_ask = best_bid_ask(depth)
        if best_bid is None or best_ask is None:
            return []

        pos = get_pos(state, UNDERLYING)
        orders: List[Order] = []

        max_size = 10
        inv_skew = 4.0 * pos / max(POSITION_LIMITS[UNDERLYING], 1)

        bid_px = int(math.floor(fair - 3 - inv_skew))
        ask_px = int(math.ceil(fair + 3 - inv_skew))

        bid_px = min(max(bid_px, best_bid + 1), best_ask - 1)
        ask_px = max(min(ask_px, best_ask - 1), best_bid + 1)

        buy_cap = min(POSITION_LIMITS[UNDERLYING] - pos, max_size)
        sell_cap = min(POSITION_LIMITS[UNDERLYING] + pos, max_size)

        if buy_cap > 0 and bid_px < best_ask:
            orders.append(Order(UNDERLYING, bid_px, buy_cap))

        if sell_cap > 0 and ask_px > best_bid:
            orders.append(Order(UNDERLYING, ask_px, -sell_cap))

        return orders

    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        orders: Dict[str, List[Order]] = {}

        under_depth = state.order_depths.get(UNDERLYING)
        if under_depth is None or not under_depth.buy_orders or not under_depth.sell_orders:
            return orders

        S = mid_price(under_depth)
        if S is None:
            return orders

        T = current_tte_years(state)
        sigma = self.calibrate_sigma(state, S, T)

        for symbol in VEV_STRIKES:
            if symbol not in state.order_depths:
                continue

            option_orders = self.trade_option(state, symbol, S, T, sigma)
            if option_orders:
                orders[symbol] = option_orders

        under_orders: List[Order] = []
        under_orders.extend(self.opportunistic_underlying_mm(state))
        under_orders.extend(self.hedge_underlying(state, S, T, sigma))

        if under_orders:
            orders[UNDERLYING] = under_orders

        return orders


class Trader:
    def __init__(self) -> None:
        self.hydrogel = HydrogelStrategy()
        self.vev_chain = VEVOptionChainStrategy()

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        saved = {}

        if state.traderData:
            try:
                saved = json.loads(state.traderData)
            except Exception:
                saved = {}

        if "hydrogel" in saved:
            self.hydrogel.load_state(saved["hydrogel"])

        if "vev_chain" in saved:
            self.vev_chain.load_state(saved["vev_chain"])

        orders: Dict[str, List[Order]] = {}

        if HYDROGEL in state.order_depths:
            h_orders = self.hydrogel.run(state)
            if h_orders:
                orders[HYDROGEL] = h_orders

        vev_orders = self.vev_chain.run(state)

        for symbol, symbol_orders in vev_orders.items():
            if symbol_orders:
                orders.setdefault(symbol, []).extend(symbol_orders)

        trader_data = json.dumps({
            "hydrogel": self.hydrogel.save_state(),
            "vev_chain": self.vev_chain.save_state(),
        })

        return orders, 0, trader_data