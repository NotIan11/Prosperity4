# v12 — Voucher cap target 80 → 160 (PnL-best)

**Status**: tested, ship-candidate (PnL winner)
**Date**: 2026-04-26

## Hypothesis

v10 kept `vfe_equiv_target=80` very conservative. JOURNEY noted this leaves
PnL on the table. Doubling the leverage knob should buy ~2x voucher PnL
linearly, paid for in DD/Sharpe.

## Changes from v10

- Single change: `voucher_cap_for(vfe_equiv_target=80)` → `=160`.
- New per-strike caps:
  - VEV_5000: 122 → 245
  - VEV_5100: 139 → 277
  - VEV_5200: 183 → 300 (hits IMC limit)
  - VEV_5300: 293 → 300 (hits IMC limit)
- Two strikes saturate at the hard cap, so this also kills strike-aware
  sizing for the deeper-OTM half. (v13 pushes to 240 and saturates everything.)

## Backtest

| Metric | v10 | **v12** |
|---|---|---|
| Total PnL | 361,705 | **460,722 (+27%)** |
| Sharpe | 8.59 | 5.20 |
| Max DD | 42,668 | 60,493 |
| Calmar | 8.48 | 7.62 |
| BT day-2 first-1000 | 35,688 | 46,113 |
| Est live | ~26,050 | **~33,659** |

## Decision

Pure leverage tradeoff: +27% PnL for ~40% lower Sharpe. With ~1 hour to round
close and v10 known-safe at ~26k live, v12 is the aggressive ship.

## LIVE RESULT — went insane

**LIVE TOTAL: $53,790** (vs estimate $33,659 — 1.60x BETTER)

Per product:
- VEV_5000: 10,980
- VEV_5100: 10,676
- VEV_5200: 8,515
- VEV_5300: 4,870 (smallest delta → smallest absolute PnL ✓)
- VFE: 10,192 (rolling-FV win)
- HG: 8,558 (Ian's takemaker)
- 4000/4500/5400/5500/6000/6500: 0 (correctly skipped)

Calibration (live/BT slice) = 1.17 for take-based (vs 0.73 for passive MM).

**vs Ian v2 live: 13,528 → ~4x.**

## Overfitting check — clean

- Live > BT estimate (1.60x): opposite of overfitting
- No PnL concentration: 4 strikes evenly profitable; ratios match expected delta ordering
- Skipped strikes stayed at zero — no surprise trades
- Per-strike sizing held up live (strike-aware caps generalized)

## Open

- v15 (v11+v12 stacked) tested LIVE: -$7.6k vs v12. Gate kills upside.
  See v15_gate_cap.md.
