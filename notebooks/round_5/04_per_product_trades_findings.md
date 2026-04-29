# Notebook 04 — Per-Product Trade Tape: Findings

Source notebook: `04_per_product_trades.ipynb`  
Data: `trades_round_5_day_{2,3,4}.csv`, `prices_round_5_day_{2,3,4}.csv`

---

1. **Counterparty columns are 100% blank.** `buyer` and `seller` are NaN in all 35,385 trade rows across days 2/3/4. Signed-flow inference must use spread-cross only. [cell 1]

2. **Three-tier category structure confirmed.** Over days 2–4 per product: 8 standard categories = 733 trades / 1,805 vol; Pebbles = 644 trades / 2,283 vol; Microchips = 569 trades / 1,119 vol. Matches AGENT_BRIEF benchmarks exactly. [cell 2]

3. **Pebbles quantity distribution is distinct.** Min qty = 2 (no single-unit trades anywhere in Pebbles). Dominant qty = 5 (885 trades, 27.5%). Mean qty = 3.545 vs 2.462 for standard categories. This is what drives higher volume per fewer trades. [cell 3 / cell 4]

4. **Microchips quantity cap at 3.** Max qty = 3 (vs 4 for standard cats, 5 for Pebbles). Qty-1 and qty-2 dominate (34% and 36%). Mean qty = 1.967. Fewer trades + smaller sizes → lowest total volume of any category. [cell 3 / cell 4]

5. **All 5 products in every category trade at identical timestamps.** Verified for all 10 categories across days 2/3/4 — 100% timestamp synchronization within each category. The category is the generation unit, not the individual product. [cell 5]

6. **All 5 products in a category also carry identical quantity per tick.** At every timestamp, all 5 members trade the same qty — 100% of ticks for GalaxySounds (733/733), Pebbles (644/644), Microchips (569/569). [cell 5]

7. **Three independent generation processes.** The 8 standard categories share identical timestamp sets (229/255/249 timestamps on days 2/3/4). Pebbles has its own set, Microchips has its own set, with <2% overlap between any Pebble/Microchip timestamp and the standard-8 set. → Three separate NPC bots (or schedules). [cell 5]

8. **Zero neutral signed-flow trades.** Every trade falls exactly at best_bid or best_ask — merge hit rate = 1.0, neutral count = 0. Spread-cross classification is complete and unambiguous. [cell 6]

9. **Microchips show strongest buy-side flow imbalance.** Net flow = +81 vol per product across days 2–4; flow imbalance ratio = +0.072. All 5 Microchip products share exactly the same imbalance (uniform generation). Needs corroboration: [03_per_product_timeseries] AR(1) on Microchip prices; [02_per_product_microstructure] book-side depth. [cell 6]

10. **8 standard categories show uniform sell-side imbalance.** Net flow = −45 vol per product, imbalance = −0.025. Uniform across all 40 standard products — further evidence of a single shared generation process for the standard-8. [cell 6]

11. **Pebbles: zero signed-flow imbalance.** Buy vol = sell vol across all days and members. No directional pressure detectable in tape. [cell 6]

12. **Trade count CoV across days: Microchips most variable (CV = 0.074), Pebbles next (0.066), standard-8 lowest (~0.056).** All categories are relatively stable but Pebbles and Microchips show slightly higher day-to-day variance. Needs corroboration: [08_time_regime] for volatility clustering. [cell 7]

13. **Time distribution of trades is broadly uniform.** CoV of trade count across 10 equal time-bins is 0.13–0.16 per day. No strong intraday burst or end-of-day clustering. [cell 4]

14. **Intra-category product variation in trade count: zero.** For every category and every day, all 5 products have exactly the same trade count and total volume. This is structural, not coincidental — products within a category are generated identically. Consequence: individual product selection within a category provides no tape-based differentiation signal. [cell 7]

15. **Pebbles mean inter-arrival time = 4,639ms; Microchips = 5,270ms; standard = 4,092ms.** Microchips arrive least frequently but with moderate IAT variance (std = 5,064). Pebbles arrive somewhat less often than standard but with higher per-trade volume. Needs corroboration: [03_per_product_timeseries] for autocorrelation in trade arrival. [cell 8]
