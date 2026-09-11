#!/usr/bin/env python3
"""Test EMA-based osmium strategies."""
import subprocess, re, os

BACKTEST = os.path.join(os.path.dirname(__file__), '..', 'tools', 'run_backtest.sh')
TRADER = os.path.join(os.path.dirname(__file__), '..', 'src', 'trader.py')

def run_backtest(rnd):
    result = subprocess.run([BACKTEST, str(rnd)], capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), '..'))
    for line in result.stdout.split('\n'):
        if 'ASH_COATED_OSMIUM' in line:
            return float(line.split()[-1])
    return 0.0

def read_trader():
    with open(TRADER) as f:
        return f.read()

def write_trader(code):
    with open(TRADER, 'w') as f:
        f.write(code)

original = read_trader()

# We'll create a new class that uses EMA and swap it in PRODUCTS
# First, let's define the EMA strategy as a replacement for OsmiumStrategy

ema_template = '''
class OsmiumEMAStrategy(Strategy):
    """EMA-based osmium market maker."""
    EMA_SPAN = {span}

    def __init__(self, symbol: str, position_limit: int) -> None:
        super().__init__(symbol, position_limit)
        self.ema: Optional[float] = None
        self.prev_mid: Optional[float] = None

    def save_state(self) -> dict:
        return {{"ema": self.ema, "prev_mid": self.prev_mid}}

    def load_state(self, data: dict) -> None:
        self.ema = data.get("ema")
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
        mid = (best_bid + best_ask) / 2.0

        # Update EMA
        alpha = 2.0 / (self.EMA_SPAN + 1)
        if self.ema is None:
            self.ema = mid
        else:
            self.ema = alpha * mid + (1 - alpha) * self.ema

        {fv_logic}

        # AC signal
        prev_up = False
        prev_down = False
        if self.prev_mid is not None:
            change = mid - self.prev_mid
            prev_up = change > 0
            prev_down = change < 0
        self.prev_mid = mid

        fd = wall_mid - fv

        # MR taking
        MR_TAKE_THR = 2.5
        MR_BUY_ADJ = 4.5
        MR_SELL_ADJ = -5.5
        if fd < -MR_TAKE_THR:
            buy_adj = MR_BUY_ADJ if prev_down else MR_BUY_ADJ * 0.8
        else:
            buy_adj = 0
        if fd > MR_TAKE_THR:
            sell_adj = MR_SELL_ADJ if prev_up else MR_SELL_ADJ * 0.8
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

        # Passive quoting
        buy_price = bid_wall + 1
        sell_price = ask_wall - 1
        if buy_price >= wall_mid:
            buy_price = int(wall_mid) - 1
        if sell_price <= wall_mid:
            sell_price = int(wall_mid) + 1

        for bp in sorted(order_depth.buy_orders.keys(), reverse=True):
            overbid = bp + 1
            if overbid < wall_mid and overbid > buy_price:
                buy_price = overbid
                break
            if bp < wall_mid:
                break

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
'''

# Test configurations
configs = [
    ("baseline (static FV)", None, None, None),
    
    # 1. EMA as FV for MR taking (replace static 10000)
    ("ema_fv span=20", 20, "fv = self.ema", "Replace static FV with EMA"),
    ("ema_fv span=50", 50, "fv = self.ema", ""),
    ("ema_fv span=100", 100, "fv = self.ema", ""),
    ("ema_fv span=200", 200, "fv = self.ema", ""),
    ("ema_fv span=500", 500, "fv = self.ema", ""),

    # 2. Use EMA deviation as extra take signal
    ("ema_dev span=50", 50,
     "fv = FAIR_VALUE\n        ema_dev = mid - self.ema\n        if ema_dev < -2:\n            buy_adj_bonus = 2.0\n        elif ema_dev > 2:\n            sell_adj_bonus = -2.0\n        else:\n            buy_adj_bonus = 0\n            sell_adj_bonus = 0",
     "EMA deviation bonus"),
    ("ema_dev span=100", 100,
     "fv = FAIR_VALUE\n        ema_dev = mid - self.ema\n        if ema_dev < -2:\n            buy_adj_bonus = 2.0\n        elif ema_dev > 2:\n            sell_adj_bonus = -2.0\n        else:\n            buy_adj_bonus = 0\n            sell_adj_bonus = 0",
     ""),
    
    # 3. Blend: fv = (EMA + static) / 2
    ("blend span=50", 50, "fv = (self.ema + FAIR_VALUE) / 2.0", ""),
    ("blend span=100", 100, "fv = (self.ema + FAIR_VALUE) / 2.0", ""),
    ("blend span=200", 200, "fv = (self.ema + FAIR_VALUE) / 2.0", ""),
]

print(f"{'Config':<25} {'R1_Osm':>10} {'R2_Osm':>10} {'Total':>10}")
print("-" * 60)

for label, span, fv_logic, desc in configs:
    if span is None:
        # baseline
        write_trader(original)
    else:
        # Build the EMA strategy
        strategy_code = ema_template.format(span=span, fv_logic=fv_logic)
        # Insert before PepperStrategy and replace PRODUCTS reference
        code = original.replace(
            "class PepperStrategy",
            strategy_code + "\n\nclass PepperStrategy"
        )
        code = code.replace(
            '"ASH_COATED_OSMIUM": OsmiumStrategy("ASH_COATED_OSMIUM", position_limit=80)',
            '"ASH_COATED_OSMIUM": OsmiumEMAStrategy("ASH_COATED_OSMIUM", position_limit=80)'
        )
        write_trader(code)
    
    r1 = run_backtest(1)
    r2 = run_backtest(2)
    print(f"{label:<25} {r1:>10.0f} {r2:>10.0f} {r1+r2:>10.0f}")

write_trader(original)
print("\nRestored original.")
