#!/usr/bin/env python3
"""Sweep AC-enhanced MR taking variants."""
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

# Find the MR taking block to replace
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

configs = [
    ("baseline (always take)", """        buy_adj = self.MR_BUY_ADJ if fd < -self.MR_TAKE_THR else 0
        sell_adj = self.MR_SELL_ADJ if fd > self.MR_TAKE_THR else 0"""),
    
    ("ac-confirmed only", """        buy_adj = self.MR_BUY_ADJ if fd < -self.MR_TAKE_THR and prev_down else 0
        sell_adj = self.MR_SELL_ADJ if fd > self.MR_TAKE_THR and prev_up else 0"""),

    ("ac-graded (full/half)", """        if fd < -self.MR_TAKE_THR:
            buy_adj = self.MR_BUY_ADJ if prev_down else self.MR_BUY_ADJ * 0.5
        else:
            buy_adj = 0
        if fd > self.MR_TAKE_THR:
            sell_adj = self.MR_SELL_ADJ if prev_up else self.MR_SELL_ADJ * 0.5
        else:
            sell_adj = 0"""),

    ("ac-confirmed thr=2.0", """        buy_adj = self.MR_BUY_ADJ if fd < -2.0 and prev_down else 0
        sell_adj = self.MR_SELL_ADJ if fd > 2.0 and prev_up else 0"""),

    ("ac-confirmed thr=3.0", """        buy_adj = self.MR_BUY_ADJ if fd < -3.0 and prev_down else 0
        sell_adj = self.MR_SELL_ADJ if fd > 3.0 and prev_up else 0"""),

    ("always@3 + ac@2", """        if fd < -3.0:
            buy_adj = self.MR_BUY_ADJ
        elif fd < -2.0 and prev_down:
            buy_adj = self.MR_BUY_ADJ
        else:
            buy_adj = 0
        if fd > 3.0:
            sell_adj = self.MR_SELL_ADJ
        elif fd > 2.0 and prev_up:
            sell_adj = self.MR_SELL_ADJ
        else:
            sell_adj = 0"""),

    ("always@3 + ac@1.5", """        if fd < -3.0:
            buy_adj = self.MR_BUY_ADJ
        elif fd < -1.5 and prev_down:
            buy_adj = self.MR_BUY_ADJ
        else:
            buy_adj = 0
        if fd > 3.0:
            sell_adj = self.MR_SELL_ADJ
        elif fd > 1.5 and prev_up:
            sell_adj = self.MR_SELL_ADJ
        else:
            sell_adj = 0"""),
    
    ("ac-confirmed + bigger adj", """        buy_adj = 6.0 if fd < -self.MR_TAKE_THR and prev_down else 0
        sell_adj = -6.0 if fd > self.MR_TAKE_THR and prev_up else 0"""),
]

print(f"{'Config':<30} {'R1_Osm':>10} {'R2_Osm':>10} {'Total':>10}")
print("-" * 65)

for label, mr_block in configs:
    code = original.replace(old_block, f"        # --- MR taking ---\n{mr_block}")
    write_trader(code)
    r1 = run_backtest(1)
    r2 = run_backtest(2)
    print(f"{label:<30} {r1:>10.0f} {r2:>10.0f} {r1+r2:>10.0f}")

write_trader(original)
print("\nRestored original.")
