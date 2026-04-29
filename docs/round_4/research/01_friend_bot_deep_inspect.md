# R4 — Deep inspection of friend's submitted bot

> Source: Sonnet subagent reading `data/round_4/live_logs/r4/544592.py` end-to-end, 2026-04-28.
> Live result: $197,363.70 (~4× our R3 v12 ship).

## VevOptionStrategy — pricing

- Black-Scholes call, **σ = 0.241 flat**, no rate (r = 0). No vol surface, no lookup table.
- **TTE inferred live each tick** by bisection-solving `bs_call_price(S, K, tte, 0.241) = market_mid` for each strike in `REAL_OPTION_STRIKES` (5000–5500), then taking the median. Falls back to `FALLBACK_TTE_DAYS = 4.0 − timestamp/1e6`. → adapts automatically across the round day window without a hardcoded day counter.
- VFE anchor: hardcoded `FV = 5_250.0`. Justification (per code): deep-ITM VEV_4000 parity + 30K-tick mean = 5250.10. No rolling, no live-derived blend.
- Dead strikes (VEV_6000, VEV_6500): `fair_value()` returns `None` → no orders.
- Deep-ITM (VEV_4000, VEV_4500): `max(S − K, 0)` — pure intrinsic.

## HydrogelStrategy — three-layer hybrid

- **Layer 1** — EMA mean-reversion take. α = 0.005 (very slow). Take when `ask < ema − 20` or `bid > ema + 20`. `MAX_TAKE = 5`/tick, `ER_CAP = 175` position cap.
- **Layer 2** — *Mark 38 intercept* (live only). Reads `state.market_trades` for `trade.buyer == "Mark 38"` / `trade.seller == "Mark 38"`. If Mk38 was buying last tick → post passive sell at `best_ask − 1`. If selling → post passive buy at `best_bid + 1`. Up to 25/tick. `M38_CAP = 75` on buy side; full ±200 on sell side.
- **Layer 2b** — Book-imbalance pre-positioning. `(bid_vol − ask_vol) / total_vol`. If > 0.15 → fire passive sell (Mk38 about to buy). If < −0.15 → fire passive buy. **Fires one tick ahead of Layer 2.** Code comment claims "~99% accuracy at tick level."
- Position limit: 200.

## VelvetfruitStrategy — pure macro MR taker

- FV = 5,250 hardcoded. Entry threshold: ±18 from FV. On signal, sweeps book to ±200 in one tick.
- **Stop-loss**: closes when `(mid − entry_price) × pos < −40 × |pos|` (40-tick adverse move). Tracks `entry_price` in traderData.
- No EMA, no passive quoting, no inventory penalty. Fully directional.

## Counterparty usage

- **Used in HydrogelStrategy only** (Layer 2 above). VFE / VEV / Osmium / Pepper strategies make zero use of `Trade.buyer` / `Trade.seller`.
- Per-strike `mark22_passive_bid` logic targets **Mark 22** in VEV_5200/5300 when VFE < 5230 (caps: 160 / 220). Logic itself doesn't re-check counterparty at runtime — the Mark 22 identification was done offline.
- **Biggest open opportunity**: VFE/VEV chain has no counterparty signal applied. Mark 38–style intercepts likely exist in those products too.

## traderData round-trip

| Strategy | Persisted fields |
|---|---|
| OsmiumStrategy | `prev_mid` |
| HydrogelStrategy | `ema_mid` |
| VelvetfruitStrategy | `entry_price` (or None) |
| VevOptionStrategy | `entry_underlying` (or None) |
| PepperStrategy | (stateless) |

- `Trader.run` does `json.loads(state.traderData)` with bare `try/except`, dispatches per-symbol `load_state`, then `json.dumps` everything back. No compression, no trimming, no size check. Payload is tiny (~5 floats), so size irrelevant.
- Directly mitigates Lambda cold-start hypothesis from `docs/round_3/research/17`.

## Risk management

- VFE + VEV: 40-tick adverse-move stop-loss on the underlying.
- HG: ER_CAP (±175) and M38_CAP (+75) hard stops.
- **No rolling daily-PnL stop-loss.**
- **No regime detection.**
- **No defensive cap reduction** if FV drifts (R3 carry-over candidate, still untried).

## Novel signals not in our v12

- Counterparty-based Mark 38 intercept (HG Layer 2). Primary R4 alpha.
- Book-imbalance pre-positioning (HG Layer 2b).
- Live TTE inference from option chain (eliminates day-counter hardcode).
- Per-strike passive bid targeting Mark 22 (VEV_5200/5300, VFE < 5230).
- Autocorrelation-graded MR taker in Osmium (prev-tick direction scales aggressiveness, full vs 80%).
- Pepper buy-hold with `MAX_PER_TICK = 10` throttle.
- Hardcoded GTO 4750 bid for the new R4 Market Access Fee auction.

## Open follow-ups

- Verify Mark 22's role in other VEV strikes — the bot only handles 5200/5300.
- Check whether counterparty data exists for R3-only days in the R4 capsule (would let us back-fit our R3 v12 with counterparty signal).
- Profile other counterparties for fade-able vs informed flow before R5.
