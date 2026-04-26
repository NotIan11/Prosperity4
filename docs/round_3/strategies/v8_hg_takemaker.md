# v8 — HYDROGEL takemaker (ported from Ian)

**Status**: tested, ship-candidate (high PnL / high variance)
**Commit**: TBD
**Date**: 2026-04-26

## Hypothesis

Replace our pure-passive HG market-maker with Ian's take-based strategy.
Per `docs/round_3/research/15_teammate_ian_compare.md`: Ian's HG made
**+8,558 live** vs our **+1,238** (7x). His full 3-day BT HG contribution
is ~108k vs our ~23k. Aggressive taking when far from FAIR=9991 captures
spread that pure passive can't.

## Changes from v7

- New `HydrogelTakeMaker` class (ported verbatim from Ian's
  `HydrogelStrategy`):
  - Hardcoded FAIR = 9991
  - Take asks below FAIR-18, take bids above FAIR+18 (MAX_TAKE=25/tick)
  - Passive MM at FAIR ± 20 (wider than our previous 8)
  - Three derisking triggers: VERY_RICH_MID, trailing drawdown, EMA break
  - block_new_buys when mid >= FAIR+35
- Soft cap on PassiveMarketMaker still exists, but HG no longer uses
  PassiveMarketMaker. (Soft cap at v7 cap=40 was redundant with Ian's
  trailing-drawdown derisk; sweep showed identical numbers across caps.)
- VFE and vouchers UNCHANGED from v7.

## Position-limit tradeoff curve (HG only sweep)

Tested HG `position_limit` from 60 to 200 holding all else equal:

| HG limit | Total PnL | Sharpe | Max DD abs | Max DD% | Calmar |
|---|---|---|---|---|---|
| 60 | 44,494 | 2.32 | 5,486 | ~3% | **8.11** |
| 80 | 54,314 | **2.44** | 7,366 | ~4% | 7.37 |
| 100 | 68,092 | 2.17 | 9,391 | ~5% | 7.25 |
| 120 | 77,524 | 2.23 | 11,451 | ~6% | 6.77 |
| 150 | 93,360 | 2.27 | 14,546 | ~7.5% | 6.42 |
| **200 (Ian's)** | **119,578** | 2.35 | 19,696 | 9.91% | 6.07 |

Picked **limit=200** for max PnL. Defers the risk-management decision to
v9/v10 (where we add VFE/voucher PnL on top — better metrics there can
offset HG variance).

## Backtest

| Day | v7 | v8 | Δ |
|---|---|---|---|
| 0 | 15,444 | 57,359 | +41,915 |
| 1 | 11,380 | 23,450 | +12,070 |
| 2 | 7,694 | 38,769 | +31,075 |
| **Total** | **34,518** | **119,578** | **+85,060 (+247%)** |

| Metric | v7 | **v8** |
|---|---|---|
| Total PnL | 34,518 | **119,578** |
| Sharpe | 2.97 | 2.35 |
| Annualized Sharpe | 47.12 | 37.26 |
| Max DD abs | 3,918 | 19,696 |
| Max DD% | 0.86% | 9.91% |
| Calmar | 8.81 | 6.07 |
| BT day-2 first-1000-tick | 1,678 | 9,154 |
| Estimated live PnL | ~1,225 | ~6,682 |

## Per-product BT contribution (v8, day 0/1/2)

| Product | Day 0 | Day 1 | Day 2 |
|---|---|---|---|
| HYDROGEL_PACK | 51,418 | 21,566 | 34,820 |
| VFE | 5,970 | 1,652 | 3,545 |
| VEV_5300 | 57 | 181 | 288 |
| VEV_5400 | -86 | 51 | 116 |

HG is now our biggest contributor by far (~108k of 119k). Vouchers and VFE
unchanged from v7 (still untouched logic).

## Learnings

- 3.5x PnL improvement from one product change. Ian's design is genuinely
  better for HG than our passive-only.
- Max DD jumped 5x (3.9k → 19.7k) and DD% jumped 11x (0.86% → 9.91%).
  This is the price of leverage. Tournament scoring is on PnL, so we
  accept it for now — but it means a bad day-2 sample could swing us
  significantly.
- Sharpe dropped (2.97 → 2.35) because Ian's strategy has high day-to-day
  variance (day 1 is 23k vs day 0 57k). We make more $ but with less
  consistency.
- Soft cap doesn't help here because Ian's takes bypass the passive cap
  gate. Hard limit reduction is the only effective constraint, but it
  proportionally costs PnL.

## Decision

**New ship-candidate.** v7 was Calmar-optimal; v8 is PnL-optimal. For
tournament leaderboard, ship v8. If we observe live blowups, fall back
to v7 or sweep down to limit=100-120 sweet spot.

## Next candidates

- **v9** — port Ian's VFE MR (FV=5250 + sweep + 40-tick stop). Add our
  L1-L2 skew as overlay. Use rolling FV per regime finding (16_regime_patterns.md:
  VFE FV drifts 5244→5258 across days; hardcoded 5250 = day-2 short bias).
- **v10** — port Ian's voucher delta-1, but with **strike-aware delta sizing**
  (16_regime_patterns.md: empirical delta is 0.74/0.65/0.43/0.13/0.05 for
  4000/5000/5200/5400/5500, NOT 1.0). Cap=100 not 300. Skip 4000/4500/5500.
