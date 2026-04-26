# v1 — baseline (symmetric MM, goods only)

**Status**: baseline (not submitted)
**Commit**: `1b08488` (current `src/trader.py`)
**Date**: 2026-04-26

## Hypothesis

Capture the bid-ask spread on HYDROGEL_PACK and VELVETFRUIT_EXTRACT by quoting
passively at `wall_mid ± half_edge` with linear position skew. Tune `half_edge`
to each product's median spread (HG=16 → 8, VFE=5 → 2). Don't trade vouchers.

## Changes from previous version

- N/A — this is the baseline.

## Code

- `src/trader.py` — `wall_mid()` helper, `PassiveMarketMaker` class, `Trader`
  with two strategy instances:
  - HYDROGEL_PACK: `half_edge=8`, `skew_per_unit=0.04`
  - VELVETFRUIT_EXTRACT: `half_edge=2`, `skew_per_unit=0.04`
- `src/utils/black_scholes.py` — present but unused at v1.

## Backtest

```
venv/bin/prosperity4btest cli src/trader.py 3 --merge-pnl --no-out
```

| Day | PnL |
|-----|-----|
| 0 | 14,752 |
| 1 | 10,536 |
| 2 | 6,319 |
| **Total** | **31,606** |

| Metric | Value |
|--------|-------|
| Sharpe | 2.50 |
| Annualized Sharpe | 39.66 |
| Max DD (abs) | 4,459 |
| Max DD (%) | 1.25 |
| Sortino | inf (no losing windows) |
| Calmar | 7.09 |

Per-product PnL by day:

| Product | Day 0 | Day 1 | Day 2 |
|---------|-------|-------|-------|
| HYDROGEL_PACK | 9,743 | 9,963 | 3,309 |
| VELVETFRUIT_EXTRACT | 5,009 | 572 | 3,010 |
| All vouchers | 0 | 0 | 0 |

## Learnings

- HYDROGEL is the workhorse — consistent ~10k/day on days 0–1, but **drops 67%
  on day 2** (3,309 vs 9,743). Affects every config equally; structural day-2
  thing, not a tunable bug. Worth investigating before R4 if R3 day-2 conditions
  recur.
- VFE is volatile across days (5,009 → 572 → 3,010). Symmetric quoting almost
  certainly leaves money on the table given the +0.63/50-tick informed-flow
  drift after buy-aggressors (`docs/round_3/research/07_bot_trades.md`).
- Vouchers are a complete zero — pure goods PnL. Voucher butterfly + smile-RMSE
  gate could plausibly add 30–50/day.
- BT Sharpe 2.50 / max DD 1.25% is comfortable headroom. Live drawdowns may be
  larger (Discord chatter), but adverse-fills EDA found NO toxicity in tape —
  likely inventory squeeze when bots vanish.

## Decision

**Baseline only**. Do not submit as-is. Use as the comparison point for v2+.

## Next candidates

- **v2** — VFE asymmetric quoting (bid edge=2, ask edge=3) + informed-flow skew
- **v3** — HYDROGEL outer layer at half_edge=9 + tighter inventory skew
- **v4** — Add voucher butterfly (long 5400 / short 5300) gated on smile RMSE
