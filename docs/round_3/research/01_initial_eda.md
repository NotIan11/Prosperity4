# R3 — Initial EDA findings

Source: `data/round_3/prices_round_3_day_*.csv` (3 days × 10,000 ticks × 12 products).
Script: `notebooks/01_r3_eda.py`.

## Cross-product structure

**HYDROGEL is fully independent of everything else.**

| Product pair | Return correlation (1-tick) |
|---|---|
| HYDROGEL × VELVETFRUIT | 0.01 |
| HYDROGEL × any VEV voucher | ~0.00 |
| VELVETFRUIT × VEV_5000 (near-ATM) | 0.75 |
| VELVETFRUIT × VEV_5500 (deep OTM) | 0.33 |

Implication for division of labor: **HYDROGEL is safe to own without coordinating with the options team.** Their voucher book cannot leak risk into your hydrogel positions. VELVETFRUIT is the contested asset — options team will likely delta-hedge through it.

VEV_6000/6500 have zero variance (pinned at 0.5) → confirmed dead, ignore.

## Per-product microstructure

### HYDROGEL_PACK
- **Mean ~9991, std ~32, range 9891–10079** across 3 days.
- **Spread: median 16, range 15–17.** Very stable. This is a *wide* spread for a product priced ~10000.
- **Lag-1 return autocorr: −0.13.** Negative — mean-reverts at the tick scale (consistent with bid-ask bounce or aggressive flow alternating sides).
- Per-day stds: 25 / 38 / 32 — vol regime varies day to day.

**Read**: textbook market-making candidate. Wide stable spread + negative microstructure autocorr + independence from other products = quote both sides at fair_value ± half_spread, capture the bounce.

### VELVETFRUIT_EXTRACT
- **Mean ~5250, std ~16, range 5198–5300.**
- **Spread: median 5, range 4–6.** Tight.
- **Lag-1 autocorr: −0.16.** Same microstructure pattern as hydrogel.
- Per-day stds: 14 / 15 / 17.

**Read**: tighter spread = thinner edge per round-trip, but still negatively autocorrelated. Complication: this is the underlying for the voucher chain, so the options team's hedging flow will hit this book. Need to coordinate position limits.

## Open questions for next pass

1. What's the actual position limit per product? (Need to confirm from R3 brief / IMC platform docs.)
2. Is the −0.13/−0.16 lag-1 autocorr robust **out of sample** (e.g. holds within each individual day, not just pooled)?
3. Does HYDROGEL have any longer-horizon structure (drift, regime, mean reversion at minute scale)?
4. Bot trade pattern in `trades_*.csv` — who's the counterparty, are they directional?
5. What does the order book look like beyond top-of-book? (`bid_price_2`, `bid_price_3` etc — depth info we haven't touched yet.)
