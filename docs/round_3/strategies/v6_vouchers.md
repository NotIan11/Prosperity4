# v6 — Voucher MM with historical bias (CURRENT FLOOR)

**Status**: tested, ship-candidate
**Commit**: TBD
**Date**: 2026-04-26

## Hypothesis

Per `docs/round_3/research/05_voucher_chain.md`: VEV_5300 has persistent rich
bias (+1.83 ticks vs smile theo) and VEV_5400 has persistent cheap bias
(-2.0 ticks). Bias-aware passive MM should harvest both:
- VEV_5300 rich → asymmetric quoting net-short (tighter ask)
- VEV_5400 cheap → asymmetric quoting net-long (tighter bid)

No smile fitting at runtime — bias is observed historically and hardcoded.
Saves Lambda time + complexity.

## Changes from v4

- Added `VEV_5300` and `VEV_5400` to `POSITION_LIMITS` (300 each per brief).
- Added two passive MM instances:
  - VEV_5300: `bid_edge=1, ask_edge=0` (at-touch ask = aggressive sell side)
  - VEV_5400: `bid_edge=1, ask_edge=2` (at-touch bid = aggressive buy side)
- Position skew per voucher: 0.02 (lower than goods because of larger limit).
- Other vouchers (4000, 4500, 5000, 5100, 5200, 5500, 6000, 6500) NOT traded:
  - Wide-spread strikes (4000-5000): our quotes never historically filled in BT.
  - VEV_6000/6500: ghost trades, dead book.

## Code

- `src/trader.py` — only adds 2 strategy instances; no new classes.
- Snapshot: `docs/round_3/strategies/snapshots/v6_trader.py`.
- **Single file, no imports beyond stdlib + `datamodel`.** Paste-ready for IMC.

## Backtest

| Day | v4 | v6 | Δ |
|-----|------|------|------|
| 0 | 15,713 | 15,684 | -29 |
| 1 | 11,616 | 11,848 | +232 |
| 2 | 6,854 | 7,258 | +404 |
| **Total** | **34,182** | **34,790** | **+608 (+1.78%)** |

| Metric | v4 | **v6** |
|--------|------|------|
| Total PnL | 34,182 | **34,790** |
| Sharpe | 2.57 | **2.75** |
| Max DD (abs) | 4,264 | 4,326 |
| Max DD (%) | 0.85 | 0.86 |
| Calmar | 8.02 | **8.04** |

Voucher contribution by day:

| Voucher | Day 0 | Day 1 | Day 2 | Total |
|---------|-------|-------|-------|-------|
| VEV_5300 | +57 | +181 | +288 | **+526** |
| VEV_5400 | -86 | +51 | +116 | +81 |

## Learnings

- VEV_5300 rich-bias quoting is the real winner (+526 across 3 days, growing
  per day). Confirms the EDA's "+1.83 tick rich" finding survives in BT.
- VEV_5400 only contributes +81 — the long-bias quote works on days 1-2 but
  loses -86 on day 0. Net positive but small.
- VEV_5000 was tested with `half_edge=1` and produced -30 on day 1, zero other
  days — quoting doesn't fill in historical tape. Dropped.
- IMC BT only matches passive quotes against actual historical trades —
  "inside the spread" quotes at non-printed prices = no fills. This makes
  voucher MM hard for vouchers with wide spreads and few historical trades.
- Cumulative wins:
  - PnL +10% over baseline (31,606 → 34,790)
  - Sharpe +10% (2.50 → 2.75)
  - Max DD% -32% (1.25% → 0.86%)
  - Calmar +13% (7.09 → 8.04)

## Decision

**New ship-candidate.** Strictly better than v4 on PnL and Sharpe. DD% is
basically unchanged (+0.01pp). Single-file, paste-ready.

## Next candidates

- **v7** — Add real smile fit + RMSE gate (from EDA #13). Trade VEV_5300
  short / VEV_5400 long aggressively when residual is extreme AND smile RMSE
  is above rolling median. Bigger upside but needs BS inlined.
- **v8** — Address the live "dip": instrument BT day-2 ticks 91-99k to see
  if the same pattern is reproducible there; if so, add a targeted defense.
- **v9** — Compare to teammates' algos when shared, port best parts.
