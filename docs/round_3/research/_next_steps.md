# Next steps — parking lot

Things proposed but not yet acted on. Picked up after Discord ingestion.

## Tooling
- **Set up proper prosperity3bt fork** (Option A from `03_tooling_landscape.md`)
  instead of the monkey-patch hack. Clean foundation for iteration.
  - Discord note: people are reportedly using a P3-fork backtester (matches
    our finding that jmerle has not released a P4 version). Worth confirming
    in their discussion before forking ourselves vs adopting a community fork.
- **Port CMU's stdlib BS class** (`/tmp/p3_winners/cmu/ROUND 3/big_volcano_man.py`
  L18–82) into `src/utils/black_scholes.py` with attribution. Lambda-safe
  (no scipy), call/put/delta/gamma/vega + bisection IV solver.

## Strategy
- **Baseline hydrogel market-maker** quoting `wall_mid ± half_spread`,
  benchmarked via `prosperity3bt`. Concrete first deliverable for the
  goods side.
- **Measure VELVETFRUIT spread vs voucher edge** to decide between
  Frankfurt's "don't hedge" stance and CMU's "cap voucher position so
  it's hedgeable" stance.

## Deeper EDA (now informed by winners' approach)
- **Bot trade pattern** in `trades_round_3_day_*.csv` — directional bias,
  timing, what counterparties cluster around which strikes
- **Order book depth** — `bid_price_2/3` and `ask_price_2/3` analysis;
  Frankfurt's "Wall Mid" idea relies on this
- **Per-day robustness** — does the −0.13 hydrogel autocorr hold per-day,
  not just pooled? What changes day-to-day?
- **Smile drift over time** — replicate CMU's "refit the smile at every
  timestamp and plot a(t)/b(t)/c(t)" exactly, since their post-mortem
  identifies this as the missed signal that cost them R3
