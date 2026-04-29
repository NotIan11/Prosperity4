# Notebook 08 — Time Regime Findings

> Source: `notebooks/round_5/08_time_regime.ipynb`, cells 1–11.
> All claims backed by computed statistics on days 2/3/4 (10,000 ticks each, 50 products).

---

## Stability

- **Nearly all products (41/50) are DRIFTING**: mean CV across days 2/3/4 ≥ 0.005 or AR(1) range ≥ 0.1. Only 8 are MOSTLY_STABLE and 1 (SNACKPACK_VANILLA) qualifies as STABLE (CV=0.0075, ar1_range=0.009). [cell 3]

- **The most price-stable products are in SNACKPACK**: SNACKPACK_RASPBERRY has the lowest cross-day mean CV of any product (0.00284; means 10065/10117/10051). SNACKPACK_VANILLA is second (CV=0.0075). Both have |AR(1)|<0.035 across all 3 days — no momentum signal, but hardcoded-FV strategies should corroborate (needs `01_per_product_distrib` cross-ref). [cell 3]

- **Highest drift products are MICROCHIP_OVAL and PEBBLES_XS**: MICROCHIP_OVAL mean falls 9766→8544→6229 (CV=0.220); PEBBLES_XS drops 9189→6968→6056 (CV=0.218). These are trending down across days — rolling estimators required for any FV strategy. [cell 4]

- **MICROCHIP category is the most drifting category**: mean CV avg = 0.117 across 5 products. PEBBLES is second (avg CV=0.104). Neither category has a STABLE member. [cell 3, category summary cell 10]

- **GALAXY_SOUNDS and TRANSLATOR are moderately stable** relative to other volatile categories (mean CV avg 0.048 and 0.040 respectively), with 3/5 MOSTLY_STABLE members each (GALAXY_SOUNDS_DARK_MATTER CV=0.017, GALAXY_SOUNDS_SOLAR_FLAMES CV=0.015, TRANSLATOR_ECLIPSE_CHARCOAL CV=0.019). [cell 3]

---

## AR(1) of Returns

- **No product clears the |AR(1)| > 0.3 threshold on average** across all 3 days — zero "likely exploitable" products under the regime triage rubric. The strongest mean AR(1) signal is ROBOT_IRONING at −0.117 (days: −0.156/−0.080/−0.114). Needs corroboration from `03_per_product_timeseries`. [cell 3, cell 11]

- **ROBOT_DISHES shows strong single-day AR(1) = −0.289 on day 4** alongside sq_acf_lag1 = 0.235 and excess kurtosis = 10.0, driven by a 6-jump step pattern around ticks 145,000–148,300 followed by a smooth trending price path that ends pinned at ~11,200 for the last 400 ticks. This is NOT a stable mean-reversion signal — it's an artefact of a one-day structural shift. [cell 6 (vol clustering), supplemental script]

- **ROBOT_IRONING is the only product with consistent negative AR(1) across all 3 days** (−0.156/−0.080/−0.114, mean −0.117). This is "probably tradable" territory but below the ≥0.3 exploitable threshold. Corroboration from `03_per_product_timeseries` and `09_determinism_anomaly` recommended. [cell 3]

---

## Intraday Seasonality

- **High "intraday amplitude" across all drifting products reflects intraday trends, not cyclic seasonality**: PEBBLES_XL's apparent amplitude of 2,667 (largest of all 50) is entirely explained by a monotone intra-day price trend from ~9,671 (day 2 open) to 13,680 (day 2 close) and similar on other days. FFT on detrended PEBBLES_XL series finds dominant period = 5,000 ticks across all 3 days (power_frac 0.35–0.37), consistent with a smooth parabolic arc, not a recurring cycle. [cell 5, supplemental script]

- **No product shows clear repeating intraday cycles** (e.g. hour-of-day seasonality). The 20-bucket intraday profiles do not repeat across days for any product — each day's shape is different, driven by its own directional trend. [cell 5–6]

- **FFT on raw time-series finds no dominant periodic signal > 50% power** in any product after detrending. The largest single-frequency power fraction observed is ~37% (PEBBLES_XL, period=5,000 ticks) which is consistent with a slow trend, not an embedded oscillator. Notebooks `03_per_product_timeseries` and `09_determinism_anomaly` should re-check with longer FFT windows and significance tests. [cell 7]

---

## Volatility Clustering

- **OXYGEN_SHAKE_CHOCOLATE and OXYGEN_SHAKE_EVENING_BREATH are distinct outliers for vol clustering**: sq_acf_lag1 = 0.239/0.239, excess kurtosis = 10.77/10.50 — far above any other product. Source: 38–44% of return ticks are exactly zero (flat price), interspersed with infrequent large jumps (p99.9 ≈ 1.0% return vs p50 ≈ 0.10%). This is a jump-diffusion pattern, not GARCH clustering. These two products are statistical anomalies within OXYGEN_SHAKE; the other three OX products have sq_acf_lag1 < 0.01 and near-zero kurtosis. [cell 8–9]

- **ROBOT_DISHES sq_acf_lag1 = 0.262 (highest among all products) on Day 4 only** — driven by the same jump pattern noted above (6 large returns of ±1% in a 2,000-tick window). Not robust across days (Days 2 and 3 show sq_acf ≈ −0.003). Treat as non-repeating. [cell 8, supplemental script]

- **The majority of products (40+/50) show sq_acf_lag1 < 0.03**: vol clustering is not a broad feature of the R5 product universe. Most products have near-Gaussian returns (kurtosis near 0). [cell 8]

---

## Cross-references needed

- `01_per_product_distrib` — corroborate SNACKPACK_RASPBERRY / SNACKPACK_VANILLA as hardcoded-FV candidates (stable means but no AR(1) signal here).
- `03_per_product_timeseries` — AR(1) and stationarity on the drifting series (MICROCHIP_OVAL, PEBBLES_XS); cross-check ROBOT_IRONING.
- `09_determinism_anomaly` — check OXYGEN_SHAKE_CHOCOLATE/EVENING_BREATH jump pattern for deterministic periodicity; check ROBOT_DISHES day-4 step change.
