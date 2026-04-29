# Notebook 09 — Determinism & Anomaly Findings

> Source: `09_determinism_anomaly.ipynb`. All claims cite cell output.
> No strategy proposals. No PnL predictions.

## Key findings

1. **PEBBLES: hard sum constraint = 50000 (basket FV confirmed).** The 5-product sum (PEBBLES_XS+S+M+L+XL) equals 50000.0 exactly in 12,188/30,000 ticks (40.6%), is within ±0.5 in 26,681/30,000 ticks (88.9%), and within ±1.5 in 29,147/30,000 ticks (97.2%). The sum has only 18 unique values across all 3 days. ADF test: stat=−122.7, p=0.0000 (strongly stationary). [cell-6, cell-7]

2. **PEBBLES: individual products wander freely but cancel.** PEBBLES_XS ranges [5052, 10496], PEBBLES_XL ranges [9188, 17240], yet their sum = 50000 ± 2.8 std. The category mean price = 10000.00 ± 0.56. This is a zero-sum constraint across all 5 members — any deviation by one must be offset by others. [cell-27]

3. **No product has a hardcoded single-price FV (≥ 90% mode prevalence).** Max mode prevalence across all 50 products is 5.38% (ROBOT_DISHES). No product is "pinned" to a single price. The PEBBLES basket sum constraint (cell-6) is the only hardcoded FV, and it applies to the basket, not individual prices. [cell-3]

4. **ROBOT_IRONING: discretized step-function prices — 40.4% zero returns, 96.7% on 10-unit grid.** Non-zero returns are ±10 in 73.1% of cases and ±20 in 14.6%. Only 631 unique prices across 30,000 ticks vs. 3,000–7,500 for typical products. This is a mechanically distinct generator — price moves in discrete +10/−10 hops. Synthetic GBM (discretized) yields < 0.1% zero returns; 40.4% is far above the noise floor. [cell-11, cell-12, cell-30]

5. **OXYGEN_SHAKE_EVENING_BREATH: same discrete step pattern — 39.2% zero returns, 96.7% on 10-grid.** Non-zero returns: ±10 (71.1%), ±20 (16.3%). Only 453 unique prices across 30,000 ticks. Signature nearly identical to ROBOT_IRONING. Both are significantly above GBM p99 (< 0.1%). [cell-11, cell-12, cell-30]

6. **ROBOT_DISHES: 27.4% zero returns — intermediate step structure.** Dominant step = ±2 (not ±10), 3,048 unique prices. 5.38% mode prevalence (highest of all 50 products). Structural anomaly compared to the ~2–3% zero-return baseline seen in most products, but weaker than IRONING/EVENING_BREATH. [cell-11, cell-3]

7. **SNACKPACK CHOCOLATE+VANILLA: strong mirror pair (corr = −0.974 on day 2, −0.980 on day 3, −0.962 on day 4).** Their sum has CV = 0.212% within a single day but DRIFTS across days (20,025 → 19,927 → 19,870). ADF on the multi-day sum: stat=−1.76, p=0.40 — NOT stationary. This is a correlated pair, not a hard constraint. Needs corroboration from notebook 05. [cell-8]

8. **SNACKPACK PISTACHIO+RASPBERRY: secondary mirror pair (corr = −0.75 to −0.95).** Within-day sum CV = 0.45–0.82%. Also drifts across days (19,721 → 19,605 → 19,396). SNACKPACK category has only 1,673–3,089 unique prices per product vs. 3,500–7,500 for most categories — indicating a constrained generator. [cell-8, cell-32]

9. **No cross-product pairs with |corr| > 0.99 on price levels.** Full 50×50 correlation scan on day-2 prices found 0 pairs with |corr| > 0.99, and 0 pairs with |corr| > 0.95. Products are not exact copies or mirrors of each other at the level-price level. [cell-20]

10. **No timestamp gaps in any product-day.** All 50 products × 3 days have exactly 10,000 consecutive ticks at step 100 (timestamps 0 to 999,900). No missing data. [cell-18]

11. **Outlier ticks > 5σ (per-day) found only in 3 products.** OXYGEN_SHAKE_CHOCOLATE: 71 outlier ticks, OXYGEN_SHAKE_EVENING_BREATH: 66, ROBOT_IRONING: 56. All outlier returns are ±100 — these are infrequent large jumps distinct from the dominant ±10 step behavior. [cell-15, cell-16]

12. **FFT periodicity: only PANEL_1X2 (marginally) beats shuffled-return null.** 49/50 products have FFT SNR below the shuffled-returns p99 null. No robust frequency-domain periodicity found. High raw FFT SNR for all products reflects non-stationary trends, not true cycles. [cell-23]

13. **Category sum CV ranking: PEBBLES (0.006%) is 50× more constrained than SNACKPACK (0.377%), and 400× more constrained than ROBOT (1.7%).** All other 8 categories have CV > 1.4%. PEBBLES is the only category with a mechanically enforced sum. [cell-5]

14. **MICROCHIP shows no special structure beyond baseline.** Despite the AGENT_BRIEF flagging Microchips as anomalous by trade-count, the 5-sum CV = 3.0% (noise range), zero-return rate = 2.1–2.8% (baseline), no grid discreteness, no FFT significance. The trade-count anomaly is not reflected in price structure visible here — needs investigation in notebook 04. [cell-26, cell-32]

15. **Triage calls from this notebook:** PEBBLES (all 5): *likely exploitable* (hard basket FV at 50000). ROBOT_IRONING, OXYGEN_SHAKE_EVENING_BREATH: *likely exploitable* (discrete step generators with > 35% zero returns). ROBOT_DISHES, OXYGEN_SHAKE_CHOCOLATE, SNACKPACK (all 5): *probably tradable* (structural anomalies needing corroboration). All other 35 products: *probably noise* from this notebook's lenses — no deterministic or anomalous structure detected.

## Cross-reference flags

- Bullets 1–2 (PEBBLES basket FV): request corroboration from notebooks 03 (AR on individual products, should show mean-reversion toward sum constraint), 05 (cointegration test should find rank 4 within PEBBLES).
- Bullet 4–5 (ROBOT_IRONING, O2_EVENING_BREATH step generators): request cross-check from notebook 03 (ADF on levels should show unit root; ADF on returns should show stationarity).
- Bullet 7–8 (SNACKPACK mirror pairs): request corroboration from notebook 05 (within-category cointegration), notebook 03 (AR on spread).
- Bullet 14 (Microchips not anomalous in price): contradicts AGENT_BRIEF trade-count signal — notebook 04 should resolve.
