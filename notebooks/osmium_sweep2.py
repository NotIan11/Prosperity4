#!/usr/bin/env python3
"""Sweep OsmiumStrategy FV and MR quote shift threshold."""
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

print("=== FV Sweep ===")
print(f"{'FV':<15} {'R1_Osm':>10} {'R2_Osm':>10} {'Total':>10}")
print("-" * 50)

for fv in [9998, 9999, 10000, 10001, 10002]:
    code = re.sub(r'FAIR_VALUE = [\d_]+', f'FAIR_VALUE = {fv}', original)
    write_trader(code)
    r1 = run_backtest(1)
    r2 = run_backtest(2)
    print(f"{fv:<15} {r1:>10.0f} {r2:>10.0f} {r1+r2:>10.0f}")

# Restore
write_trader(original)

print("\n=== MR Quote Shift Threshold Sweep ===")
print(f"{'MR_QS_THR':<15} {'R1_Osm':>10} {'R2_Osm':>10} {'Total':>10}")
print("-" * 50)

for thr in [1.0, 1.5, 2.0, 2.5, 3.0, 999]:  # 999 = disabled
    code = re.sub(
        r'mr = -1 if fd > [\d.]+ else \(1 if fd < -[\d.]+ else 0\)',
        f'mr = -1 if fd > {thr} else (1 if fd < -{thr} else 0)',
        original
    )
    write_trader(code)
    r1 = run_backtest(1)
    r2 = run_backtest(2)
    label = f"thr={thr}" if thr < 100 else "disabled"
    print(f"{label:<15} {r1:>10.0f} {r2:>10.0f} {r1+r2:>10.0f}")

# Restore
write_trader(original)
print("\nRestored original trader.py")
