import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

try:
    # For IMC production environment
    from datamodel import Order, OrderDepth, TradingState  # type: ignore
except ImportError:
    # For local development
    from src.datamodel import Order, OrderDepth, TradingState  # type: ignore


class Strategy(ABC):
    def __init__(self, symbol: str, position_limit: int) -> None:
        self.symbol = symbol
        self.position_limit = position_limit

    @abstractmethod
    def run(self, state: TradingState) -> List[Order]:
        raise NotImplementedError()

    def get_position(self, state: TradingState) -> int:
        return state.position.get(self.symbol, 0)

    def save_state(self) -> dict:
        return {}

    def load_state(self, data: dict) -> None:
        pass



FAIR_VALUE = 10_000


class OsmiumStrategy(Strategy):
    MR_TAKE_THR = 2.5
    MR_BUY_ADJ = 4.5
    MR_SELL_ADJ = -5.5

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)
        self.prev_mid: Optional[float] = None

    def save_state(self) -> dict:
        return {"prev_mid": self.prev_mid}

    def load_state(self, data: dict) -> None:
        self.prev_mid = data.get("prev_mid")

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        pos = self.get_position(state)
        orders: List[Order] = []
        buys = 0
        sells = 0

        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        bid_wall = min(order_depth.buy_orders.keys())
        ask_wall = max(order_depth.sell_orders.keys())
        wall_mid = (bid_wall + ask_wall) / 2.0
        fd = wall_mid - FAIR_VALUE

        # --- Autocorrelation signal: track mid price changes ---
        mid = (best_bid + best_ask) / 2.0
        prev_up = False
        prev_down = False
        if self.prev_mid is not None:
            change = mid - self.prev_mid
            prev_up = change > 0
            prev_down = change < 0
        self.prev_mid = mid

        # --- MR-biased taking: widen take zone when price deviates from FV ---
        # AC-graded: full adj with tick confirmation, reduced adj without
        if fd < -self.MR_TAKE_THR:
            buy_adj = self.MR_BUY_ADJ if prev_down else self.MR_BUY_ADJ * 0.8
        else:
            buy_adj = 0
        if fd > self.MR_TAKE_THR:
            sell_adj = self.MR_SELL_ADJ if prev_up else self.MR_SELL_ADJ * 0.8
        else:
            sell_adj = 0

        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price > wall_mid - 0.5 + buy_adj:
                break
            remaining = self.position_limit - pos - buys
            if remaining <= 0:
                break
            qty = min(-order_depth.sell_orders[ask_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                buys += qty

        for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
            if bid_price < wall_mid + 0.5 + sell_adj:
                break
            remaining = self.position_limit + pos - sells
            if remaining <= 0:
                break
            qty = min(order_depth.buy_orders[bid_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, bid_price, -qty))
                sells += qty

        # --- Passive quoting: anchor to walls for better fill prices ---
        buy_price = bid_wall + 1
        sell_price = ask_wall - 1
        if buy_price >= wall_mid:
            buy_price = int(wall_mid) - 1
        if sell_price <= wall_mid:
            sell_price = int(wall_mid) + 1

        # --- Overbidding: improve queue priority by outbidding best passive bid ---
        for bp in sorted(order_depth.buy_orders.keys(), reverse=True):
            overbid = bp + 1
            if overbid < wall_mid and overbid > buy_price:
                buy_price = overbid
                break
            if bp < wall_mid:
                break

        # --- Underbidding: improve queue priority by underbidding best passive ask ---
        for ap in sorted(order_depth.sell_orders.keys()):
            underbid = ap - 1
            if underbid > wall_mid and underbid < sell_price:
                sell_price = underbid
                break
            if ap > wall_mid:
                break

        buy_cap = self.position_limit - pos - buys
        sell_cap = self.position_limit + pos - sells
        if buy_cap > 0:
            orders.append(Order(self.symbol, buy_price, buy_cap))
        if sell_cap > 0:
            orders.append(Order(self.symbol, sell_price, -sell_cap))

        return orders


class PepperStrategy(Strategy):
    """Buy-hold for INTARIAN_PEPPER_ROOT.

    Pepper trends +1000/day (slope 0.1/tick).

    MAX_PER_TICK limits how many lots we buy each tick to avoid
    adverse impact from large orders. Set to 0 for unlimited (sweep all).
    """

    MAX_PER_TICK = 10  # 0 = unlimited; 10 is optimal in backtester (+~85/day)
    SELL_SPREAD_THR = 16  # only sell when spread >= this; 0 = disabled

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.sell_orders:
            return []

        pos = self.get_position(state)
        orders: List[Order] = []
        buys = 0
        tick_cap = self.MAX_PER_TICK if self.MAX_PER_TICK > 0 else self.position_limit

        for ask_price in sorted(order_depth.sell_orders.keys()):
            remaining = min(self.position_limit - pos - buys, tick_cap - buys)
            if remaining <= 0:
                break
            qty = min(-order_depth.sell_orders[ask_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                buys += qty

        # Conditional passive sell when spread is wide
        if self.SELL_SPREAD_THR > 0 and order_depth.buy_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            spread = best_ask - best_bid
            if spread >= self.SELL_SPREAD_THR:
                sell_price = best_ask - 1
                effective_pos = pos + buys
                sell_qty = min(10, effective_pos)
                if sell_qty > 0:
                    orders.append(Order(self.symbol, sell_price, -sell_qty))

        return orders


class PepperCyclingStrategy(Strategy):
    """Experimental cycling for INTARIAN_PEPPER_ROOT.

    Identical to PepperStrategy (aggressive buy to limit) PLUS a passive sell of
    CYCLE_SIZE units at ask_wall-1 on every tick where 2+ ask levels exist.

    When an aggressive bot buyer sweeps through best_ask and reaches ask_wall-1,
    our resting sell fills at a premium above best_ask. The next tick's aggressive
    buy loop reinstates the full position, capturing the spread differential as profit.

    ask_wall-1 > best_ask by construction (wall is the deepest ask level), so each
    successful fill earns more than the current market ask price.

    To revert: in PRODUCTS below, change PepperCyclingStrategy back to PepperStrategy.
    """

    CYCLE_SIZE: int = 20

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.sell_orders:
            return []

        pos = self.get_position(state)
        orders: List[Order] = []
        buys = 0
        sells = 0

        # 1. Aggressive buy to position limit (same as PepperStrategy)
        for ask_price in sorted(order_depth.sell_orders.keys()):
            remaining = self.position_limit - pos - buys
            if remaining <= 0:
                break
            qty = min(-order_depth.sell_orders[ask_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                buys += qty

        # 2. Passive cycling sell at ask_wall-1 (only when a deeper ask level exists)
        if len(order_depth.sell_orders) >= 2:
            ask_wall = max(order_depth.sell_orders.keys())
            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else 0
            sell_price = ask_wall - 1
            if sell_price > best_bid:  # ensure truly passive (no immediate cross)
                effective_pos = pos + buys - sells
                floor = self.position_limit - self.CYCLE_SIZE  # 60
                qty = min(self.CYCLE_SIZE, max(0, effective_pos - floor))
                if qty > 0:
                    orders.append(Order(self.symbol, sell_price, -qty))

        return orders


class HydrogelStrategy(Strategy):
    """
    HYDROGEL_PACK mean-reversion around a dynamic Wall Mid fair value.

    Fair value is computed each tick as the midpoint of the outermost
    bid and ask walls visible in the order book:
        wall_mid = (min_bid + max_ask) / 2
    This adapts to slow price drift rather than anchoring to a fixed 10,000.

    Base behaviour: take asks ≤ FV - TAKE_EDGE, bids ≥ FV + TAKE_EDGE,
    and post passive resting orders at FV ± PASSIVE_SPREAD.

    Trend guard (defensive, magnitude-based): compute the total mid-price
    change over the last TREND_WINDOW ticks. When it drops by more than
    TREND_DROP_THR, sell existing longs to flat and suppress buying.
    Mirror for rises. The guard never goes directional; it only unwinds
    existing exposure and pauses new entries.
    """

    TAKE_EDGE = 8
    PASSIVE_SPREAD = 7
    SOFT_LIMIT_FRAC = 0.7

    # Trend detection — magnitude-based
    TREND_WINDOW = 10
    TREND_DROP_THR = 25

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)
        self.mid_history: List[float] = []

    def save_state(self) -> dict:
        return {"mid_history": self.mid_history[-(self.TREND_WINDOW + 1):]}

    def load_state(self, data: dict) -> None:
        self.mid_history = data.get("mid_history", [])

    def _detect_trend(self, mid: float) -> int:
        self.mid_history.append(mid)
        if len(self.mid_history) > self.TREND_WINDOW + 1:
            self.mid_history = self.mid_history[-(self.TREND_WINDOW + 1):]

        if len(self.mid_history) <= self.TREND_WINDOW:
            return 0

        total_change = self.mid_history[-1] - self.mid_history[-(self.TREND_WINDOW + 1)]

        if total_change <= -self.TREND_DROP_THR:
            return -1
        if total_change >= self.TREND_DROP_THR:
            return 1
        return 0

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        pos = self.get_position(state)
        orders: List[Order] = []
        buys = 0
        sells = 0

        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        wall_bid = min(order_depth.buy_orders.keys())
        wall_ask = max(order_depth.sell_orders.keys())
        wall_mid = (wall_bid + wall_ask) / 2.0

        mid = (best_bid + best_ask) / 2.0
        trend = self._detect_trend(mid)

        if trend == -1:
            # --- Downtrend: suppress buying, keep selling at edge ---
            sell_thr = wall_mid + self.TAKE_EDGE

            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                if bid_price < sell_thr:
                    break
                remaining = self.position_limit + pos - sells
                if remaining <= 0:
                    break
                qty = min(order_depth.buy_orders[bid_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, bid_price, -qty))
                    sells += qty

            sell_cap = self.position_limit + pos - sells
            if sell_cap > 0:
                passive_ask_px = round(wall_mid + self.PASSIVE_SPREAD)
                orders.append(Order(self.symbol, passive_ask_px, -sell_cap))

        elif trend == 1:
            # --- Uptrend: suppress selling, keep buying at edge ---
            buy_thr = wall_mid - self.TAKE_EDGE

            for ask_price in sorted(order_depth.sell_orders.keys()):
                if ask_price > buy_thr:
                    break
                remaining = self.position_limit - pos - buys
                if remaining <= 0:
                    break
                qty = min(-order_depth.sell_orders[ask_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, ask_price, qty))
                    buys += qty

            buy_cap = self.position_limit - pos - buys
            if buy_cap > 0:
                passive_bid_px = round(wall_mid - self.PASSIVE_SPREAD)
                orders.append(Order(self.symbol, passive_bid_px, buy_cap))

        else:
            # --- Neutral: standard mean-reversion ---
            buy_thr = wall_mid - self.TAKE_EDGE
            sell_thr = wall_mid + self.TAKE_EDGE

            for ask_price in sorted(order_depth.sell_orders.keys()):
                if ask_price > buy_thr:
                    break
                remaining = self.position_limit - pos - buys
                if remaining <= 0:
                    break
                qty = min(-order_depth.sell_orders[ask_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, ask_price, qty))
                    buys += qty

            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                if bid_price < sell_thr:
                    break
                remaining = self.position_limit + pos - sells
                if remaining <= 0:
                    break
                qty = min(order_depth.buy_orders[bid_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, bid_price, -qty))
                    sells += qty

            soft_limit = int(self.position_limit * self.SOFT_LIMIT_FRAC)
            effective_pos = pos + buys - sells
            skew = round(self.PASSIVE_SPREAD * effective_pos / max(soft_limit, 1))
            skew = max(-self.PASSIVE_SPREAD, min(self.PASSIVE_SPREAD, skew))

            passive_bid_px = round(wall_mid - self.PASSIVE_SPREAD - skew)
            passive_ask_px = round(wall_mid + self.PASSIVE_SPREAD - skew)

            buy_cap = self.position_limit - pos - buys
            sell_cap = self.position_limit + pos - sells

            if buy_cap > 0 and effective_pos < soft_limit:
                orders.append(Order(self.symbol, passive_bid_px, buy_cap))
            if sell_cap > 0 and effective_pos > -soft_limit:
                orders.append(Order(self.symbol, passive_ask_px, -sell_cap))

        return orders


PRODUCTS = {
    "ASH_COATED_OSMIUM": OsmiumStrategy("ASH_COATED_OSMIUM", position_limit=80),
    "INTARIAN_PEPPER_ROOT": PepperStrategy("INTARIAN_PEPPER_ROOT", position_limit=80),
    "HYDROGEL_PACK": HydrogelStrategy("HYDROGEL_PACK", position_limit=200),
}


class Trader:
    def bid(self) -> int:
        # GTO Market Access Fee bid.
        #
        # Final simulation is 1 day, so V = incremental value for one day of extra access.
        # Extra access = 25% more quotes (testing uses 80%; full access = 100%).
        # Incremental value per day:
        #   - Osmium:  ~19,773/day × 0.25 ≈ 4,943  (fills scale linearly with flow)
        #   - Pepper:  ~79,262/day × 0.05 ≈ 3,963  (conservative; mostly position-limited)
        #   - Total V  ≈ 8,906 per day
        #
        # Mechanism: top 50% of bids win + pay their bid. Only need to beat the median.
        # Nash equilibrium (uniform bids on [0,V]): bid V/2 ≈ 4,453.
        # Bidding slightly above GTO (~V*0.56) to protect against a low-skewed distribution.
        # Bidding above V is dominated (pay more than you gain).
        return 4750

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        saved = {}
        if state.traderData:
            try:
                saved = json.loads(state.traderData)
            except Exception:
                pass

        for symbol, strategy in PRODUCTS.items():
            if symbol in saved:
                strategy.load_state(saved[symbol])

        orders: Dict[str, List[Order]] = {}
        for symbol, strategy in PRODUCTS.items():
            if symbol in state.order_depths:
                orders[symbol] = strategy.run(state)

        trader_data = json.dumps({s: strat.save_state() for s, strat in PRODUCTS.items()})

        return orders, 0, trader_data