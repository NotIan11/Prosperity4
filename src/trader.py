"""IMC Prosperity 4 R3 trader — modular baseline.

Goods side (HYDROGEL_PACK + VELVETFRUIT_EXTRACT):
  - HYDROGEL: passive market-make at wall_mid +/- half_edge with position skew.
    Independent product, lag-1 autocorr -0.13, median spread 16.
  - VELVETFRUIT_EXTRACT: passive market-make, tighter (median spread 5).
    Note: options team may be hedging through this book; coordinate.

Vouchers (VEV_*): not traded here. Options team owns these. Plug their
strategy classes into Trader.__init__ and they'll be invoked per tick.
"""
from typing import Any

try:
    from datamodel import Order, OrderDepth, TradingState  # IMC platform
except ImportError:
    from prosperity3bt.datamodel import Order, OrderDepth, TradingState  # local bt


POSITION_LIMITS = {
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
}


def wall_mid(depth: OrderDepth) -> float | None:
    """Frankfurt-style fair-price proxy: midpoint of the deepest level on each
    side (largest visible size), not best bid/ask. Falls back to top-of-book
    midpoint, then None if either side is empty."""
    if not depth.buy_orders or not depth.sell_orders:
        return None
    deep_bid = max(depth.buy_orders, key=lambda p: depth.buy_orders[p])
    deep_ask = min(depth.sell_orders, key=lambda p: -depth.sell_orders[p])
    return (deep_bid + deep_ask) / 2.0


class PassiveMarketMaker:
    """Quote bid/ask at fair +/- half_edge with linear position skew."""

    def __init__(self, symbol: str, position_limit: int,
                 half_edge: int, skew_per_unit: float = 0.05) -> None:
        self.symbol = symbol
        self.position_limit = position_limit
        self.half_edge = half_edge
        self.skew_per_unit = skew_per_unit  # ticks per unit of inventory

    def run(self, state: TradingState) -> list[Order]:
        depth = state.order_depths.get(self.symbol)
        if depth is None:
            return []
        fair = wall_mid(depth)
        if fair is None:
            return []
        position = state.position.get(self.symbol, 0)
        skew = self.skew_per_unit * position
        bid_px = int(round(fair - self.half_edge - skew))
        ask_px = int(round(fair + self.half_edge - skew))
        # Don't cross the market.
        best_ask = min(depth.sell_orders) if depth.sell_orders else ask_px + 1
        best_bid = max(depth.buy_orders) if depth.buy_orders else bid_px - 1
        bid_px = min(bid_px, best_ask - 1)
        ask_px = max(ask_px, best_bid + 1)
        bid_size = self.position_limit - position
        ask_size = self.position_limit + position
        orders: list[Order] = []
        if bid_size > 0:
            orders.append(Order(self.symbol, bid_px, bid_size))
        if ask_size > 0:
            orders.append(Order(self.symbol, ask_px, -ask_size))
        return orders


class Trader:
    def __init__(self) -> None:
        # Goods strategies (this PR's scope).
        # half_edge tuned to historical median spreads:
        # HYDROGEL median spread 16 -> half_edge 8.
        # VELVETFRUIT median spread 5 -> half_edge 2 (tighter, careful with options hedging flow).
        self.strategies = {
            "HYDROGEL_PACK": PassiveMarketMaker(
                "HYDROGEL_PACK", POSITION_LIMITS["HYDROGEL_PACK"],
                half_edge=8, skew_per_unit=0.04,
            ),
            "VELVETFRUIT_EXTRACT": PassiveMarketMaker(
                "VELVETFRUIT_EXTRACT", POSITION_LIMITS["VELVETFRUIT_EXTRACT"],
                half_edge=2, skew_per_unit=0.04,
            ),
            # Voucher strategies plug in here from the options team.
        }

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        orders: dict[str, list[Order]] = {}
        for symbol, strategy in self.strategies.items():
            result = strategy.run(state)
            if result:
                orders[symbol] = result
        return orders, 0, ""
