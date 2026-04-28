#!/usr/bin/env python3
"""
Parameter sweep for EMAMarketMaker products.
Sweeps ema_alpha and take_edge for Snackpacks (together) and Translator (separately).
Keeps DirectionalStrategy products at defaults — no tunable params there.
"""

import subprocess, re, itertools, textwrap
from pathlib import Path

DATASET = "data/round5"
BASE = Path("src/trader.py")
TMP  = Path("src/_sweep_tmp.py")

SNACKPACK_PRODUCTS = [
    "SNACKPACK_RASPBERRY", "SNACKPACK_VANILLA",
    "SNACKPACK_CHOCOLATE",  "SNACKPACK_PISTACHIO",
]
TRANSLATOR_PRODUCTS = ["TRANSLATOR_GRAPHITE_MIST"]

DIRECTIONAL_BLOCK = textwrap.dedent("""\
    # Directional — short
    "PEBBLES_XS":     DirectionalStrategy("PEBBLES_XS",     10, direction=-1),
    "UV_VISOR_AMBER": DirectionalStrategy("UV_VISOR_AMBER", 10, direction=-1),
    "MICROCHIP_OVAL": DirectionalStrategy("MICROCHIP_OVAL", 10, direction=-1),
    # Directional — long
    "PEBBLES_XL":          DirectionalStrategy("PEBBLES_XL",          10, direction=+1),
    "MICROCHIP_SQUARE":    DirectionalStrategy("MICROCHIP_SQUARE",    10, direction=+1),
    "OXYGEN_SHAKE_GARLIC": DirectionalStrategy("OXYGEN_SHAKE_GARLIC", 10, direction=+1),
    "SLEEP_POD_POLYESTER": DirectionalStrategy("SLEEP_POD_POLYESTER", 10, direction=+1),
""")


def build_products_block(snack_alpha, snack_edge, trans_alpha, trans_edge):
    lines = ["PRODUCTS = {"]
    lines.append("    # Market making")
    for p in SNACKPACK_PRODUCTS:
        lines.append(f'    "{p}": EMAMarketMaker("{p}", 10, ema_alpha={snack_alpha}, take_edge={snack_edge}),')
    for p in TRANSLATOR_PRODUCTS:
        lines.append(f'    "{p}": EMAMarketMaker("{p}", 10, ema_alpha={trans_alpha}, take_edge={trans_edge}),')
    lines.append("")
    for line in DIRECTIONAL_BLOCK.strip().splitlines():
        lines.append("    " + line)
    lines.append("}")
    return "\n".join(lines)


def write_trader(products_block: str):
    src = BASE.read_text()
    # Replace the PRODUCTS = { ... } block
    new_src = re.sub(
        r"^PRODUCTS = \{.*?^\}",
        products_block,
        src,
        flags=re.MULTILINE | re.DOTALL,
    )
    TMP.write_text(new_src)


def run_backtest() -> dict[str, float]:
    out = subprocess.run(
        ["rust_backtester", "--dataset", DATASET, "--trader", str(TMP), "--products", "full"],
        capture_output=True, text=True,
    ).stdout
    pnl: dict[str, float] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 5:
            try:
                pnl[parts[0]] = float(parts[4])
            except ValueError:
                pass
    return pnl


def total_mm(pnl, products):
    return sum(pnl.get(p, 0.0) for p in products)


# ── Snackpack sweep (fix Translator at defaults) ──────────────────────────────
TRANS_ALPHA_DEFAULT = 0.01
TRANS_EDGE_DEFAULT  = 150

snack_alphas = [0.005, 0.01, 0.02, 0.03, 0.05]
snack_edges  = [20, 40, 60, 80, 100, 150]

print("=== Snackpack sweep ===")
print(f"{'alpha':>8}  {'edge':>6}  {'total_MM':>12}  {'SNACK total':>12}")
snack_results = []
for alpha, edge in itertools.product(snack_alphas, snack_edges):
    write_trader(build_products_block(alpha, edge, TRANS_ALPHA_DEFAULT, TRANS_EDGE_DEFAULT))
    pnl = run_backtest()
    mm_total = total_mm(pnl, SNACKPACK_PRODUCTS)
    snack_results.append((mm_total, alpha, edge, pnl))
    print(f"{alpha:>8.3f}  {edge:>6}  {mm_total:>12.1f}")

best_snack = max(snack_results, key=lambda x: x[0])
best_snack_alpha, best_snack_edge = best_snack[1], best_snack[2]
print(f"\nBest snack: alpha={best_snack_alpha}  edge={best_snack_edge}  MM={best_snack[0]:.1f}\n")

# ── Translator sweep (fix Snackpacks at best) ─────────────────────────────────
trans_alphas = [0.005, 0.01, 0.02, 0.03]
trans_edges  = [50, 100, 150, 200, 300]

print("=== Translator sweep ===")
print(f"{'alpha':>8}  {'edge':>6}  {'TRANSLATOR_GRAPHITE_MIST':>24}")
trans_results = []
for alpha, edge in itertools.product(trans_alphas, trans_edges):
    write_trader(build_products_block(best_snack_alpha, best_snack_edge, alpha, edge))
    pnl = run_backtest()
    t_total = pnl.get("TRANSLATOR_GRAPHITE_MIST", 0.0)
    trans_results.append((t_total, alpha, edge))
    print(f"{alpha:>8.3f}  {edge:>6}  {t_total:>24.1f}")

best_trans = max(trans_results, key=lambda x: x[0])
best_trans_alpha, best_trans_edge = best_trans[1], best_trans[2]
print(f"\nBest translator: alpha={best_trans_alpha}  edge={best_trans_edge}  PnL={best_trans[0]:.1f}\n")

# ── Final run with best params ─────────────────────────────────────────────────
print("=== Final run with best params ===")
write_trader(build_products_block(best_snack_alpha, best_snack_edge, best_trans_alpha, best_trans_edge))
pnl = run_backtest()
total = sum(pnl.values())
print(f"TOTAL: {total:.1f}")
for p, v in sorted(pnl.items(), key=lambda x: -x[1]):
    if v != 0:
        print(f"  {p:<35} {v:>12.1f}")

TMP.unlink(missing_ok=True)
print(f"\nBest params:")
print(f"  Snackpacks:  ema_alpha={best_snack_alpha}  take_edge={best_snack_edge}")
print(f"  Translator:  ema_alpha={best_trans_alpha}  take_edge={best_trans_edge}")
