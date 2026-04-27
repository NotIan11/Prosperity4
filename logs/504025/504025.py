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
    Hydrogel strategy ported from Lennon's implementation.

    Uses a layered approach instead of bang-bang:
    - Small position increments (MAX_TAKE per tick) rather than sweeping to max
    - Passive market-making orders around FV (inventory-skewed)
    - Three dynamic derisking triggers (no hard stop-loss by price level):
        1. VERY_RICH_MID: price spiked far above FV → take profit aggressively
        2. Trailing drawdown: peak_while_long - mid >= TRAILING_DRAWDOWN → start selling
        3. EMA break: mid < ema - EMA_BREAK after a rich peak → sell cautiously
    - block_new_buys guard prevents adding longs when price is already elevated

    This trades lower peak PnL for much smaller givebacks on adverse moves.
    """

    FAIR: float = 9_991.0
    TAKE_EDGE: float = 18.0
    PASSIVE_EDGE: float = 20.0
    MAX_TAKE: int = 25
    MAX_PASSIVE: int = 25
    MAX_DERISK_PER_TICK: int = 40

    EMA_ALPHA: float = 0.015
    RICH_MID: float = FAIR + 35       # 10_026
    VERY_RICH_MID: float = FAIR + 55  # 10_046
    TRAILING_DRAWDOWN: float = 22.0
    EMA_BREAK: float = 18.0

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)
        self.ema_mid: Optional[float] = None
        self.peak_mid_while_long: Optional[float] = None

    def save_state(self) -> dict:
        return {
            "ema_mid": self.ema_mid,
            "peak_mid_while_long": self.peak_mid_while_long,
        }

    def load_state(self, data: dict) -> None:
        self.ema_mid = data.get("ema_mid")
        self.peak_mid_while_long = data.get("peak_mid_while_long")

    def _update_state(self, mid: float, pos: int) -> None:
        self.ema_mid = mid if self.ema_mid is None else (
            (1.0 - self.EMA_ALPHA) * self.ema_mid + self.EMA_ALPHA * mid
        )
        if pos > 0:
            self.peak_mid_while_long = mid if self.peak_mid_while_long is None else max(
                self.peak_mid_while_long, mid
            )
        else:
            self.peak_mid_while_long = mid

    def _should_derisk(self, mid: float, pos: int) -> bool:
        if pos <= 0:
            return False
        ema = self.ema_mid if self.ema_mid is not None else mid
        peak = self.peak_mid_while_long if self.peak_mid_while_long is not None else mid
        return (
            mid >= self.VERY_RICH_MID
            or (peak - mid >= self.TRAILING_DRAWDOWN and mid > self.FAIR + 5)
            or (mid < ema - self.EMA_BREAK and peak > self.RICH_MID)
        )

    def _should_block_new_buys(self, mid: float, pos: int) -> bool:
        ema = self.ema_mid if self.ema_mid is not None else mid
        peak = self.peak_mid_while_long if self.peak_mid_while_long is not None else mid
        if mid >= self.RICH_MID:
            return True
        if pos > 0 and peak - mid >= self.TRAILING_DRAWDOWN:
            return True
        if pos > 0 and mid < ema - self.EMA_BREAK:
            return True
        return False

    def run(self, state: TradingState) -> List[Order]:
        order_depth: Optional[OrderDepth] = state.order_depths.get(self.symbol)
        if order_depth is None or not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        pos = self.get_position(state)
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid = (best_bid + best_ask) / 2.0

        self._update_state(mid, pos)

        orders: List[Order] = []
        bought = 0
        sold = 0

        # Dynamic derisking: sell into bids when trailing drawdown or EMA break fires
        if self._should_derisk(mid, pos):
            ema = self.ema_mid if self.ema_mid is not None else mid
            peak = self.peak_mid_while_long if self.peak_mid_while_long is not None else mid
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                if sold >= self.MAX_DERISK_PER_TICK:
                    break
                if mid >= self.VERY_RICH_MID:
                    min_bid = self.FAIR + 25
                elif peak - mid >= self.TRAILING_DRAWDOWN:
                    min_bid = self.FAIR + 8
                elif mid < ema - self.EMA_BREAK:
                    min_bid = self.FAIR
                else:
                    min_bid = self.FAIR + self.TAKE_EDGE
                if bid_price < min_bid:
                    break
                remaining = pos - sold
                if remaining <= 0:
                    break
                qty = min(order_depth.buy_orders[bid_price], remaining, self.MAX_DERISK_PER_TICK - sold)
                if qty > 0:
                    orders.append(Order(self.symbol, bid_price, -qty))
                    sold += qty

        block_new_buys = self._should_block_new_buys(mid, pos)

        # Aggressive takes on cheap asks
        if not block_new_buys:
            for ask_price in sorted(order_depth.sell_orders.keys()):
                if ask_price > self.FAIR - self.TAKE_EDGE:
                    break
                cap = min(self.position_limit - pos - bought, self.MAX_TAKE - bought)
                if cap <= 0:
                    break
                qty = min(-order_depth.sell_orders[ask_price], cap)
                if qty > 0:
                    orders.append(Order(self.symbol, ask_price, qty))
                    bought += qty

        # Aggressive takes on rich bids
        for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
            if bid_price < self.FAIR + self.TAKE_EDGE:
                break
            cap = min(self.position_limit + pos - sold, self.MAX_TAKE - sold)
            if cap <= 0:
                break
            qty = min(order_depth.buy_orders[bid_price], cap)
            if qty > 0:
                orders.append(Order(self.symbol, bid_price, -qty))
                sold += qty

        # Passive market-making: undercut Mark 14 (the sole maker) by 1 tick on
        # each side so Mark 38 (the sole taker) hits us before Mark 14.
        # Inventory skew adjusts both prices toward fair value, but is capped so
        # it can never push our bid ABOVE best_bid+1 or our ask ABOVE best_ask-1
        # (which would mean retreating behind Mark 14 on the sell side).
        effective_pos = pos + bought - sold
        inv_skew = int(round(8 * effective_pos / max(self.position_limit, 1)))
        bid_px = min(best_bid + 1, best_bid + 1 - inv_skew)   # skew only moves bid DOWN
        ask_px = min(best_ask - 1, best_ask - 1 - inv_skew)   # skew only moves ask DOWN

        buy_cap  = min(self.position_limit - pos - bought,  self.MAX_PASSIVE)
        sell_cap = min(self.position_limit + pos - sold,    self.MAX_PASSIVE)

        if not block_new_buys and buy_cap > 0:
            orders.append(Order(self.symbol, bid_px, buy_cap))
        if sell_cap > 0:
            orders.append(Order(self.symbol, ask_px, -sell_cap))

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
    # VELVETFRUIT std ≈ 15 ticks. Entry at 20 ticks (~1.3σ from FV).
    # Stop at 40 ticks beyond entry means total 60 ticks from FV (~4σ) — very extreme.
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
    Options overlay using the VELVETFRUIT_EXTRACT price as the signal.

    VEV_XXXX are European call options on VELVETFRUIT_EXTRACT priced by the
    BOT via a no-theta BS surface (option price is a deterministic function of
    S only, confirmed empirically). This means we can trade them exactly like
    the underlying: when S deviates from FV, take a max option position in the
    direction of reversion.

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