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


# Signal: 1 = bullish (buy at daily low), -1 = bearish (sell at daily high), 0 = neutral
LONG, NEUTRAL, SHORT = 1, 0, -1


class ExtremeSignalTracker:
    """
    Detects informed-trader-like behavior by watching for trades at daily
    price extremes. Inspired by Frankfurt Hedgehogs' Prosperity 3 strategy.

    Tracks running daily min/max of mid prices. When a market trade occurs
    at or near a new extreme in the expected direction (buy at low, sell at
    high), flags a directional signal. False positives are managed by
    invalidating signals when new contradicting extremes form.
    """

    def __init__(self, threshold_ticks: int = 2) -> None:
        self.threshold = threshold_ticks  # how close to extreme counts as "at extreme"
        self.daily_low: Optional[float] = None
        self.daily_high: Optional[float] = None
        self.signal: int = NEUTRAL
        self.signal_ts: int = 0  # timestamp of last signal

    def save_state(self) -> dict:
        return {
            "daily_low": self.daily_low,
            "daily_high": self.daily_high,
            "signal": self.signal,
            "signal_ts": self.signal_ts,
        }

    def load_state(self, data: dict) -> None:
        self.daily_low = data.get("daily_low")
        self.daily_high = data.get("daily_high")
        self.signal = data.get("signal", NEUTRAL)
        self.signal_ts = data.get("signal_ts", 0)

    def update(self, state: TradingState, symbol: str) -> int:
        """Update tracker with latest state. Returns current signal."""
        order_depth = state.order_depths.get(symbol)
        if not order_depth or not order_depth.buy_orders or not order_depth.sell_orders:
            return self.signal

        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid = (best_bid + best_ask) / 2.0

        # Update running daily extremes
        if self.daily_low is None or mid < self.daily_low:
            self.daily_low = mid
            # New low invalidates a previous bullish signal
            if self.signal == LONG:
                self.signal = NEUTRAL
        if self.daily_high is None or mid > self.daily_high:
            self.daily_high = mid
            # New high invalidates a previous bearish signal
            if self.signal == SHORT:
                self.signal = NEUTRAL

        # Scan market trades for informed-like behavior
        for trade in state.market_trades.get(symbol, []):
            # Skip our own trades
            if trade.buyer == "SUBMISSION" or trade.seller == "SUBMISSION":
                continue

            # Infer trade direction: price >= mid → buy-initiated, < mid → sell-initiated
            is_buy = trade.price >= mid

            # Buy near daily low → bullish signal
            if is_buy and self.daily_low is not None:
                if trade.price <= self.daily_low + self.threshold:
                    self.signal = LONG
                    self.signal_ts = state.timestamp

            # Sell near daily high → bearish signal
            if not is_buy and self.daily_high is not None:
                if trade.price >= self.daily_high - self.threshold:
                    self.signal = SHORT
                    self.signal_ts = state.timestamp

        return self.signal


FAIR_VALUE = 10_000


class OsmiumStrategy(Strategy):
    def __init__(self, symbol: str, position_limit: int, spread: int = 1) -> None:
        super().__init__(symbol, position_limit)
        self.spread = spread

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None:
            return []

        actual_pos = self.get_position(state)
        orders: List[Order] = []
        buys_submitted = 0
        sells_submitted = 0

        # --- Calculate best bid/ask and walls ---
        best_bid = max(order_depth.buy_orders.keys(), default=None)
        best_ask = min(order_depth.sell_orders.keys(), default=None)
        bid_wall = min(order_depth.buy_orders.keys()) if order_depth.buy_orders else best_bid
        ask_wall = max(order_depth.sell_orders.keys()) if order_depth.sell_orders else best_ask

        # --- Dynamic wall offset: if walls are too deep, adjust back toward best bid/ask ---
        buy_wall_offset = 1
        sell_wall_offset = 1
        if best_bid is not None and bid_wall is not None:
            wall_distance = best_bid - bid_wall
            if wall_distance > 10:  # Wall is too deep
                buy_wall_offset = max(1, wall_distance // 5)
        if best_ask is not None and ask_wall is not None:
            wall_distance = ask_wall - best_ask
            if wall_distance > 10:
                sell_wall_offset = max(1, wall_distance // 5)

        # Wall mid as dynamic reference for taking (2nd place approach)
        wall_mid = None
        if bid_wall is not None and ask_wall is not None:
            wall_mid = (bid_wall + ask_wall) / 2.0

        for ask_price in sorted(order_depth.sell_orders.keys()):
            take_ref = (wall_mid - 1) if wall_mid is not None else FAIR_VALUE
            if ask_price > take_ref:
                # At wall_mid exactly, only buy to unwind short position
                if wall_mid is not None and ask_price <= wall_mid and actual_pos + buys_submitted < 0:
                    remaining = min(-order_depth.sell_orders[ask_price],
                                    min(abs(actual_pos + buys_submitted),
                                        self.position_limit - actual_pos - buys_submitted))
                    if remaining > 0:
                        orders.append(Order(self.symbol, ask_price, remaining))
                        buys_submitted += remaining
                break
            remaining = self.position_limit - actual_pos - buys_submitted
            if remaining <= 0:
                break
            qty = min(-order_depth.sell_orders[ask_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                buys_submitted += qty

        for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
            take_ref = (wall_mid + 1) if wall_mid is not None else FAIR_VALUE
            if bid_price < take_ref:
                # At wall_mid exactly, only sell to unwind long position
                if wall_mid is not None and bid_price >= wall_mid and actual_pos - sells_submitted > 0:
                    remaining = min(order_depth.buy_orders[bid_price],
                                    min(actual_pos - sells_submitted,
                                        self.position_limit + actual_pos - sells_submitted))
                    if remaining > 0:
                        orders.append(Order(self.symbol, bid_price, -remaining))
                        sells_submitted += remaining
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

        # Wall mid as dynamic fair value reference (2nd place approach)
        wall_mid = None
        if bid_wall is not None and ask_wall is not None:
            wall_mid = (bid_wall + ask_wall) / 2.0

        # Post inside the walls with overbidding/penny-ing (outbid best orders in book)
        if passive_buy_cap > 0:
            buy_price = bid_wall + buy_wall_offset if bid_wall is not None else FAIR_VALUE - self.spread
            # Overbid: find best bid below wall_mid and outbid it
            if wall_mid is not None:
                for bp in sorted(order_depth.buy_orders.keys(), reverse=True):
                    overbid = bp + 1
                    if order_depth.buy_orders[bp] > 1 and overbid < wall_mid:
                        buy_price = max(buy_price, overbid)
                        break
                    elif bp < wall_mid:
                        buy_price = max(buy_price, bp)
                        break
            orders.append(Order(self.symbol, buy_price, passive_buy_cap))
        if passive_sell_cap > 0:
            sell_price = ask_wall - sell_wall_offset if ask_wall is not None else FAIR_VALUE + self.spread
            # Underbid: find best ask above wall_mid and underbid it
            if wall_mid is not None:
                for sp in sorted(order_depth.sell_orders.keys()):
                    underbid = sp - 1
                    if abs(order_depth.sell_orders[sp]) > 1 and underbid > wall_mid:
                        sell_price = min(sell_price, underbid)
                        break
                    elif sp > wall_mid:
                        sell_price = min(sell_price, sp)
                        break
            orders.append(Order(self.symbol, sell_price, -passive_sell_cap))

        return orders


class TrendBiasedMMStrategy(Strategy):
    """
    Market-making for INTARIAN_PEPPER_ROOT anchored to best_bid+1 / best_ask-1
    (inside the real ~13-tick spread) with a trend-biased inventory target.

    Trend is computed from a 25-step linear slope of mid prices + rolling
    signed market-trade flow. When trending up, inventory target shifts long
    (up to +70) so we systematically build exposure in the direction of drift.
    EWM state and trend history persist across Lambda invocations via traderData.
    """

    def __init__(self, symbol: str, position_limit: int, order_size: int = 15) -> None:
        super().__init__(symbol, position_limit)
        self.order_size = order_size
        self._mids: list = []
        self._flows: list = []
        self._signal_tracker = ExtremeSignalTracker(threshold_ticks=2)

    def save_state(self) -> dict:
        return {
            "mids": self._mids,
            "flows": self._flows,
            "signal": self._signal_tracker.save_state(),
        }

    def load_state(self, data: dict) -> None:
        self._mids = data.get("mids", [])
        self._flows = data.get("flows", [])
        if "signal" in data:
            self._signal_tracker.load_state(data["signal"])

    def _trend_score(self) -> float:
        n = min(25, len(self._mids))
        if n < 5:
            return 0.0
        ys = self._mids[-n:]
        mx = (n - 1) / 2.0
        my = sum(ys) / n
        num = sum((i - mx) * (ys[i] - my) for i in range(n))
        den = sum((i - mx) ** 2 for i in range(n)) or 1.0
        slope = num / den  # ticks per step
        flow_sum = sum(self._flows[-20:])
        return slope * 5.0 + flow_sum * 0.01

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None:
            return []

        best_bid = max(order_depth.buy_orders.keys(), default=None)
        best_ask = min(order_depth.sell_orders.keys(), default=None)
        if best_bid is None or best_ask is None:
            return []

        mid = (best_bid + best_ask) / 2.0

        # Signed market trade flow: positive = buy-initiated (bullish)
        signed = 0
        for t in state.market_trades.get(self.symbol, []):
            signed += t.quantity if t.price >= mid else -t.quantity

        self._mids.append(mid)
        self._mids = self._mids[-60:]
        self._flows.append(signed)
        self._flows = self._flows[-60:]

        trend = self._trend_score()
        informed_signal = self._signal_tracker.update(state, self.symbol)
        actual_pos = self.get_position(state)
        orders: List[Order] = []
        buys_submitted = 0
        sells_submitted = 0

        # Informed signal adjustment: shift caps when signal detected
        signal_adj = 0
        if informed_signal == LONG:
            signal_adj = 20  # Bias toward long
        elif informed_signal == SHORT:
            signal_adj = -20  # Bias toward short

        # Inventory caps: allow larger long when trending up or signal is bullish
        long_cap = int(min(self.position_limit, max(40, 40 + trend * 15 + signal_adj)))
        short_cap = int(min(self.position_limit, max(10, 20 - trend * 10 - signal_adj)))

        # Aggressive lift: take the best ask when trend is strong
        if trend > 1.0:
            for ask_price in sorted(order_depth.sell_orders.keys()):
                if ask_price > best_ask:
                    break
                remaining = self.position_limit - actual_pos - buys_submitted
                if remaining <= 0:
                    break
                qty = min(-order_depth.sell_orders[ask_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, ask_price, qty))
                    buys_submitted += qty

        # Passive quotes anchored to walls (deepest liquidity) instead of best bid/ask
        bid_wall = min(order_depth.buy_orders.keys()) if order_depth.buy_orders else best_bid
        ask_wall = max(order_depth.sell_orders.keys()) if order_depth.sell_orders else best_ask
        
        # Dynamic wall offset: if walls are too deep, adjust back toward best bid/ask
        buy_wall_offset = 1
        sell_wall_offset = 1
        if best_bid is not None and bid_wall is not None:
            wall_distance = best_bid - bid_wall
            if wall_distance > 10:  # Wall is too deep
                buy_wall_offset = max(1, wall_distance // 5)
        if best_ask is not None and ask_wall is not None:
            wall_distance = ask_wall - best_ask
            if wall_distance > 10:
                sell_wall_offset = max(1, wall_distance // 5)
        
        quote_bid = bid_wall + buy_wall_offset
        quote_ask = ask_wall - sell_wall_offset
        if quote_ask <= quote_bid:
            quote_bid = best_bid
            quote_ask = best_ask

        passive_buy_cap = self.position_limit - actual_pos - buys_submitted
        passive_sell_cap = self.position_limit + actual_pos - sells_submitted

        # Scale bid size up when trending up, ask size up when trending down
        bid_size = int(self.order_size * (1.0 + max(0.0, min(1.0, trend * 0.5))))
        ask_size = int(self.order_size * (1.0 + max(0.0, min(1.0, -trend * 0.5))))

        # Be more aggressive (post larger sizes) at cold start when we're still learning
        if len(self._mids) < 10:
            bid_size = int(passive_buy_cap * 0.5) if passive_buy_cap > 0 else 0
            ask_size = int(passive_sell_cap * 0.5) if passive_sell_cap > 0 else 0
            quote_bid = best_bid + 1  # Post closer to market at cold start
            quote_ask = best_ask - 1

        if passive_buy_cap > 0 and actual_pos < long_cap:
            orders.append(Order(self.symbol, quote_bid, min(bid_size, passive_buy_cap)))
        if passive_sell_cap > 0 and actual_pos > -short_cap:
            orders.append(Order(self.symbol, quote_ask, -min(ask_size, passive_sell_cap)))

        return orders


PRODUCTS = {
    "ASH_COATED_OSMIUM": OsmiumStrategy("ASH_COATED_OSMIUM", position_limit=80, spread=3),
    "INTARIAN_PEPPER_ROOT": TrendBiasedMMStrategy(
        "INTARIAN_PEPPER_ROOT",
        position_limit=80,
        order_size=15,
    ),
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
