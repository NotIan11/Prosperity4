# R3 Synthesis — read this first

Plain-English summary of everything we know and what to do about it.
Built from `01`–`08*.md` + `02a–c` (winners) + `03` (tooling) +
the four Discord channel digests.

If you only have 5 minutes: skip to **§7 Decisions to make**.

---

## 1. What R3 is

We're trading 12 instruments against an exchange of bots:

- **HYDROGEL_PACK** — a "delta-1" product that trades around 9990 with
  a stable 16-tick bid-ask spread. Position limit 200.
- **VELVETFRUIT_EXTRACT (VFE)** — another delta-1, trades around 5250
  with a tighter 5-tick spread. Position limit 200.
- **10 vouchers (VEV_4000 through VEV_6500)** — these are call options
  on VFE. Strike = the suffix number. Position limit 300 each.
  Cannot be exercised before expiry, expiry is 5 days after R3 ends so
  we never see exercise. Open positions get marked-to-fair at end of round.

There's also a **manual challenge** ("Bio-Pods") — a one-shot bidding
game submitted via the GUI. Separate from the algo trader.

## 2. The 30-second story of what works

Two near-orthogonal opportunities live in the data:

- **A) Market-make the goods** (HYDROGEL + VFE). Quote on both sides,
  collect the spread, manage inventory. HYDROGEL is the cleanest trade
  on the board: independent of everything else, wide stable spread, low
  bot toxicity. VFE is similar but smaller spread AND has informed buy
  flow you have to dodge.
- **B) Trade voucher mispricings.** The implied vol surface drifts
  intraday. A rolling per-tick smile fit gives a fair-value estimate
  that beats a static smile by ~30% RMSE. Two specific trades:
  the rolling-smile residual mean-reversion (mid vs theo) and a
  durable VEV_5300/5400 butterfly (5300 trades 1.8 ticks rich, 5400
  trades 2.0 ticks cheap, persistently).

The P3 winner (Frankfurt Hedgehogs) made ~200K/round on R3 doing
something close to (B), running it **completely unhedged**. The 7th
place team (CMU) tried something similar but used a STATIC smile and
went from 7th → 241st when the smile drifted intraday. Don't be CMU.

## 3. What the data actually shows (per product)

### HYDROGEL_PACK
- Trades around 9990. Spread = 16 on 92.7% of ticks.
- **Independent of everything else** (return correlation ~0 with VFE
  and all vouchers, confirmed three different ways including PCA).
- Lag-1 autocorrelation on `wall_mid` (midpoint of the deepest visible
  level on each side, not best bid/ask) is only −0.01 to −0.05. The
  earlier −0.13 figure was bid-ask bounce, not real fair-value
  reversion. **Don't expect "mean reversion edge" — the edge is just
  capturing the spread as a market-maker.**
- Bot toxicity: LOW. Two-sided flow, no informed drift.
- Stable across all 3 historical days.

### VELVETFRUIT_EXTRACT (VFE)
- Trades around 5250. Spread = 5 on 74% of ticks.
- **Buy-aggressor flow is informed** (mid drifts +0.63 ticks over the
  next 50 ticks after a buy-aggression event, t-stat +2.64). When
  bots aggressively lift VFE, prices keep going up. Quoting a tight
  ask = adverse selection. Solution: quote ask wider than bid (e.g.
  bid_offset=2, ask_offset=3).
- Cointegrated with the voucher chain via PC1 (60.5% of return variance
  loads on this factor). Options team's voucher hedging will hit this
  book — coordinate position limits.

### Vouchers
- **VEV_5000–5500**: real markets, real trades. The interesting ones.
- **VEV_4000, VEV_4500**: behave as delta-1 proxies (intrinsic + tiny
  premium). The price spread VEV_4500 − VEV_4000 should track exactly
  −500. Use as a kill-switch / sanity check.
- **VEV_5100, VEV_5200**: thin tape, very few bot trades. We'd be the
  market if we quote here.
- **VEV_6000, VEV_6500**: completely dead. Mid pinned at 0.5, every
  trade is a paired ghost event between the two strikes at price 0.0.
  **Skip these.**
- **The smile drifts heavily intraday** — quadratic curvature `a`
  swings ±0.28 within a single day and flips sign repeatedly. Static
  fit fails. Rolling fit (window=100) wins by 31% RMSE. This is the
  CMU disaster pattern, fully reproduced on our data, and corroborated
  by Discord chatter (Ethan, MarkBrezina, sama, Tribes all reporting
  static-smile burns).
- **Implied vol < realized vol** systematically (~0.25 vs ~0.34).
  Long-gamma is theoretically EV+ but theta and bid-ask eat most of it.

## 3.5. Informed-flow / insider-style signals

Two relevant classes here, and they're different:

### A. VFE buy-aggressor is informed (R3, tradeable now)

When bots aggressively lift VFE (price hits/crosses our ask), the mid
drifts **+0.63 ticks over the next 50 ticks** (n=780, t-stat +2.64,
statistically significant). This is the closest thing to an insider
signal we have in R3 — somebody (bots collectively) is consistently
right about VFE direction on the buy side.

**Two ways to use it**:
1. **Defensive (currently in our trader)**: quote ask wider than bid
   on VFE. Don't sell cheap when the toxic side is buying.
2. **Offensive (NOT in our trader yet)**: when a buy-aggression event
   happens (we see a print at-or-above current ask), GO LONG VFE
   ourselves to ride the +0.63-tick drift. This is "follow the
   informed flow" — same logic as UCSD's R5 trick but without needing
   counterparty IDs.

The offensive version is unproven on our data — we'd need to backtest
a "trigger long-buy on detected buy-aggression" overlay before we'd
know if it actually adds PnL net of the round-trip cost.

### B. UCSD-style counterparty insider (R5, not now)

Per `02c_ucsd.md`, the P3 winning play in R5 was: counterparty IDs
get revealed → rank bots by their forward-looking "% good trades" →
identify "Olivia" the insider → copy her trades → max position. **R3
tape is anonymized.** UCSD's trick will not work in R3. Defer to R5.

**Verified by Discord (07_bot_trades.md + 08a_discord_algo_trading.md)**:
no R3 user has identified a named insider bot in the chat — counterparty
IDs are still anonymous in R3, matching our finding.

### C. What is NOT an informed-trader signal here

- HYDROGEL has LOW flow toxicity — bot trades there are not informed,
  so there's no insider-flow play, just spread capture.
- OTM vouchers (5300/5400/5500) get 100% sell-aggressor flow, but the
  mid-drift after these dumps is ~0 — these are passive systematic
  shorts, not informed. **Harvestable on the bid (free voucher
  inventory at OK prices), not a momentum signal.**
- Voucher buy-aggression: insufficient data in R3 tape to test
  rigorously; defer.

### Bottom line on informed flow

There's exactly one statistically significant informed-flow signal in
R3 tape: **VFE buy-aggressor predicts +0.63 ticks/50-tick mid drift**.
We currently use it defensively. We could also use it offensively —
worth a backtest spike before R3 ends if voucher modules go on hold.

## 4. Cross-product structure

The board cleanly splits into two orthogonal books:
- {VFE + 8 live vouchers}
- {HYDROGEL alone}

- **No exploitable lead-lag.** Every meaningful pair peaks at lag 0.
- **Voucher cointegration in price space is mostly dead** — only the
  trivial VEV_4000↔4500 pair (both deep-ITM delta-1). Real voucher
  alpha lives in IV space (rolling-smile residuals), not price space.
- All structure is stable across days 0/1/2 — strategies should
  generalize to live R3.

## 5. Manual round (Bio-Pods bidding)

Submit two bids `(bid1, bid2)`. Each gardener has a hidden reserve
uniformly distributed on integers divisible by 5 between 670 and 920.
Acquired Bio-Pods auto-sell next day at 920.

- **Recommended: `(bid1=756, bid2=851)`** — captures 99% of unconstrained
  optimum, penalty-free unless crowd avg_b2 > 851.
- Crowd avg_b2 estimates from Discord cluster at 840–855.
- **DO NOT submit textbook (751, 836)** — drops 14% PnL if avg_b2 hits 850.
- "Higher than" reserve = strictly greater. So bid 756 clears reserve 755.
- Bids ending in 1 or 6 (one above multiples of 5) maximize sweep
  efficiency under the strict-greater rule.

This is a separate GUI submission, not part of `trader.py`.

## 6. Tools and accuracy expectations

We use a single backtester: **`prosperity4btest`** (Nabayan Saha's P4
fork, listed in `requirements.txt`). It has correct P4 LIMITS hardcoded
and includes free risk metrics (Sharpe, max DD, Sortino, Calmar).

```bash
venv/bin/prosperity4btest cli src/trader.py 3 --no-out
```

That's the whole command. No patching, no harness, no staging dirs.
See `03_tooling_landscape.md` for full details.

**Backtester accuracy reality check** (sourced from Discord +
inspection of BT source):

- **Goods (HYDROGEL + VFE)**: BT is trustworthy for relative
  comparisons. Absolute PnL within ~10–25% of live.
- **Vouchers**: BT marks open inventory at last observed mid; the IMC
  platform marks at a hidden fair value. Possible material discrepancy.
  Mitigate by ending the round flat on voucher positions.
- **Portal score** is NOT a tuning target — portal runs ~10% of one
  day, gives ~3% of 3-day BT PnL. Use local BT for ranking.
- **Honest BT cap from Discord**: ~150–200K on 3 days (oracle ~155K
  per lanister5240). Anyone claiming >100K portal is overfit.
  **Our draft trader does ~31K over 3 days on `prosperity4btest`
  (goods only, Sharpe 2.50, max DD 1.25%).**

**Avoid** uploading logs to `prosperity.equirag.com` — confirmed to
store uploaded files (alpha leakage risk).

## 7. Decisions to make

### Locked
- **Don't trade VEV_6000 / VEV_6500** — dead.
- **Use rolling smile, not static smile** — for any voucher trader.
- **Use `wall_mid` as the fair-price anchor** — modestly better than
  top-of-book mid.
- **Stay on `prosperity4btest`** — don't churn on tooling.
- **Manual round: submit (756, 851)** — needs a click in the GUI.

### Open

1. **Voucher modules in OUR `trader.py`: yes/no?**
   - YES → higher PnL ceiling (rolling-smile mid-theo + 5300/5400
     butterfly, both EDA-validated). Coordinate with options-team
     teammates so we don't double-trade.
   - NO → ship goods-only, let teammates merge their voucher logic.
     Lower coordination risk.
2. **HYDROGEL `half_edge` final pick** — preliminary sweep showed
   `half_edge=8` is best in BT, but Discord notes some users complain
   of HG drawdowns despite the stable spread (hint: BT may underestimate
   adverse fills). Run a final {7, 8, 9} sweep before submission.
3. **VFE asymmetric quoting** — preliminary sweep validated `(bid=2,
   ask=3)`. Confirm under final sweep.
4. **Final sanity**: `src/trader.py` is currently DRAFT. Whatever we
   ship needs one more pass to make sure no `print()` spam (Lambda
   100MB log limit) and no slow rolling-window code in `traderData`
   (Discord-flagged hidden cost).

## 8. The risks we should hold lightly

- **Single dataset** — all our EDA is on the 3 historical days. Live
  R3 may behave differently. Stable cross-day metrics is reassuring
  but not a guarantee.
- **Day-2 HYDROGEL underperformance** — drops ~33% in BT vs days 0/1.
  Affects every parameter config equally so probably structural, not
  a bug. Possibly a regime that R3 live also has.
- **Implied < realized vol** — could be a real edge or could be that
  the bots know the realized-vol regime is about to shift down.
  We don't know which.
- **Insider bot trick (UCSD's "Olivia")** — counterparty IDs are
  anonymized in R3. The trick lives in R5. Don't spend cycles on it
  now.
- **Backtester is approximate** — already covered, but bears repeating:
  rank by BT, don't trust absolute numbers.

## 9. What the P3 winners taught us (in one paragraph each)

- **Frankfurt Hedgehogs (P3 2nd, ~200K/round on R3)**: Made the
  contrarian call to NOT delta-hedge — the bid-ask spread on the
  underlying ate any hedging benefit. Used hardcoded smile coefficients
  fitted offline once. Vega-gated to skip dead strikes. Single-file
  submission, stdlib only. **Lesson: simplicity + offline rigor wins
  over live cleverness.**
- **CMU Physics (P3 7th → 241st on R3)**: Same general approach as
  Frankfurt but with a STATIC smile fitted on day 0 and re-used. Smile
  drifted intraday and they didn't notice until post-mortem. Their
  fix (rolling per-voucher mid-IV window of 20) is what we're using.
  **Lesson: validate smile stability before you assume it.**
- **UCSD Alpha Animals (P3 9th)**: Their R3 had a literal pricing bug
  (priced underlying using `avg_strike` for spot pricing → BS(S,S)
  small → algo perma-shorted to limit, accidentally profitable in P3
  because rock drifted down). **Lesson: build divergence kill-switches
  so a model bug doesn't go max-position.** Their R5 insider-bot
  detection (rank counterparties by % of "good" trades) is the prep
  for our R5.

## 10. Where to find the receipts

Every claim above traces to one of these (lean-bulleted, with cited
data wherever possible):

- Data findings: `01_initial_eda.md`, `04_microstructure.md`,
  `05_voucher_chain.md`, `06_cross_product.md`, `07_bot_trades.md`
- Plots: `plots/`
- P3 winners: `02a_frankfurt.md`, `02b_cmu.md`, `02c_ucsd.md`
- Discord channels: `08a_discord_algo_trading.md`,
  `08b_discord_general.md`, `08c_discord_manual_trading.md`,
  `08d_discord_open_source.md`
- Tooling: `03_tooling_landscape.md`
- State of code/work: `_session_state.md`, `_next_steps.md`
- Navigation: `INDEX.md`
