from typing import List, Optional

from src.datamodel import Order, OrderDepth, TradingState
from src.strategies.base import Strategy


class MeanReversionStrategy(Strategy):
    """
    Dynamic fair value market-making for trending/volatile products (INTARIAN_PEPPER_ROOT).

    Fair value = EWM of mid prices over `window` ticks (adapts to drifting price level).
    Strategy:
      1. Take any sell orders priced at or below fair_value - spread (edge ≥ spread ticks).
      2. Take any buy orders priced at or above fair_value + spread.
      3. Post passive quotes with inventory skew to encourage mean-reversion to flat.

    Capacity is tracked gross (buys and sells separately) to avoid the
    backtester's limit check: current_pos + sum(buys) > limit → all rejected.
    """

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
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None:
            return []

        best_bid = max(order_depth.buy_orders.keys(), default=None)
        best_ask = min(order_depth.sell_orders.keys(), default=None)
        if best_bid is None or best_ask is None:
            return []

        # --- Calculate walls (deepest liquidity) ---
        bid_wall = min(order_depth.buy_orders.keys()) if order_depth.buy_orders else best_bid
        ask_wall = max(order_depth.sell_orders.keys()) if order_depth.sell_orders else best_ask

        mid = (best_bid + best_ask) / 2.0
        fair_value = self._update_ewm(mid)

        actual_pos = self.get_position(state)
        orders: List[Order] = []
        buys_submitted = 0
        sells_submitted = 0

        # --- Take mispriced sell orders (ask ≤ FV - spread) ---
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

        # --- Take mispriced buy orders (bid ≥ FV + spread) ---
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

        # --- Passive quotes with inventory skew and remaining gross capacity ---
        # Post inside the walls where real liquidity sits, with skew for inventory management
        skew = round(self.spread * actual_pos / max(self.soft_limit, 1))
        skew = max(-self.spread, min(self.spread, skew))

        bid_price = bid_wall + 1 + skew
        ask_price = ask_wall - 1 + skew

        passive_buy_cap = self.position_limit - actual_pos - buys_submitted
        passive_sell_cap = self.position_limit + actual_pos - sells_submitted

        # Suppress passive quote on the overweight side to avoid compounding directional exposure
        if passive_buy_cap > 0 and actual_pos < self.soft_limit:
            orders.append(Order(self.symbol, bid_price, min(self.order_size, passive_buy_cap)))
        if passive_sell_cap > 0 and actual_pos > -self.soft_limit:
            orders.append(Order(self.symbol, ask_price, -min(self.order_size, passive_sell_cap)))

        return orders
