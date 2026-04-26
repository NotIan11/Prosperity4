# v16 — Friend's live-delta-recompute (TESTED, LOST $20.8k)

**Status**: tested live, lost vs v12. Important empirical finding.
**Date**: 2026-04-26
**Source**: friend's submission 480983 (likely Rohit per Discord context)

## What it does

Replaces v12's hardcoded `VOUCHER_DELTA` table with **per-strike live OLS
regression** of voucher_mid vs vfe_mid:

- Each `VevOptionTaker` keeps its own 1000-tick `voucher_history` deque
- Every 50 ticks: refits delta + R² from the last n≥200 samples
- Cap = `vfe_equiv_target / max(delta, 0.1)`, capped at `position_limit`
- If R² < 0.5: cap = 0 (don't trade this strike)
- Trades all 8 strikes (4000–5500); R² gate decides which fire live

## LIVE result vs v12

| | v12 (hardcoded δ) | v16 (live δ) | Δ |
|--|--|--|--|
| HG | 8,558 | 8,558 | 0 |
| VFE | 10,192 | 8,469 | -1,722 |
| VEV_5000 | 10,980 | 2,892 | **-8,088** |
| VEV_5100 | 10,676 | 2,907 | **-7,769** |
| VEV_5200 | 8,515 | 3,059 | -5,455 |
| VEV_5300 | 4,870 | 2,175 | -2,694 |
| VEV_4000 | 0 | 1,554 | +1,554 |
| VEV_4500 | 0 | 1,997 | +1,997 |
| VEV_5400 | 0 | 930 | +930 |
| VEV_5500 | 0 | 445 | +445 |
| **TOTAL** | **53,790** | **32,988** | **-20,802** |

## Why it lost

1. **Less data → noisier deltas.** Hardcoded fits used 30k+ historical
   samples. Live refits use max 1000 samples → much higher variance →
   wrong cap sizing on the high-conviction strikes.
2. **R² ≥ 0.5 gate is too conservative early.** Need n≥200 samples to
   start trading → first 200+ ticks of the session are dead. Lost early
   MR opportunities.
3. **Trading 8 strikes diluted concentration.** Captured ~$5k on
   strikes we skip (4000/4500/5400/5500) but lost much more by under-
   sizing the 4 high-conviction ones (5000/5100/5200/5300 lost $24k).

## Verdict for R3 vs R4/R5

- **R3 (stable regime)**: hardcoded deltas WIN. Empirically confirmed.
  30k samples of historical training data is more accurate than 200-1000
  live samples.
- **R4/R5 (potential regime shift)**: live-delta is theoretically correct
  but needs:
  - Warm-start from prior-day's deltas (not zero)
  - Longer warmup window or shorter R² threshold during warmup
  - Hybrid: blend hardcoded × (1 - α) + live × α as samples accumulate

## Files
- `data/teammate_logs/friend_live_delta/480983.{py,log,json}`
