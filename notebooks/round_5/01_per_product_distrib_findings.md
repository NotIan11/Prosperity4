# Notebook 01 — Distributional Findings

> Explorer 01. Lenses: mid stats, distinct prices, hardcoded-FV check, range/CV, mode prevalence.
> All numbers come from 30,000 ticks × 3 days = 90,000 ticks per product (1,500,000 total).

---

## Findings (15 bullets)

**1. No product has a hardcoded FV by the ≥90% definition.**
`fv_pct` (fraction of all 90,000 ticks at the single most-common mid-price) peaks at
5.38% for `ROBOT_DISHES` (10,600.0) and 2.27% for `OXYGEN_SHAKE_EVENING_BREATH` (10,100.0).
All other products are below 1.3%. The brief hint about "embedded patterns" does not manifest
as a pinned price level. [cell 4]
Needs corroboration: **notebook 09** (hardcoded-FV / periodic-step detection).

**2. PEBBLES and MICROCHIP are the highest-CV categories by a wide margin.**
Mean CV across the 5 products: PEBBLES = 0.2245, MICROCHIP = 0.2298 — roughly 2–5× higher
than every other category. Next highest are UV_VISOR (0.1365) and OXYGEN_SHAKE (0.1123).
Tightest is SNACKPACK (0.0457). [cell 9]
Needs corroboration: **notebook 03** (ADF stationarity / AR series), **notebook 08** (regime).

**3. PEBBLES_XL and MICROCHIP_SQUARE have the most distinct mid-price values (10,051 and 8,725).**
PEBBLES_XL alone has more distinct prices than any other product, consistent with its CV of 0.134.
Contrast with `OXYGEN_SHAKE_EVENING_BREATH` (453 distinct values) and `ROBOT_IRONING` (631).
[cell 10] Cross-ref: **notebook 02** (spread regime), **notebook 03** (AR).

**4. PEBBLES_XS has the largest day-over-day mean shift: |day3−day2| = 2,221 on a mean of ~7,405
(30.0% of mean). MICROCHIP_SQUARE shifts by 3,316 between day 2 and day 3 (24.4% of mean).**
Both products exhibit large directional drifts across days, inconsistent with a stable FV process.
[cell 15] Corroborate/contradict: **notebook 08** (day-stability), **notebook 03** (trend slope R²).

**5. SNACKPACK is the most stable category: SNACKPACK_RASPBERRY has max_shift_pct = 0.0066 (0.66%)
across all three days; the four other SNACKPACKs are below 2.5%.**
The SNACKPACK mean mid-prices cluster between 9,495 and 10,707, with within-category spread of only
1,211. Their low CV (0.017–0.034) and low daily drift suggest a predictable, tightly-bounded process.
[cells 6, 15] Corroborate: **notebook 03** (AR), **notebook 05** (within-category cointegration).

**6. OXYGEN_SHAKE_EVENING_BREATH is a distributional outlier: only 453 distinct mid-prices across
90,000 ticks, with an avg mode prevalence of 4.19% — the second-highest mode prevalence of all 50
products.**
This implies a heavily discretized or piecewise-constant price series relative to the other
OXYGEN_SHAKE products (453 vs 3,512–6,343 for its siblings). [cells 3, 10]
Needs corroboration: **notebook 09** (step-pattern detection), **notebook 03** (ADF).

**7. ROBOT_DISHES has the highest avg mode prevalence (5.63%) with FV candidate 10,600.**
ROBOT_IRONING is next (3.39%, FV candidate 10,000). Both are ROBOT products. The other three ROBOT
products (MOPPING, LAUNDRY, VACUUMING) have avg mode prevalence <0.29%. The within-ROBOT pattern is
non-uniform. [cell 3] Corroborate: **notebook 09** (step detection), **notebook 02** (spread).

**8. Within-category price spread is smallest for SNACKPACK (1,211) and GALAXY_SOUNDS (1,240), largest
for PEBBLES (5,821) and MICROCHIP (5,415).**
This directly confirms that PEBBLES and MICROCHIP have widely dispersed product prices within
their own category, making cross-product basket plays structurally different from SNACKPACK/GALAXY.
[cell 12] Cross-ref: **notebook 05** (cointegration, basket spread), **notebook 07** (name-as-signal).

**9. PANEL products show no clear size-based price ordering: PANEL_2X4 has mean mid 11,265 but
PANEL_4X4 (which has 4× the area) has mean mid 9,879, lower than PANEL_2X4.**
The naïve expectation of area → price is violated. Within-PANEL spread = 2,343. [cell 12]
Cross-ref: **notebook 07** (name-as-signal regression on panel dimensions).

**10. UV_VISOR_AMBER is the distributional outlier within its category: mean mid 7,912 vs
next-lowest sibling UV_VISOR_ORANGE at 10,427 (gap of 2,515, i.e., 32% below category average).**
Its CV (0.126) is also 2× higher than UV_VISOR_RED/ORANGE/YELLOW. The other four UV visors cluster
between 10,427 and 11,112. [cells 6, 12] Corroborate: **notebook 05** (pairwise within-category corr).

**11. MICROCHIP_SQUARE is the distributional outlier within MICROCHIP: mean mid 13,595 vs siblings
ranging 8,180–9,686, a gap of 3,908 over the next-highest (MICROCHIP_TRIANGLE at 9,686).**
The CV of 0.135 is the second-highest across all 50 products. [cells 6, 12]
Corroborate: **notebook 05** (basket spread), **notebook 08** (regime stability).

**12. GALAXY_SOUNDS products show modest between-product price spread (1,240) and low CV (0.033–0.083),
but price levels are NOT identical across siblings — they differ by up to 1,241 in mean.**
No product in this category reaches even 5% mode prevalence. [cells 2, 12]
Cross-ref: **notebook 05** (within-category correlation), **notebook 03** (AR, trend).

**13. All 50 products produce mid-prices that are predominantly non-integer (half-integer or
finer). The grid analysis confirms no product has all-integer mid-prices; all have fractional
ticks (bid/ask average produces .0 or .5 values). Minimum gap between consecutive distinct
prices ranges from 0.5 (most products) down to 0.1 for some highly dispersed products.**
[cell 13] Context for: **notebook 02** (spread/tick-size regime), **notebook 09** (gap detection).

**14. The two categories flagged in the AGENT_BRIEF as differently generated (PEBBLES, MICROCHIP)
are confirmed as the highest-CV categories by a large margin (CV 0.22–0.23 vs next at 0.14).**
They also show the largest day-over-day drifts (PEBBLES_XS: 30%, MICROCHIP_SQUARE: 24%).
This distributional evidence is consistent with a non-stationary or trending price process.
[cells 6, 9, 15] Priority for: **notebook 03** (ADF), **notebook 08** (regime), **notebook 09**.

**15. SNACKPACK, GALAXY_SOUNDS, and TRANSLATOR have the three lowest category-level CVs
(0.046, 0.073, 0.073 respectively) and the lowest max day-shift-pct among their members
(all below 5% for SNACKPACK, below 10% for GALAXY/TRANSLATOR).**
These three categories show distributions most consistent with a mean-reverting or bounded
process, making them candidates for market-making or mean-reversion strategies.
[cells 6, 9, 15] Corroborate: **notebook 03** (AR ρ, ADF), **notebook 05** (within-category corr).
