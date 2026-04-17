import json
from abc import ABC, abstractmethod
from typing import Dict, List

from datamodel import Order, OrderDepth, TradingState


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
    def __init__(self, symbol: str, position_limit: int, spread: int = 1) -> None:
        super().__init__(symbol, position_limit)
        self.spread = spread

    def run(self, state: TradingState) -> List[Order]:
        order_depth: OrderDepth = state.order_depths.get(self.symbol)
        if order_depth is None:
            return []

        actual_pos = self.get_position(state)
        orders: List[Order] = []
        buys_submitted = 0
        sells_submitted = 0

        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price >= FAIR_VALUE:
                break
            remaining = self.position_limit - actual_pos - buys_submitted
            if remaining <= 0:
                break
            qty = min(-order_depth.sell_orders[ask_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                buys_submitted += qty

        for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
            if bid_price <= FAIR_VALUE:
                break
            remaining = self.position_limit + actual_pos - sells_submitted
            if remaining <= 0:
                break
            qty = min(order_depth.buy_orders[bid_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, bid_price, -qty))
                sells_submitted += qty

        passive_buy_cap = self.position_limit - actual_pos - buys_submitted
        passive_sell_cap = self.position_limit + actual_pos - sells_submitted

        if passive_buy_cap > 0:
            orders.append(Order(self.symbol, FAIR_VALUE - self.spread, passive_buy_cap))
        if passive_sell_cap > 0:
            orders.append(Order(self.symbol, FAIR_VALUE + self.spread, -passive_sell_cap))

        return orders


class IPRDirectionalStrategy(Strategy):
    """
    IPR price is deterministic: FV(ts) = day_start + ts * 0.001 (RMSE ≈ 2 ticks).
    Carry is +1000 ticks/day on 80 units; ask premium is only ~6-8 ticks.
    Optimal: stay max long the entire session by aggressively taking all asks.
    Never sell — any sell forgoes carry worth hundreds of ticks per unit.
    """

    def run(self, state: TradingState) -> List[Order]:
        order_depth: OrderDepth = state.order_depths.get(self.symbol)
        if order_depth is None:
            return []

        pos = self.get_position(state)
        orders: List[Order] = []
        buys = 0

        for ask_price in sorted(order_depth.sell_orders.keys()):
            remaining = self.position_limit - pos - buys
            if remaining <= 0:
                break
            qty = min(-order_depth.sell_orders[ask_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                buys += qty

        return orders


PRODUCTS = {
    "ASH_COATED_OSMIUM": OsmiumStrategy("ASH_COATED_OSMIUM", position_limit=80, spread=3),
    "INTARIAN_PEPPER_ROOT": IPRDirectionalStrategy("INTARIAN_PEPPER_ROOT", position_limit=80),
}


class Trader:
    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
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
