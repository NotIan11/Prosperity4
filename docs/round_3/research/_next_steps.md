# Next steps — parking lot

Things proposed but not yet acted on. State after Discord ingestion + synthesis.

## Done since last update
- ✅ Stdlib BS class ported (`src/utils/black_scholes.py`)
- ✅ Baseline hydrogel + VFE market-maker scaffolded (`src/trader.py` — DRAFT)
- ✅ All 4 deep EDA agents complete (`04`–`07_*.md`)
- ✅ Bot trade pattern, order book depth, per-day robustness, smile drift
  all answered by the EDA agents — no longer open
- ✅ All 4 Discord channels parsed (`08a`–`08d_*.md`)
- ✅ Synthesis written (`09_synthesis.md`) — read this first

## Open / pending decisions

- **Voucher modules in our trader: yes/no?** Coordination question with
  options-team teammates. EDA + Discord both validate the rolling-smile
  + 5300/5400 RV approach. If we ship it, we collide with their work.
- **HYDROGEL `half_edge` final pick** — a sweep showed h=8 best in BT,
  but Discord chatter hints HG drawdowns may be larger live than BT.
  Worth a sweep of {7, 8, 9} immediately before any submission.
- **VFE asymmetric quoting offsets** — EDA suggests `(bid=2, ask=3)`,
  validated by sweep, but un-shipped pending the voucher decision above.
- **Submit (756, 851) for the manual round** — needs the user to actually
  click submit in the Manual GUI before round end.
- **Strip `traderData` JSON load if used** — Discord flags it as a hidden
  Lambda cost. We don't use it yet but a future voucher module might.

## Investigations deferred (do NOT do unless asked)

- Try alternative backtesters if `prosperity4btest` ever breaks on
  something specific. First fallback: `shh1v/imc-prosperity-4-backtester`
  (active, similar lineage). Second: `prosperity3bt` + monkey-patched
  LIMITS (we used to do this; works but adds harness overhead).
- Day-2 HYDROGEL underperformance (~33% drop in BT) — affects every
  param config equally, so likely a structural day-2 thing not a tunable
  bug. Investigate before R4 if relevant.
- VEV_4000 ↔ VEV_4500 spread guardrail (~500) — kill-switch / sanity
  monitor for the voucher trader. Useful for whoever owns vouchers.

## R4 / R5 prep (not now)

- UCSD-style insider-bot ranking — needs counterparty IDs, only revealed
  in R5 per multiple sources.
- R4 mechanics not in our docs yet; brief.md only covers R3.
