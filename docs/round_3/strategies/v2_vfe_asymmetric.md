# v2 — VFE asymmetric quoting

**Status**: tested (not submitted)
**Commit**: TBD (current uncommitted edit on top of v1)
**Date**: 2026-04-26

## Hypothesis

VFE buy-aggressor flow is informed (+0.63 mid drift / 50 ticks, t=+2.64 from
`docs/round_3/research/07_bot_trades.md`). When we sell to a buy-aggressor at
our ask, mid tends to drift up — we lose. **Defense**: quote the ask one tick
farther from fair than the bid. Same fills on the safe side, fewer toxic fills
on the dangerous side.

## Changes from previous version

- `PassiveMarketMaker` now accepts optional `bid_edge` / `ask_edge` (falls back
  to `half_edge` for symmetric mode → v1 behavior preserved).
- VFE config: `bid_edge=2, ask_edge=3`.
- HYDROGEL unchanged (still symmetric `half_edge=8`).
- No new files, no voucher logic.

## Code

- `src/trader.py` — `PassiveMarketMaker.__init__` extended; VFE strategy
  instance gets the asymmetric kwargs.

## Backtest

```
venv/bin/prosperity4btest cli src/trader.py 3 --merge-pnl --no-out
```

| Day | v1 PnL | v2 PnL | Δ |
|-----|--------|--------|---|
| 0 | 14,752 | 15,685 | +933 |
| 1 | 10,536 | 11,426 | +890 |
| 2 | 6,319 | 6,565 | +246 |
| **Total** | **31,606** | **33,676** | **+2,070 (+6.5%)** |

| Metric | v1 | v2 |
|--------|-------|-------|
| Sharpe | 2.50 | 2.46 |
| Annualized Sharpe | 39.66 | 39.05 |
| Max DD (abs) | 4,459 | 4,264 |
| Max DD (%) | 1.25 | 1.20 |
| Calmar | 7.09 | 7.90 |

Per-product PnL by day:

| Product | Day 0 | Day 1 | Day 2 |
|---------|-------|-------|-------|
| HYDROGEL_PACK | 9,743 | 9,963 | 3,309 |
| VELVETFRUIT_EXTRACT (v1) | 5,009 | 572 | 3,010 |
| VELVETFRUIT_EXTRACT (v2) | 5,942 | 1,464 | 3,256 |
| VFE delta | +933 | +892 | +246 |

## Learnings

- Asymmetric edge captured the informed-flow defense as predicted. Day 1 is the
  biggest win (+156% on VFE), consistent with day 1 being the toxic-flow day.
- HYDROGEL byte-identical (no changes there) — same numbers, confirms the BT is
  deterministic.
- Sharpe dipped slightly (2.50 → 2.46) because we trade more VFE volume now
  with non-zero variance, but max DD also improved (4,459 → 4,264). Net better.
- Calmar improved 7.09 → 7.90 — best risk-adjusted version so far.
- Single-line config change, ~5 lines code. Cheap win.

## Decision

**Ship as the floor**. v3+ should be measured against v2, not v1.

## Next candidates

- **v3** — Add informed-flow quote skew to VFE (lean inventory long when
  net buy-flow > +5 over last 50 ticks). Defensive use of EDA #12 finding.
  Expected +20–60 seashells/day.
- **v4** — Add iacobus L1-L2 quote skew on VFE (small effect, but free).
- **v5** — Voucher butterfly (long 5400 / short 5300) gated on smile RMSE.
  Biggest potential upside but most complex.
