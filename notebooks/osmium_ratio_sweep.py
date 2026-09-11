#!/usr/bin/env python3
"""Sweep AC grading ratio."""
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

old_block = """        # --- MR-biased taking: widen take zone when price deviates from FV ---
        # Two tiers: always take at threshold, extra-take with AC confirmation
        # AC confirmation: price just moved AWAY from FV → expect bounce
        if fd < -self.MR_TAKE_THR:
            buy_adj = self.MR_BUY_ADJ if prev_down else self.MR_BUY_ADJ * 0.5
        else:
            buy_adj = 0
        if fd > self.MR_TAKE_THR:
            sell_adj = self.MR_SELL_ADJ if prev_up else self.MR_SELL_ADJ * 0.5
        else:
            sell_adj = 0"""

print(f"{'Ratio':<15} {'R1_Osm':>10} {'R2_Osm':>10} {'Total':>10}")
print("-" * 50)

for ratio in [0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]:
    new_block = f"""        if fd < -self.MR_TAKE_THR:
            buy_adj = self.MR_BUY_ADJ if prev_down else self.MR_BUY_ADJ * {ratio}
        else:
            buy_adj = 0
        if fd > self.MR_TAKE_THR:
            sell_adj = self.MR_SELL_ADJ if prev_up else self.MR_SELL_ADJ * {ratio}
        else:
            sell_adj = 0"""
    code = original.replace(old_block, f"        # --- MR taking ---\n{new_block}")
    write_trader(code)
    r1 = run_backtest(1)
    r2 = run_backtest(2)
    label = f"ratio={ratio}" if ratio > 0 else "ac-only (0.0)"
    print(f"{label:<15} {r1:>10.0f} {r2:>10.0f} {r1+r2:>10.0f}")

write_trader(original)
print("\nRestored original.")
