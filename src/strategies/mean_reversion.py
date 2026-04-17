from typing import List

from datamodel import Order, OrderDepth, TradingState
from strategies.base import Strategy


class MeanReversionStrategy(Strategy):
    """
    Simple market-making strategy around a rolling mid-price fair value.

    Places passive bids/asks a fixed spread away from fair value.
    Skews quotes toward flat inventory when position builds up.
    """

    def __init__(
        self,
        symbol: str,
        position_limit: int,
        window: int = 50,
        spread: int = 2,
        order_size: int = 10,
    ) -> None:
        super().__init__(symbol, position_limit)
        self.window = window
        self.spread = spread
        self.order_size = order_size
        self._price_history: List[float] = []

    def run(self, state: TradingState) -> List[Order]:
        order_depth: OrderDepth = state.order_depths.get(self.symbol)
        if order_depth is None:
            return []

        # Compute mid price from best bid/ask
        best_bid = max(order_depth.buy_orders.keys(), default=None)
        best_ask = min(order_depth.sell_orders.keys(), default=None)
        if best_bid is None or best_ask is None:
            return []

        mid = (best_bid + best_ask) / 2
        self._price_history.append(mid)
        if len(self._price_history) > self.window:
            self._price_history.pop(0)

        fair_value = sum(self._price_history) / len(self._price_history)
        position = self.get_position(state)

        # Inventory skew: shift quotes by up to half-spread to lean against position
        skew = int(self.spread * position / self.position_limit)

        bid_price = round(fair_value - self.spread + skew)
        ask_price = round(fair_value + self.spread + skew)

        orders: List[Order] = []

        buy_capacity = self.position_limit - position
        sell_capacity = self.position_limit + position

        if buy_capacity > 0:
            orders.append(Order(self.symbol, bid_price, min(self.order_size, buy_capacity)))

        if sell_capacity > 0:
            orders.append(Order(self.symbol, ask_price, -min(self.order_size, sell_capacity)))

        return orders
