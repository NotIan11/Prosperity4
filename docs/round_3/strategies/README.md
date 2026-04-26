# R3 Strategies — iteration log

One file per submission-candidate version. Each version is a snapshot:
hypothesis, what changed, BT numbers, learnings. Numbered sequentially.

## R3 FINAL SUBMISSION: **v12** (`snapshots/v12_trader.py`)

Live results (3 runs of identical code, portal is stochastic):
- sub #1: **$53,790** (best)
- sub #2: $13,889 (bad-luck run, 25% normal fill rate)
- sub #3: $49,081
- Mean ~$40k, mode ~$50k, ~4x Ian's $13.5k

Other strategies tested live (all lost vs v12):
- v15 (v12 + flow gate): $46,156 — gate cost $7.6k by blocking profitable trades
- v16 (Rohit live-delta): $32,988 — less data → noisier deltas → mis-sized caps
- Ian v2 (cap=300 uniform): $13,528 — bots dodge over-aggression in live

## Index

| Version | Status | Total PnL (3-day BT) | Sharpe | Max DD | Live actual / est | Notes |
|---------|--------|----------------------|--------|--------|----------|-------|
| [v1_baseline](v1_baseline.md) | baseline | 31,606 | 2.50 | 4,459 (1.25%) | — | HG h=8 sym + VFE h=2 sym |
| [v2_vfe_asymmetric](v2_vfe_asymmetric.md) | tested | 33,676 (+6.5%) | 2.46 | 4,264 (1.20%) | — | + VFE bid=2/ask=3 |
| [v3_vfe_flow_skew](v3_vfe_flow_skew.md) | abandoned | 31,222 (-7.3%) | 4.62 | 4,816 (1.24%) | — | + flow-tracker skew (too sticky) |
| [v4_vfe_l1l2_skew](v4_vfe_l1l2_skew.md) | superseded | 34,182 (+8.2%) | 2.57 | 4,264 (0.85%) | 1,220 (live ✓) | + L1-L2 skew |
| [v5_pre_flatten](v5_pre_flatten.md) | abandoned | 30,812 (-9.9%) | 2.60 | 4,264 (0.85%) | — | + end-of-day pre-flatten (wrong threshold) |
| [v6_vouchers](v6_vouchers.md) | superseded | 34,790 (+10.1%) | 2.75 | 4,326 (0.86%) | ~1,225 (est) | + VEV_5300/5400 bias-aware MM |
| [v7_hg_inventory_cap](v7_hg_inventory_cap.md) | superseded | 34,518 (+9.2%) | 2.97 | 3,918 (0.86%) | ~1,225 (est) | + HG soft cap=40 (Calmar-optimal) |
| [v8_hg_takemaker](v8_hg_takemaker.md) | superseded | 119,578 (+278%) | 2.35 | 19,696 (9.91%) | ~6,682 (est) | + Ian's HG take+derisk |
| [v9_vfe_mr_taker](v9_vfe_mr_taker.md) | superseded | 188,449 (+496%) | 6.86 | 22,460 (21.10%) | ~12,451 (est) | + VFE MR taker w/ rolling FV |
| [v10_voucher_taker](v10_voucher_taker.md) | superseded | 361,705 (+1045%) | 8.59 | 42,668 (20.11%) | ~26,050 (est) | + voucher taker w/ strike-aware delta |
| [v11_flow_gate](v11_flow_gate.md) | superseded | 360,407 (+1040%) | 9.29 | 42,668 (20.11%) | ~26,050 (est) | + VFE informed-flow gate |
| **[v12_cap_160](v12_cap_160.md)** | **SHIP — best live** | **460,722 (+1358%)** | **5.20** | **60,493 (20.11%)** | **53,790 LIVE ✓** | v10 + voucher cap target 80→160 |
| [v13_cap_240](v13_cap_240.md) | abandoned | 479,276 (+1417%) | (lower) | (higher) | ~33,985 (est) | v12 + cap→240 (past elbow, +4% PnL only) |
| [v15_gate_cap](v15_gate_cap.md) | abandoned | 458,648 (+1351%) | 5.50 | 60,493 (20.11%) | **46,156 LIVE** (-$7.6k vs v12) | v11+v12; gate kills profitable trades live |
| [v16_friend_live_delta](v16_friend_live_delta.md) | abandoned (friend) | n/a | n/a | n/a | **32,988 LIVE** (-$20.8k vs v12) | Live OLS delta refit; less data than 30k hardcoded → noisier caps |

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
