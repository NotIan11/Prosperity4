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
    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)

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

        # --- MR-biased taking: widen take zone when price deviates from FV ---
        buy_adj = 4.5 if fd < -2.5 else 0
        sell_adj = -5.5 if fd > 2.5 else 0

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

        # --- MR quote shift: nudge quotes toward FV when price deviates ---
        mr = -1 if fd > 2.0 else (1 if fd < -2.0 else 0)

        # --- Dynamic wall offset: if wall is very deep, pull quote in toward best ---
        buy_wall_dist = best_bid - bid_wall
        sell_wall_dist = ask_wall - best_ask
        buy_offset = max(1, buy_wall_dist // 5) if buy_wall_dist > 10 else 1
        sell_offset = max(1, sell_wall_dist // 5) if sell_wall_dist > 10 else 1

        # --- Passive quoting: anchor to walls for better fill prices ---
        buy_price = bid_wall + buy_offset + mr
        sell_price = ask_wall - sell_offset + mr
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
    """Unconditional buy for INTARIAN_PEPPER_ROOT — ride the ~1000/day uptrend.

    Price trends continuously +~1000 ticks within each day. Maximising long exposure
    as early as possible and holding captures nearly the full intraday range.
    EWM market-making is counter-productive here: passive asks get swept in the uptrend
    and accumulate a costly short position.
    """

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.sell_orders:
            return []

        pos = self.get_position(state)
        orders: List[Order] = []

        for ask_price in sorted(order_depth.sell_orders.keys()):
            remaining = self.position_limit - pos
            if remaining <= 0:
                break
            qty = min(-order_depth.sell_orders[ask_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                pos += qty

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


PRODUCTS = {
    "ASH_COATED_OSMIUM": OsmiumStrategy("ASH_COATED_OSMIUM", position_limit=80),
    # To revert pepper cycling: swap PepperCyclingStrategy → PepperStrategy below
    "INTARIAN_PEPPER_ROOT": PepperCyclingStrategy("INTARIAN_PEPPER_ROOT", position_limit=80),
}


class Trader:
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