# R3 vs R4 — General lessons going into R5

> Comparison of our R3 v12 ship to friend's R4 bot (`544592.py`).
> Live PnL: R3 v12 = **$77,539** (single submission, day 3 scoring).
> Live PnL: R4 friend = **$197,363** (~2.5× more).
> Same 3 products (HYDROGEL/VELVETFRUIT/VEV vouchers); difference is purely strategy.

## What R4 did better

1. **Used the new mechanic.** R4 added counterparty IDs; friend's bot
   exploited it with the **Mark 38 intercept** in HG (passive quote one
   tick ahead of Mark 38's known cross direction). Layer 2b book-imbalance
   pre-positioning was even more aggressive — fires *one tick before*
   Layer 2's reactive signal. R3 v12 had no equivalent edge source.
   → For R5: when IMC introduces a new mechanic mid-comp, treating it
   as the headline alpha source, not a side feature.

2. **Live TTE inference instead of hardcoded day counter.** Friend's BS
   pricer bisection-solves for TTE from the live option-chain mid each
   tick. Our v12 hardcoded TTE per day. Result: zero day-boundary errors,
   zero stale-TTE pricing, automatically adapts to round structure.
   → For R5: prefer self-calibrating from live data over hardcoded
   constants whenever possible.

3. **`traderData` JSON round-trip on every strategy.** Persists EMAs,
   entry prices, etc. across ticks. Mitigates the Lambda cold-start
   hypothesis (research/17). v12 had no traderData usage at all.
   → For R5: every stateful strategy gets save/load from day 0.
   Cheap defensive hygiene with no downside.

4. **Stop-losses actually wired in.** Friend's bot closes positions on
   40-tick adverse moves. v12 had no stop-loss — relied entirely on the
   FV anchor and inventory cap. Live max drawdown for v12 was 88.8%
   (we nearly gave back all gains before recovering). Stop-loss prevents
   that.
   → For R5: every directional position needs an exit rule.

5. **Modular Strategy base class.** Clean abstract interface with
   `save_state` / `load_state` per strategy. Made adding new products
   cheap (Osmium and Pepper strategies were stubbed out and ready). v12
   was a single 600-line monolith.
   → For R5 with 50 products: a per-product strategy abstraction is
   essentially mandatory.

## What R3 v12 did right (carry-overs that still apply)

- **Hardcoded FV anchor** for stable products (VFE = 5250). Friend's R4
  bot kept this. If R5 reveals stable-FV products, hardcode after
  verification (don't roll live-derived too eagerly — v16's pure
  live-delta lost $20k vs v12).
- **Position-aware inventory caps** (ER_CAP, M38_CAP).
- **Conservative size in the unknown.** v12 ships at cap=160; v13's
  cap=240 would have been worse in live volatility.
- **Build BT-vs-live trust early.** Even with the calibration
  imperfections, BT direction was right; we knew v12 > v13 from BT
  alone, which is what mattered.

## R5 priorities derived from this

In order:

1. **Read the R5 brief and data for "embedded patterns"** — the brief
   explicitly says some categories are exploitable. EDA first.
2. **Build a Strategy base class scaffold** (steal friend's pattern).
   Position limit 10/product means strategies can't be PnL-heavy
   individually — selection across products matters more than tuning.
3. **Cherry-pick winners.** With 50 products and limit 10, we may run
   strategies on only 5-15 products. Skip noise products entirely.
4. **Counterparty profiling on R5 trade data** if `Trade.buyer/seller`
   persist (CLAUDE.md flagged this — verify on R5 data).
5. **Manual: news-driven directional, quadratic-fee budget allocation.**
   Treat as separate problem from algo.

## Calibration anchor for R5 BT

R3 v12 BT-vs-live ratio on day 3 (same data) = **2.72×** over-prediction.
Use this as a sanity floor — any R5 strategy with BT > $200k for the
scoring day should expect ~$80k live. Treat BT outputs > 3× this anchor
with suspicion (likely overfitting to the 3 historical days).
