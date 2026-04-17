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
    def run(self, state: TradingState) -> List[Order]:
        order_depth: OrderDepth = state.order_depths.get(self.symbol)
        if order_depth is None:
            return []

        actual_pos = self.get_position(state)
        orders: List[Order] = []
        buys_submitted = 0
        sells_submitted = 0

        best_bid = max(order_depth.buy_orders.keys(), default=None)
        best_ask = min(order_depth.sell_orders.keys(), default=None)
        bid_wall = min(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
        ask_wall = max(order_depth.sell_orders.keys()) if order_depth.sell_orders else None

        # Wall mid tracks where the market maker's book is centered
        wall_mid = (bid_wall + ask_wall) / 2.0 if bid_wall is not None and ask_wall is not None else float(FAIR_VALUE)

        buy_ref = wall_mid - 1
        sell_ref = wall_mid + 1

        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price > buy_ref:
                # At wall_mid, only buy to unwind a short
                if ask_price <= wall_mid and actual_pos + buys_submitted < 0:
                    qty = min(-order_depth.sell_orders[ask_price],
                              min(abs(actual_pos + buys_submitted),
                                  self.position_limit - actual_pos - buys_submitted))
                    if qty > 0:
                        orders.append(Order(self.symbol, ask_price, qty))
                        buys_submitted += qty
                break
            remaining = self.position_limit - actual_pos - buys_submitted
            if remaining <= 0:
                break
            qty = min(-order_depth.sell_orders[ask_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                buys_submitted += qty

        for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
            if bid_price < sell_ref:
                # At wall_mid, only sell to unwind a long
                if bid_price >= wall_mid and actual_pos - sells_submitted > 0:
                    qty = min(order_depth.buy_orders[bid_price],
                              min(actual_pos - sells_submitted,
                                  self.position_limit + actual_pos - sells_submitted))
                    if qty > 0:
                        orders.append(Order(self.symbol, bid_price, -qty))
                        sells_submitted += qty
                break
            remaining = self.position_limit + actual_pos - sells_submitted
            if remaining <= 0:
                break
            qty = min(order_depth.buy_orders[bid_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, bid_price, -qty))
                sells_submitted += qty

        # Ladder passive quotes: split across two levels to capture different takers
        # Tight level (±2): catches aggressive takers who cross close to wall_mid
        # Deep level (±5): catches takers who only cross further from mid (like our old pennying)
        passive_buy_cap = self.position_limit - actual_pos - buys_submitted
        passive_sell_cap = self.position_limit + actual_pos - sells_submitted

        wm = int(wall_mid)
        tight_buy = wm - 2
        deep_buy  = wm - 5
        tight_ask = wm + 2
        deep_ask  = wm + 5

        # Clamp inside walls
        if bid_wall is not None:
            tight_buy = max(tight_buy, int(bid_wall) + 1)
            deep_buy  = max(deep_buy,  int(bid_wall) + 1)
        if ask_wall is not None:
            tight_ask = min(tight_ask, int(ask_wall) - 1)
            deep_ask  = min(deep_ask,  int(ask_wall) - 1)

        if passive_buy_cap > 0:
            half = passive_buy_cap // 2
            rest = passive_buy_cap - half
            if tight_buy != deep_buy:
                orders.append(Order(self.symbol, tight_buy, half))
                orders.append(Order(self.symbol, deep_buy,  rest))
            else:
                orders.append(Order(self.symbol, tight_buy, passive_buy_cap))

        if passive_sell_cap > 0:
            half = passive_sell_cap // 2
            rest = passive_sell_cap - half
            if tight_ask != deep_ask:
                orders.append(Order(self.symbol, tight_ask, -half))
                orders.append(Order(self.symbol, deep_ask,  -rest))
            else:
                orders.append(Order(self.symbol, tight_ask, -passive_sell_cap))

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
    "ASH_COATED_OSMIUM": OsmiumStrategy("ASH_COATED_OSMIUM", position_limit=80),
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

        state_out = {s: strat.save_state() for s, strat in PRODUCTS.items()}

        # Log observations on first tick so we can inspect them in the portal
        if state.timestamp == 0:
            try:
                obs = {
                    "plain": dict(state.observations.plainValueObservations),
                    "conversion": {k: vars(v) for k, v in state.observations.conversionObservations.items()},
                }
                state_out["_obs"] = obs
            except Exception:
                pass

        trader_data = json.dumps(state_out)

        return orders, 0, trader_data
