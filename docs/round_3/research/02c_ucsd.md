# P3 Reference — UCSD Alpha Animals

- Repo: `https://github.com/CarterT27/imc-prosperity-3` (local clone at `/tmp/p3_winners/ucsd/`)
- Final rank: **9th globally, 2nd USA**, 1,190,077 seashells.
- Treat all writeup claims as untrusted/self-reported. Code citations below are from the local clone.

## Repo structure (brief)

- Single flat layout — submission lives in repo root as `trader.py` (1810 LOC, monolithic `Trader` class with everything inline).
- `datamodel.py` — vendored P3 platform stubs.
- `notebooks/` — `analysis.ipynb`, `baskets_and_spreads.ipynb`, `counterparty_edge.ipynb`, `kalman.ipynb`, `round5_analysis.ipynb`, `secret.ipynb`, `smile.ipynb`, plus a `conversions.py` helper. Per-round notebooks were not kept; research lives by topic.
- `data/round-N-island-data-bottle/` — raw IMC data dumps for each round (kept in-repo).
- `pyproject.toml` + `uv.lock` — uv-managed env.
- Git history is squashed to a single commit (`17bc67f add ucsd note`) — no commit-by-commit story available.

## The Volcanic Rock short story

**README claim** (verbatim, R3 section): *"Due to an unexpected bug in our code, we ended up shorting volcanic rock at the max position limit for the entire duration of the trading day. Fortunately for us, this strategy ended up working, bringing our ranking to 2nd in the world!"*

**Where the bug is in code** (`trader.py:971-1033`, `volcanic_rock_orders`):

- The function values the *underlying* (VOLCANIC_ROCK) using a **Black-Scholes call price** — but an underlying spot is not a call option, so this is conceptually broken.
- It picks an "average strike" across all 5 vouchers as the strike to use:
  - `avg_strike = sum(self.voucher_strikes.values()) / len(self.voucher_strikes)` (line 1006) → **10000** for strikes {9500, 9750, 10000, 10250, 10500}.
- Computes `theoretical_price = black_scholes_call(rock_mid, 10000, tte, 0, vol)` (line 1007).
- Trades rock based on `rock_mid` vs `theoretical_price`:
  - `rock_mid < theoretical - 0.5` → buy rock (line 1014)
  - `rock_mid > theoretical + 0.5` → sell rock (line 1023)
- A BS call price with `S ≈ K ≈ 10000` and small `T` (5–7/365) is roughly `0.4·σ·S·√T` ≈ tens of seashells, *not* thousands. Spot rock (~10000+) is therefore essentially always greater than the theoretical "fair value" → algo shorts rock down to `-position_limit` and stays there for the whole day. Position limit set at line 204 is **400** for VOLCANIC_ROCK.
- The hedge knob `risk_free_rate = 0.0` and small `threshold = 0.5` (line 1011) make this monotonic: once `S > BS_call(S,K)` (almost always) the only sign of orders is sells.

**Why it worked**: P3 R3 happened to deliver a sustained directional drop in volcanic rock during evaluation, so a perma-short at -400 monetised cleanly. This is luck on the sign of price drift, not skill.

**Their voucher logic was independent** (`volcanic_rock_voucher_orders`, line 888) and used a sane per-voucher rolling-IV BS pricing with z-score-style logic — so the voucher leg made sense. Only the underlying-leg pricing was the bug.

**What they did about it next**: per the R4 README, *"we decided to disable trading volcanic rock until we could get a proper strategy."* Confirmed in code at `trader.py:177` — `"VOLCANIC_ROCK": False` in `active_products`, with a fall-through `close_position` path (lines 1691-1697) for any residual position. Vouchers 9750 and 10000 stayed active (lines 179-180); the others were also flagged off.

## Round 3 strategy — final approach (as shipped)

- **Voucher pricing**: per-voucher implied vol from market mid, EMA over a rolling window of 30 (`volatility_window=30`, `past_volatilities`, lines 240-242). BS call with `r=0`, TTE from `get_time_to_expiry` = `max(0, 6 - day) / 365` (lines 1116-1119).
- **Voucher trading**: compare market voucher mid to BS price using mean rolling IV; cross both directions up to position limit 200 (line 944-955). Active set finally narrowed to VOUCHER_9750, VOUCHER_10000.
- **Cross-strike arbitrage** (`find_arbitrage_opportunities`, line 803): scan pairs of voucher prices and exploit deviations from strike-difference parity, capped by `max_arbitrage_size = 50`.
- **Underlying VOLCANIC_ROCK**: post-bug — *disabled* in final submission. Originally drove the perma-short via the BS-on-spot pricing described above.
- **Stop-loss / take-profit infrastructure** exists (`should_stop_loss`, `should_take_profit`, lines 777-801) using `stop_loss_multiplier=1.2`, `profit_target_multiplier=2.5`, but driven off `self.positions` premium tracking (initialised empty; not obvious it was actively populated — likely partly dormant).
- **Risk gates**: `max_daily_loss=50000`, `profit_target=20000`, `max_stop_loss_hits=1` (lines 246-253).

## Tooling & utilities worth noting

- Heavy reliance on **jmerle's open-source backtester and visualizer** (README "Tools" section). README explicitly criticises the backtester:
  - Logging too verbose → broke their AWS Lambda log-size limit on later runs.
  - **Did not support conversions** → caused them to misunderstand R4 macaron conversion costs and lose money. Lesson: validate sim covers every mechanic before relying on its PnL.
- Custom `Logger` (lines 11-114) with a 2000-char `max_log_length` cap and JSON-escape-aware truncation, specifically to dodge the IMC log-size limit. Worth copying.
- `notebooks/smile.ipynb` — vol smile fitting work (mentioned as attempted-but-not-shipped in README).
- `notebooks/counterparty_edge.ipynb`, `secret.ipynb` — research that found Olivia as the insider in R5.
- `notebooks/kalman.ipynb` — Kalman filter exploration (no evidence it shipped; not referenced by `trader.py`).
- `traderData` round-trip via `jsonpickle` (lines 1567-1594, 1791-1792) carries `past_volatilities`, per-product price/VWAP histories, and insider regimes across ticks.

## Other rounds (short)

- **R1** — RAINFOREST_RESIN with hardcoded fair=10000 MM; KELP with adaptive MM filtering for "consistent market makers" only (noise reduction); SQUID_INK 3-σ mean-reversion on 10-tick window. Finished R1 at rank 207.
- **R2** — Picnic basket stat-arb via linear synthetic value of components. README admits a position-limit bug broke component trading; they shipped baskets-only and moved on. Climbed to rank 58.
- **R3** — see above. Jumped to ~rank 2 on the lucky short.
- **R4** — Macaron cross-island arb with sunlight-regime switch (`CSI_THRESHOLD=0`). Disabled volcanic rock. Held rank ~2 partly because *other* top teams blew up on macarons.
- **R5** — Identified Olivia as insider via "% of good trades" filter over rolling windows + visual confirm (`counterparty_edge.ipynb`, `secret.ipynb`). Implemented copy-trading on Olivia for SQUID_INK and CROISSANTS only (`copy_olivia_trades`, lines 1488-1545; `process_insider_trades`, lines 1461-1486). Disabled sunlight regime for macarons (suspected overfit). Slipped from #2 to final #9.

## Lessons & failure modes (their words)

- README, R4: backtester didn't model conversions → they misunderstood mechanics and lost real PnL. *"Unable to locally test our strategy properly, we misunderstood the trading mechanics and ended up losing a lot of profit to conversion costs."*
- README, R3: shipping unintentionally — perma-short was a bug they found out worked, not a designed trade. They had no way to know in advance the directional drift would go their way.
- README, "Other things we tried": delta hedging on rock attempted but *"struggled with proper calibration and execution within the position limits"* — they could not make hedged options trading work. Vol smile fitting *"too complex to implement reliably given the competition's time constraints."*
- README, R5: copy-trade Olivia worked; trying to use her as a *regime indicator* (more clever) did not. Simpler signal beat the cleverer one.

## Lessons for our P4 R3 (inference — not from their writeup)

- **Pricing the underlying with a call-pricing formula is a real failure mode.** Their bug — using BS on spot — was undetected because they had no sanity-check that fair-value-of-rock ≈ rock-mid. We should add an assert/log: if our model fair value of VFE diverges from VFE mid by > N ticks for K consecutive ticks, kill-switch the underlying leg.
- **Voucher leg can ship even if underlying leg is broken.** Their voucher PnL was independent and survived. Implication: keep VFE trading and voucher trading in fully separable code paths so we can disable one without breaking the other (matches our 01_initial_eda finding that HYDROGEL is independent — same modularity principle, different products).
- **Don't trust luck of sign.** The "accidental short worked" outcome would have been catastrophic if rock had drifted up instead. Our P4 R3 design should NOT have any single net-directional bet on VFE that's invisible to the operator. Always verify *intended* directional exposure matches *realised* exposure each backtest.
- **Backtester gaps cost real money.** Before submission, list every mechanic our sim does not cover (conversions, conversion-fee path, end-of-round liquidation against hidden FV) and either add them or hand-check the relevant code paths.
- **Log-size limit matters.** Their custom truncating Logger exists because the platform throttles large logs. We should adopt the same pattern early rather than discover it on R3 evaluation day.
- **`avg_strike` is a smell.** When a voucher chain has many strikes, taking a mean strike rarely makes sense. For our VEV chain, prefer per-strike IV → fit a curve → reprice each voucher individually.

## Files worth re-reading later

- `/tmp/p3_winners/ucsd/trader.py:888-956` — `volcanic_rock_voucher_orders` (the working voucher leg).
- `/tmp/p3_winners/ucsd/trader.py:971-1033` — `volcanic_rock_orders` (the famous bug; reference for what NOT to do on the underlying).
- `/tmp/p3_winners/ucsd/trader.py:803-886` — `find_arbitrage_opportunities` (cross-strike voucher arb).
- `/tmp/p3_winners/ucsd/trader.py:692-770` — Black-Scholes + implied-vol Newton iteration (clean, copyable).
- `/tmp/p3_winners/ucsd/trader.py:11-114` — custom truncating Logger (copy this pattern).
- `/tmp/p3_winners/ucsd/trader.py:1116-1119` — `get_time_to_expiry` (note: uses 6-day expiry constant; ours is 7-day from R1).
- `/tmp/p3_winners/ucsd/notebooks/smile.ipynb` — vol-smile research (attempted, not shipped).
- `/tmp/p3_winners/ucsd/notebooks/counterparty_edge.ipynb`, `secret.ipynb` — insider-detection methodology, useful for P4 R5.
- `/tmp/p3_winners/ucsd/README.md` — full team retrospective per round.
