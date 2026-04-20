#!/usr/bin/env python3
"""Sweep pepper conditional sell: qty + price combos at spread thresholds."""
import subprocess, re, os

BACKTEST = os.path.join(os.path.dirname(__file__), '..', 'tools', 'run_backtest.sh')
TRADER = os.path.join(os.path.dirname(__file__), '..', 'src', 'trader.py')

def run_backtest(rnd):
    result = subprocess.run([BACKTEST, str(rnd)], capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), '..'))
    for line in result.stdout.split('\n'):
        if 'INTARIAN_PEPPER_ROOT' in line:
            return float(line.split()[-1])
    return 0.0

def read_trader():
    with open(TRADER) as f:
        return f.read()

def write_trader(code):
    with open(TRADER, 'w') as f:
        f.write(code)

original = read_trader()

# Replace the sell block with parameterized version
sell_block = """        # Conditional passive sell when spread is wide
        if self.SELL_SPREAD_THR > 0 and order_depth.buy_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            spread = best_ask - best_bid
            if spread >= self.SELL_SPREAD_THR:
                sell_price = best_ask - 1
                effective_pos = pos + buys
                sell_qty = min(5, effective_pos)  # sell up to 5 lots
                if sell_qty > 0:
                    orders.append(Order(self.symbol, sell_price, -sell_qty))"""

configs = [
    ("baseline", 0, None),
    # Vary qty at thr=16
    ("thr=16,qty=1,ask-1", 16, "sell_price = best_ask - 1\n                sell_qty = min(1, effective_pos)"),
    ("thr=16,qty=3,ask-1", 16, "sell_price = best_ask - 1\n                sell_qty = min(3, effective_pos)"),
    ("thr=16,qty=5,ask-1", 16, "sell_price = best_ask - 1\n                sell_qty = min(5, effective_pos)"),
    ("thr=16,qty=10,ask-1", 16, "sell_price = best_ask - 1\n                sell_qty = min(10, effective_pos)"),
    ("thr=16,qty=20,ask-1", 16, "sell_price = best_ask - 1\n                sell_qty = min(20, effective_pos)"),
    # At mid price
    ("thr=16,qty=5,mid", 16, "sell_price = int((best_ask + best_bid) / 2)\n                sell_qty = min(5, effective_pos)"),
    # At ask (crossing into L1)
    ("thr=16,qty=5,ask", 16, "sell_price = best_ask\n                sell_qty = min(5, effective_pos)"),
    # Vary qty at thr=18
    ("thr=18,qty=1,ask-1", 18, "sell_price = best_ask - 1\n                sell_qty = min(1, effective_pos)"),
    ("thr=18,qty=5,ask-1", 18, "sell_price = best_ask - 1\n                sell_qty = min(5, effective_pos)"),
    ("thr=18,qty=10,ask-1", 18, "sell_price = best_ask - 1\n                sell_qty = min(10, effective_pos)"),
    ("thr=18,qty=20,ask-1", 18, "sell_price = best_ask - 1\n                sell_qty = min(20, effective_pos)"),
    # At ask-2 (deeper passive)
    ("thr=18,qty=5,ask-2", 18, "sell_price = best_ask - 2\n                sell_qty = min(5, effective_pos)"),
    ("thr=18,qty=10,ask-2", 18, "sell_price = best_ask - 2\n                sell_qty = min(10, effective_pos)"),
]

print(f"{'Config':<30} {'R1_Pep':>10} {'R2_Pep':>10} {'Total':>10}")
print("-" * 65)

for label, thr, price_qty in configs:
    if thr == 0:
        code = re.sub(r'SELL_SPREAD_THR = \d+', 'SELL_SPREAD_THR = 0', original)
    else:
        code = re.sub(r'SELL_SPREAD_THR = \d+', f'SELL_SPREAD_THR = {thr}', original)
        if price_qty:
            code = code.replace(
                "sell_price = best_ask - 1\n                effective_pos = pos + buys\n                sell_qty = min(5, effective_pos)  # sell up to 5 lots",
                f"effective_pos = pos + buys\n                {price_qty}"
            )
    write_trader(code)
    r1 = run_backtest(1)
    r2 = run_backtest(2)
    print(f"{label:<30} {r1:>10.0f} {r2:>10.0f} {r1+r2:>10.0f}")

write_trader(original)
print("\nRestored original.")
