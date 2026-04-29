# Notebook 06 — Cross-Category Factor Structure: Findings

> Source: `06_cross_category_factors.ipynb`, cells 1–16. Days 2+3+4 (30,000 ticks × 50 products each).
> Return correlations = pooled tick-level log-returns. Level correlations = z-scored mid-price within day.

---

1. **PEBBLES dominates the global factor structure.** PC1 (12.70% of total variance) and PC2 (5.80%) are almost entirely PEBBLES: all five top PC1 |loadings| are PEBBLES (PEBBLES_XL +0.784, PEBBLES_XS −0.468, S/M/L each ≈ −0.22); next-highest non-PEBBLES loading on PC1 is 0.005. PC2 is likewise PEBBLES-dominated. PC4 (3.84%) is a third PEBBLES factor. No other category comes close to this factor concentration. Cross-ref: `[cell 10]`, `[cell 11]`.

2. **PEBBLES products anti-correlate within the category.** Within-category mean return correlation = −0.191 (all other categories range −0.016 to +0.007). PEBBLES_XS vs PEBBLES_XL pairwise return corr ≈ −0.506 — strongest pairwise relationship in the entire 50×50 matrix. This is not noise; PEBBLES_XL and PEBBLES_XS move in opposite directions tick-by-tick. Needs corroboration from `[05_within_category_corr]` and `[09_determinism_anomaly]`. `[cell 15]`

3. **ROBOT_DISHES is a singleton factor.** PC3 (4.28%) has loading +0.995 from ROBOT_DISHES alone — no other product has |loading| > 0.07 on PC3. This is an extreme outlier: one product driving an entire PC that explains more variance than most categories. Needs corroboration from `[03_per_product_timeseries]` and `[09_determinism_anomaly]`. `[cell 10]`, `[cell 11]`

4. **MICROCHIP dominates PCs 5–8.** PC5 (3.37%), PC6 (3.31%), PC7 (3.30%), PC8 (3.27%) are all MICROCHIP-dominant (mean |loading| 0.268–0.361 vs all others < 0.15). MICROCHIP uniquely consumes four consecutive PCs, suggesting five products with substantially independent dynamics rather than a uniform basket. Cross-ref: `[05_within_category_corr]`, `[03_per_product_timeseries]`. `[cell 10]`

5. **SNACKPACK shows extreme internal polarization.** Within-category return corr: mean = −0.160, but range is −0.923 to +0.913 — the widest range of any category. Some SNACKPACK pairs are nearly perfectly anti-correlated, others nearly perfectly co-correlated. PC10 (2.11%) is SNACKPACK-dominant. Needs corroboration from `[05_within_category_corr]` and `[01_per_product_distrib]`. `[cell 15]`, `[cell 10]`

6. **No cross-category return correlations exceed |0.30|.** Zero cross-category pairs hit the threshold. The factor structure is entirely within-category for return dynamics. Categories are isolated from each other in return space. `[cell 14]`

7. **8 of 10 categories are nearly uncorrelated internally (in returns).** GALAXY_SOUNDS (mean = 0.0040), PANEL (0.0045), TRANSLATOR (0.0045), SLEEP_POD (0.0028), ROBOT (−0.0008), UV_VISOR (0.0060), OXYGEN_SHAKE (0.0070), MICROCHIP (0.0062) all have mean within-category return correlations in the range [−0.01, +0.014]. These products behave like 40 independent random walks in return space. `[cell 4]`

8. **Hierarchical clustering at k=10 does NOT recover named categories.** At Ward k=10, MICROCHIP products scatter across clusters 4, 5, and 10; 5 of those clusters contain strays from 3–5 different categories mixed together. Only PEBBLES (cluster 2) and partial SNACKPACK (clusters 1 and 3) achieve clean single-category clusters. Needs cross-ref with `[05_within_category_corr]`. `[cell 7]`

9. **The factor structure is stable across days 2/3/4.** Frobenius norm of the 50×50 correlation matrix difference: Day 2 vs Day 3 = 0.690, Day 2 vs Day 4 = 0.720, Day 3 vs Day 4 = 0.717. These are consistent — the structure does not collapse or invert day-to-day. Per-day PC1 explained variance is consistent (varies by < 1pp). `[cell 13]`

10. **50% of return variance requires 13 PCs; 90% requires 40.** The spectrum is flat after PC1 (12.70%): PCs 2–9 each contribute 3.2–5.8%. Random baseline (1/50) = 2.0%; 8 out of 50 PCs beat this by < 2×. The market has no dominant single factor beyond PEBBLES; most products are independently noisy. `[cell 8]`

11. **Level correlations do not rescue category coherence.** Within-category level-corr means are all near zero or negative (range −0.214 to +0.135). SLEEP_POD has the highest level-corr mean (0.135) but max pair is only 0.740 and min is −0.328 — not a coherent basket. No category shows the strong positive level-corr pattern expected from co-integrated products. `[cell 4]`

12. **PEBBLES_XL is the single largest contributor to global variance.** Absolute loading on PC1 = 0.784, on PC2 = 0.219. Its combined factor weight is far higher than any other product. PEBBLES_XS is the second-largest contributor (PC1 = −0.468, PC2 = +0.816). These two products alone absorb most of the Pebbles factor variance. Cross-ref `[01_per_product_distrib]`, `[03_per_product_timeseries]`. `[cell 11]`

13. **ROBOT category splits into two sub-clusters.** In Ward clustering, ROBOT products appear in clusters 4 (ROBOT_MOPPING), 5 (ROBOT_VACUUMING, ROBOT_IRONING), 9 (ROBOT_LAUNDRY), and 10 (ROBOT_DISHES). ROBOT_DISHES is isolated as a singleton factor (PC3). The other four ROBOT products scatter but their within-category return corr mean is only −0.001 — essentially zero. No strong basket structure. `[cell 7]`

14. **Categories that may be "probably noise" by global structure alone.** GALAXY_SOUNDS (within-ret mean 0.0040, no dominant PC, Ward cluster fragmented), PANEL (0.0045, same), TRANSLATOR (0.0045, same), UV_VISOR (0.0060, same), OXYGEN_SHAKE (0.0070, same) all show negligible inter-product correlations and fragment across clusters. Needs corroboration from `[03_per_product_timeseries]` (ADF, AR1) before declaring noise. `[cell 4]`, `[cell 7]`

15. **PEBBLES and MICROCHIP are the highest-priority categories by global structure.** PEBBLES: 3 of top-4 PCs are pure-PEBBLES factors; internal anti-correlation is structural (not noisy). MICROCHIP: dominates 4 consecutive PCs (5–8); products have differentiated idiosyncratic dynamics. ROBOT_DISHES flags as a special case (singleton PC3, loading 0.995). All three findings are replicable across days 2, 3, 4. Triage call pending corroboration from `[05_within_category_corr]`, `[03_per_product_timeseries]`, `[09_determinism_anomaly]`.
