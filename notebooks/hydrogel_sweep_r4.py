"""
Grid-sweep HydrogelStrategy parameters on round 4 data.
Uses direct string replacement on known parameter lines for reliability.
"""

import subprocess, re, os, sys
import numpy as np
import matplotlib.pyplot as plt

TRADER_PATH = "src/trader.py"
DATASET = os.path.expanduser("~/Desktop/Programming/prosperity_rust_backtester/datasets/round4")
BT_BIN = os.path.expanduser("~/.cargo/bin/rust_backtester")

TAKE_EDGE_VALS   = [8, 10, 12, 14, 16, 18, 20, 22]
TRAILING_DD_VALS = [12, 15, 18, 20, 22, 25, 28]
EMA_BREAK_VALS   = [14, 16, 18, 20]
RICH_MID_VALS    = [25, 30, 35, 40]   # offset from FAIR

def p(msg):
    print(msg, flush=True)

def read_trader():
    with open(TRADER_PATH) as f:
        return f.read()

def write_trader(src):
    with open(TRADER_PATH, "w") as f:
        f.write(src)

def set_params(src, take_edge, trailing_dd, ema_break, rich_offset):
    """Replace known parameter lines by exact pattern match."""
    src = re.sub(r'(    TAKE_EDGE: float = )[\d.]+', rf'\g<1>{take_edge}', src)
    src = re.sub(r'(    TRAILING_DRAWDOWN: float = )[\d.]+', rf'\g<1>{trailing_dd}', src)
    src = re.sub(r'(    EMA_BREAK: float = )[\d.]+', rf'\g<1>{ema_break}', src)
    src = re.sub(r'(    RICH_MID: float = FAIR \+ )\d+', rf'\g<1>{rich_offset}', src)
    src = re.sub(r'(    VERY_RICH_MID: float = FAIR \+ )\d+', rf'\g<1>{rich_offset + 20}', src)
    return src

def run_backtest():
    result = subprocess.run(
        [BT_BIN, "--trader", TRADER_PATH, "--dataset", DATASET],
        capture_output=True, text=True
    )
    out = result.stdout
    pnl = {}
    for line in out.splitlines():
        m = re.match(r'^(\w[\w_]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', line.strip())
        if m:
            pnl[m.group(1)] = float(m.group(5))
    return pnl

original = read_trader()

# ── Phase 1: TAKE_EDGE × TRAILING_DRAWDOWN ───────────────────────────────────
p(f"Phase 1: TAKE_EDGE ({len(TAKE_EDGE_VALS)}) × TRAILING_DRAWDOWN ({len(TRAILING_DD_VALS)}) "
  f"= {len(TAKE_EDGE_VALS)*len(TRAILING_DD_VALS)} runs")

grid1 = np.full((len(TRAILING_DD_VALS), len(TAKE_EDGE_VALS)), np.nan)

try:
    for i, td in enumerate(TRAILING_DD_VALS):
        for j, te in enumerate(TAKE_EDGE_VALS):
            src = set_params(original, te, td, 18.0, 35)
            write_trader(src)
            pnl = run_backtest()
            hg = pnl.get("HYDROGEL_PACK", 0)
            grid1[i, j] = hg
            p(f"  TE={te:4}  TD={td:4}  → HG={hg:>10,.0f}")
finally:
    write_trader(original)

bi, bj = np.unravel_index(np.nanargmax(grid1), grid1.shape)
best_te, best_td = TAKE_EDGE_VALS[bj], TRAILING_DD_VALS[bi]
baseline = grid1[TRAILING_DD_VALS.index(22), TAKE_EDGE_VALS.index(18)]
p(f"\nPhase 1 best: TE={best_te}  TD={best_td}  HG={grid1[bi,bj]:,.0f}  (baseline={baseline:,.0f})")

# ── Phase 2: EMA_BREAK × RICH_MID_OFFSET ─────────────────────────────────────
p(f"\nPhase 2: EMA_BREAK ({len(EMA_BREAK_VALS)}) × RICH_MID_OFFSET ({len(RICH_MID_VALS)}) "
  f"= {len(EMA_BREAK_VALS)*len(RICH_MID_VALS)} runs")

grid2 = np.full((len(RICH_MID_VALS), len(EMA_BREAK_VALS)), np.nan)

try:
    for i, rm in enumerate(RICH_MID_VALS):
        for j, eb in enumerate(EMA_BREAK_VALS):
            src = set_params(original, best_te, best_td, eb, rm)
            write_trader(src)
            pnl = run_backtest()
            hg = pnl.get("HYDROGEL_PACK", 0)
            grid2[i, j] = hg
            p(f"  EB={eb:4}  RM={rm:3}  → HG={hg:>10,.0f}")
finally:
    write_trader(original)

bi2, bj2 = np.unravel_index(np.nanargmax(grid2), grid2.shape)
best_eb, best_rm = EMA_BREAK_VALS[bj2], RICH_MID_VALS[bi2]
p(f"\nPhase 2 best: EB={best_eb}  RM={best_rm}  HG={grid2[bi2,bj2]:,.0f}")

# ── Final combined run ────────────────────────────────────────────────────────
p("\nFinal run with all best params...")
try:
    src = set_params(original, best_te, best_td, best_eb, best_rm)
    write_trader(src)
    final = run_backtest()
    p(f"  HYDROGEL={final.get('HYDROGEL_PACK',0):,.0f}  TOTAL={sum(final.values()):,.0f}")
finally:
    write_trader(original)

# ── Plots ─────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle("HydrogelStrategy sweep — round 4 (undercut passive)", fontsize=13, fontweight="bold")

for ax, grid, xv, yv, xl, yl, title, bxp, byp in [
    (axes[0], grid1, TAKE_EDGE_VALS, TRAILING_DD_VALS,
     "TAKE_EDGE", "TRAILING_DRAWDOWN", "Phase 1", bj, bi),
    (axes[1], grid2, EMA_BREAK_VALS, RICH_MID_VALS,
     "EMA_BREAK", "RICH_MID offset", "Phase 2", bj2, bi2),
]:
    vmin, vmax = np.nanmin(grid), np.nanmax(grid)
    im = ax.imshow(grid, aspect="auto", origin="lower",
                   cmap="RdYlGn", vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(xv))); ax.set_xticklabels(xv)
    ax.set_yticks(range(len(yv))); ax.set_yticklabels(yv)
    ax.set_xlabel(xl); ax.set_ylabel(yl); ax.set_title(title)
    for ii in range(len(yv)):
        for jj in range(len(xv)):
            v = grid[ii, jj]
            if not np.isnan(v):
                norm = (v - vmin) / (vmax - vmin + 1e-9)
                col = "black" if 0.25 < norm < 0.75 else "white"
                ax.text(jj, ii, f"{v/1000:.1f}k", ha="center", va="center", fontsize=7.5, color=col)
    ax.scatter([bxp], [byp], marker="*", s=220, color="gold", zorder=5)
    plt.colorbar(im, ax=ax, label="HYDROGEL PNL")

plt.tight_layout()
out = "notebooks/r4_plots/hydrogel_sweep_r4.png"
fig.savefig(out, dpi=130, bbox_inches="tight")
p(f"\nPlot saved: {out}")
p(f"\n=== SUMMARY ===")
p(f"Baseline (TE=18, TD=22, EB=18, RM=35):  {baseline:,.0f}")
p(f"Best Phase-1 (TE={best_te}, TD={best_td}):            {grid1[bi,bj]:,.0f}")
p(f"Best all params combined:               {final.get('HYDROGEL_PACK',0):,.0f}")
p(f"Best params: TAKE_EDGE={best_te}  TRAILING_DD={best_td}  EMA_BREAK={best_eb}  RICH_MID_OFFSET={best_rm}")
