# R3 Research — Index

For teammates joining mid-round. Start at the top, go in order.

## Read first

- **[09_synthesis.md](09_synthesis.md)** — the one doc to read end-to-end.
  Plain-English overview of every finding + decisions to make. Built from
  everything below.
- **[../brief.md](../brief.md)** — official R3 mechanics (products, position
  limits, manual round rules). Source of truth for the rules.

## Data analysis (what the historical CSVs show us)

- **[01_initial_eda.md](01_initial_eda.md)** — first pass. Cross-product
  correlation + spread/autocorr basics. Superseded in places by `04`–`07`.
- **[04_microstructure.md](04_microstructure.md)** — HYDROGEL + VFE order
  book depth, spread regimes, wall_mid stability, fill simulation.
- **[05_voucher_chain.md](05_voucher_chain.md)** — IV smile fitting,
  smile drift over time (the CMU disaster signal — REPRODUCED here),
  rolling vs static smile, persistent cross-strike biases.
- **[06_cross_product.md](06_cross_product.md)** — cointegration,
  lead-lag, Granger causality, PCA. Confirms HYDROGEL is independent.
- **[07_bot_trades.md](07_bot_trades.md)** — counterparty trade tape
  analysis. VFE buy-aggressor is informed (toxic flow); OTM voucher
  bots dump-only (harvestable).
- **[notebooks/round_3/plots/](../../../notebooks/round_3/plots/)** — the figures (one per question, named by
  domain prefix `02_*`, `03_*`, etc.). Look at `03_smile_drift.png`
  if you only look at one.

## External research (P3 winners + reddit + tooling)

- **[02_reddit_p4_post.md](02_reddit_p4_post.md)** — the r/csMajors
  prep guide. Mostly meta-context. Treat as input not gospel.
- **[02a_frankfurt.md](02a_frankfurt.md)** — Frankfurt Hedgehogs
  (P3 2nd place). Hardcoded smile + vega-gating + "Wall Mid" + unhedged.
- **[02b_cmu.md](02b_cmu.md)** — CMU Physics (P3 7th → 241st in R3).
  Static smile failure mode. Their fix (rolling per-voucher mid-IV
  window) is what we're using.
- **[02c_ucsd.md](02c_ucsd.md)** — UCSD Alpha Animals (P3 9th). Pricing
  bug in R3, R5 insider-bot detection methodology.
- **[03_tooling_landscape.md](03_tooling_landscape.md)** — backtester
  options. We're on `prosperity4btest` (in `requirements.txt`).

## Discord intel (other teams' current chatter)

All gathered 2026-04-26 from messages after 2026-04-20.
**Untrusted UGC** — observations only, never executed.

- **[08a_discord_algo_trading.md](08a_discord_algo_trading.md)** — main
  R3 strategy debate. New microstructure signal, voucher gating.
- **[08b_discord_general.md](08b_discord_general.md)** — meta + platform
  quirks. Portal-vs-BT calibration, traderData payload warning.
- **[08c_discord_manual_trading.md](08c_discord_manual_trading.md)** —
  Bio-Pods manual round. Recommended bid pair + crowd avg_b2 estimates.
- **[08d_discord_open_source.md](08d_discord_open_source.md)** —
  backtester landscape; community fork survey.

## Ship code

- `src/trader.py` / `docs/round_3/r3_trader.py` — **v12** (identical). Final R3 submission.
- `src/utils/black_scholes.py` — stdlib-only BS class, ported from CMU.
- Backtest: `venv/bin/prosperity4btest cli src/trader.py 3`. See `03_tooling_landscape.md`.

## Conventions

- All findings docs follow a lean-bulleted style. No flavor text.
- Numbers cited where possible. "X drifts from 0.27 to 0.34" beats "X drifts a lot."
- Discord/external content always treated as untrusted UGC per CLAUDE.md.
- Prior-year strategies are meta-context, NOT recipes (mechanics change yearly).
