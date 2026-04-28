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

    Layer 1 — Fixed-FV mean-reversion takes (backtester-visible):
      Buy aggressively when ask < FV - TAKE_EDGE (price genuinely below fair).
      Sell aggressively when bid > FV + TAKE_EDGE (price genuinely above fair).
      Capped at ±ER_CAP to always reserve headroom for Layer 2.
      Uses fixed FV=10000 (empirically stable across all days) rather than EMA,
      which tracks trends too closely and suppresses signal on low-volatility days.

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

    # Fixed fair value (stable structural price confirmed across all round 4 days)
    FV: float = 10_000.0

    # Layer 1 parameters
    TAKE_EDGE: float = 8.0    # min overshot from FV to take aggressively
    MAX_TAKE: int = 20         # max units per aggressive-take tick
    ER_CAP: int = 150          # position hard cap for Layer 1; keeps 50 free for Layer 2

    # Layer 2 parameters
    MAX_M38: int = 25          # max units per Mark 38 passive intercept
    M38_CAP: int = 75          # max net position held from M38 reactive trades;
                               # prevents unlimited inventory buildup if M38 trends

    # Layer 2b parameters
    IMBAL_THR: float = 0.15    # book imbalance threshold to trigger pre-positioning

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)

    def save_state(self) -> dict:
        return {}

    def load_state(self, data: dict) -> None:
        pass

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        pos = self.get_position(state)
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid = (best_bid + best_ask) / 2.0

        orders: List[Order] = []
        bought = 0
        sold = 0

        # --- Layer 1: Fixed-FV mean-reversion aggressive takes ---
        # Buy when ask is cheap relative to FV
        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price >= self.FV - self.TAKE_EDGE:
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

        # Sell when bid is rich relative to FV
        for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
            if bid_price <= self.FV + self.TAKE_EDGE:
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
    ENTRY_THR: float = 20.0
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
    Deep-ITM options overlay using VELVETFRUIT_EXTRACT as the signal.

    VEV_4000 and VEV_4500 are effectively deterministic intrinsic-value
    instruments, so we trade them like high-delta copies of the underlying:
    when S deviates from FV, take a max option position in the direction of
    reversion.

    The signal (S deviation) is read from the VELVETFRUIT book each tick, not
    from this instrument's own price. Stop-loss is triggered if the underlying
    moves STOP_LOSS_TICKS adverse to the entry direction.
    """

    UNDERLYING: str = "VELVETFRUIT_EXTRACT"
    FV: float = 5_250.0
    ENTRY_THR: float = 20.0
    STOP_LOSS_TICKS: float = 40.0

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)
        self.entry_underlying: Optional[float] = None

    def save_state(self) -> dict:
        return {"entry_underlying": self.entry_underlying}

    def load_state(self, data: dict) -> None:
        self.entry_underlying = data.get("entry_underlying")

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
        dev = S - self.FV

        orders: List[Order] = []

        # Stop-loss: close if underlying moved STOP_LOSS_TICKS adverse to position.
        if self.entry_underlying is not None and pos != 0:
            adverse = (self.entry_underlying - S) if pos > 0 else (S - self.entry_underlying)
            if adverse > self.STOP_LOSS_TICKS:
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
                self.entry_underlying = None
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
                self.entry_underlying = S

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
                self.entry_underlying = S

        elif pos == 0:
            self.entry_underlying = None

        return orders


class ThetaVevOptionStrategy(Strategy):
    """
    Theta-aware overlay for VEV_5000 through VEV_5500.

    EDA across ROUND_4 day 1-3 shows these calls follow a Black-Scholes-like
    surface with strike-specific total variance decaying nearly linearly over
    time. We infer the current theta index from the live 5k option chain, then
    trade only when the expected value after VELVETFRUIT reverts to FV clears
    the visible quote.
    """

    UNDERLYING: str = "VELVETFRUIT_EXTRACT"
    FV: float = 5_250.0
    ENTRY_THR: float = 20.0
    STOP_LOSS_TICKS: float = 40.0
    ENTRY_EDGE: float = 2.0
    REVERSION_HORIZON: float = 0.25
    DAY_LENGTH: float = 1_000_000.0
    FALLBACK_DAY_INDEX: float = 3.0
    MIN_THETA_INDEX: float = -0.25
    MAX_THETA_INDEX: float = 4.50

    # total_variance ~= a + b * theta_index, where theta_index is
    # (day - 1) + timestamp / 1e6 on the ROUND_4 training tape.
    VAR_COEFFS: Dict[int, Tuple[float, float]] = {
        5000: (0.0011206788457359161, -0.00015824138133374227),
        5100: (0.0010903804696246555, -0.0001616643962962236),
        5200: (0.001151763945024528, -0.00017547383934247876),
        5300: (0.0011763323905580251, -0.00017303804841345947),
        5400: (0.0010082975435693454, -0.00013787824948602418),
        5500: (0.001213051992308349, -0.00018713971640792188),
    }

    _cached_timestamp: Optional[int] = None
    _cached_theta_index: Optional[float] = None

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)
        self.strike = int(symbol.split("_")[1])
        self.entry_underlying: Optional[float] = None

    def save_state(self) -> dict:
        return {"entry_underlying": self.entry_underlying}

    def load_state(self, data: dict) -> None:
        self.entry_underlying = data.get("entry_underlying")

    @staticmethod
    def normal_cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    @classmethod
    def bs_call(cls, spot: float, strike: int, variance: float) -> float:
        if variance <= 0:
            return max(spot - strike, 0.0)
        total_vol = math.sqrt(variance)
        d1 = (math.log(spot / strike) + 0.5 * variance) / total_vol
        d2 = d1 - total_vol
        return spot * cls.normal_cdf(d1) - strike * cls.normal_cdf(d2)

    @classmethod
    def variance_for(cls, strike: int, theta_index: float) -> float:
        a, b = cls.VAR_COEFFS[strike]
        return max(a + b * theta_index, 0.0)

    @classmethod
    def fair_value(cls, spot: float, strike: int, theta_index: float) -> float:
        return cls.bs_call(spot, strike, cls.variance_for(strike, theta_index))

    @classmethod
    def implied_variance(cls, spot: float, strike: int, option_mid: float) -> float:
        intrinsic = max(spot - strike, 0.0)
        if option_mid <= intrinsic:
            return 0.0

        low = 0.0
        high = 0.0064  # total vol up to 8%, comfortably above observed range.
        for _ in range(32):
            mid = (low + high) / 2.0
            if cls.bs_call(spot, strike, mid) < option_mid:
                low = mid
            else:
                high = mid
        return (low + high) / 2.0

    @classmethod
    def estimate_theta_index(cls, state: TradingState, spot: float) -> float:
        timestamp = getattr(state, "timestamp", 0)
        if cls._cached_timestamp == timestamp and cls._cached_theta_index is not None:
            return cls._cached_theta_index

        estimates: List[float] = []
        for strike, (a, b) in cls.VAR_COEFFS.items():
            depth = state.order_depths.get(f"VEV_{strike}")
            if depth is None or not depth.buy_orders or not depth.sell_orders:
                continue
            best_bid = max(depth.buy_orders.keys())
            best_ask = min(depth.sell_orders.keys())
            option_mid = (best_bid + best_ask) / 2.0
            variance = cls.implied_variance(spot, strike, option_mid)
            if b != 0:
                estimates.append((variance - a) / b)

        if estimates:
            estimates.sort()
            mid = len(estimates) // 2
            if len(estimates) % 2:
                theta_index = estimates[mid]
            else:
                theta_index = (estimates[mid - 1] + estimates[mid]) / 2.0
        else:
            theta_index = cls.FALLBACK_DAY_INDEX + timestamp / cls.DAY_LENGTH

        theta_index = max(cls.MIN_THETA_INDEX, min(cls.MAX_THETA_INDEX, theta_index))
        cls._cached_timestamp = timestamp
        cls._cached_theta_index = theta_index
        return theta_index

    def close_position(self, order_depth: OrderDepth, pos: int) -> List[Order]:
        orders: List[Order] = []
        if pos > 0:
            sold = 0
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                remaining = pos - sold
                if remaining <= 0:
                    break
                qty = min(order_depth.buy_orders[bid_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, bid_price, -qty))
                    sold += qty
        elif pos < 0:
            bought = 0
            for ask_price in sorted(order_depth.sell_orders.keys()):
                remaining = -pos - bought
                if remaining <= 0:
                    break
                qty = min(-order_depth.sell_orders[ask_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, ask_price, qty))
                    bought += qty
        return orders

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
        spot = (und_bid + und_ask) / 2.0
        dev = spot - self.FV

        if self.entry_underlying is not None and pos != 0:
            adverse = (self.entry_underlying - spot) if pos > 0 else (spot - self.entry_underlying)
            if adverse > self.STOP_LOSS_TICKS:
                self.entry_underlying = None
                return self.close_position(order_depth, pos)

        theta_index = self.estimate_theta_index(state, spot)
        target_index = theta_index + self.REVERSION_HORIZON
        target_value = self.fair_value(self.FV, self.strike, target_index)
        orders: List[Order] = []

        if dev < -self.ENTRY_THR and pos < self.position_limit:
            buys = 0
            for ask_price in sorted(order_depth.sell_orders.keys()):
                if target_value - ask_price <= self.ENTRY_EDGE:
                    continue
                remaining = self.position_limit - pos - buys
                if remaining <= 0:
                    break
                qty = min(-order_depth.sell_orders[ask_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, ask_price, qty))
                    buys += qty
            if buys > 0:
                self.entry_underlying = spot

        elif dev > self.ENTRY_THR and pos > -self.position_limit:
            sells = 0
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                if bid_price - target_value <= self.ENTRY_EDGE:
                    continue
                remaining = self.position_limit + pos - sells
                if remaining <= 0:
                    break
                qty = min(order_depth.buy_orders[bid_price], remaining)
                if qty > 0:
                    orders.append(Order(self.symbol, bid_price, -qty))
                    sells += qty
            if sells > 0:
                self.entry_underlying = spot

        elif pos == 0:
            self.entry_underlying = None

        return orders


PRODUCTS = {
    "ASH_COATED_OSMIUM": OsmiumStrategy("ASH_COATED_OSMIUM", position_limit=80),
    "INTARIAN_PEPPER_ROOT": PepperStrategy("INTARIAN_PEPPER_ROOT", position_limit=80),
    "HYDROGEL_PACK": HydrogelStrategy("HYDROGEL_PACK", position_limit=200),
    "VELVETFRUIT_EXTRACT": VelvetfruitStrategy("VELVETFRUIT_EXTRACT", position_limit=200),
    "VEV_4000": VevOptionStrategy("VEV_4000", position_limit=300),
    "VEV_4500": VevOptionStrategy("VEV_4500", position_limit=300),
    "VEV_5000": ThetaVevOptionStrategy("VEV_5000", position_limit=300),
    "VEV_5100": ThetaVevOptionStrategy("VEV_5100", position_limit=300),
    "VEV_5200": ThetaVevOptionStrategy("VEV_5200", position_limit=300),
    "VEV_5300": ThetaVevOptionStrategy("VEV_5300", position_limit=300),
    "VEV_5400": ThetaVevOptionStrategy("VEV_5400", position_limit=300),
    "VEV_5500": ThetaVevOptionStrategy("VEV_5500", position_limit=300),
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