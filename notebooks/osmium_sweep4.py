#!/usr/bin/env python3
"""Test overbid/underbid removal and autocorrelation fade."""
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

print("=== Component Tests ===")
print(f"{'Config':<30} {'R1_Osm':>10} {'R2_Osm':>10} {'Total':>10}")
print("-" * 65)

# 1. Baseline
write_trader(original)
r1 = run_backtest(1)
r2 = run_backtest(2)
print(f"{'baseline (no MR shift)':<30} {r1:>10.0f} {r2:>10.0f} {r1+r2:>10.0f}")

# 2. No overbid/underbid
overbid_block = """        # --- Overbidding: improve queue priority by outbidding best passive bid ---
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
                break"""

code = original.replace(overbid_block, "")
write_trader(code)
r1 = run_backtest(1)
r2 = run_backtest(2)
print(f"{'no overbid/underbid':<30} {r1:>10.0f} {r2:>10.0f} {r1+r2:>10.0f}")

# 3. No dynamic wall offset (simplify to offset=1)
wall_block = """        # --- Dynamic wall offset: if wall is very deep, pull quote in toward best ---
        buy_wall_dist = best_bid - bid_wall
        sell_wall_dist = ask_wall - best_ask
        buy_offset = max(1, buy_wall_dist // 5) if buy_wall_dist > 10 else 1
        sell_offset = max(1, sell_wall_dist // 5) if sell_wall_dist > 10 else 1"""

simple_offset = """        buy_offset = 1
        sell_offset = 1"""

code = original.replace(wall_block, simple_offset)
write_trader(code)
r1 = run_backtest(1)
r2 = run_backtest(2)
print(f"{'simplified offset=1':<30} {r1:>10.0f} {r2:>10.0f} {r1+r2:>10.0f}")

# 4. No MR taking at all
code = original.replace(
    "        buy_adj = self.MR_BUY_ADJ if fd < -self.MR_TAKE_THR else 0\n        sell_adj = self.MR_SELL_ADJ if fd > self.MR_TAKE_THR else 0",
    "        buy_adj = 0\n        sell_adj = 0"
)
write_trader(code)
r1 = run_backtest(1)
r2 = run_backtest(2)
print(f"{'no MR taking':<30} {r1:>10.0f} {r2:>10.0f} {r1+r2:>10.0f}")

# 5. More aggressive overbid: +2 instead of +1
code = original.replace("overbid = bp + 1", "overbid = bp + 2").replace("underbid = ap - 1", "underbid = ap - 2")
write_trader(code)
r1 = run_backtest(1)
r2 = run_backtest(2)
print(f"{'overbid/underbid +/-2':<30} {r1:>10.0f} {r2:>10.0f} {r1+r2:>10.0f}")

# Restore
write_trader(original)
print("\nRestored original.")
