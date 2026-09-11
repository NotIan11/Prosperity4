#!/usr/bin/env python3
"""Sweep wall offset divisor and threshold."""
import subprocess, re, sys, os

BACKTEST = os.path.join(os.path.dirname(__file__), '..', 'tools', 'run_backtest.sh')
TRADER = os.path.join(os.path.dirname(__file__), '..', 'src', 'trader.py')

def run_backtest(rnd):
    result = subprocess.run([BACKTEST, str(rnd)], capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), '..'))
    for line in result.stdout.split('\n'):
        if 'ASH_COATED_OSMIUM' in line:
            parts = line.split()
            return float(parts[-1])
    return 0.0

def read_trader():
    with open(TRADER) as f:
        return f.read()

def write_trader(code):
    with open(TRADER, 'w') as f:
        f.write(code)

original = read_trader()

# Current code:
# buy_wall_dist = best_bid - bid_wall
# sell_wall_dist = ask_wall - best_ask
# buy_offset = max(1, buy_wall_dist // 5) if buy_wall_dist > 10 else 1
# sell_offset = max(1, sell_wall_dist // 5) if sell_wall_dist > 10 else 1

print("=== Wall Offset Configs ===")
print(f"{'Config':<25} {'R1_Osm':>10} {'R2_Osm':>10} {'Total':>10}")
print("-" * 60)

configs = [
    ("current (div5,thr10)", None),  # no change
    ("fixed offset=1",
     "        buy_offset = 1\n        sell_offset = 1"),
    ("fixed offset=2",
     "        buy_offset = 2\n        sell_offset = 2"),
    ("div3,thr10",
     "        buy_offset = max(1, buy_wall_dist // 3) if buy_wall_dist > 10 else 1\n        sell_offset = max(1, sell_wall_dist // 3) if sell_wall_dist > 10 else 1"),
    ("div7,thr10",
     "        buy_offset = max(1, buy_wall_dist // 7) if buy_wall_dist > 10 else 1\n        sell_offset = max(1, sell_wall_dist // 7) if sell_wall_dist > 10 else 1"),
    ("div5,thr5",
     "        buy_offset = max(1, buy_wall_dist // 5) if buy_wall_dist > 5 else 1\n        sell_offset = max(1, sell_wall_dist // 5) if sell_wall_dist > 5 else 1"),
    ("div5,thr15",
     "        buy_offset = max(1, buy_wall_dist // 5) if buy_wall_dist > 15 else 1\n        sell_offset = max(1, sell_wall_dist // 5) if sell_wall_dist > 15 else 1"),
]

old_block = """        buy_wall_dist = best_bid - bid_wall
        sell_wall_dist = ask_wall - best_ask
        buy_offset = max(1, buy_wall_dist // 5) if buy_wall_dist > 10 else 1
        sell_offset = max(1, sell_wall_dist // 5) if sell_wall_dist > 10 else 1"""

for label, replacement in configs:
    if replacement is None:
        write_trader(original)
    else:
        new_block = f"        buy_wall_dist = best_bid - bid_wall\n        sell_wall_dist = ask_wall - best_ask\n{replacement}"
        code = original.replace(old_block, new_block)
        write_trader(code)
    
    r1 = run_backtest(1)
    r2 = run_backtest(2)
    print(f"{label:<25} {r1:>10.0f} {r2:>10.0f} {r1+r2:>10.0f}")

write_trader(original)
print("\nRestored original.")
