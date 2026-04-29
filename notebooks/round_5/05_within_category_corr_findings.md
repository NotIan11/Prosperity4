# Notebook 05 — Within-Category Correlation Findings

> Source: `05_within_category_corr.ipynb`. All numbers from executed cells.
> Data: `prices_round_5_day_{2,3,4}.csv`, n ≈ 30,000 ticks per product (all days combined).
> Lenses: pairwise corr (levels + returns), Engle-Granger cointegration, lead-lag CCF, basket spread ADF.

## Key findings (≤15 bullets)

1. **No category has a uniformly high within-category level correlation.** Median level corr across all C(5,2)=10 pairs ranges from -0.67 (ROBOT) to +0.35 (SLEEP_POD). No category exceeds the 0.7 "probably tradable" threshold. Triage from this lens alone: all 10 categories → **probably noise**. [cell: cat_summary print, lc_median column]

2. **SNACKPACK has the widest within-category spread: level corr min=-0.9259, max=+0.4704.** This extreme dispersion (range=1.40) implies products move in strongly opposing directions — two subsets of snack products are anti-correlated. Compare to SLEEP_POD (range=0.94) or GALAXY_SOUNDS (range=0.80). Needs corroboration from notebook 03 (AR structure) and 07 (name-feature encoding). [cell: cat_full]

3. **SNACKPACK is the only category with multiple Engle-Granger cointegrated pairs: 3 out of 10 pairs (p<0.05).** MICROCHIP has 1 cointegrated pair (p=0.0274). All other 8 categories have zero cointegrated pairs on the all-days combined series. However, **no pair was cointegrated on all 3 individual days** — i.e., zero pairs show day-stable cointegration. Flag: 3/10 SNACKPACK pairs cointegrated may reflect regime-conditional structure rather than true long-run equilibrium. [cell: coint_df, stable_coint]

4. **PEBBLES has the strongest returns-level correlation among all within-category pairs: PEBBLES_L/PEBBLES_XL ret_corr = -0.4932.** Every other category has returns corr in [-0.10, +0.10] range. This -0.49 contemporaneous anti-correlation in returns is anomalously strong and may indicate opposing bookkeeping or synthetic offset mechanics. Needs corroboration from notebook 04 (trade tape) and 09 (anomaly/determinism). [cell: corr_df, pairwise corr print]

5. **Returns correlations are near-zero for all other category pairs.** Median returns corr per category: SNACKPACK=0.021, OXYGEN_SHAKE=0.007, PANEL=0.006, UV_VISOR=0.006, MICROCHIP=0.006, SLEEP_POD=0.005, TRANSLATOR=0.004, GALAXY_SOUNDS=0.003, PEBBLES=-0.00, ROBOT=-0.001. Only SNACKPACK and PEBBLES are meaningfully non-zero at the median. All others are consistent with independent random walks. [cell: cat_ret]

6. **ROBOT has the most negative median level correlation: -0.6674.** The five robot types show systematically anti-correlated price levels — products within ROBOT diverge rather than converge over time. This rules out basket mean-reversion for ROBOT. [cell: cat_full, lc_median]

7. **Lead-lag CCF asymmetries are uniformly small across all categories.** The largest asymmetry observed is PANEL_1X2/PANEL_2X4 = -0.0118; all others are below 0.012 in absolute value. This means no product reliably leads or lags its category-mate by 1–10 ticks. The CCF peak magnitudes (off lag-0) are also small: max peak_val = 0.0234 (PANEL 1X2/2X4). No cross-product lead-lag signal was found. [cell: ccf_df top-15 print]

8. **Basket spread stationarity is weak across all categories.** Only SNACKPACK has any stationary spreads: SNACKPACK_RASPBERRY (ADF p=0.0010) and SNACKPACK_VANILLA (p=0.0275) show stationary deviation from the SNACKPACK equal-weight basket. All other 48 products (9 categories × 5, minus SNACKPACK) have basket spreads with ADF p>0.09. Basket mean-reversion is not supported outside SNACKPACK. [cell: basket_df sorted by adf_pval]

9. **SNACKPACK_RASPBERRY and SNACKPACK_VANILLA basket spreads are stationary and of opposite sign.** RASPBERRY spread_mean = +33.6 (above basket), VANILLA = +53.1, CHOCOLATE = -200.8. CHOCOLATE has the largest negative mean deviation from basket. Two stationary spreads coexist with one very large negative outlier — internal structure is heterogeneous. Corroboration from notebook 07 (flavor feature regression) and notebook 01 (price level distribution) needed. [cell: basket_df, adf_pval < 0.05]

10. **No within-category level correlations are stable across days 2/3/4 at high magnitude.** Per-day stability analysis shows all categories have median level corr < 0.5 on every individual day, with high day-over-day variance. SLEEP_POD has the highest maximum pair corr on any single day (0.875) but this is not consistent. This means within-category synchrony — if it exists — is transient or regime-dependent, not structural. [cell: pair_stability, day_stability]

11. **MICROCHIP has the widest single-pair level-corr range: -0.8823 (min) to +0.8705 (max).** With median=-0.255, this suggests some MICROCHIP pairs co-move strongly and others strongly anti-correlate — possible categorical sub-structure (e.g. shape-based pairing). The one cointegrated MICROCHIP pair has p=0.0274. Needs notebook 07 (shape as feature) and notebook 06 (cross-category) to determine if this is meaningful sub-grouping. [cell: cat_full, coint_df[coint_df.category=='MICROCHIP']]

12. **SNACKPACK has 3 cointegrated pairs but none stable on all 3 individual days.** Per-day cointegration test confirms that while the pooled 3-day series yields 3 significant pairs, no pair maintains cointegration on day 2, day 3, and day 4 independently. This weakens the cointegration signal — pooling may create spurious long-run relationships from day-to-day level shifts. Critic notebooks should flag this. [cell: stable_coint == 0 for SNACKPACK]

13. **PEBBLES basket-spread std (1073.9) and MICROCHIP (1055.2) are the largest by far.** These two categories show the widest absolute spread volatility relative to their basket — products are dispersed widely in price level. Compare TRANSLATOR (454.4) and SLEEP_POD (516.3) which are much tighter. High spread std without stationarity = random drift, not mean-reversion. [cell: basket_cat, mean_spread_std]

14. **All lag-0 returns correlations (CCF at lag=0) are < 0.013 in absolute value except PEBBLES_L/XL (-0.4932).** This is the only pair with a practically meaningful contemporaneous return co-movement signal. All other 99 pairs (10 categories × 10 pairs - 1) have |lag0| < 0.013. PEBBLES_L/XL is a clear outlier from the cross-sectional distribution. [cell: ccf_df, lag0 column]

15. **Cross-ref requests**: (a) Notebook 01 should confirm whether SNACKPACK products have distinct price-level regimes (separate hardcoded FVs per product). (b) Notebook 03 should check whether PEBBLES_L/XL AR(1) structure explains the -0.49 return anti-correlation. (c) Notebook 07 should test whether flavor type (CHOCOLATE, VANILLA, RASPBERRY, etc.) is a proxy for price level within SNACKPACK. (d) Notebook 09 should test SNACKPACK for near-identical or hardcoded-FV structure — the stationary RASPBERRY/VANILLA spreads could arise from a hardcoded price offset rather than mean-reversion dynamics.
