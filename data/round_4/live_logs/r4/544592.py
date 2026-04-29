import json
import math
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


PRODUCTS = {
    "ASH_COATED_OSMIUM": OsmiumStrategy("ASH_COATED_OSMIUM", position_limit=80),
    "INTARIAN_PEPPER_ROOT": PepperStrategy("INTARIAN_PEPPER_ROOT", position_limit=80),
    "HYDROGEL_PACK": HydrogelStrategy("HYDROGEL_PACK", position_limit=200),
    "VELVETFRUIT_EXTRACT": VelvetfruitStrategy("VELVETFRUIT_EXTRACT", position_limit=200),
    "VEV_4000": VevOptionStrategy("VEV_4000", position_limit=300),
    "VEV_4500": VevOptionStrategy("VEV_4500", position_limit=300),
    "VEV_5000": VevOptionStrategy("VEV_5000", position_limit=300),
    "VEV_5100": VevOptionStrategy("VEV_5100", position_limit=300),
    "VEV_5200": VevOptionStrategy("VEV_5200", position_limit=300),
    "VEV_5300": VevOptionStrategy("VEV_5300", position_limit=300),
    "VEV_5400": VevOptionStrategy("VEV_5400", position_limit=300),
    "VEV_5500": VevOptionStrategy("VEV_5500", position_limit=300),
}


class Trader:
    def bid(self) -> int:
        # GTO Market Access Fee bid.
        #
        # Final simulation is 1 day, so V = incremental value for one day of extra access.
        # Extra access = 25% more quotes (testing uses 80%; full access = 100%).
        # Incremental value per day:
        #   - Osmium:  ~19,773/day × 0.25 ≈ 4,943  (fills scale linearly with flow)
        #   - Pepper:  ~79,262/day × 0.05 ≈ 3,963  (conservative; mostly position-limited)
        #   - Total V  ≈ 8,906 per day
        #
        # Mechanism: top 50% of bids win + pay their bid. Only need to beat the median.
        # Nash equilibrium (uniform bids on [0,V]): bid V/2 ≈ 4,453.
        # Bidding slightly above GTO (~V*0.56) to protect against a low-skewed distribution.
        # Bidding above V is dominated (pay more than you gain).
        return 4750

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

        state_dict = {s: strat.save_state() for s, strat in PRODUCTS.items()}
        trader_data = json.dumps(state_dict)

        return orders, 0, trader_data