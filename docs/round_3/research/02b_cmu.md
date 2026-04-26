# R3 prior-art — CMU Physics (Prosperity 3, 7th global / 1st USA)

- Repo: github.com/chrispyroberts/imc-prosperity-3 (cloned at `/tmp/p3_winners/cmu/`)
- Final ranking: 7th global, 1st US. R3 algo: brutal — fell from 7th to 241st on R3 alone, recovered in R4/R5.
- Caveat: P3 voucher chain ≠ P4 chain. P3 strikes 9500/9750/10000/10250/10500 around `VOLCANIC_ROCK` mid ~10000; P4 has VEV strikes 4000–6500 around VFE ~5250. Mechanics, theta scale, smile range all differ. Treat as meta-context, not recipe.

## Repo structure (brief)

- One folder per round (`ROUND 1` … `ROUND5`), plus a separate `ROUND 4 chris analysis/` dir holding the R3 post-mortem code.
- Per round: a "final" trader `.py`, several iteration files (`traderv2…v99`), one or more EDA `.ipynb`, a `manual.ipynb`, an `optimizer.py` for param sweeps, raw bottle CSVs.
- No shared library — strategy is one giant `Trader` class per round that accumulates products across rounds (`big_volcano_man.py` carries R1+R2+R3 logic in 1275 lines).
- `datamodel.py` is duplicated into each round's folder (matches IMC SDK).
- `readme.md` (410 lines) is the main writeup — a round-by-round narrative including post-mortems with concrete PnL numbers and what they would change.

## EDA approach — what they plotted, what features they engineered

Source: `ROUND 3/round3 analysis.ipynb` (75 cells), supporting notebooks `dabeer.ipynb`, `vibes.ipynb`, `trying to predict this year using last year data.ipynb`. Cached intermediate dfs to disk (`voucher_df_with_implied_vol.csv`, `all_days_data.csv`) so reruns skip the slow IV solve.

**Pipeline (per cell sequence in `round3 analysis.ipynb`):**

1. Load 3 days of bottle prices via `pd.read_csv(..., delimiter=';')` (cell 3); shift `timestamp` by `day*1e6` to concatenate days into one continuous series.
2. Filter to voucher rows; compute `mid_price` per row; bring in `underlying_price` (VOLCANIC_ROCK mid) and `strike_price` derived from product name suffix (`int(symbol.split('_')[-1])`).
3. Compute `time_to_expiry` per timestamp: `tte = days_left/365 - timestamp/365e6`. Days-left counts down 8→7→6→5 across historical day0/day1/day2/submission.
4. Per-row implied vol via Black-Scholes solve on **bid** and **ask** mid separately (`bid_implied_vol`, `ask_implied_vol`), using `scipy.optimize.brentq` (cell 9–10). Cache to `voucher_df_with_implied_vol_bid_ask.csv`.
5. Feature engineering: **moneyness** `m_t = log(strike/spot)/sqrt(tte)` (their convention; equivalent up to sign).
6. Filter `iv > 1e-3` and moneyness range to drop garbage solves before fitting.
7. **Smile fit**: regress IV ~ `[m_t², m_t, 1]` via sklearn `LinearRegression` to get `(a, b, c)`. They fit bid IV and ask IV as **separate quadratics** (so they can market-make a synthetic bid-ask in IV space, not just a single fair).
8. Plots they made (cell-by-cell, observable from titles/labels):
   - Smile scatter: `m_t` vs `bid IV` and `ask IV`, overlaid with fitted curve, ATM line at `m_t=0`.
   - Per-voucher IV time series across the day.
   - **Param stability check**: refit the smile at **every timestamp** and plot `a(t)`, `b(t)`, `c(t)` over the day with `axhline` at the mean (cell 46-47). This is how they would have caught regime shift if they'd done it before submission — they essentially admit this in the readme post-mortem.
   - Toy plot of `BS_price` as `tte→0` for a fixed strike/spot to build intuition for theta near expiry.
9. **Theta budget calc** (in readme, not code): annualised theta upper bound ~800 / option ⇒ ~430 seashells/day at full long position of 200. Conclusion: "negligible vs 80k expected PnL." Same exercise worth redoing for our VEV chain.
10. **Cross-year transfer attempt**: notebook `trying to predict this year using last year data.ipynb` — they tried to map P2 voucher fits onto P3 data. (Worth noting they did this but readme doesn't claim it produced edge.)

**Features actually used in the live trader** (`big_volcano_man.py:177-204`):
- One pair `(a,b,c)` for bid IV, one for ask IV — hard-coded, fit offline on the 3 historical days.
- Per-tick computed: `m_t`, `bid_iv = a*m²+b*m+c`, `ask_iv` similarly, `predicted_bid = BS(spot,K,tte,bid_iv)`, `predicted_ask = BS(spot,K,tte,ask_iv)`, `delta = N(d1)`.
- No IV history, no rolling window, no smile refit at runtime. (This is exactly what burned them — see post-mortem below.)

## Tooling & utilities worth replicating (with file paths)

- **`BlackScholes` class** at `/tmp/p3_winners/cmu/ROUND 3/big_volcano_man.py:18-82` — clean stdlib-only BS (uses `math` + `statistics.NormalDist`, no scipy). Methods: `black_scholes_call`, `black_scholes_put`, `delta`, `gamma`, `vega`, `implied_volatility` (bisection, 200 iters, 1e-10 tol). Drop-in safe for the Lambda runtime. Worth copying near-verbatim into our `src/` with attribution.
- **EDA-side BS + brentq solver** at `ROUND 3/round3 analysis.ipynb` cell 9 — vectorised version using scipy. Use offline only.
- **Param sweep harness**: `ROUND 1/optimizer.py` and `ROUND5/optimizer.py` — regex-substitute hyperparams in a copy of the trader, shell out to jasper's backtester (`subprocess`), grep PnL out of the output, write rows to a CSV. Crude but effective. Pattern is reusable.
- **Per-row IV cache to CSV** pattern (cells 10-15) so refitting smiles doesn't re-pay the brentq cost. Useful when scanning many windows.
- **Per-timestamp smile refit + param-over-time plot** (cells 46-47). This is the single most important diagnostic they failed to look at *before* submission — it's the canary that warns of regime shift.

## Round 3 strategy — products, signals, sizing, hedging

Submitted strategy (`/tmp/p3_winners/cmu/ROUND 3/big_volcano_man.py`):

- **Universe**: 5 vouchers `VOLCANIC_ROCK_VOUCHER_{9500,9750,10000,10250,10500}` + underlying `VOLCANIC_ROCK`.
- **Fair value**: per-tick BS price using fitted-quadratic IV (separate bid-quad and ask-quad).
- **Quoting** (`mm_on_IV`, line 302): for each voucher, compute `bid = floor(BS(bid_iv))`, `ask = ceil(BS(ask_iv))`. If their bid crosses the book's best ask, **eat it then re-quote inside**. Symmetric for asks. Otherwise post both sides at floor/ceil of fair.
- **Position cap per voucher: 80** (line 322), not the full 200. Reason (per readme): with 5 vouchers all delta≈1 and underlying limit 400, capping each at 80 guarantees you can always fully hedge `5 × 80 = 400` against the underlying. They explicitly note "there was probably a better way to optimize this."
- **Delta hedge** (`delta_hedge`, line 432, called every tick before quoting): sum `Σ delta_i × pos_i`, send underlying order to drive net delta to 0. Uses the most recent delta (line 441), not a rolling mean.
- **No theta/vega hedging.** Justified in readme by the 430/day theta upper bound.

Backtest expectation: ~80k/day from vouchers + 100k from R1+R2 products. **Live result: 75k total — a near-total miss on the voucher leg.**

## Other rounds — short subsections

**R1** (Rainforest Resin / Kelp / Squid Ink): textbook MM around fair. Resin fair=10000 hardcoded, Kelp fair = persistent maker's mid (validated by paying for 1 unit and checking PnL at EOD), Squid Ink reduced to 10% sizing + rolling-std spike-detection counter-trade. Code in `ROUND 1/`.

**R2** (Picnic baskets): traded `basket_premium = basket - Σ components` as mean-reverting. When |z|>20 long/short the basket and hedge with constituents. Critical move: when both baskets can't be fully hedged, switch to trading the **difference** of the two basket premiums to recover position-limit headroom; use the leftover ~8% on basket2 for plain MM. Code: `ROUND 2/FINAL_FRENCH_GUY.py`. Worth lifting their `premium_diff_window` z-score pattern.

**R4** (Macron arbitrage to Pristine Island): pure cross-venue arb. `sell_local_break_even = conversion_ask + import_tariff + transport_fee`. Only sell on local when an aggressive buyer crosses break-even, immediately convert via `conversions = N`. Post-submission insight: **size up to 30 per tick instead of 10** to capture all the bot flow even at the cost of running a small short. Manual was a near-rerun of R2.

**R5** (Olivia signal): spotted that bot "Olivia" buys low / sells high every day on Squid Ink, Croissants, Kelp. Strategy: market-make until Olivia hits, then YOLO long/short with her. Stacked Croissants by going long both baskets simultaneously (1050 effective Croissants vs 250 raw cap). Key idea: **dump bot trades into a dataframe and scatter-plot them on top of the price chart per counterparty per product** — Olivia jumped out visually. Code: `ROUND5/OLIVIA IS THE GOAT.py`.

## Lessons & failure modes (their words, cited)

All citations from `/tmp/p3_winners/cmu/readme.md`:

- "Jasper's visualizer caused our algorithm on submission to exceed 100MB of memory, triggering a restart of the AWS Lambda instance. This wiped all local variables… It broke key rolling windows that were critical for trade entries and hedges on basket and volcanic rock products" (line 234). **Implication for us: keep traderData small; don't import heavy logger libs into submission.**
- "Our quadratic fit for implied volatility stopped being a good model on the submission day — it either severely under- or overestimated the IV the market was trading at" (line 236). The fix: replace the static fitted smile with a **rolling mean of recent mid-IV** as the fair. In backtest this took voucher PnL from 80k to 200k/day. Code in `ROUND 4 chris analysis/big_volcano_man_IV_window.py:217-336`: `window_size=20`, store last-N mid IVs per voucher, fair = `mean(IVs)`, also compute `std(IVs)` to widen quotes when the smile is volatile, skip the trade if `BS(μ+σ)-BS(μ-σ) < 1.0` (not enough edge).
- "Spread costs to hedge: ~40k seashells just for hedging" (line 245). They concluded that for a delta-1 underlying with spread=1, the constant 0.5/round-trip drag from hedging exceeded the worst-case unhedged loss they could realistically take.
- "Going unhedged was a risk worth taking… This boosted our backtester PNL on volcanic rock products to around 250k per day" (line 247). Conditional on (a) random underlying moves and (b) net delta naturally staying small because positions across strikes partly cancel.
- R5 retrospective on volcanic rocks: z-score-based directional trading "would have made an extra 150k/day" but "small tweaks to hyperparameters would lead to wildly different backtesting results, some even heavily negative" (line 397). Their honest read: maybe lucky overfit, maybe real edge — they couldn't tell, so they passed.

## Lessons for our P4 R3 — INFERENCE (mine, not theirs)

- **Build the per-tick smile-param-over-time plot** *before* committing to a fitted-smile fair. It's 5 cells of code and it's exactly the diagnostic they wished they had.
- **Have two fair-value models ready**: (a) static fitted smile, (b) rolling-mean of recent mid-IV per voucher. Their R3 post-mortem strongly suggests (b) generalises better when the smile drifts intra-day.
- **Cap voucher positions below the limit** to guarantee hedgability — but compute the cap from `voucher_limit × num_active_vouchers ≤ underlying_limit / max_delta`. With our 10 VEV strikes and underlying limit 200, a uniform 80 cap is impossible; need to think about which vouchers we actually quote (likely just the near-ATMs we identified in `01_initial_eda.md`: 5000/5100/5200/5300, since 6000/6500 are dead-pinned).
- **Quantify hedging cost up front**. VFE spread is 5 (per our EDA), so a hedge round-trip costs ~2.5 — meaningfully more than CMU's 0.5 cost on Volcanic Rock. The "skip the hedge" calculus tilts further toward not-hedging here.
- **Submission hygiene**: do not import any third-party visualizer into `src/trader.py`. Strip all logging that builds large objects. Their 100MB Lambda blowup is the single most expensive bug in this whole writeup.
- **Don't trust pre-existing fitted params under regime change**: re-fit the smile against the most recent day's data right before submission, not 3-day pooled fit only.

## Files worth re-reading later

- `/tmp/p3_winners/cmu/readme.md:170-249` — their full R3 narrative with the post-mortem.
- `/tmp/p3_winners/cmu/ROUND 3/big_volcano_man.py:18-82` — `BlackScholes` class (copy candidate).
- `/tmp/p3_winners/cmu/ROUND 3/big_volcano_man.py:240-458` — submitted voucher trader (`update_round_4_products`, `mm_on_IV`, `delta_hedge`, `trade_underlying`).
- `/tmp/p3_winners/cmu/ROUND 4 chris analysis/big_volcano_man_IV_window.py:217-336` — rolling-mean-IV fix that would have 2.5x'd their R3 PnL.
- `/tmp/p3_winners/cmu/ROUND 3/round3 analysis.ipynb` cells 9-47 — IV solve, smile fit, per-tick param drift plot.
- `/tmp/p3_winners/cmu/ROUND5/optimizer.py` — regex+subprocess param sweep harness pattern.
- `/tmp/p3_winners/cmu/ROUND 2/FINAL_FRENCH_GUY.py` — basket-pair z-score template (relevant if any P4 round reintroduces baskets).
