from typing import List, Optional

from src.datamodel import Order, OrderDepth, TradingState
from src.strategies.base import Strategy

FAIR_VALUE = 10_000


class OsmiumStrategy(Strategy):
    """
    ASH_COATED_OSMIUM market-making around a hardcoded fair value of 10,000.

    Fair value is stable across all observed data (mean 10000.20, std 5.35).
    Strategy:
      1. Take any available sell orders priced below fair value (free edge).
      2. Take any available buy orders priced above fair value (free edge).
      3. Post remaining capacity passively at FV-1 / FV+1.

    Capacity is tracked gross (buys and sells separately) to avoid the
    backtester's limit check: current_pos + sum(buys) > limit → all rejected.
    """

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None:
            return []

        actual_pos = self.get_position(state)
        orders: List[Order] = []
        buys_submitted = 0
        sells_submitted = 0

        # --- Calculate walls (deepest liquidity) ---
        bid_wall = min(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
        ask_wall = max(order_depth.sell_orders.keys()) if order_depth.sell_orders else None

        # --- Take mispriced sell orders (ask < FV → buy cheap) ---
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

        # --- Take mispriced buy orders (bid > FV → sell expensive) ---
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

        # --- Passive orders with remaining gross capacity, posted at walls ---
        passive_buy_cap = self.position_limit - actual_pos - buys_submitted
        passive_sell_cap = self.position_limit + actual_pos - sells_submitted

        # Post inside the walls where real liquidity sits
        if passive_buy_cap > 0:
            buy_price = bid_wall + 1 if bid_wall is not None else FAIR_VALUE - 1
            orders.append(Order(self.symbol, buy_price, passive_buy_cap))
        if passive_sell_cap > 0:
            sell_price = ask_wall - 1 if ask_wall is not None else FAIR_VALUE + 1
            orders.append(Order(self.symbol, sell_price, -passive_sell_cap))

        return orders
