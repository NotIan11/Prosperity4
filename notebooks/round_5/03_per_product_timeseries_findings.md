# Notebook 03 — Time-Series Findings

Explorer 03 | R5 EDA Swarm | Lenses: ADF stationarity, AR(1)/AR(5) on returns, trend slope+R², FFT top-5 frequencies.

---

## Triage rubric applied

- **likely exploitable**: AR(1) |ρ₁| > 0.3 (stable across all 3 days)
- **probably tradable**: AR(1) 0.1 ≤ |ρ₁| ≤ 0.3
- **probably noise**: AR(1) |ρ₁| < 0.1

---

## Findings (≤15 bullets)

1. **No product clears the "likely exploitable" AR(1) threshold (|ρ₁| > 0.3) on returns.** The highest mean |ρ₁| across 3 days is ROBOT_IRONING at 0.1168, which falls in the "probably tradable" band. All 50 products are either probably_tradable or probably_noise by this lens alone. [Cell 3, Cell 4]

2. **ROBOT_IRONING is the strongest AR(1) signal: ρ₁ = −0.117 (mean across days 2/3/4), stable and negative on all 3 days (ρ₁_d2, ρ₁_d3, ρ₁_d4 all negative), p-value ≈ 3e−16.** This is a consistent mean-reversion signal on returns. Needs corroboration from Notebook 02 (book imbalance) and Notebook 05 (within-ROBOT category correlation). [Cell 3, Cell 5]

3. **OXYGEN_SHAKE_EVENING_BREATH is second: ρ₁ = −0.112 (mean), also stable negative across all 3 days, p ≈ 3e−15.** Both ROBOT_IRONING and OXYGEN_SHAKE_EVENING_BREATH are probably_tradable by AR(1); neither crosses |ρ₁| > 0.3. Corroboration needed from Notebook 08 (regime stability) and Notebook 05 (OXYGEN_SHAKE category basket). [Cell 3, Cell 5]

4. **ROBOT_DISHES shows high mean |ρ₁| = 0.098 but with std = 0.166 — it has extreme day-to-day instability.** One day may have |ρ₁| ≈ 0.3+ while another is near zero. This is unreliable; the mean is driven by an outlier day. Statistical critic (Notebook A) should flag this high std. [Cell 3, Cell 5]

5. **The SNACKPACK category produces the tightest cluster of probably_tradable products (5 products, all with 0.013 ≤ |ρ₁| ≤ 0.031, negative ρ₁).** This suggests mild within-category mean-reversion on returns. Notebook 05 should test whether SNACKPACK forms a coherent basket with corr > 0.7. [Cell 3, Cell 13]

6. **ADF stationarity on price LEVELS: 44 of 50 products have 0% stationary days (fail to reject unit root at p<0.05 on all 3 days).** Only UV_VISOR_RED (2/3 days stationary, mean p = 0.20), UV_VISOR_AMBER (1/3), MICROCHIP_CIRCLE (1/3), OXYGEN_SHAKE_EVENING_BREATH (1/3), TRANSLATOR_ASTRO_BLACK (1/3), SNACKPACK_STRAWBERRY (1/3) occasionally reject. No product is consistently stationary in levels. [Cell 2]

7. **ALL 50 products fail to be consistently stationary in levels — this means all mid_price series are best treated as random walks (or near-random walks) for levels-based analysis.** AR(1) on levels would be spurious; all AR(1) analysis in this notebook correctly uses log-returns. Corroborate with Notebook 09 (anomaly detection) and Notebook 01 (distributional). [Cell 2]

8. **Trend (linear R²) is high for many products despite low AR(1): 40 of 50 products have mean trend R² > 0.3, and 20+ have R² > 0.5.** Top: PANEL_1X2 (R²=0.766, slope=+2.75e−4/tick), SLEEP_POD_NYLON (R²=0.737), PEBBLES_XS (R²=0.705, slope=−1.76e−3). High trend R² + non-stationary levels + near-zero AR(1) on returns is consistent with a slow, persistent drift that is predictable at the day level but not the tick level. [Cell 6]

9. **PEBBLES_XS has the steepest negative drift: slope = −1.76e−3 per tick (mean across 3 days), R²=0.705.** PEBBLES_XL has the steepest positive drift: slope = +2.84e−3, R²=0.600. These trends are persistent across all 3 days. Notebook 07 (name-as-signal: XS=smallest, XL=largest) should test whether size encodes the price trend direction within PEBBLES. [Cell 6]

10. **PANEL products show high trend R²: PANEL_1X2 (0.766), PANEL_2X4 (0.622), PANEL_1X4 (0.487) all trending upward. PANEL_4X4 (R²=0.231) is weaker.** The pattern suggests area/size of the panel encodes price level rather than price trend. Notebook 07 should parse panel dimensions. [Cell 6]

11. **FFT peak-to-noise ratios (PNR) are uniformly high across all 50 products (top-20 range: 1,556–2,717), with top-1 period clustering at 8,333 or 10,000 ticks.** These canonical periods (1/1.2 and 1/1.0 of the 10,000-tick day) suggest the FFT is mostly detecting the overall trend and its harmonics, NOT embedded periodicity. PNR is not a useful discriminator here without baseline-correcting for trend. This is a potential false positive — Notebook A (statistical critic) should flag that FFT on a trending series will always show a low-frequency peak. [Cell 7]

12. **ROBOT_IRONING is the only product where both AR(1) signal AND non-trivial AR(5) gain coexist.** AR(5) R² is modestly higher than AR(1) R² for ROBOT_IRONING, suggesting at least 2-3 lags carry signal beyond lag 1. For most other products, AR(5) adds minimal R² over AR(1). [Cell 12]

13. **Category-level AR(1) ranking: ROBOT (mean |ρ₁| = 0.048) > OXYGEN_SHAKE (0.040) > SNACKPACK (0.023) > MICROCHIP (0.013) > PEBBLES (0.009). Bottom: PANEL (0.004), UV_VISOR (0.003), SLEEP_POD (0.003), TRANSLATOR (0.007).** ROBOT and OXYGEN_SHAKE categories have the most consistent short-horizon mean-reversion on returns. PANEL, UV_VISOR, and SLEEP_POD are noise by AR(1). [Cell 13]

14. **Returns for the top AR(1) products (ROBOT_IRONING, OXYGEN_SHAKE_EVENING_BREATH) have a small number of distinct values (lattice structure in prices implies discrete returns).** This is consistent with integer-tick prices. The negative AR(1) likely reflects a bid-ask bounce at the tick level — a well-known microstructure artifact. Notebook 02 (microstructure) must corroborate or contradict this interpretation before any exploitability call can be made. [Cell 15]

15. **No product shows a convincing narrow-band spectral peak clearly above the noise floor in the detrended FFT.** After detrending, all products produce broad, relatively flat spectra without a single dominant frequency. The brief's "strong patterns embedded in price movements" appear to manifest in LEVELS (trend+mean-reversion) rather than in tick-level periodicity detectable by FFT on mid_price. Notebook 09 (determinism anomaly) should apply a more targeted step-pattern detector. [Cell 7, Cell 8]

---

## Cross-notebook corroboration requests

- **Notebook 02** (microstructure): Does the AR(1) mean-reversion in ROBOT_IRONING and OXYGEN_SHAKE_EVENING_BREATH disappear after accounting for bid-ask bounce? Spread regime and book imbalance for these two products.
- **Notebook 05** (within-category corr): Do SNACKPACK, ROBOT, OXYGEN_SHAKE form coherent baskets? Does within-category cross-sectional ranking add to single-product AR(1)?
- **Notebook 07** (name-as-signal): PEBBLES size (XS→XL) appears to encode drift direction; PANEL dimensions appear to encode price trend. Test linear regression of price level on size feature.
- **Notebook 08** (regime): Are the trend R² values (Cell 6) stable day-over-day or are they driven by a single day? Particularly for PANEL_1X2, SLEEP_POD_NYLON, PEBBLES_XS.
- **Notebook 09** (anomaly): Re-examine FFT with a proper baseline (synthetic GBM) to determine if any product's spectral peak is truly anomalous, not just a trend artifact.
- **Notebook A** (statistical critic): (a) ROBOT_DISHES has std_ρ₁=0.166 — flag as unstable. (b) FFT PNR is inflated by trend — flag as not meaningful without detrend verification. (c) ADF run on the full 10,000-tick day series may have insufficient power for slowly-drifting near-unit-root processes.
