# v10 — Voucher delta-1 taker (strike-aware) (CURRENT FLOOR)

**Status**: tested, ship-candidate
**Commit**: TBD
**Date**: 2026-04-26

## Hypothesis

Vouchers are deterministic functions of VFE (no theta, no IV variation —
confirmed in `05_voucher_chain.md` and `15_teammate_ian_compare.md`).
Trade them as leveraged bets on VFE deviation from FV. Ian does this
with uniform cap=300 across all 8 strikes — that bleeds on deep ITM
(VEV_4000 lost 1,350 in his live).

**Key upgrade from Ian**: STRIKE-AWARE caps based on EMPIRICAL DELTA
(per `16_regime_patterns.md`):

| Strike | Empirical δ | R² | Our cap (80 VFE-equiv target) |
|--------|------|----|---|
| VEV_4000 | 0.745 | 0.354 | SKIP (low R²) |
| VEV_4500 | 0.662 | 0.358 | SKIP (low R²) |
| **VEV_5000** | 0.654 | 0.568 | **122** |
| **VEV_5100** | 0.577 | 0.586 | **139** |
| **VEV_5200** | 0.437 | 0.515 | **183** |
| **VEV_5300** | 0.273 | 0.386 | **293** |
| VEV_5400 | 0.129 | 0.292 | SKIP (R² too low, cap > 300) |
| VEV_5500 | 0.055 | 0.121 | SKIP (noise) |

Cap formula: `cap = round(vfe_equiv_target / delta)`, capped at 300 (IMC limit).
80 VFE-equiv across 4 strikes = 320 total VFE-equivalent voucher exposure.

## Changes from v9

- New `VevOptionTaker` class (port of Ian's `VevOptionStrategy` + rolling FV).
  Uses our v9 rolling-1000-median FV mechanism (regime-adaptive).
- `VOUCHER_DELTA` dict + `voucher_cap_for()` helper for strike-aware sizing.
- Trades VEV_5000 / 5100 / 5200 / 5300 only.
  Replaces v6 passive bias-MM on 5300/5400.
- HYDROGEL (v8) and VFE (v9) unchanged.

## Code

`src/trader.py` — adds `VevOptionTaker` class + `VOUCHER_DELTA` dict + 4 new
strategy instances. Snapshot at `docs/round_3/strategies/snapshots/v10_trader.py`.

## Backtest

| Day | v9 | **v10** | Δ |
|---|---|---|---|
| 0 | 73,475 | 124,592 | +51,117 |
| 1 | 57,328 | 135,859 | +78,531 |
| 2 | 57,681 | 108,254 | +50,573 |
| **Total** | **188,449** | **361,705** | **+173,256 (+92%)** |

| Metric | v9 | **v10** |
|---|---|---|
| Total PnL | 188,449 | **361,705** |
| Sharpe | 6.86 | **8.59** |
| Annualized Sharpe | 108.9 | **136.3** |
| Max DD abs | 22,460 | 42,668 |
| Max DD% | 21.10% | 20.11% |
| Calmar | 8.39 | **8.48** |
| BT day-2 first-1000-tick | 17,058 | **35,688** |
| Estimated live PnL | ~12,451 | **~26,050** |

Voucher contribution (3-day total):
- VEV_5000: 41,598
- VEV_5100: 45,348
- VEV_5200: 44,994
- VEV_5300: 41,923
- **Total: ~174k**

Per-strike PnL is roughly equal — confirms strike-aware sizing equalizes
exposure. Ian's uniform sizing produced 6x range (5100=110k, 5300=52k).

## Comparison vs Ian's full strategy

| | Ian v2 BT | **Our v10 BT** |
|---|---|---|
| Total | 769,690 | 361,705 (47% of his) |
| Sharpe | 7.13 | **8.59** |
| Max DD abs | 115,257 | 42,668 (37% of his) |
| Calmar | 6.68 | **8.48** |
| Per-strike voucher PnL | 110/85/52/24/19/3k (uneven) | **41/45/45/42k (even)** |
| Live result | 13,528 actual | ~26,050 estimated |

We have **47% of his PnL but BETTER Sharpe and Calmar**. His extra PnL is
all leverage — same logic, more units. We could close the gap by raising
`vfe_equiv_target` from 80 to 160 (rough 2x → ~700k). Or add 4000/4500
back with smaller caps.

## Learnings

- **Strike-aware delta sizing is the trick Ian missed.** His VEV_4000 lost
  -1,350 because uniform cap=300 means 300 × 0.745 = 224 VFE-equiv per
  strike — way more than his cap on near-ATM strikes effectively.
- **R² as a strike filter** is strict but smart. Skipping 4000/4500/5400/5500
  costs us ~50k of "noisy PnL" but cleans up the tail risk.
- **Sharpe 8.59 is huge** — comparable to Ian's 7.13 despite half the PnL.
  This is the difference between aggressive and risk-aware leverage.
- The rolling-FV + strike-aware combo means signals are consistent: only
  trade when VFE is genuinely far from regime-adjusted FV, only on strikes
  whose voucher price is genuinely predictable from VFE.

## Decision

**New ship-candidate, strictly best version.** Beats every prior version on
PnL, Sharpe, AND Calmar simultaneously. First "Pareto-dominant" version.

## Next candidates

- **v11** — informed-flow gate: pause adding voucher inventory during VFE
  buy-aggressor bursts. Defensive overlay. Low PnL impact, reduces tail
  variance. Most useful now that voucher exposure is ~174k.
- **v12** — sweep `vfe_equiv_target` (80 → 120 → 160) to find the
  PnL/Calmar elbow. 80 leaves PnL on the table; too high creates
  Ian-style variance.
- **v13** — try adding VEV_4000/4500 with smaller caps (delta-corrected
  but R²-discounted: cap = (target/delta) * R²).
