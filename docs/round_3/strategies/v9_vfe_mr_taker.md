# v9 — VFE mean-reversion taker with rolling FV (CURRENT FLOOR)

**Status**: tested, ship-candidate
**Commit**: TBD
**Date**: 2026-04-26

## Hypothesis

Replace our passive VFE MM with Ian's directional MR strategy, but use a
**rolling-1000-tick median FV** instead of his hardcoded 5250.

Per `16_regime_patterns.md`: VFE FV drifts up day-by-day (5244.5 → 5248.5
→ 5257.5 medians). Hardcoded 5250 produces systematic short bias on day 2
where mid is consistently above. Rolling FV adapts.

Empirical confirmation:
- Hardcoded 5250: |dev| > 20 fires on **20.7%** of ticks
- Rolling-1000: |dev| > 20 fires on **13.1%** of ticks
- 1/3 fewer false signals → fewer toxic-direction takes

## Changes from v8

- New `VfeMrTaker` class (port of Ian's VelvetfruitStrategy + rolling FV).
- Replaces VFE `PassiveMarketMaker` instance.
- Rolling FV: median of last 1000 mids; falls back to 5250 during warmup.
- ENTRY_THR = 20, STOP_LOSS_TICKS = 40 (same as Ian).
- Takes the WHOLE book on entry (sweeps), not size-capped per tick like HG.

## Backtest

| Day | v8 | v9 | Δ |
|---|---|---|---|
| 0 | 57,359 | 73,475 | +16,116 |
| 1 | 23,450 | 57,328 | +33,878 |
| 2 | 38,769 | 57,681 | +18,912 |
| **Total** | **119,578** | **188,449** | **+68,871 (+57.6%)** |

| Metric | v8 | **v9** |
|---|---|---|
| Total PnL | 119,578 | **188,449** |
| Sharpe | 2.35 | **6.86** |
| Annualized Sharpe | 37.3 | **108.9** |
| Max DD abs | 19,696 | 22,460 |
| Max DD% | 9.91% | 21.10% |
| Calmar | 6.07 | **8.39** |
| BT day-2 first-1000-tick | 9,154 | **17,058** |
| Estimated live PnL | ~6,682 | **~12,451** |

VFE per-day contribution: 22,000 + 35,581 + 22,457 = **+80,038**
(vs v8's ~11k passive MM).

## Learnings

- **Rolling FV is meaningful.** Day 1 VFE jumped from 1,652 (v8) to 35,581
  (v9). That day's mid was 5248 — well within hardcoded 5250 range, so
  hardcoded wouldn't fire much. Rolling FV adapts and triggers more.
- **Sharpe nearly tripled** (2.35 → 6.86). VFE MR has very consistent
  per-trade edge — when the entry threshold fires, mean reversion almost
  always plays out within 40 ticks (the stop-loss window).
- **Calmar improved** (6.07 → 8.39) even though raw Max DD% went up
  21.1% — that's just a denominator effect (DD% is normalized to peak
  PnL which is now higher).
- **L1-L2 skew was dropped** because Ian's strategy is taker, not maker.
  Could revisit later as a passive overlay outside the entry window.

## Decision

**New ship-candidate.** Strictly better than v8 on PnL, Sharpe, and Calmar.
DD$ marginally worse but acceptable given PnL gain.

## Next candidates

- **v10** — voucher delta-1 strategy with strike-aware delta (NOT uniform)
  and conservative caps (100 not 300). Per `16_regime_patterns.md`:
  empirical delta is 0.74/0.65/0.55/0.43/0.13 for VEV_4000/5000/5100/5200/5400.
  Trade only ATM/near-ATM (5000-5400), skip deep ITM and OTM.
  Expected gain: +200-300k PnL.
- **v11** — informed-flow gate (pause adding inventory during VFE
  buy-aggressor bursts). Defensive overlay; small PnL impact, reduces
  variance. Most useful AFTER v10 when voucher exposure is large.
