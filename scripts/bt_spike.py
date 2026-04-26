"""Spike: run prosperity3bt on our P4 R3 data with a trivial no-op trader.

Validates the assumption that prosperity3bt works on P4 data after monkey-patching
the LIMITS dict to include P4 R3 products.

Usage: venv/bin/python scripts/bt_spike.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

P4_LIMITS = {
    "HYDROGEL_PACK": 200,
    "VELVETFRUIT_EXTRACT": 200,
    "VEV_4000": 300, "VEV_4500": 300, "VEV_5000": 300, "VEV_5100": 300,
    "VEV_5200": 300, "VEV_5300": 300, "VEV_5400": 300, "VEV_5500": 300,
    "VEV_6000": 300, "VEV_6500": 300,
}

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "round_3"
BT_DATA_DIR = ROOT / "data" / "_bt_resources" / "round3"
TRADER_PATH = ROOT / "scripts" / "_noop_trader.py"
LIMITS_PATCH = ROOT / "scripts" / "_limits_patch.py"


def stage_data() -> None:
    """Mirror our R3 CSVs into the layout prosperity3bt expects."""
    BT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for src in DATA_DIR.glob("*.csv"):
        dst = BT_DATA_DIR / src.name
        if not dst.exists():
            shutil.copy(src, dst)
    # __init__.py so it's a package (matches bundled resources structure)
    (BT_DATA_DIR / "__init__.py").touch()
    (BT_DATA_DIR.parent / "__init__.py").touch()


def write_noop_trader() -> None:
    """Trader uses `from datamodel import ...` (IMC platform convention).
    We colocate a datamodel.py shim that re-exports from prosperity3bt."""
    TRADER_PATH.write_text(
        'from datamodel import TradingState\n'
        'class Trader:\n'
        '    def run(self, state: TradingState):\n'
        '        return {}, 0, ""\n'
    )
    (TRADER_PATH.parent / "datamodel.py").write_text(
        'from prosperity3bt.datamodel import *  # noqa: F401,F403\n'
    )


def write_limits_patch() -> None:
    """Sitecustomize-style monkey-patch: prepend P4 limits before bt loads data."""
    LIMITS_PATCH.write_text(
        f'import prosperity3bt.data as _d\n'
        f'_d.LIMITS.update({P4_LIMITS!r})\n'
    )


def run_bt() -> int:
    cmd = [
        sys.executable, "-c",
        f"import sys; sys.path.insert(0, {str(LIMITS_PATCH.parent)!r}); "
        f"exec(open({str(LIMITS_PATCH)!r}).read()); "
        f"from prosperity3bt.__main__ import main; "
        f"sys.argv = ['prosperity3bt', {str(TRADER_PATH)!r}, '3', "
        f"'--data', {str(BT_DATA_DIR.parent)!r}, '--no-out']; "
        f"main()"
    ]
    print("running:", " ".join(cmd[:3]) + " ...")
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    stage_data()
    write_noop_trader()
    write_limits_patch()
    rc = run_bt()
    print(f"exit code: {rc}")
    sys.exit(rc)
