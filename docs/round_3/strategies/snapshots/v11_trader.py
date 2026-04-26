"""IMC Prosperity 4 R3 trader.

v8: HYDROGEL takemaker (ported from Ian).
v9: VFE mean-reversion taker with ROLLING FV (regime-aware).
v10: Voucher delta-1 taker on VFE deviation, with STRIKE-AWARE caps
    (16_regime_patterns.md: empirical delta is 0.65/0.58/0.44/0.27 for
    5000/5100/5200/5300 — NOT uniform 1.0 like Ian assumes).
    Trade only high-R² strikes (5000/5100/5200/5300). Skip 5400/5500
    (signal too weak), skip 4000/4500 (R² < 0.36).
"""
from collections import deque
from typing import Any

try:
    from datamodel import Order, OrderDepth, TradingState  # IMC platform
except ImportError:
    from prosperity3bt.datamodel import Order, OrderDepth, TradingState  # local bt


POSITION_LIMITS = {
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
    "VEV_5000": 300,
    "VEV_5100": 300,
    "VEV_5200": 300,
    "VEV_5300": 300,
}

# Empirical delta vs VFE (from 30k-tick OLS regression, regime EDA #16).
# Used to size positions for equal VFE-equivalent exposure across strikes.
VOUCHER_DELTA = {
    "VEV_5000": 0.654,
    "VEV_5100": 0.577,
    "VEV_5200": 0.437,
    "VEV_5300": 0.273,
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
                 l1l2_skew: int = 1,
                 soft_pos_cap: int | None = None) -> None:
        self.symbol = symbol
        self.position_limit = position_limit
        self.soft_pos_cap = soft_pos_cap  # if set, stop adding when |pos| reaches this
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
        if self.soft_pos_cap is not None:
            if position >= self.soft_pos_cap:
                bid_size = 0
            elif position <= -self.soft_pos_cap:
                ask_size = 0
        orders: list[Order] = []
        if bid_size > 0:
            orders.append(Order(self.symbol, bid_px, bid_size))
        if ask_size > 0:
            orders.append(Order(self.symbol, ask_px, -ask_size))
        return orders


class HydrogelTakeMaker:
    """Ported from Ian's HG strategy. Take aggressively when far from FAIR,
    passive MM at wider edges, derisk longs via trailing drawdown / EMA break."""

    FAIR: float = 9991.0
    TAKE_EDGE: float = 18.0
    PASSIVE_EDGE: float = 20.0
    MAX_TAKE: int = 25
    MAX_PASSIVE: int = 25
    MAX_DERISK_PER_TICK: int = 40
    EMA_ALPHA: float = 0.015
    RICH_MID: float = FAIR + 35
    VERY_RICH_MID: float = FAIR + 55
    TRAILING_DRAWDOWN: float = 22.0
    EMA_BREAK: float = 18.0

    def __init__(self, symbol: str, position_limit: int,
                 soft_pos_cap: int | None = None) -> None:
        self.symbol = symbol
        self.position_limit = position_limit
        self.soft_pos_cap = soft_pos_cap
        self.ema_mid: float | None = None
        self.peak_mid_while_long: float | None = None

    def _update_state(self, mid: float, pos: int) -> None:
        self.ema_mid = mid if self.ema_mid is None else (
            (1.0 - self.EMA_ALPHA) * self.ema_mid + self.EMA_ALPHA * mid)
        if pos > 0:
            self.peak_mid_while_long = mid if self.peak_mid_while_long is None else max(
                self.peak_mid_while_long, mid)
        else:
            self.peak_mid_while_long = mid

    def _should_derisk(self, mid: float, pos: int) -> bool:
        if pos <= 0:
            return False
        ema = self.ema_mid if self.ema_mid is not None else mid
        peak = self.peak_mid_while_long if self.peak_mid_while_long is not None else mid
        return (mid >= self.VERY_RICH_MID
                or (peak - mid >= self.TRAILING_DRAWDOWN and mid > self.FAIR + 5)
                or (mid < ema - self.EMA_BREAK and peak > self.RICH_MID))

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

    def run(self, state: TradingState) -> list[Order]:
        depth = state.order_depths.get(self.symbol)
        if depth is None or not depth.buy_orders or not depth.sell_orders:
            return []
        pos = state.position.get(self.symbol, 0)
        best_bid = max(depth.buy_orders)
        best_ask = min(depth.sell_orders)
        mid = (best_bid + best_ask) / 2.0
        self._update_state(mid, pos)
        orders: list[Order] = []
        bought = sold = 0
        if self._should_derisk(mid, pos):
            ema = self.ema_mid if self.ema_mid is not None else mid
            peak = self.peak_mid_while_long if self.peak_mid_while_long is not None else mid
            for bid_price in sorted(depth.buy_orders, reverse=True):
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
                qty = min(depth.buy_orders[bid_price], remaining,
                          self.MAX_DERISK_PER_TICK - sold)
                if qty > 0:
                    orders.append(Order(self.symbol, bid_price, -qty))
                    sold += qty
        block_new_buys = self._should_block_new_buys(mid, pos)
        if not block_new_buys:
            for ask_price in sorted(depth.sell_orders):
                if ask_price > self.FAIR - self.TAKE_EDGE:
                    break
                cap = min(self.position_limit - pos - bought, self.MAX_TAKE - bought)
                if cap <= 0:
                    break
                qty = min(-depth.sell_orders[ask_price], cap)
                if qty > 0:
                    orders.append(Order(self.symbol, ask_price, qty))
                    bought += qty
        for bid_price in sorted(depth.buy_orders, reverse=True):
            if bid_price < self.FAIR + self.TAKE_EDGE:
                break
            cap = min(self.position_limit + pos - sold, self.MAX_TAKE - sold)
            if cap <= 0:
                break
            qty = min(depth.buy_orders[bid_price], cap)
            if qty > 0:
                orders.append(Order(self.symbol, bid_price, -qty))
                sold += qty
        effective_pos = pos + bought - sold
        inv_skew = int(round(8 * effective_pos / max(self.position_limit, 1)))
        bid_px = int(self.FAIR - self.PASSIVE_EDGE - inv_skew)
        ask_px = int(self.FAIR + self.PASSIVE_EDGE - inv_skew)
        buy_cap = min(self.position_limit - pos - bought, self.MAX_PASSIVE)
        sell_cap = min(self.position_limit + pos - sold, self.MAX_PASSIVE)
        if self.soft_pos_cap is not None:
            if effective_pos >= self.soft_pos_cap:
                buy_cap = 0
            elif effective_pos <= -self.soft_pos_cap:
                sell_cap = 0
        if not block_new_buys and buy_cap > 0:
            orders.append(Order(self.symbol, bid_px, buy_cap))
        if sell_cap > 0:
            orders.append(Order(self.symbol, ask_px, -sell_cap))
        return orders


class VfeMrTaker:
    """Ported from Ian's VelvetfruitStrategy (delta-1 mean reverter on VFE)
    with rolling-FV upgrade. When mid deviates from rolling-1000 median by
    >= ENTRY_THR ticks, sweep the book in the reversion direction. Stop-loss
    closes if mid moves STOP_LOSS_TICKS adverse to entry."""

    ENTRY_THR: float = 20.0
    STOP_LOSS_TICKS: float = 40.0
    FV_WINDOW: int = 1000          # ticks for rolling median
    FV_WARMUP_FALLBACK: float = 5250.0  # used until window has >= 100 samples

    def __init__(self, symbol: str, position_limit: int) -> None:
        self.symbol = symbol
        self.position_limit = position_limit
        self.mid_history: deque[float] = deque(maxlen=self.FV_WINDOW)
        self.entry_price: float | None = None

    def _rolling_fv(self) -> float:
        if len(self.mid_history) < 100:
            return self.FV_WARMUP_FALLBACK
        sorted_mids = sorted(self.mid_history)
        n = len(sorted_mids)
        return sorted_mids[n // 2] if n % 2 else (sorted_mids[n // 2 - 1] + sorted_mids[n // 2]) / 2

    def run(self, state: TradingState) -> list[Order]:
        depth = state.order_depths.get(self.symbol)
        if depth is None or not depth.buy_orders or not depth.sell_orders:
            return []
        pos = state.position.get(self.symbol, 0)
        best_bid = max(depth.buy_orders)
        best_ask = min(depth.sell_orders)
        mid = (best_bid + best_ask) / 2.0
        self.mid_history.append(mid)
        fv = self._rolling_fv()
        dev = mid - fv
        orders: list[Order] = []
        # Stop-loss: close losing position before it grows further
        if self.entry_price is not None and pos != 0:
            loss = (mid - self.entry_price) * pos
            if loss < -self.STOP_LOSS_TICKS * abs(pos):
                if pos > 0:
                    closed = 0
                    for bid_price in sorted(depth.buy_orders, reverse=True):
                        rem = pos - closed
                        if rem <= 0:
                            break
                        qty = min(depth.buy_orders[bid_price], rem)
                        if qty > 0:
                            orders.append(Order(self.symbol, bid_price, -qty))
                            closed += qty
                else:
                    closed = 0
                    for ask_price in sorted(depth.sell_orders):
                        rem = -pos - closed
                        if rem <= 0:
                            break
                        qty = min(-depth.sell_orders[ask_price], rem)
                        if qty > 0:
                            orders.append(Order(self.symbol, ask_price, qty))
                            closed += qty
                self.entry_price = None
                return orders
        buys = sells = 0
        if dev < -self.ENTRY_THR and pos < self.position_limit:
            for ask_price in sorted(depth.sell_orders):
                rem = self.position_limit - pos - buys
                if rem <= 0:
                    break
                qty = min(-depth.sell_orders[ask_price], rem)
                if qty > 0:
                    orders.append(Order(self.symbol, ask_price, qty))
                    buys += qty
            if buys > 0:
                self.entry_price = mid
        elif dev > self.ENTRY_THR and pos > -self.position_limit:
            for bid_price in sorted(depth.buy_orders, reverse=True):
                rem = self.position_limit + pos - sells
                if rem <= 0:
                    break
                qty = min(depth.buy_orders[bid_price], rem)
                if qty > 0:
                    orders.append(Order(self.symbol, bid_price, -qty))
                    sells += qty
            if sells > 0:
                self.entry_price = mid
        elif pos == 0:
            self.entry_price = None
        return orders


class VevOptionTaker:
    """Treat voucher as deterministic function of VFE (no theta, no IV variation —
    confirmed in our 05_voucher_chain.md and 16_regime_patterns.md). When VFE
    deviates from rolling FV by >= ENTRY_THR, take max position in the voucher
    in the reversion direction. Cap is STRIKE-AWARE (sized for equal VFE-equiv
    exposure across strikes — corrects Ian's uniform-cap-300 bleed on deep ITM)."""

    UNDERLYING: str = "VELVETFRUIT_EXTRACT"
    ENTRY_THR: float = 20.0
    STOP_LOSS_TICKS: float = 40.0
    FV_WINDOW: int = 1000
    FV_WARMUP_FALLBACK: float = 5250.0

    def __init__(self, symbol: str, position_limit: int) -> None:
        self.symbol = symbol
        self.position_limit = position_limit
        self.und_history: deque[float] = deque(maxlen=self.FV_WINDOW)
        self.entry_underlying: float | None = None
        # v11: defensive flow gates set by Trader each tick
        self.block_long_add: bool = False
        self.block_short_add: bool = False

    def _rolling_fv(self) -> float:
        if len(self.und_history) < 100:
            return self.FV_WARMUP_FALLBACK
        s = sorted(self.und_history)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    def run(self, state: TradingState) -> list[Order]:
        depth = state.order_depths.get(self.symbol)
        und = state.order_depths.get(self.UNDERLYING)
        if (depth is None or not depth.buy_orders or not depth.sell_orders
                or und is None or not und.buy_orders or not und.sell_orders):
            return []
        pos = state.position.get(self.symbol, 0)
        und_mid = (max(und.buy_orders) + min(und.sell_orders)) / 2.0
        self.und_history.append(und_mid)
        fv = self._rolling_fv()
        dev = und_mid - fv
        orders: list[Order] = []
        # Stop-loss on adverse VFE move
        if self.entry_underlying is not None and pos != 0:
            adverse = (self.entry_underlying - und_mid) if pos > 0 else (und_mid - self.entry_underlying)
            if adverse > self.STOP_LOSS_TICKS:
                if pos > 0:
                    closed = 0
                    for bid_price in sorted(depth.buy_orders, reverse=True):
                        rem = pos - closed
                        if rem <= 0:
                            break
                        qty = min(depth.buy_orders[bid_price], rem)
                        if qty > 0:
                            orders.append(Order(self.symbol, bid_price, -qty))
                            closed += qty
                else:
                    closed = 0
                    for ask_price in sorted(depth.sell_orders):
                        rem = -pos - closed
                        if rem <= 0:
                            break
                        qty = min(-depth.sell_orders[ask_price], rem)
                        if qty > 0:
                            orders.append(Order(self.symbol, ask_price, qty))
                            closed += qty
                self.entry_underlying = None
                return orders
        buys = sells = 0
        # v11: gate adding inventory when informed flow predicts adverse drift.
        # block_long_add: sell-aggressors dominate -> VFE drifts down -> don't go long voucher.
        # block_short_add: buy-aggressors dominate -> VFE drifts up -> don't go short voucher.
        if dev < -self.ENTRY_THR and pos < self.position_limit and not self.block_long_add:
            for ask_price in sorted(depth.sell_orders):
                rem = self.position_limit - pos - buys
                if rem <= 0:
                    break
                qty = min(-depth.sell_orders[ask_price], rem)
                if qty > 0:
                    orders.append(Order(self.symbol, ask_price, qty))
                    buys += qty
            if buys > 0:
                self.entry_underlying = und_mid
        elif dev > self.ENTRY_THR and pos > -self.position_limit and not self.block_short_add:
            for bid_price in sorted(depth.buy_orders, reverse=True):
                rem = self.position_limit + pos - sells
                if rem <= 0:
                    break
                qty = min(depth.buy_orders[bid_price], rem)
                if qty > 0:
                    orders.append(Order(self.symbol, bid_price, -qty))
                    sells += qty
            if sells > 0:
                self.entry_underlying = und_mid
        elif pos == 0:
            self.entry_underlying = None
        return orders


class InformedFlowTracker:
    """v11: track recent VFE aggressor imbalance from market_trades.
    Buy-aggressor (trade at-or-above mid) predicts upward drift (EDA #7,
    +0.63 ticks/50t, t=2.64). Used as a *gate*, not a skew (per v3 lesson:
    sticky directional signals create their own problems if used as biases).

    Sums signed aggressor volume over WINDOW recent ticks; sign tells us
    which direction adds are likely to be adverse."""
    UNDERLYING: str = "VELVETFRUIT_EXTRACT"
    WINDOW: int = 50
    THRESHOLD: int = 8

    def __init__(self) -> None:
        self.flow: deque[int] = deque(maxlen=self.WINDOW)

    def update(self, state: TradingState) -> None:
        depth = state.order_depths.get(self.UNDERLYING)
        if depth is None or not depth.buy_orders or not depth.sell_orders:
            self.flow.append(0)
            return
        mid = (max(depth.buy_orders) + min(depth.sell_orders)) / 2.0
        net = 0
        trades = state.market_trades.get(self.UNDERLYING, []) or []
        for t in trades:
            if t.price > mid:
                net += t.quantity
            elif t.price < mid:
                net -= t.quantity
        self.flow.append(net)

    def block_long(self) -> bool:
        return sum(self.flow) <= -self.THRESHOLD

    def block_short(self) -> bool:
        return sum(self.flow) >= self.THRESHOLD


def voucher_cap_for(strike: str, vfe_equiv_target: int = 80) -> int:
    """Cap voucher position so its VFE-equivalent exposure equals target.
    e.g. delta=0.5, target=80 -> cap=160 voucher units."""
    delta = VOUCHER_DELTA[strike]
    cap = int(round(vfe_equiv_target / delta))
    return min(cap, POSITION_LIMITS[strike])


class Trader:
    def __init__(self) -> None:
        self.flow = InformedFlowTracker()  # v11
        self.strategies = {
            "HYDROGEL_PACK": HydrogelTakeMaker(
                "HYDROGEL_PACK", POSITION_LIMITS["HYDROGEL_PACK"],
            ),
            "VELVETFRUIT_EXTRACT": VfeMrTaker(
                "VELVETFRUIT_EXTRACT", POSITION_LIMITS["VELVETFRUIT_EXTRACT"],
            ),
            "VEV_5000": VevOptionTaker("VEV_5000", voucher_cap_for("VEV_5000")),
            "VEV_5100": VevOptionTaker("VEV_5100", voucher_cap_for("VEV_5100")),
            "VEV_5200": VevOptionTaker("VEV_5200", voucher_cap_for("VEV_5200")),
            "VEV_5300": VevOptionTaker("VEV_5300", voucher_cap_for("VEV_5300")),
        }

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        self.flow.update(state)
        block_long = self.flow.block_long()
        block_short = self.flow.block_short()
        for sym, strat in self.strategies.items():
            if isinstance(strat, VevOptionTaker):
                strat.block_long_add = block_long
                strat.block_short_add = block_short
        orders: dict[str, list[Order]] = {}
        for symbol, strategy in self.strategies.items():
            result = strategy.run(state)
            if result:
                orders[symbol] = result
        return orders, 0, ""
