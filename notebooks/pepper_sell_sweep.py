#!/usr/bin/env python3
"""Sweep pepper conditional sell spread threshold."""
import subprocess, re, os

BACKTEST = os.path.join(os.path.dirname(__file__), '..', 'tools', 'run_backtest.sh')
TRADER = os.path.join(os.path.dirname(__file__), '..', 'src', 'trader.py')

def run_backtest(rnd):
    result = subprocess.run([BACKTEST, str(rnd)], capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), '..'))
    pep = osm = 0.0
    for line in result.stdout.split('\n'):
        if 'INTARIAN_PEPPER_ROOT' in line:
            pep = float(line.split()[-1])
        if 'ASH_COATED_OSMIUM' in line:
            osm = float(line.split()[-1])
    return pep, osm

def read_trader():
    with open(TRADER) as f:
        return f.read()

def write_trader(code):
    with open(TRADER, 'w') as f:
        f.write(code)

original = read_trader()

print(f"{'Config':<25} {'R1_Pep':>10} {'R1_Osm':>10} {'R1_Tot':>10} {'R2_Pep':>10} {'R2_Osm':>10} {'R2_Tot':>10}")
print("-" * 100)

for thr in [0, 14, 16, 18, 20, 22, 25]:
    code = re.sub(r'SELL_SPREAD_THR = \d+', f'SELL_SPREAD_THR = {thr}', original)
    write_trader(code)
    r1p, r1o = run_backtest(1)
    r2p, r2o = run_backtest(2)
    label = f"thr={thr}" if thr > 0 else "disabled (baseline)"
    print(f"{label:<25} {r1p:>10.0f} {r1o:>10.0f} {r1p+r1o:>10.0f} {r2p:>10.0f} {r2o:>10.0f} {r2p+r2o:>10.0f}")

write_trader(original)
print("\nRestored original.")
