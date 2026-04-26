# R3 — VFE informed-flow signal: OFFENSIVE feasibility

Source: `notebooks/12_vfe_offensive.py`, 3 days pooled
(`prices_round_3_day_{0,1,2}.csv`, `trades_round_3_day_{0,1,2}.csv`).
Plots: `plots/12_signal_vs_drift.png`, `plots/12_equity_curves.png`.
Numerics: `12_ic_summary.csv`, `12_bt_long.csv`, `12_bt_short.csv`,
`12_bt_midonly.csv`.

## Question

Earlier (`07_bot_trades.md`) found VFE buy-aggressor flow predicts +0.63t mid
drift over 50 ticks (t=+2.64). That's defensive (don't be the seller). Can
we be **offensive** — go long after observing aggressive buy flow?

## Method

- Aggressor side per trade: `buy_aggr if price >= mid else sell_aggr`.
- Signal: `net_buyflow_K = sum(buy_qty − sell_qty)` over last K ticks
  (K ∈ {10, 50, 100}, summed per-day, no cross-day leak).
- Forward returns: `mid[t+h] − mid[t]` for h ∈ {1, 5, 20, 50}.
- Backtests: enter long when `net_buyflow_K > thr`, exit after N ticks.
  Two cost models:
  1. **Mid-to-mid** (gross alpha, no costs).
  2. **Cross spread both sides** (entry at ask, exit at bid) — realistic
     when the signal forces aggressive execution.

## Headline result

**The signal is real but uneconomic. Not tradeable as a directional taker.**

### IC (Pearson, signed)

| K | h | n | corr | t |
|---:|---:|---:|---:|---:|
| 50 | 50 | 29,850 | **+0.048** | **+8.3** |
| 100 | 50 | 29,850 | +0.036 | +6.2 |
| 50 | 20 | 29,940 | +0.033 | +5.6 |
| 10 | 1  | 29,997 | +0.024 | +4.2 |

Signal is statistically robust at every horizon. Best is K=50, h=50.

### Mid-to-mid PnL (no spread, no fees) — best LONG configs

| K | thr | N | trades | mean (t) | sharpe/trade | total |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 10 | 20 | 118 | +1.36 | 0.33 | +161 |
| 50 | 20 | 50 | 66  | +1.30 | 0.17 | +86  |
| 50 | 20 | 20 | 120 | +0.73 | 0.15 | +88  |
| 50 | 3  | 50 | 352 | +0.73 | 0.11 | +256 |

Gross alpha at the best operating point is ~1 tick per trade.

### Realistic cost: VFE spread is ~5 ticks

```
spread:  mean 4.99,  median 5,  std 0.85,  min 1, max 6
```

Round-trip cost crossing the spread = **~5 ticks**. Gross edge = **~1 tick**.

### Cross-spread backtest — every config loses

| K | thr | N | trades | mean (t) | total |
|---:|---:|---:|---:|---:|---:|
| 10 | 10 | 50 | 98  | −3.12 | −306 |
| 50 | 20 | 50 | 66  | −3.12 | −206 |
| 100 | 20 | 50 | 138 | −3.78 | −522 |

Every (K, thr, N) in the long grid produces negative PnL once we pay the
spread. Same picture for shorts (mostly worse — the signal is asymmetric).

## Interpretation

- The R3 finding "+0.63t over 50 ticks" was already smaller than half the
  VFE bid-ask spread (≈2.5t). Going OFFENSIVE requires lifting the offer
  and later hitting the bid — which costs a full spread (~5t) — so the
  alpha is **eaten ~5x over** by execution friction.
- IC scales with K and h (more flow context → more predictive), but the
  per-trade magnitude never approaches the spread. Even the best
  high-threshold buckets average <1.5 ticks gross.
- Short side is weaker (sell-aggressor was insignificant in 07). Mid-only
  short PnL is near zero or negative at every threshold.

## Decision

**Tradeable as offensive directional taker?  NO.**

The signal is genuine (IC t-stats up to +8) but the spread eats it.

**How to use it instead** (defensive / passive):

1. **Asymmetric VFE quoting** — when `net_buyflow_50 > +5`, widen our ask
   by 1 tick and tighten our bid by 1 tick (lean inventory long). When
   `< −5`, do the reverse. Captures the drift via passive fills, not by
   crossing.
2. **Inventory bias** — when signal > threshold, allow a +N long
   skew on our resting position; let the predicted +0.5–1 tick drift
   pay for it.
3. **No standalone taker leg.** Do not lift offers on this signal alone.

## Expected per-day PnL contribution

- Standalone offensive: **negative** — skip.
- As a passive-quote bias inside the existing VFE MM: **rough order +20–60
  seashells/day** (signal corrects ~60% of MM adverse-selection on the ask
  side, where buy-aggressor toxicity is strongest). Treat as a tweak to
  the existing VFE quoter, not a new strategy.

## Recommended params (passive bias only)

- `K = 50` ticks (best IC/horizon trade-off, t=+8.3 at h=50).
- `threshold = ±5` net contracts.
- Exit / decay: refresh each tick; signal is stationary.
- Inventory skew cap: ±5 units beyond neutral.
