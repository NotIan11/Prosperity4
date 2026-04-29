# Notebook 07 — Categorical Features Findings

> Source: `07_categorical_features.ipynb` cells 2–19. Days 2/3/4.
> All R² / ρ values are OLS and Spearman respectively.

## Key findings

1. **PEBBLES size is the strongest feature-price signal of all 10 categories.**
   Mean R² = 0.852 across days 2/3/4; Spearman ρ = 1.000 on days 2 and 3, 0.900 on day 4.
   Rank order XS < S < M < L < XL is fully preserved in prices (mean mids: 7,405 / 8,932 / 10,263 / 10,174 / 13,226).
   [cells 5, 9] — needs corroboration from 01 (hardcoded FV check), 03 (AR(1) per product).

2. **PEBBLES price-rank is maximally stable day-to-day: mean ρ(day pairs) = 0.933.**
   Day pairs: ρ(2,3)=1.000, ρ(2,4)=0.900, ρ(3,4)=0.900. The size hierarchy holds across all three days.
   [cell 13] — corroborate with 08 (day-over-day regime stability).

3. **PEBBLES_L and PEBBLES_M pricing anomaly: PEBBLES_L (mean 10,174) is CHEAPER than PEBBLES_M (mean 10,263) in the 3-day average.**
   This breaks strict monotonicity at the L/M boundary. The gap is small (~89 units on a ~10k base) and may reflect day-2 noise; day-3 and day-4 preserve full XS < S < M < L < XL order.
   [cell 9] — flag for 09 (anomaly detector) and 05 (cointegration).

4. **SNACKPACK price rank is also highly stable (mean ρ = 0.933) but the flavor encoding has low OLS R² (0.091).**
   This means price differences exist and are consistent across days but do NOT scale linearly with our "popularity" ordinal.
   Actual 3-day mean prices: CHOCOLATE=9,437 / VANILLA=10,137 / STRAWBERRY=10,150 / RASPBERRY=9,994 / PISTACHIO=10,505.
   [cells 5, 6] — corroborate with 01 (distributional) and 03 (trend).

5. **PANEL area shows moderate Spearman ρ but PANEL_4X4 breaks the monotone trend.**
   Spearman ρ = 0.872 (log2 area, 3-day average), but PANEL_4X4 (area=16, mean mid=9,879) is CHEAPER than PANEL_2X4 (area=8, mean mid=11,265).
   Linear area R² = 0.161; log2(area) R² = 0.378. Neither is stable; day-pair rank ρ mean = 0.467.
   [cells 7, 8] — flag for 05 (basket PANEL_1X2/PANEL_2X4 pair cointegration).

6. **TRANSLATOR color-darkness ordinal has mean R² = 0.388 but is unstable across days (mean ρ = 0.467).**
   Day-pair rank stability: ρ(2,3)=0.100 (near-random), ρ(2,4)=0.500, ρ(3,4)=0.800. Price order shifted significantly between days 2 and 3.
   3-day prices: SPACE_GRAY=9,432 / GRAPHITE_MIST=10,085 / ASTRO_BLACK=9,385 / ECLIPSE_CHARCOAL=9,814 / VOID_BLUE=10,859.
   [cells 5, 13] — needs corroboration from 08 (regime shift).

7. **MICROCHIP shapes have no natural ordinal; alphabetical encoding gives R² = 0.296, Spearman ρ = 0.500.**
   Actual price ordering (low to high): OVAL (8,180) < RECTANGLE (8,732) < CIRCLE (9,215) < TRIANGLE (9,686) < SQUARE (13,595).
   MICROCHIP_SQUARE is a clear outlier: 3,909 above the next product. Vertex-count and area-proxy orderings yield weaker fits.
   [cells 5, 10] — flag for 09 (MICROCHIP_SQUARE outlier / hardcoded FV check) and 01.

8. **MICROCHIP price ranks are moderately stable (mean ρ = 0.600): ρ(2,3)=0.700, ρ(2,4)=0.300, ρ(3,4)=0.800.**
   The day-2 to day-4 jump is weak. MICROCHIP_SQUARE dominates the spread at all three days but the other four products shift rank.
   [cell 13] — cross-ref with 03 (time series structure per shape).

9. **UV_VISOR wavelength encoding shows negligible feature-price correlation: mean R² = 0.135, Spearman ρ = 0.233.**
   Day-4 alone has ρ=0.800 but days 2 (ρ=-0.100) and 3 (ρ=0.000) are near-zero; AMBER is the anomalous outlier (mean mid=7,912 vs category mean=10,294).
   [cells 5, 11] — UV_VISOR_AMBER is a candidate for anomaly notebook 09.

10. **ROBOT task-complexity ordinal yields R² = 0.115 with a negative Spearman ρ (-0.400) — reversed from our encoding.**
    Meaning simpler tasks (VACUUMING) may price higher than complex ones, or the encoding is wrong. Rank stability is high: mean ρ=0.833 (pairs: 0.900/0.700/0.900).
    Actual prices need checking by product; consistent rank but wrong direction for "complexity" hypothesis.
    [cells 5, 18] — corroborate with 01 (mode prevalence per product).

11. **OXYGEN_SHAKE flavor encoding has mean R² = 0.282, Spearman ρ = 0.333; moderate rank stability (mean ρ = 0.567).**
    Day 2 is the most stable (ρ(2,3)=0.900) but weakens by day 4. The "pungency" ordinal is speculative and the low Spearman suggests no clean monotone relationship.
    [cells 5, 17] — probably noise for feature encoding; may still have detectable patterns by 03.

12. **GALAXY_SOUNDS and SLEEP_POD show near-zero feature-price signal and near-zero rank stability.**
    GALAXY_SOUNDS mean R²=0.089, mean ρ(feature)=-0.033, rank stability mean=0.033 (the worst of all categories).
    SLEEP_POD mean R²=0.051, mean ρ(feature)=-0.067, rank stability mean=0.433.
    Both are likely noise for the name-as-signal lens. [cells 5, 18] — corroborate with 09 (random control).

13. **Absolute intra-category price spread is large for PEBBLES (~58% of mean) and MICROCHIP (~58%), moderate for UV_VISOR (~33%), OXYGEN_SHAKE (~26%), PANEL (~26%).**
    GALAXY_SOUNDS (~15%) and SNACKPACK (~12%) have the tightest spreads. Large spread + high rank stability (PEBBLES, SNACKPACK) = strong candidate for cross-sectional signals.
    [cell 14] — cross-ref with 05 (basket spread).

14. **PANEL_1X4 and PANEL_2X2 share area=4; their mean prices differ by 179 units (9,398 vs 9,577).**
    If area were the sole driver we would expect them to be equal. The gap is small relative to overall PANEL spread (2,582) but non-trivial. Suggests dimensions beyond area matter, or PANEL prices are only weakly area-driven.
    [cell 8] — flag for 05 (PANEL_1X4/PANEL_2X2 pairwise cointegration test).

15. **PEBBLES is the only category where the name feature alone is a plausible price predictor (R² ≥ 0.74 on every day, rank fully preserved).**
    All other categories require additional lenses (time-series structure, within-category cointegration, regime) before triage can be assigned.
    Needs corroboration: 01 (hardcoded FV check on PEBBLES products), 03 (stationarity per PEBBLES product), 05 (pairwise PEBBLES cointegration).
