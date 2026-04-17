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


FAIR_VALUE = 10_000


class OsmiumStrategy(Strategy):
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
            orders.append(Order(self.symbol, FAIR_VALUE - 1, passive_buy_cap))
        if passive_sell_cap > 0:
            orders.append(Order(self.symbol, FAIR_VALUE + 1, -passive_sell_cap))

        return orders


class MeanReversionStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        position_limit: int,
        window: int = 2,
        spread: int = 1,
        order_size: int = 15,
        soft_limit_frac: float = 0.5,
    ) -> None:
        super().__init__(symbol, position_limit)
        self.window = window
        self.spread = spread
        self.order_size = order_size
        self.soft_limit = int(position_limit * soft_limit_frac)
        self._alpha = 2.0 / (window + 1)
        self._ewm: float | None = None

    def _update_ewm(self, mid: float) -> float:
        if self._ewm is None:
            self._ewm = mid
        else:
            self._ewm = self._alpha * mid + (1 - self._alpha) * self._ewm
        return self._ewm

    def run(self, state: TradingState) -> List[Order]:
        order_depth: OrderDepth = state.order_depths.get(self.symbol)
        if order_depth is None:
            return []

        best_bid = max(order_depth.buy_orders.keys(), default=None)
        best_ask = min(order_depth.sell_orders.keys(), default=None)
        if best_bid is None or best_ask is None:
            return []

        mid = (best_bid + best_ask) / 2.0
        fair_value = self._update_ewm(mid)

        actual_pos = self.get_position(state)
        orders: List[Order] = []
        buys_submitted = 0
        sells_submitted = 0

        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price > fair_value - self.spread:
                break
            remaining = self.position_limit - actual_pos - buys_submitted
            if remaining <= 0:
                break
            qty = min(-order_depth.sell_orders[ask_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                buys_submitted += qty

        for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
            if bid_price < fair_value + self.spread:
                break
            remaining = self.position_limit + actual_pos - sells_submitted
            if remaining <= 0:
                break
            qty = min(order_depth.buy_orders[bid_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, bid_price, -qty))
                sells_submitted += qty

        skew = round(self.spread * actual_pos / max(self.soft_limit, 1))
        skew = max(-self.spread, min(self.spread, skew))

        bid_price = round(fair_value) - self.spread + skew
        ask_price = round(fair_value) + self.spread + skew

        passive_buy_cap = self.position_limit - actual_pos - buys_submitted
        passive_sell_cap = self.position_limit + actual_pos - sells_submitted

        if passive_buy_cap > 0 and actual_pos < self.soft_limit:
            orders.append(Order(self.symbol, bid_price, min(self.order_size, passive_buy_cap)))
        if passive_sell_cap > 0 and actual_pos > -self.soft_limit:
            orders.append(Order(self.symbol, ask_price, -min(self.order_size, passive_sell_cap)))

        return orders


PRODUCTS = {
    "ASH_COATED_OSMIUM": OsmiumStrategy("ASH_COATED_OSMIUM", position_limit=80),
    "INTARIAN_PEPPER_ROOT": MeanReversionStrategy(
        "INTARIAN_PEPPER_ROOT",
        position_limit=80,
        window=2,
        spread=1,
        order_size=15,
        soft_limit_frac=0.5,
    ),
}


class Trader:
    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        orders: Dict[str, List[Order]] = {}

        for symbol, strategy in PRODUCTS.items():
            if symbol in state.order_depths:
                orders[symbol] = strategy.run(state)

        return orders, 0, ""
