#!/usr/bin/env python3
"""Sweep OsmiumStrategy MR parameters."""
import subprocess, re, sys, os

# Add src to path so we can modify the class attributes
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

BACKTEST = os.path.join(os.path.dirname(__file__), '..', 'tools', 'run_backtest.sh')

def run_backtest(rnd):
    result = subprocess.run([BACKTEST, str(rnd)], capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), '..'))
    # Parse osmium total from "ASH_COATED_OSMIUM" line
    for line in result.stdout.split('\n'):
        if 'ASH_COATED_OSMIUM' in line:
            parts = line.split()
            return float(parts[-1])
    return 0.0

def set_params(thr, buy_adj, sell_adj, mr_thr=None, mr_shift=None):
    """Patch trader.py class variables."""
    path = os.path.join(os.path.dirname(__file__), '..', 'src', 'trader.py')
    with open(path) as f:
        code = f.read()
    
    code = re.sub(r'MR_TAKE_THR = [\d.]+', f'MR_TAKE_THR = {thr}', code)
    code = re.sub(r'MR_BUY_ADJ = [\d.]+', f'MR_BUY_ADJ = {buy_adj}', code)
    code = re.sub(r'MR_SELL_ADJ = -[\d.]+', f'MR_SELL_ADJ = -{sell_adj}', code)
    
    with open(path, 'w') as f:
        f.write(code)

# Parameter combinations to test
configs = [
    # (thr, buy_adj, sell_adj_abs, label)
    (2.5, 4.5, 5.5, "baseline"),
    (2.0, 4.5, 5.5, "thr=2.0"),
    (3.0, 4.5, 5.5, "thr=3.0"),
    (2.5, 3.5, 4.5, "adj=3.5/4.5"),
    (2.5, 5.5, 6.5, "adj=5.5/6.5"),
    (2.5, 5.5, 5.5, "symmetric=5.5"),
    (2.5, 4.5, 4.5, "symmetric=4.5"),
    (2.0, 5.0, 5.0, "thr=2.0,sym=5"),
    (3.0, 5.5, 5.5, "thr=3.0,sym=5.5"),
    (2.5, 6.0, 6.0, "symmetric=6.0"),
]

print(f"{'Config':<25} {'R1_Osm':>10} {'R2_Osm':>10} {'Total':>10}")
print("-" * 60)

for thr, buy_adj, sell_adj, label in configs:
    set_params(thr, buy_adj, sell_adj)
    r1 = run_backtest(1)
    r2 = run_backtest(2)
    total = r1 + r2
    print(f"{label:<25} {r1:>10.0f} {r2:>10.0f} {total:>10.0f}")

# Restore baseline
set_params(2.5, 4.5, 5.5)
print("\nRestored baseline params.")
