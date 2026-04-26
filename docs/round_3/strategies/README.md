# R3 Strategies — iteration log

One file per submission-candidate version. Each version is a snapshot:
hypothesis, what changed, BT numbers, learnings. Numbered sequentially.

## Index

| Version | Status | Total PnL (3-day BT) | Sharpe | Max DD | Live est | Notes |
|---------|--------|----------------------|--------|--------|----------|-------|
| [v1_baseline](v1_baseline.md) | baseline | 31,606 | 2.50 | 4,459 (1.25%) | — | HG h=8 sym + VFE h=2 sym |
| [v2_vfe_asymmetric](v2_vfe_asymmetric.md) | tested | 33,676 (+6.5%) | 2.46 | 4,264 (1.20%) | — | + VFE bid=2/ask=3 |
| [v3_vfe_flow_skew](v3_vfe_flow_skew.md) | abandoned | 31,222 (-7.3%) | 4.62 | 4,816 (1.24%) | — | + flow-tracker skew (too sticky) |
| [v4_vfe_l1l2_skew](v4_vfe_l1l2_skew.md) | superseded | 34,182 (+8.2%) | 2.57 | 4,264 (0.85%) | 1,220 (live ✓) | + L1-L2 skew |
| [v5_pre_flatten](v5_pre_flatten.md) | abandoned | 30,812 (-9.9%) | 2.60 | 4,264 (0.85%) | — | + end-of-day pre-flatten (wrong threshold) |
| [v6_vouchers](v6_vouchers.md) | superseded | 34,790 (+10.1%) | 2.75 | 4,326 (0.86%) | ~1,225 (est) | + VEV_5300/5400 bias-aware MM |
| **[v7_hg_inventory_cap](v7_hg_inventory_cap.md)** | **ship-candidate** | **34,518 (+9.2%)** | **2.97** | **3,918 (0.86%)** | **~1,225 (est)** | + HG soft cap=40 (Calmar 8.81 — best risk-adj) |

`Live est` = `BT day-2 first-1000-tick PnL / 1.37` (calibration factor from v4
actual; see `docs/round_3/research/14_bt_vs_live_calibration.md`).

## Snapshots

Easy copy-paste into IMC portal: `snapshots/vN_trader.py` (frozen per version).

## How to use this folder

1. Before changing `src/trader.py`, copy the previous version's doc to `vN_<name>.md`.
2. Write the **Hypothesis** and **Changes from previous** sections BEFORE editing code.
3. Make the code change. Tag the commit so the BT is reproducible.
4. Run `venv/bin/python scripts/bt_dual.py` — gives full + portal-slice + live estimate.
5. Fill in **Learnings**. What surprised you. What to try next.

## Template

See `_template.md`.
