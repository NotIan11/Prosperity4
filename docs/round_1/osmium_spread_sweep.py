"""
Sweep OsmiumStrategy passive spread (1, 2, 3) against R1 tutorial days.
Run from repo root: python notebooks/osmium_spread_sweep.py
"""

import re
import subprocess
import sys
from pathlib import Path

TRADER = Path("src/trader.py")
VENV_BT = Path(".venv/bin/prosperity4btest")
SPREADS = [1, 2, 3]

PATTERN = re.compile(
    r"Round 1 day -2: ([\d,]+).*?Round 1 day -1: ([\d,]+).*?Round 1 day 0: ([\d,]+).*?Total profit: ([\d,]+)",
    re.DOTALL,
)


def run_backtest(spread: int) -> dict:
    src = TRADER.read_text()
    patched = re.sub(
        r'OsmiumStrategy\("ASH_COATED_OSMIUM", position_limit=80\)',
        f'OsmiumStrategy("ASH_COATED_OSMIUM", position_limit=80, spread={spread})',
        src,
    )
    tmp = Path(f"/tmp/trader_osm_spread{spread}.py")
    tmp.write_text(patched)

    result = subprocess.run(
        [str(VENV_BT), str(tmp), "1"],
        capture_output=True,
        text=True,
    )
    output = result.stdout
    m = PATTERN.search(output)
    if not m:
        print(f"[spread={spread}] Failed to parse output:\n{output}\n{result.stderr}")
        return {}
    return {
        "day-2": int(m.group(1).replace(",", "")),
        "day-1": int(m.group(2).replace(",", "")),
        "day0":  int(m.group(3).replace(",", "")),
        "total": int(m.group(4).replace(",", "")),
    }


def main():
    print(f"{'spread':<8} {'day -2':>10} {'day -1':>10} {'day 0':>10} {'total':>12}")
    print("-" * 52)
    for s in SPREADS:
        r = run_backtest(s)
        if r:
            print(f"{s:<8} {r['day-2']:>10,} {r['day-1']:>10,} {r['day0']:>10,} {r['total']:>12,}")


if __name__ == "__main__":
    main()
