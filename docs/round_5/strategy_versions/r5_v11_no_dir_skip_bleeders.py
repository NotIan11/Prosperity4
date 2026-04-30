import json
import math
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

try:
    # For IMC production environment
    from datamodel import Order, OrderDepth, TradingState  # type: ignore
except ImportError:
    # For local development
    from prosperity4bt.datamodel import Order, OrderDepth, TradingState  # type: ignore


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


VEV_STRIKES = {
    "VEV_4000": 4000,
    "VEV_4500": 4500,
    "VEV_5000": 5000,
    "VEV_5100": 5100,
    "VEV_5200": 5200,
    "VEV_5300": 5300,
    "VEV_5400": 5400,
    "VEV_5500": 5500,
    "VEV_6000": 6000,
    "VEV_6500": 6500,
}


def mid_price(depth: OrderDepth) -> Optional[float]:
    if not depth.buy_orders or not depth.sell_orders:
        return None
    return (max(depth.buy_orders) + min(depth.sell_orders)) / 2.0


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_call_price(S: float, K: float, t_days: float, sigma: float) -> float:
    if S <= 0 or K <= 0:
        return max(S - K, 0.0)

    T = max(t_days, 0.0) / 365.0
    if T <= 0.0 or sigma <= 0.0:
        return max(S - K, 0.0)

    vol_sqrt_t = sigma * math.sqrt(T)
    if vol_sqrt_t <= 0.0:
        return max(S - K, 0.0)

    d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / vol_sqrt_t
    d2 = d1 - vol_sqrt_t
    return S * norm_cdf(d1) - K * norm_cdf(d2)


def implied_tte_days(price: float, S: float, K: float, sigma: float) -> Optional[float]:
    intrinsic = max(S - K, 0.0)
    if price < intrinsic - 0.25:
        return None
    if price <= intrinsic + 0.05:
        return 0.05

    lo = 0.05
    hi = 10.0
    for _ in range(32):
        mid = (lo + hi) / 2.0
        if bs_call_price(S, K, mid, sigma) > price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0



class DirectionalStrategy(Strategy):
    """Hold max long (+1) or max short (-1) by sweeping available book levels."""

    def __init__(self, symbol: str, position_limit: int, direction: int) -> None:
        super().__init__(symbol, position_limit)
        self.direction = direction  # +1 = long, -1 = short

    def run(self, state: TradingState) -> List[Order]:
        order_depth = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        pos = self.get_position(state)
        target = self.direction * self.position_limit
        remaining = target - pos  # positive = need to buy, negative = need to sell

        if remaining == 0:
            return []

        orders: List[Order] = []
        if remaining > 0:
            for ask_price in sorted(order_depth.sell_orders.keys()):
                qty = min(remaining, -order_depth.sell_orders[ask_price])
                if qty > 0:
                    orders.append(Order(self.symbol, ask_price, qty))
                    remaining -= qty
                if remaining <= 0:
                    break
        else:
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                qty = min(-remaining, order_depth.buy_orders[bid_price])
                if qty > 0:
                    orders.append(Order(self.symbol, bid_price, -qty))
                    remaining += qty
                if remaining >= 0:
                    break

        return orders


class EntryGateStrategy(Strategy):
    """Activate a wrapped strategy after market-state confirmation."""

    def __init__(
        self,
        strategy: Strategy,
        mode: str,
        direction: int = 0,
        fast_alpha: float = 0.05,
        slow_alpha: float = 0.005,
        trend_spreads: float = 1.0,
        trigger_spreads: float = 2.0,
        settle_spreads: float = 1.0,
    ) -> None:
        super().__init__(strategy.symbol, strategy.position_limit)
        self.strategy = strategy
        self.mode = mode
        self.direction = direction
        self.fast_alpha = fast_alpha
        self.slow_alpha = slow_alpha
        self.trend_spreads = trend_spreads
        self.trigger_spreads = trigger_spreads
        self.settle_spreads = settle_spreads
        self.fast_mid: Optional[float] = None
        self.slow_mid: Optional[float] = None
        self.saw_dislocation = False
        self.active = False

    def save_state(self) -> dict:
        return {
            "fast_mid": self.fast_mid,
            "slow_mid": self.slow_mid,
            "saw_dislocation": self.saw_dislocation,
            "active": self.active,
            "wrapped": self.strategy.save_state(),
        }

    def load_state(self, data: dict) -> None:
        self.fast_mid = data.get("fast_mid")
        self.slow_mid = data.get("slow_mid")
        self.saw_dislocation = bool(data.get("saw_dislocation", False))
        self.active = bool(data.get("active", False))
        wrapped = data.get("wrapped")
        if isinstance(wrapped, dict):
            self.strategy.load_state(wrapped)
        else:
            self.strategy.load_state(data)

    def run(self, state: TradingState) -> List[Order]:
        order_depth = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        best_bid = max(order_depth.buy_orders)
        best_ask = min(order_depth.sell_orders)
        mid = (best_bid + best_ask) / 2.0
        spread = max(best_ask - best_bid, 1.0)

        if self.fast_mid is None or self.slow_mid is None:
            self.fast_mid = mid
            self.slow_mid = mid
        else:
            self.fast_mid = (1.0 - self.fast_alpha) * self.fast_mid + self.fast_alpha * mid
            self.slow_mid = (1.0 - self.slow_alpha) * self.slow_mid + self.slow_alpha * mid

        signal = self.fast_mid - self.slow_mid
        abs_signal = abs(signal)
        if abs_signal >= self.trigger_spreads * spread:
            self.saw_dislocation = True

        if not self.active:
            if self.mode == "trend":
                self.active = self.direction * signal >= self.trend_spreads * spread
            elif self.mode == "settled":
                self.active = self.saw_dislocation and abs_signal <= self.settle_spreads * spread

        if not self.active:
            return []
        return self.strategy.run(state)


class EMAMarketMaker(Strategy):
    """EMA-anchored market maker: quote inside the spread, skew by inventory,
    take aggressively when price deviates beyond take_edge from fair value."""

    def __init__(
        self,
        symbol: str,
        position_limit: int,
        ema_alpha: float = 0.02,
        take_edge: float = 80.0,
        max_take: int = 10,
        skew_per_lot: float = 0.1,
    ) -> None:
        super().__init__(symbol, position_limit)
        self.ema_alpha = ema_alpha
        self.take_edge = take_edge
        self.max_take = max_take
        self.skew_per_lot = skew_per_lot
        self.ema_mid: Optional[float] = None

    def save_state(self) -> dict:
        return {"ema_mid": self.ema_mid}

    def load_state(self, data: dict) -> None:
        self.ema_mid = data.get("ema_mid")

    def run(self, state: TradingState) -> List[Order]:
        order_depth = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        pos = self.get_position(state)
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid = (best_bid + best_ask) / 2.0

        self.ema_mid = mid if self.ema_mid is None else (
            (1.0 - self.ema_alpha) * self.ema_mid + self.ema_alpha * mid
        )
        ema = self.ema_mid

        orders: List[Order] = []
        bought = 0
        sold = 0

        # Aggressive takes on large deviations from EMA
        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price >= ema - self.take_edge:
                break
            cap = min(self.position_limit - pos - bought, self.max_take - bought)
            if cap <= 0:
                break
            qty = min(-order_depth.sell_orders[ask_price], cap)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                bought += qty

        for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
            if bid_price <= ema + self.take_edge:
                break
            cap = min(self.position_limit + pos - sold, self.max_take - sold)
            if cap <= 0:
                break
            qty = min(order_depth.buy_orders[bid_price], cap)
            if qty > 0:
                orders.append(Order(self.symbol, bid_price, -qty))
                sold += qty

        # Passive quoting inside the spread, skewed by inventory
        eff_pos = pos + bought - sold
        skew = round(-eff_pos * self.skew_per_lot)

        buy_price = best_bid + 1 + skew
        sell_price = best_ask - 1 + skew

        # Keep quotes on correct sides of mid
        buy_price = min(buy_price, int(mid) - 1)
        sell_price = max(sell_price, int(mid) + 1)

        buy_cap = self.position_limit - pos - bought
        sell_cap = self.position_limit + pos - sold

        if buy_cap > 0 and buy_price > 0:
            orders.append(Order(self.symbol, buy_price, buy_cap))
        if sell_cap > 0 and sell_price > buy_price:
            orders.append(Order(self.symbol, sell_price, -sell_cap))

        return orders


class PairTradingStrategy(Strategy):
    """Mean-revert spread of a cointegrated pair, hedged across both legs.

    leg1 + leg2 ≈ basket_constant; trade leg1 - leg2 against its mean.
    Returns a dict of orders for both legs (handled by Trader.run dispatch).
    """

    def __init__(
        self,
        leg1: str,
        leg2: str,
        position_limit: int,
        spread_mean: float,
        entry_thr: float = 400.0,
        exit_thr: float = 100.0,
    ) -> None:
        super().__init__(leg1, position_limit)
        self.leg1 = leg1
        self.leg2 = leg2
        self.spread_mean = spread_mean
        self.entry_thr = entry_thr
        self.exit_thr = exit_thr

    @staticmethod
    def _sweep(symbol: str, depth: OrderDepth, pos: int, target: int) -> List[Order]:
        remaining = target - pos
        if remaining == 0:
            return []
        orders: List[Order] = []
        if remaining > 0:
            for ask in sorted(depth.sell_orders.keys()):
                qty = min(remaining, -depth.sell_orders[ask])
                if qty > 0:
                    orders.append(Order(symbol, ask, qty))
                    remaining -= qty
                if remaining <= 0:
                    break
        else:
            for bid in sorted(depth.buy_orders.keys(), reverse=True):
                qty = min(-remaining, depth.buy_orders[bid])
                if qty > 0:
                    orders.append(Order(symbol, bid, -qty))
                    remaining += qty
                if remaining >= 0:
                    break
        return orders

    def run(self, state: TradingState):
        d1 = state.order_depths.get(self.leg1)
        d2 = state.order_depths.get(self.leg2)
        if (d1 is None or d2 is None or
                not d1.buy_orders or not d1.sell_orders or
                not d2.buy_orders or not d2.sell_orders):
            return {}

        mid1 = (max(d1.buy_orders) + min(d1.sell_orders)) / 2.0
        mid2 = (max(d2.buy_orders) + min(d2.sell_orders)) / 2.0
        dev = (mid1 - mid2) - self.spread_mean

        pos1 = state.position.get(self.leg1, 0)
        pos2 = state.position.get(self.leg2, 0)

        if dev > self.entry_thr:
            target1, target2 = -self.position_limit, +self.position_limit
        elif dev < -self.entry_thr:
            target1, target2 = +self.position_limit, -self.position_limit
        elif abs(dev) < self.exit_thr:
            target1, target2 = 0, 0
        else:
            return {}

        result: Dict[str, List[Order]] = {}
        o1 = self._sweep(self.leg1, d1, pos1, target1)
        o2 = self._sweep(self.leg2, d2, pos2, target2)
        if o1:
            result[self.leg1] = o1
        if o2:
            result[self.leg2] = o2
        return result


class OsmiumStrategy(Strategy):
    FAIR_VALUE: float = 10_000.0
    MR_TAKE_THR = 2.5
    MR_BUY_ADJ = 4.5
    MR_SELL_ADJ = -5.5

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)
        self.prev_mid: Optional[float] = None

    def save_state(self) -> dict:
        return {"prev_mid": self.prev_mid}

    def load_state(self, data: dict) -> None:
        self.prev_mid = data.get("prev_mid")

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
        fd = wall_mid - self.FAIR_VALUE

        # --- Autocorrelation signal: track mid price changes ---
        mid = (best_bid + best_ask) / 2.0
        prev_up = False
        prev_down = False
        if self.prev_mid is not None:
            change = mid - self.prev_mid
            prev_up = change > 0
            prev_down = change < 0
        self.prev_mid = mid

        # --- MR-biased taking: widen take zone when price deviates from FV ---
        # AC-graded: full adj with tick confirmation, reduced adj without
        if fd < -self.MR_TAKE_THR:
            buy_adj = self.MR_BUY_ADJ if prev_down else self.MR_BUY_ADJ * 0.8
        else:
            buy_adj = 0
        if fd > self.MR_TAKE_THR:
            sell_adj = self.MR_SELL_ADJ if prev_up else self.MR_SELL_ADJ * 0.8
        else:
            sell_adj = 0

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

        # --- Passive quoting: anchor to walls for better fill prices ---
        buy_price = bid_wall + 1
        sell_price = ask_wall - 1
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
    """Buy-hold for INTARIAN_PEPPER_ROOT.

    Pepper trends +1000/day (slope 0.1/tick).

    MAX_PER_TICK limits how many lots we buy each tick to avoid
    adverse impact from large orders. Set to 0 for unlimited (sweep all).
    """

    MAX_PER_TICK = 10  # 0 = unlimited; 10 is optimal in backtester (+~85/day)
    SELL_SPREAD_THR = 16  # only sell when spread >= this; 0 = disabled

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.sell_orders:
            return []

        pos = self.get_position(state)
        orders: List[Order] = []
        buys = 0
        tick_cap = self.MAX_PER_TICK if self.MAX_PER_TICK > 0 else self.position_limit

        for ask_price in sorted(order_depth.sell_orders.keys()):
            remaining = min(self.position_limit - pos - buys, tick_cap - buys)
            if remaining <= 0:
                break
            qty = min(-order_depth.sell_orders[ask_price], remaining)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                buys += qty

        # Conditional passive sell when spread is wide
        if self.SELL_SPREAD_THR > 0 and order_depth.buy_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            spread = best_ask - best_bid
            if spread >= self.SELL_SPREAD_THR:
                sell_price = best_ask - 1
                effective_pos = pos + buys
                sell_qty = min(10, effective_pos)
                if sell_qty > 0:
                    orders.append(Order(self.symbol, sell_price, -sell_qty))

        return orders


class HydrogelStrategy(Strategy):
    """
    Hybrid market-making for HYDROGEL_PACK.

    Market structure (Round 4):
      - Mark 14: sole passive maker, ~190 fills/day each side
      - Mark 38: sole aggressive taker, ~190 crosses/day each side, avg spread ~15.7 ticks
      - Spread always >= 7 ticks

    Layer 1 — EMA mean-reversion takes (backtester-visible):
      Buy aggressively when ask < ema - TAKE_EDGE (price genuinely below fair).
      Sell aggressively when bid > ema + TAKE_EDGE (price genuinely above fair).
      Capped at ±ER_CAP to always reserve headroom for Layer 2.

    Layer 2 — Mark 38 intercept (live only; backtester cannot model re-routing):
      When Mark 38 was buying last tick → post passive sell at best_ask-1.
      When Mark 38 was selling last tick → post passive buy at best_bid+1.
      Mark 38 always crosses best_ask/best_bid, so our inside-spread quote gets
      first priority and captures ~7+ ticks of spread per fill.

    Layer 2b — Order book imbalance pre-positioning:
      When bid volume significantly exceeds ask volume, Mark 38 is about to
      lift the thin ask side. Post sell at ask-1 to intercept before it trades.
      Symmetric for ask-heavy books. Fires even when Mark 38 hasn't traded
      yet, giving us one tick of queue priority over the reactive Layer 2.
    """

    EMA_ALPHA: float = 0.005

    # Layer 1 parameters
    TAKE_EDGE: float = 20.0
    MAX_TAKE: int = 5
    ER_CAP: int = 175

    # Layer 2 parameters
    MAX_M38: int = 25
    M38_CAP: int = 75

    # Layer 2b parameters
    IMBAL_THR: float = 0.15

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)
        self.ema_mid: Optional[float] = None

    def save_state(self) -> dict:
        return {"ema_mid": self.ema_mid}

    def load_state(self, data: dict) -> None:
        self.ema_mid = data.get("ema_mid")

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        pos = self.get_position(state)
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid = (best_bid + best_ask) / 2.0

        self.ema_mid = mid if self.ema_mid is None else (
            (1.0 - self.EMA_ALPHA) * self.ema_mid + self.EMA_ALPHA * mid
        )
        ema: float = self.ema_mid

        orders: List[Order] = []
        bought = 0
        sold = 0

        # --- Layer 1: EMA mean-reversion aggressive takes ---
        # Buy when ask is cheap relative to EMA
        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price >= ema - self.TAKE_EDGE:
                break
            eff = pos + bought - sold
            if eff >= self.ER_CAP:
                break
            cap = min(self.ER_CAP - eff, self.MAX_TAKE - bought)
            if cap <= 0:
                break
            qty = min(-order_depth.sell_orders[ask_price], cap)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                bought += qty

        # Sell when bid is rich relative to EMA
        for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
            if bid_price <= ema + self.TAKE_EDGE:
                break
            eff = pos + bought - sold
            if eff <= -self.ER_CAP:
                break
            cap = min(self.ER_CAP + eff, self.MAX_TAKE - sold)
            if cap <= 0:
                break
            qty = min(order_depth.buy_orders[bid_price], cap)
            if qty > 0:
                orders.append(Order(self.symbol, bid_price, -qty))
                sold += qty

        # --- Layer 2 + 2b: Mark 38 intercept + book imbalance ---
        recent = state.market_trades.get(self.symbol, [])
        m38_buying  = any(t.buyer  == "Mark 38" for t in recent)
        m38_selling = any(t.seller == "Mark 38" for t in recent)

        # Layer 2b: order book volume imbalance predicts Mark 38's next cross
        # direction with ~99% accuracy at the tick level. Thin asks → Mark 38
        # will lift the ask; thin bids → Mark 38 will hit the bid.
        bid_vol = sum(order_depth.buy_orders.values())
        ask_vol = sum(-v for v in order_depth.sell_orders.values())
        total_vol = bid_vol + ask_vol
        imbalance = (bid_vol - ask_vol) / total_vol if total_vol > 0 else 0.0
        imbal_sell = imbalance > self.IMBAL_THR   # thin asks → Mk38 buys
        imbal_buy  = imbalance < -self.IMBAL_THR  # thin bids → Mk38 sells

        want_sell = m38_buying or imbal_sell
        want_buy  = m38_selling or imbal_buy

        eff = pos + bought - sold

        if want_sell:
            sell_cap = min(self.MAX_M38, self.position_limit + eff)
            if sell_cap > 0:
                orders.append(Order(self.symbol, best_ask - 1, -sell_cap))

        if want_buy:
            buy_cap = min(self.MAX_M38, self.M38_CAP - eff)
            if buy_cap > 0:
                orders.append(Order(self.symbol, best_bid + 1, buy_cap))

        return orders


class VelvetfruitStrategy(Strategy):
    """
    Macro mean-reversion taking strategy for VELVETFRUIT_EXTRACT.

    VELVETFRUIT oscillates around a structural FV of 5,250 (confirmed via
    deep-ITM VEV_4000 call: C + 4000 = S exactly; 30K-tick mean = 5250.10).
    When deviation exceeds ENTRY_THR, sweep the book to take a max position.

    Stop-loss closes the position if price moves more than STOP_LOSS_TICKS
    beyond the entry price, guarding against a wrong-FV scenario.
    """

    FV: float = 5_250.0
    ENTRY_THR: float = 18.0
    STOP_LOSS_TICKS: float = 40.0

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)
        self.entry_price: Optional[float] = None

    def save_state(self) -> dict:
        return {"entry_price": self.entry_price}

    def load_state(self, data: dict) -> None:
        self.entry_price = data.get("entry_price")

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        pos = self.get_position(state)
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid = (best_bid + best_ask) / 2.0
        dev = mid - self.FV

        orders: List[Order] = []

        # Stop-loss: close losing position before it grows further
        if self.entry_price is not None and pos != 0:
            loss = (mid - self.entry_price) * pos
            if loss < -self.STOP_LOSS_TICKS * abs(pos):
                if pos > 0:
                    for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                        remaining = pos - sum(-o.quantity for o in orders)
                        if remaining <= 0:
                            break
                        qty = min(order_depth.buy_orders[bid_price], remaining)
                        if qty > 0:
                            orders.append(Order(self.symbol, bid_price, -qty))
                else:
                    for ask_price in sorted(order_depth.sell_orders.keys()):
                        remaining = -pos - sum(o.quantity for o in orders)
                        if remaining <= 0:
                            break
                        qty = min(-order_depth.sell_orders[ask_price], remaining)
                        if qty > 0:
                            orders.append(Order(self.symbol, ask_price, qty))
                self.entry_price = None
                return orders

        buys = 0
        sells = 0

        if dev < -self.ENTRY_THR and pos < self.position_limit:
            for ask_price in sorted(order_depth.sell_orders.keys()):
                remaining = self.position_limit - pos - buys
                if remaining <= 0:
                    break
                qty = min(-order_depth.sell_orders[ask_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, ask_price, qty))
                    buys += qty
            if buys > 0:
                self.entry_price = mid

        elif dev > self.ENTRY_THR and pos > -self.position_limit:
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                remaining = self.position_limit + pos - sells
                if remaining <= 0:
                    break
                qty = min(order_depth.buy_orders[bid_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, bid_price, -qty))
                    sells += qty
            if sells > 0:
                self.entry_price = mid

        elif pos == 0:
            self.entry_price = None

        return orders


class VevOptionStrategy(Strategy):
    """
    Strike-aware VEV voucher strategy.

    Round-4 evidence splits the chain into three regimes:
      - VEV_4000/4500 are deterministic intrinsic-value proxies.
      - VEV_5000-5500 are real options with visible theta decay.
      - VEV_6000/6500 are dead strikes; Mark 22 prints them at zero.

    The real-option strikes are priced with a Black-Scholes call surface. We
    infer the current time-to-expiry from the visible chain so the same code can
    run on any historical/final day without a day identifier in TradingState.
    Separately, we post passive bids in VEV_5200/5300 when VFE is deeply below
    fair, targeting Mark 22's recurring bid-side sells.
    """

    UNDERLYING: str = "VELVETFRUIT_EXTRACT"
    FV: float = 5_250.0
    ENTRY_THR: float = 18.0
    STOP_LOSS_TICKS: float = 40.0
    MARK22_BID_UNDERLYING_THR: float = 5_230.0

    # Fitted from round-4 VEV_5000-5500 surfaces when TTE is 7/6/5 days.
    OPTION_SIGMA: float = 0.241
    FALLBACK_TTE_DAYS: float = 4.0

    DEAD_STRIKES = {"VEV_6000", "VEV_6500"}
    REAL_OPTION_STRIKES = {
        "VEV_5000",
        "VEV_5100",
        "VEV_5200",
        "VEV_5300",
        "VEV_5400",
        "VEV_5500",
    }
    MARK22_PASSIVE_BID_STRIKES = {"VEV_5200", "VEV_5300"}

    EXIT_UNDERLYING_THR: float = 5_250.0
    MAX_EXIT_PER_TICK: int = 25
    MAX_PASSIVE_FAIR_PREMIUM: float = 10.0
    PASSIVE_BID_CAP = {
        "VEV_5200": 160,
        "VEV_5300": 220,
    }
    PASSIVE_BID_SIZE = {
        "VEV_5200": 20,
        "VEV_5300": 25,
    }

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)
        self.entry_underlying: Optional[float] = None

    def save_state(self) -> dict:
        return {"entry_underlying": self.entry_underlying}

    def load_state(self, data: dict) -> None:
        self.entry_underlying = data.get("entry_underlying")

    def estimate_tte_days(self, state: TradingState, S: float) -> float:
        estimates: List[float] = []
        for symbol in self.REAL_OPTION_STRIKES:
            if symbol == self.symbol:
                continue

            depth = state.order_depths.get(symbol)
            if depth is None:
                continue

            option_mid = mid_price(depth)
            if option_mid is None:
                continue

            tte = implied_tte_days(
                option_mid,
                S,
                VEV_STRIKES[symbol],
                self.OPTION_SIGMA,
            )
            if tte is not None and 0.05 <= tte <= 10.0:
                estimates.append(tte)

        if not estimates:
            intraday_decay = min(max(state.timestamp / 1_000_000.0, 0.0), 1.0)
            return max(self.FALLBACK_TTE_DAYS - intraday_decay, 0.05)

        estimates.sort()
        mid = len(estimates) // 2
        if len(estimates) % 2:
            return estimates[mid]
        return (estimates[mid - 1] + estimates[mid]) / 2.0

    def fair_value(self, state: TradingState, S: float) -> Optional[float]:
        if self.symbol in self.DEAD_STRIKES:
            return None

        K = VEV_STRIKES[self.symbol]
        if self.symbol in {"VEV_4000", "VEV_4500"}:
            return max(S - K, 0.0)

        tte_days = self.estimate_tte_days(state, S)
        return bs_call_price(S, K, tte_days, self.OPTION_SIGMA)

    def directional_reversion_orders(
        self,
        depth: OrderDepth,
        pos: int,
        S: float,
    ) -> Tuple[List[Order], int, int]:
        orders: List[Order] = []

        # Stop-loss: close if the underlying moved adverse to the entry.
        if self.entry_underlying is not None and pos != 0:
            adverse = (self.entry_underlying - S) if pos > 0 else (S - self.entry_underlying)
            if adverse > self.STOP_LOSS_TICKS:
                if pos > 0:
                    sold = 0
                    for bid_price in sorted(depth.buy_orders.keys(), reverse=True):
                        remaining = pos - sold
                        if remaining <= 0:
                            break
                        qty = min(depth.buy_orders[bid_price], remaining)
                        if qty > 0:
                            orders.append(Order(self.symbol, bid_price, -qty))
                            sold += qty
                    self.entry_underlying = None
                    return orders, 0, sold

                bought = 0
                for ask_price in sorted(depth.sell_orders.keys()):
                    remaining = -pos - bought
                    if remaining <= 0:
                        break
                    qty = min(-depth.sell_orders[ask_price], remaining)
                    if qty > 0:
                        orders.append(Order(self.symbol, ask_price, qty))
                        bought += qty
                self.entry_underlying = None
                return orders, bought, 0

        bought = 0
        sold = 0
        dev = S - self.FV

        if dev < -self.ENTRY_THR and pos < self.position_limit:
            for ask_price in sorted(depth.sell_orders.keys()):
                remaining = self.position_limit - pos - bought
                if remaining <= 0:
                    break
                qty = min(-depth.sell_orders[ask_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, ask_price, qty))
                    bought += qty
            if bought > 0:
                self.entry_underlying = S

        elif dev > self.ENTRY_THR and pos > -self.position_limit:
            for bid_price in sorted(depth.buy_orders.keys(), reverse=True):
                remaining = self.position_limit + pos - sold
                if remaining <= 0:
                    break
                qty = min(depth.buy_orders[bid_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, bid_price, -qty))
                    sold += qty
            if sold > 0:
                self.entry_underlying = S

        elif pos == 0:
            self.entry_underlying = None

        return orders, bought, sold

    def mark22_passive_bid(
        self,
        depth: OrderDepth,
        fair: float,
        S: float,
        pos_after_takes: int,
        already_bought: int,
    ) -> List[Order]:
        if self.symbol not in self.MARK22_PASSIVE_BID_STRIKES:
            return []
        if S >= self.MARK22_BID_UNDERLYING_THR:
            return []

        best_bid = max(depth.buy_orders)
        best_ask = min(depth.sell_orders)
        bid_price = best_bid + 1
        if bid_price >= best_ask:
            return []
        if bid_price > fair + self.MAX_PASSIVE_FAIR_PREMIUM:
            return []

        cap = min(
            self.PASSIVE_BID_CAP[self.symbol] - pos_after_takes,
            self.position_limit - pos_after_takes,
            self.PASSIVE_BID_SIZE[self.symbol] - already_bought,
        )
        if cap <= 0:
            return []

        return [Order(self.symbol, bid_price, cap)]

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        und_depth: Optional[OrderDepth] = state.order_depths.get(self.UNDERLYING)
        if (
            order_depth is None
            or not order_depth.buy_orders
            or not order_depth.sell_orders
            or und_depth is None
            or not und_depth.buy_orders
            or not und_depth.sell_orders
        ):
            return []

        pos = self.get_position(state)
        und_bid = max(und_depth.buy_orders.keys())
        und_ask = min(und_depth.sell_orders.keys())
        S = (und_bid + und_ask) / 2.0

        fair = self.fair_value(state, S)
        if fair is None:
            return []

        orders, bought, sold = self.directional_reversion_orders(order_depth, pos, S)
        pos_after_directional = pos + bought - sold
        orders.extend(
            self.mark22_passive_bid(order_depth, fair, S, pos_after_directional, bought)
        )
        return orders


ROUND5_GATE_FAST_ALPHA = 0.05
ROUND5_GATE_SLOW_ALPHA = 0.005
ROUND5_TREND_SPREADS = 1.0
ROUND5_SETTLE_TRIGGER_SPREADS = 2.0
ROUND5_SETTLE_SPREADS = 1.0


def trend_round5(strategy: DirectionalStrategy) -> EntryGateStrategy:
    return EntryGateStrategy(
        strategy,
        mode="trend",
        direction=strategy.direction,
        fast_alpha=ROUND5_GATE_FAST_ALPHA,
        slow_alpha=ROUND5_GATE_SLOW_ALPHA,
        trend_spreads=ROUND5_TREND_SPREADS,
        trigger_spreads=ROUND5_SETTLE_TRIGGER_SPREADS,
        settle_spreads=ROUND5_SETTLE_SPREADS,
    )


def settled_round5(strategy: Strategy) -> EntryGateStrategy:
    return EntryGateStrategy(
        strategy,
        mode="settled",
        fast_alpha=ROUND5_GATE_FAST_ALPHA,
        slow_alpha=ROUND5_GATE_SLOW_ALPHA,
        trigger_spreads=ROUND5_SETTLE_TRIGGER_SPREADS,
        settle_spreads=ROUND5_SETTLE_SPREADS,
    )


PRODUCTS = {
    # Round 5 — position limit 10 for all products

    # Spread capture / market making
    "SNACKPACK_RASPBERRY":      settled_round5(EMAMarketMaker("SNACKPACK_RASPBERRY",      10, ema_alpha=0.005, take_edge=200)),
    "TRANSLATOR_GRAPHITE_MIST": EMAMarketMaker("TRANSLATOR_GRAPHITE_MIST", 10, ema_alpha=0.005, take_edge=200, skew_per_lot=0.5),
    "GALAXY_SOUNDS_DARK_MATTER":      settled_round5(EMAMarketMaker("GALAXY_SOUNDS_DARK_MATTER",      10, ema_alpha=0.003, take_edge=150)),
    "GALAXY_SOUNDS_PLANETARY_RINGS":  settled_round5(EMAMarketMaker("GALAXY_SOUNDS_PLANETARY_RINGS",  10, ema_alpha=0.01, take_edge=10_000)),
    "GALAXY_SOUNDS_SOLAR_WINDS":      settled_round5(EMAMarketMaker("GALAXY_SOUNDS_SOLAR_WINDS",      10, ema_alpha=0.01, take_edge=200)),
    "MICROCHIP_CIRCLE":               settled_round5(EMAMarketMaker("MICROCHIP_CIRCLE",               10, ema_alpha=0.01, take_edge=10_000)),
    "OXYGEN_SHAKE_CHOCOLATE":         EMAMarketMaker("OXYGEN_SHAKE_CHOCOLATE",         10, ema_alpha=0.01, take_edge=150),
    # SKIPPED (v10 BT bleeder): "OXYGEN_SHAKE_MINT":              settled_round5(EMAMarketMaker("OXYGEN_SHAKE_MINT",              10, ema_alpha=0.01, take_edge=10_000)),
    "PEBBLES_M": EMAMarketMaker("PEBBLES_M", 10, ema_alpha=0.003, take_edge=200),
    "SLEEP_POD_NYLON":                EMAMarketMaker("SLEEP_POD_NYLON",                10, ema_alpha=0.005, take_edge=75),
    "TRANSLATOR_ECLIPSE_CHARCOAL":    EMAMarketMaker("TRANSLATOR_ECLIPSE_CHARCOAL",    10, ema_alpha=0.003, take_edge=200),
    "UV_VISOR_YELLOW":                EMAMarketMaker("UV_VISOR_YELLOW",                10, ema_alpha=0.01, take_edge=10_000),

    # Pair trading — CHOCOLATE/VANILLA cointegrated, sum locked at ~19,941 (σ=76)
    # Keyed under CHOCOLATE so dispatch fires when the leg is present; emits orders for both legs.
    "SNACKPACK_CHOCOLATE": PairTradingStrategy(
        "SNACKPACK_CHOCOLATE", "SNACKPACK_VANILLA",
        position_limit=10, spread_mean=-254.0, entry_thr=500.0, exit_thr=0.0,
    ),

    # Short-biased legs, with maker substitutions where execution beat holding
    # PEBBLES: sum locked at 50,000; XS/S/L all drift below 10,000 start
    "PEBBLES_XS": EMAMarketMaker("PEBBLES_XS", 10, ema_alpha=0.005, take_edge=150),  # drift −3962
    "PEBBLES_S":  EMAMarketMaker("PEBBLES_S", 10, ema_alpha=0.005, take_edge=150),  # drift −1934
    "PEBBLES_L":  EMAMarketMaker("PEBBLES_L", 10, ema_alpha=0.003, take_edge=50),  # drift  −874

    # MICROCHIP: OVAL/TRIANGLE/RECTANGLE all drift below 10,000
    "MICROCHIP_OVAL":      EMAMarketMaker("MICROCHIP_OVAL", 10, ema_alpha=0.005, take_edge=150),  # drift −4481
    "MICROCHIP_TRIANGLE":  EMAMarketMaker("MICROCHIP_TRIANGLE", 10, ema_alpha=0.005, take_edge=150),  # drift −2058
    "MICROCHIP_RECTANGLE": EMAMarketMaker("MICROCHIP_RECTANGLE", 10, ema_alpha=0.005, take_edge=150),  # drift −1228

    # ROBOT: IRONING/VACUUMING/LAUNDRY all drift below 10,000
    # SKIPPED (v10 BT bleeder): "ROBOT_IRONING":   EMAMarketMaker("ROBOT_IRONING", 10, ema_alpha=0.005, take_edge=150),  # drift −2170
    "ROBOT_VACUUMING": EMAMarketMaker("ROBOT_VACUUMING", 10, ema_alpha=0.005, take_edge=150),  # drift −1725
    "ROBOT_LAUNDRY":   EMAMarketMaker("ROBOT_LAUNDRY", 10, ema_alpha=0.005, take_edge=75),  # drift  −746

    # TRANSLATOR: SPACE_GRAY/ASTRO_BLACK drift below 10,000
    "TRANSLATOR_SPACE_GRAY":  EMAMarketMaker("TRANSLATOR_SPACE_GRAY", 10, ema_alpha=0.005, take_edge=150),  # drift −1571
    "TRANSLATOR_ASTRO_BLACK": EMAMarketMaker("TRANSLATOR_ASTRO_BLACK", 10, ema_alpha=0.01, take_edge=100),  # drift −1036

    # PANEL: all except 2X4 drift below 10,000
    "PANEL_4X4": EMAMarketMaker("PANEL_4X4", 10, ema_alpha=0.01, take_edge=150),  # drift −872
    "PANEL_1X4": settled_round5(EMAMarketMaker("PANEL_1X4", 10, ema_alpha=0.01, take_edge=10_000)),  # drift −772
    "PANEL_2X2": settled_round5(EMAMarketMaker("PANEL_2X2", 10, ema_alpha=0.01, take_edge=100)),  # drift −607
    # SKIPPED (v10 BT bleeder): "PANEL_1X2": EMAMarketMaker("PANEL_1X2", 10, ema_alpha=0.005, take_edge=150),  # drift −304

    # OXYGEN_SHAKE: EVENING_BREATH/MORNING_BREATH drift below 10,000
    "OXYGEN_SHAKE_EVENING_BREATH": EMAMarketMaker("OXYGEN_SHAKE_EVENING_BREATH", 10, ema_alpha=0.01, take_edge=10_000),  # drift −580
    "OXYGEN_SHAKE_MORNING_BREATH": EMAMarketMaker("OXYGEN_SHAKE_MORNING_BREATH", 10, ema_alpha=0.01, take_edge=10_000),  # drift −450

    # SNACKPACK: PISTACHIO drifts below 10,000 (changed from EMAMarketMaker to avoid bad inventory)
    "SNACKPACK_PISTACHIO": EMAMarketMaker("SNACKPACK_PISTACHIO", 10, ema_alpha=0.005, take_edge=150),  # drift −887

    # UV_VISOR
    "UV_VISOR_AMBER":  EMAMarketMaker("UV_VISOR_AMBER", 10, ema_alpha=0.005, take_edge=150),  # drift −2870
    "UV_VISOR_ORANGE": EMAMarketMaker("UV_VISOR_ORANGE", 10, ema_alpha=0.01, take_edge=200),  # drift  −660

    # Long-biased legs
    # PEBBLES_XL: largest drift in entire round
    "PEBBLES_XL": EMAMarketMaker("PEBBLES_XL", 10, ema_alpha=0.005, take_edge=150),  # drift +6068

    # MICROCHIP
    # SKIPPED (v10 BT bleeder): "MICROCHIP_SQUARE": EMAMarketMaker("MICROCHIP_SQUARE", 10, ema_alpha=0.005, take_edge=150),  # drift +3633

    # OXYGEN_SHAKE
    "OXYGEN_SHAKE_GARLIC": EMAMarketMaker("OXYGEN_SHAKE_GARLIC", 10, ema_alpha=0.005, take_edge=150),  # drift +3886

    # GALAXY_SOUNDS: BLACK_HOLES has the largest upward drift in the family
    # SKIPPED (v10 BT bleeder): "GALAXY_SOUNDS_BLACK_HOLES":  EMAMarketMaker("GALAXY_SOUNDS_BLACK_HOLES", 10, ema_alpha=0.005, take_edge=150),  # drift +3458
    # SKIPPED (v10 BT bleeder): "GALAXY_SOUNDS_SOLAR_FLAMES": EMAMarketMaker("GALAXY_SOUNDS_SOLAR_FLAMES", 10, ema_alpha=0.005, take_edge=150),  # drift  +823

    # PANEL
    "PANEL_2X4": EMAMarketMaker("PANEL_2X4", 10, ema_alpha=0.005, take_edge=150),  # drift +2354

    # SLEEP_POD: POLYESTER/SUEDE/COTTON all drift well above 10,000
    "SLEEP_POD_POLYESTER":  EMAMarketMaker("SLEEP_POD_POLYESTER", 10, ema_alpha=0.005, take_edge=150),  # drift +1970
    "SLEEP_POD_SUEDE":      EMAMarketMaker("SLEEP_POD_SUEDE", 10, ema_alpha=0.005, take_edge=150),  # drift +1800
    # SKIPPED (v10 BT bleeder): "SLEEP_POD_COTTON":     EMAMarketMaker("SLEEP_POD_COTTON", 10, ema_alpha=0.005, take_edge=150),  # drift +1414
    # SKIPPED (v10 BT bleeder): "SLEEP_POD_LAMB_WOOL":  EMAMarketMaker("SLEEP_POD_LAMB_WOOL", 10, ema_alpha=0.005, take_edge=150),  # drift  +808

    # UV_VISOR
    # SKIPPED (v10 BT bleeder): "UV_VISOR_RED":     EMAMarketMaker("UV_VISOR_RED", 10, ema_alpha=0.005, take_edge=150),  # drift +1722
    "UV_VISOR_MAGENTA": EMAMarketMaker("UV_VISOR_MAGENTA", 10, ema_alpha=0.005, take_edge=150),  # drift +1532

    # ROBOT
    # SKIPPED (v10 BT bleeder): "ROBOT_MOPPING": EMAMarketMaker("ROBOT_MOPPING", 10, ema_alpha=0.005, take_edge=150),  # drift +1588
    "ROBOT_DISHES":  EMAMarketMaker("ROBOT_DISHES", 10, ema_alpha=0.005, take_edge=150),  # drift +1200

    # TRANSLATOR
    "TRANSLATOR_VOID_BLUE": EMAMarketMaker("TRANSLATOR_VOID_BLUE", 10, ema_alpha=0.005, take_edge=150),  # drift +1564

    # SNACKPACK
    "SNACKPACK_STRAWBERRY": EMAMarketMaker("SNACKPACK_STRAWBERRY", 10, ema_alpha=0.003, take_edge=150),  # drift +902

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
            if symbol not in state.order_depths:
                continue
            result = strategy.run(state)
            if isinstance(result, dict):
                for sym, ords in result.items():
                    orders.setdefault(sym, []).extend(ords)
            else:
                orders.setdefault(symbol, []).extend(result)

        state_dict = {s: strat.save_state() for s, strat in PRODUCTS.items()}
        return orders, 0, json.dumps(state_dict)