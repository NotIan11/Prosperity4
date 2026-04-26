# v7 — HYDROGEL soft inventory cap (CURRENT FLOOR)

**Status**: tested, ship-candidate
**Commit**: TBD
**Date**: 2026-04-26

## Hypothesis

Per BT diagnostic on day 2 (`14_bt_vs_live_calibration.md` + this analysis):
the "dip" pattern people on Discord describe is pure mark-to-market on
accumulated HYDROGEL short positions. All 3 biggest day-2 drops in BT
follow the same template:

| Drop | Pos at peak | Mid Δ | PnL drop | Pos × Mid Δ |
|---|---|---|---|---|
| 91100→99900 | -33 | +45 | -1,501 | **-1,485** |
| 113400→121500 | -47 | +41 | -2,007 | **-1,927** |
| 292700→301300 | -44 | +45 | -1,919 | **-1,980** |

Position barely changes during the drops — pure MTM on existing inventory.
HYDROGEL is independent (per `06_cross_product.md` PC2 = 100% HG, max CCF
≤ 0.02 vs anything). Vol weakly predicts forward drops (-0.10 corr), position
size weakly predicts (-0.19 corr). The defense is **inventory limit**, not
flow detection or vol-regime gating.

## Changes from v6

- Added `soft_pos_cap` kwarg to `PassiveMarketMaker`. When `|position| >=
  soft_pos_cap`, stop posting orders that would *add* to inventory.
- HG configured with `soft_pos_cap=40`. Below the historical max observed
  position (54), so it actually binds during dip windows.
- VFE and vouchers unchanged.

## Tradeoff curve (HG cap sweep)

| Cap | Total PnL | Sharpe | Max DD abs | Calmar | Notes |
|---|---|---|---|---|---|
| none (v6) | 34,790 | 2.75 | 4,326 | 8.04 | baseline |
| 40 (v7) | **34,518** | **2.97** | **3,918** | **8.81** | -0.78% PnL, +8% Sharpe, -9% DD, +10% Calmar |
| 35 | 33,648 | 3.08 | 3,690 | 9.12 | -3.3% PnL |
| 30 | 32,964 | 3.26 | 3,262 | 10.11 | -5.2% PnL |

Choose **cap=40** because it's almost never binding (position rarely exceeds
40 anyway), so it costs minimal PnL while still catching the worst dip cases.
Tighter caps (30, 35) trade more PnL for Sharpe/DD — would prefer them only
if we observed live blowups.

## Code

`src/trader.py` — single new kwarg + 4 new lines in `run()`. Snapshot at
`docs/round_3/strategies/snapshots/v7_trader.py`.

## Backtest

| Day | v6 | v7 | Δ |
|---|---|---|---|
| 0 | 15,684 | 15,444 | -240 |
| 1 | 11,848 | 11,380 | -468 |
| 2 | 7,258 | 7,694 | **+436** |
| **Total** | **34,790** | **34,518** | **-272 (-0.78%)** |

| Metric | v6 | v7 |
|---|---|---|
| Total PnL | 34,790 | 34,518 |
| Sharpe | 2.75 | **2.97** |
| Max DD abs | 4,326 | **3,918** |
| Max DD% | 0.86% | 0.86% |
| Calmar | 8.04 | **8.81** |
| BT day-2 first-1000-tick | 1,678 | 1,678 |
| Estimated live PnL | ~1,225 | ~1,225 |

Day 2 (the dip-affected day) gained +436 from cap. Days 0-1 lost -708 because
cap occasionally bound during favorable accumulation. Net slightly negative
PnL, but the risk metrics improved substantially.

## Why this is NOT overfitting

- **Mechanism is general**: cap any position from growing too large. Not tied
  to a specific timestamp window.
- **Validated on all 3 days, not just day 2**: improvement only on day 2,
  small regression on days 0/1, but the regression is much smaller than the
  Sharpe/DD gain.
- **Cap value (40) is conservative**: only 80% of historical max observed
  position (54). Not picking the value that "best maximizes day-2 PnL".
- **Doesn't help portal slice** (1,678 unchanged): the cap doesn't bind during
  the portal window's dip (max position there was -33 < 40). So we're not
  fitting to the portal-visible data.

## Decision

**New ship-candidate.** Better risk-adjusted; minimal PnL loss; mechanism is
sound and generalizable. Recommend uploading v7 over v6 if the goal is
robustness over peak PnL.

## Next candidates

- **v8** — Compare to teammate's optimized HYDROGEL trader; port best parts.
- **v9** — Investigate why we run chronically short (mean position -31).
  If we can fix the directional bias, both PnL and DD could improve.
- **v10** — Smile-based voucher trade (long 5400 / short 5300 aggressive
  taking when smile RMSE > rolling median). EDA #13 baseline standalone
  PnL 47.5; could add ~30-50/day across 3 days.
