# R3 — Counterparty bot-trade tape EDA

Source: `data/round_3/trades_round_3_day_{0,1,2}.csv` joined to
`prices_round_3_day_*.csv`. Script: `notebooks/05_bot_trades_eda.py`.
Plots: `docs/round_3/../../../notebooks/round_3/plots/05_*.png`.
Numeric summary: `docs/round_3/research/05_bot_trades_summary.csv`.

## TL;DR

- **Counterparty IDs are fully anonymized** in R3 (`buyer`/`seller` 100% null
  across 4,048 trades). UCSD-style per-bot edge ranking is **deferred to R5**.
- **One robust informed-flow signal**: VFE buyer-aggressor → mid +0.63 ticks
  over next 50 ticks (n=780, t=+2.64). Bot VFE buying predicts price up.
- **OTM vouchers (5300/5400/5500/6000/6500) are 100% sell-aggressor tape** —
  bots dump them, never lift offers. Drift after dumps is not informed →
  passive systematic short-premium quoters, not predictive.
- **VEV_6000 / VEV_6500 zero-price trades are PAIRED ghost events**: every
  zero-price 6000 trade matches a 6500 trade at the same timestamp + same qty.
  Mid stays pinned at 0.5 throughout. Tape-only (book never shows 0 ask).
  **Do not try to lift them — not free money.**
- Three vouchers (4500, 5000, 5100) have only **1 counterparty trade each** —
  effectively no bot tape; whatever we post defines the market.

## Counterparty IDs

`buyer` and `seller` columns are entirely null on all three days, all 4,048
trades. Cannot identify per-bot informed/dumb behavior à la UCSD's "Olivia"
in P3 R5. Re-run the methodology in P4 R5 if names leak there.

## Trade volume per product (3 days pooled)

| Product | n_trades | n_volume | %sell_aggr | drift50 informed? |
|---|---:|---:|---:|---|
| VELVETFRUIT_EXTRACT | 1,372 | 8,269 | 43% | **buy side: +0.63t (t=+2.64)** |
| HYDROGEL_PACK | 1,010 | 4,078 | 48% | no (|t|<1.3 both sides) |
| VEV_4000 | 464 | 940 | 51% | no |
| VEV_6000 | 284 | 1,002 | 100% (price=0) | n/a (frozen mid) |
| VEV_6500 | 284 | 1,002 | 100% (price=0) | n/a (frozen mid) |
| VEV_5500 | 267 | 937 | 100% | no (drift ~0) |
| VEV_5400 | 225 | 787 | 100% | no |
| VEV_5300 | 121 | 420 | 98% | sells slightly informed (t=-1.4) |
| VEV_5200 | 18 | 63 | 94% | thin |
| VEV_4500 / 5000 / 5100 | 1 each | 1 each | — | dead in tape |

## Trade size

- HYDROGEL: lots of 1-6, mode 4. Suggests fixed-lot bot.
- VFE: lots of 1-15, mode 6.
- All vouchers: lots 1-5, mode 4. Same lot profile across all OTM strikes →
  likely same bot family quoting the OTM chain.

## Direction & mid-drift detail

Conditional drift @ +50 ticks (signed in absolute, not aggressor-aligned):

| Product | side | n | mean drift50 | std | t |
|---|---|---:|---:|---:|---:|
| VFE | **buy_aggr** | 780 | **+0.629** | 6.66 | **+2.64** |
| VFE | sell_aggr | 589 | +0.077 | 6.39 | +0.29 |
| VEV_4000 | buy_aggr | 221 | -0.011 | 6.31 | -0.03 |
| VEV_4000 | sell_aggr | 237 | -0.323 | 7.30 | -0.68 |
| VEV_5300 | sell_aggr | 119 | -0.340 | 2.66 | -1.40 |
| VEV_5400 | sell_aggr | 225 | -0.036 | 1.35 | -0.39 |
| VEV_5500 | sell_aggr | 267 | +0.009 | 0.67 | +0.23 |
| HYDROGEL | buy_aggr | 523 | -0.178 | 13.14 | -0.31 |
| HYDROGEL | sell_aggr | 484 | +0.727 | 12.99 | +1.23 |

Only VFE buy-aggressor crosses statistical significance.

## VEV_6000 / VEV_6500 zero-price trades

- 568 total zero-price trades (284 in each of 6000 & 6500).
- 100% paired: every zero-price (day, ts) has both symbols, same quantity.
- Mid for both symbols pinned at **0.5** every tick of every day.
- All VEV_6000/VEV_6500 trades in the entire tape are at price 0 (no other
  prices ever traded).
- **Interpretation**: tape-only matched-pair ghost events, almost certainly
  platform settlement / paired-quote self-cross at deep-OTM zero-bid books.
  The order book never offers VEV_6000/6500 at 0 — it's not a liftable price.
  No alpha here.

## Per-product flow toxicity (for OUR market-making)

- **HYDROGEL_PACK** — **LOW**. Two-sided flow (52/48), no informed drift,
  wide stable spread. **Safe MM target.**
- **VELVETFRUIT_EXTRACT** — **MEDIUM**. Tape is two-sided but buy-aggressor
  is informed (+0.63t, t=+2.64). Risk: posting a tight ASK gets adversely
  selected. **Quote asymmetric** — wider ask than bid, OR lean inventory long
  to ride the buyer-informed flow. Also: VFE is the voucher underlying, so
  hedging flow from voucher bots may add unseen toxicity.
- **VEV_4000** — **LOW-MEDIUM**. Behaves delta-1 (deep ITM); no informed
  flow detected; reasonable MM candidate.
- **VEV_5300 / 5400 / 5500** — **MEDIUM-LOW**. Bots only sell here. Sit on
  the BID inside their dump price → harvest cheap inventory. But these are
  short-vega positions; need vol model to mark them.
- **VEV_4500 / 5000 / 5100** — **N/A**. No counterparty tape (1 trade each).
  Whatever we post defines the market. Use these for arb against other
  strikes; don't expect counterparty fills.
- **VEV_5200** — **N/A** (18 trades, thin).
- **VEV_6000 / VEV_6500** — **DEAD**. Mid pinned 0.5; only 0-price ghost
  trades. Do not trade.

## Actionable items

1. VFE strategy: build a buy-aggression signal (count of buyer-aggressor
   trades in last K ticks, or signed volume) and bias inventory long when
   it spikes. Expect ~0.6t edge over 50-tick horizon.
2. OTM voucher MM (5300-5500): post passive bids ≤ wall_mid; expect to be
   filled by dumping bots; mark short positions with a vol model (own
   skew/IV — these are real options).
3. Skip VEV_6000/6500 entirely.
4. Re-run this notebook on R5 trade tape immediately when it drops — if
   names appear, the counterparty-edge ranking from `notebooks/05_*.py`
   becomes directly applicable (pasting a Q8 block is the next step).
