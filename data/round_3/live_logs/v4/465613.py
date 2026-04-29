"""IMC Prosperity 4 R3 trader — modular baseline.

Goods side (HYDROGEL_PACK + VELVETFRUIT_EXTRACT):
  - HYDROGEL: passive market-make at wall_mid +/- half_edge with position skew.
    Independent product, lag-1 autocorr -0.13, median spread 16.
  - VELVETFRUIT_EXTRACT: passive market-make, tighter (median spread 5).
    Asymmetric edges (bid=2/ask=3) defend against informed buy-aggressor
    (07_bot_trades.md: +0.63/50t drift, t=+2.64). Plus L1-L2 skew bias
    (10_iacobus_l1_l2_signal.md): when L1 is much narrower than L2, lean long.

Vouchers (VEV_*): not traded here.
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


def l1_l2_diff(depth: OrderDepth) -> int | None:
    """L1 spread minus L2 spread. Negative = L1 narrower than L2."""
    bids = sorted(depth.buy_orders.keys(), reverse=True)
    asks = sorted(depth.sell_orders.keys())
    if len(bids) < 2 or len(asks) < 2:
        return None
    return (asks[0] - bids[0]) - (asks[1] - bids[1])


class PassiveMarketMaker:
    """Quote bid/ask at fair +/- edges with linear position skew + optional
    L1-L2 skew (signed shift applied equally to both bid and ask)."""

    def __init__(self, symbol: str, position_limit: int,
                 half_edge: int, skew_per_unit: float = 0.05,
                 bid_edge: int | None = None, ask_edge: int | None = None,
                 use_l1l2: bool = False, l1l2_threshold: int = -3,
                 l1l2_skew: int = 1) -> None:
        self.symbol = symbol
        self.position_limit = position_limit
        self.bid_edge = bid_edge if bid_edge is not None else half_edge
        self.ask_edge = ask_edge if ask_edge is not None else half_edge
        self.skew_per_unit = skew_per_unit
        self.use_l1l2 = use_l1l2
        self.l1l2_threshold = l1l2_threshold
        self.l1l2_skew = l1l2_skew

    def _l1l2_shift(self, depth: OrderDepth) -> float:
        if not self.use_l1l2:
            return 0.0
        diff = l1_l2_diff(depth)
        if diff is not None and diff <= self.l1l2_threshold:
            return float(self.l1l2_skew)
        return 0.0

    def run(self, state: TradingState) -> list[Order]:
        depth = state.order_depths.get(self.symbol)
        if depth is None:
            return []
        fair = wall_mid(depth)
        if fair is None:
            return []
        position = state.position.get(self.symbol, 0)
        inv_skew = self.skew_per_unit * position
        flow_shift = self._l1l2_shift(depth)
        bid_px = int(round(fair - self.bid_edge - inv_skew + flow_shift))
        ask_px = int(round(fair + self.ask_edge - inv_skew + flow_shift))
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
        self.strategies = {
            "HYDROGEL_PACK": PassiveMarketMaker(
                "HYDROGEL_PACK", POSITION_LIMITS["HYDROGEL_PACK"],
                half_edge=8, skew_per_unit=0.04,
            ),
            "VELVETFRUIT_EXTRACT": PassiveMarketMaker(
                "VELVETFRUIT_EXTRACT", POSITION_LIMITS["VELVETFRUIT_EXTRACT"],
                half_edge=2, skew_per_unit=0.04,
                bid_edge=2, ask_edge=3,            # v2 asymmetric defense
                use_l1l2=True,                     # v4 L1-L2 skew
                l1l2_threshold=-3, l1l2_skew=1,
            ),
        }

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        orders: dict[str, list[Order]] = {}
        for symbol, strategy in self.strategies.items():
            result = strategy.run(state)
            if result:
                orders[symbol] = result
        return orders, 0, ""