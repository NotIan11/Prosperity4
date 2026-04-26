# R3 Strategies — iteration log

One file per submission-candidate version. Each version is a snapshot:
hypothesis, what changed, BT numbers, learnings. Numbered sequentially.

## Index

| Version | Status | Total PnL (3-day BT) | Sharpe | Max DD | Notes |
|---------|--------|----------------------|--------|--------|-------|
| [v1_baseline](v1_baseline.md) | baseline | 31,606 | 2.50 | 4,459 (1.25%) | HG h=8 sym + VFE h=2 sym, no vouchers |
| [v2_vfe_asymmetric](v2_vfe_asymmetric.md) | tested | 33,676 (+6.5%) | 2.46 | 4,264 (1.20%) | + VFE bid=2/ask=3 |
| [v3_vfe_flow_skew](v3_vfe_flow_skew.md) | abandoned | 31,222 (-7.3%) | 4.62 | 4,816 (1.24%) | + flow-tracker skew (too sticky, lost PnL) |
| **[v4_vfe_l1l2_skew](v4_vfe_l1l2_skew.md)** | **ship-candidate** | **34,182 (+8.2%)** | **2.57** | **4,264 (0.85%)** | + L1-L2 skew (Calmar 8.02 — best yet) |

## Snapshots

Easy copy-paste into IMC portal: `snapshots/vN_trader.py` (frozen per version).

## How to use this folder

1. Before changing `src/trader.py`, copy the previous version's doc to `vN_<name>.md`.
2. Write the **Hypothesis** and **Changes from previous** sections BEFORE editing code.
3. Make the code change. Tag the commit so the BT is reproducible.
4. Run `venv/bin/prosperity4btest cli src/trader.py 3 --merge-pnl --no-out`. Paste numbers.
5. Fill in **Learnings**. What surprised you. What to try next.

## Template

See `_template.md`.
