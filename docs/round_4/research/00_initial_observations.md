# R4 — Initial observations (pre-EDA)

> Working notes captured 2026-04-28 from the R4 brief and a quick scan of the
> friend's submitted bot (`data/round_4/live_logs/r4/544592.py`). Not authoritative.

## R4 brief — observations

- **Algo products = R3 products.** HYDROGEL_PACK / VELVETFRUIT_EXTRACT /
  VELVETFRUIT_EXTRACT_VOUCHER (10 strikes). Position limits unchanged (200/200/300).
  → All R3 v12 carry-overs apply directly: regime patterns (research/16),
  portal stochasticity (research/17), hardcoded+OLS hybrid, informed-flow tilt.
- **New signal: counterparty IDs.** `Trade.buyer` and `Trade.seller` are now
  participant names. Profile bot vs human flow, fade-able vs informed
  counterparties, cluster behavior.
- **Manual is fully standalone.** GBM, σ=251% annualized, hold-to-expiry,
  marked to mean of 100 sims. Pricing problem, not a flow problem.
  Knockout barrier checked only at 4 discrete steps/day.

## Submitted R4 bot (`544592.py`) — quick observations

- **Live PnL: $197,363.70.** ~4× our R3 ship ($50k mean). Big jump.
- **Architecture is a fresh rewrite, not v12-derived.** Abstract `Strategy`
  base class, `save_state` / `load_state` per-strategy, `traderData` JSON
  round-trip in `Trader.run` — exactly the defensive carry-over we flagged
  but never shipped.
- **Strategies in code:** `OsmiumStrategy`, `PepperStrategy`,
  `HydrogelStrategy`, `VelvetfruitStrategy`, `VevOptionStrategy`. Final
  positions show only HYDROGEL/VELVETFRUIT/VEV_strikes traded — Osmium and
  Pepper strategies exist but didn't fire (likely speculative R5 prep,
  those products aren't in R4 brief).
- **Doesn't use counterparty info.** R4's headline new feature
  (`buyer`/`seller` names) — needs verification by grepping the source, but
  the high-level scan saw no buyer/seller logic. If true, headline R4 edge
  was left on the table; ours to grab.
- **`Trader.bid()` returns 4750** as a "GTO bid for market access fee
  auction" — a new R4 mechanic. `XIRECS` final position -121,125 is residual
  from this auction.
- **Final positions:** all VEV strikes +300 (max long), HYDROGEL -144,
  VELVETFRUIT +200 (max long). Aggressive directional posture into close.

## Open questions for deeper R4 inspection

- Does the bot actually ignore `buyer`/`seller`, or is there a subtle use?
- What's the `VevOptionStrategy` pricing model (BS, table, regression)?
- How does `HydrogelStrategy` differ from R3 hydrogel handling?
- What's the FV anchor for `VelvetfruitStrategy` — still 5250 or live-derived?
- How is `traderData` persisted across ticks (compression, trimming)?
