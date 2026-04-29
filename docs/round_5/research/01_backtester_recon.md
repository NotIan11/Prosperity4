# Backtester recon — current state, gaps, paths forward

> Source: Sonnet subagent reading `scripts/bt_dual.py`, `prosperity4bt` PyPI package internals,
> R3 calibration research, and surveying community BTs on GitHub. 2026-04-28.

## Our current backtester

`scripts/bt_dual.py` wraps the `prosperity4bt` PyPI package (jmerle's port,
installed at `.venv/lib/python3.13/site-packages/prosperity4bt/`). Runs full
3-day BT, then a single-day (day 2), and slices day 2 at tick 99,900 to
produce a "portal slice" PnL × hardcoded **0.73× calibration factor** derived
from a single v4 data point.

### What `prosperity4bt` actually models

- **Order book fills**: FIFO at touch. Iterates sorted asks/bids, fills at book price, respects position limit per fill. No pro-rata.
- **Market-trade fallback**: if order book is exhausted, matches against historical market trades from the CSV at *your* order's price (not the trade's). Default `--match-trades all` includes trades equal to your price.
- **Position limits**: enforced as net long + net short ≤ limit. If breach, **all orders for that product are cancelled** (all-or-nothing, not partial). `runner.py:406`.
- **Self-trade prevention**: not explicit. SUBMISSION trades can fill against any historical level.
- **traderData round-trip**: passed correctly (`runner.py:379`), so state persists tick-to-tick in BT.
- **Counterparty data**: `state.market_trades` retains buyer/seller from CSV for non-SUBMISSION trades. Layer 2 (Mark 38 intercept) would fire correctly in BT *if* the CSV trade data includes counterparty names.
- **Not modeled**: latency, market impact, queue position within a price level, partial-fill rules, stochastic NPC-order randomization (the platform's per-submission 20% drop).

## Why BT diverges from live (root causes)

**Architecture clarification (per `docs/competition.md` lines 38–39):**
"all algorithms run... against the Prosperity trading bots. Each team's
algorithm trades independently — no interaction between different teams'
algorithms." → submissions replay against pre-recorded NPC bots; teams
do NOT trade against each other. Earlier "competing-bot reactivity"
framing was wrong.

**Calibration measurement (2026-04-28):** v12 BT on day 3 (extracted
from r3 final live log) = $210,908. Live r3 final = $77,539. Gap =
**2.72×** with same data. This is the pure execution-divergence number
for v12-class strategies.

1. **Platform randomization** (`docs/round_3/research/17`, biggest factor).
   IMC drops ~20% of NPC orders per submission with a fresh seed each
   time. Three v12 portal runs spread $13k–$53k from the same code. BT
   is deterministic, so it measures one path; live is one draw from a
   wide distribution.

2. **Matching engine differences.**
   The BT fills at the historical book without modeling queue position,
   latency, or partial-fill rules the platform may enforce. Most of the
   2.72× day-3 gap is randomization + matching idealization, not
   adversarial response.

3. **Lambda cold-start hypothesis** (`docs/round_3/research/17`).
   Stateful strategies may lose EMA / `entry_price` if IMC re-instantiates
   the Trader mid-run. BT keeps the Trader instance alive all day. Adding
   `traderData` round-trip (which `544592.py` does) mitigates this.

## Community backtesters surveyed

| Repo | Stars | License | Modeling | Last commit | Closes gap? |
|---|---|---|---|---|---|
| `jmerle/imc-prosperity-3-backtester` | 195 | MIT | Same as our current (this is what `prosperity4bt` is ported from) | 2025-04-25 | No — this IS our current BT |
| `Xeeshan85/imc-prosperity-4-backtester` (`prosperity4btx`) | 51 | MIT | jmerle architecture rewritten OOP. Adds `--match-trades worse` (refuses fills at exactly-your-price). P4 R4 data bundled. | 2026-04-28 (active) | **Marginally** — `worse` mode is more conservative. Same fundamental determinism. |
| `kevin-fu1/imc-prosperity-4-backtester` | 65 | MIT | Same arch, adds local visualizer + Logger integration. | 2026-04-28 (active) | No — better observability, no gap-closing |
| `chrispyroberts/imc-prosperity-4` | 76 | None | Rust Monte-Carlo over synthetic GBM-like paths. Tutorial round only. | 2026-04-06 | Inapplicable to VFE/HG/VEV |

## Recommendation for R5

- **Cheapest win**: switch to `Xeeshan85/imc-prosperity-4-backtester` with `--match-trades worse`. Drop-in CLI-compatible, same log format, P4 data bundled. ~30-min change.
- **Run BT 3× per candidate** to measure variance from cold-start sensitivity. With `traderData` round-trip in place, this gap should narrow vs R3.
- **Don't build a new BT for R5 timeline.** The gap is dominated by platform randomization which we can't model exactly. Adding a 20% random NPC-order drop to BT (matching the platform's behavior) is a cheap experiment if we want to bracket BT variance — but the deterministic BT is still useful for *ranking* strategies.

## Calibration test for any new BT

Feed `544592.py` (the friend's R4 bot, lived $197k) through a candidate BT and see if it predicts close to $197k. Likely outcome: significant over-prediction, because Layer 2 Mark 38 intercept will over-fill in the absence of bot-avoidance modeling. The 0.73× R3 factor was calibrated on pure passive MM and may not transfer to a strategy with aggressive intercept layers. Combined with portal stochasticity (single live run is one draw from a wide distribution), absolute PnL match is unrealistic — relative ranking of candidate strategies is the realistic goal.
