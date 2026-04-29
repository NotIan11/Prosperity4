# EDA Final Triage — Round 5

> Synthesizer output. All claims backed by recomputed numerics in `notebooks/round_5/10_synthesis.ipynb`.
> 6 specific disputes resolved (D1–D6). 50 products × 5 columns.

---

## Dispute Resolutions (computed in `10_synthesis.ipynb`)

| ID | Dispute | Verdict | Key number |
|----|---------|---------|------------|
| D1 | ROBOT_IRONING AR(1)=−0.117: genuine MR vs bounce? | **Both partially correct. Reversal_frac=55% (not 100% as Critic B claimed).** Step=10 > half-spread=3.2. 55% reversal > 50% bounce baseline → weak but real MR above bounce. Triage: **probably tradable**. | reversal=0.550/0.544/0.559 days 2/3/4 |
| D1b | OXYGEN_SHAKE_EVENING_BREATH same dispute | Same mechanism, reversal_frac=54% all days → probably tradable. | reversal=0.540/0.550/0.535 |
| D2 | PEBBLES anti-corr: independent signal or mechanical? | **Partially mechanical, not purely.** Predicted corr(XL, others) = −0.347 to −0.505 (varies by product std). Observed = −0.475 to −0.506. The basket sum=50000 is the exploitable constraint; anti-corr is a consequence, not an independent signal. | Pred vs obs: PEBBLES_L pred=−0.397 obs=−0.493; PEBBLES_XL pred=−0.505 obs=−0.506 |
| D3 | SNACKPACK 2+2+1 architecture | **Confirmed.** CHOC/VAN=−0.916, STRAW/RASP=−0.924, PIST/STRAW=+0.913 (pooled); per-day all stable ±0.01. All cross-group |corr|≤0.04. Pair-sums drift: CHOC+VAN: −98→−57 per day; RASP+PIST: −116→−209 per day. | Per-day CHOC/VAN: d2=−0.920, d3=−0.915, d4=−0.912 |
| D4 | Trend R²>0.3 for 40/50: above random-walk null? | **Marginally significant (p=0.0067).** P(R²>0.3 \| random walk, n=10000) = 62.7%. Expected: 31.4 products. Observed: 40. Excess: 8.6. Significant but modest — high R² alone does not confer tick-level exploitability without AR(1) or cointegration. | Monte Carlo n=2000: p=0.0067 |
| D5 | MICROCHIP buy-side flow imbalance: N=569 not 2845 | **Not significant.** Effective N=569 unique timestamps. Pooled p=0.104. Per day: p=0.099/0.175/0.556. Imbalance fully decays by day 4 (49.8% at-ask). | N=569, k_ask=300, p=0.104 |
| D6 | ROBOT_DISHES PC3 singleton: artifact or signal? | **Artifact confirmed.** Per-day PC3 loading: −0.004/+0.015/+0.002. Pooled loading −0.995 caused by day-4 variance spike (6.7× days 2/3). Standardized PCA: loading = 0.005. | Day-4 var=6.66e−6 vs days 2/3 ~1.03e−6 |

---

## Executive Triage Table — 50 Products

| # | Product | Category | Triage | 1-sentence reason | Key lens(es) | Unresolved concerns |
|---|---------|----------|--------|-------------------|--------------|---------------------|
| 1 | GALAXY_SOUNDS_BLACK_HOLES | GALAXY_SOUNDS | **probably noise** | AR(1)=−0.017, no within-cat corr (mean 0.004), no sum constraint, no structure across any lens | NB03, NB06 | None |
| 2 | GALAXY_SOUNDS_DARK_MATTER | GALAXY_SOUNDS | **probably noise** | AR(1)=−0.012, spread unstable day-over-day, no exploitable structure | NB03, NB06 | None |
| 3 | GALAXY_SOUNDS_PLANETARY_RINGS | GALAXY_SOUNDS | **probably noise** | AR(1)=−0.003, all lenses return noise, spread unstable | NB02, NB03, NB06 | None |
| 4 | GALAXY_SOUNDS_SOLAR_FLAMES | GALAXY_SOUNDS | **probably noise** | AR(1)=−0.012, feature R²=0.089 (name-as-signal lens), no structure | NB07, NB06 | None |
| 5 | GALAXY_SOUNDS_SOLAR_WINDS | GALAXY_SOUNDS | **probably noise** | AR(1)=−0.007, near-zero within-cat return corr (mean 0.004) | NB06, NB05 | None |
| 6 | MICROCHIP_CIRCLE | MICROCHIP | **probably noise** | No sum constraint (5-sum CV=3.04%), all pairwise corr<0.013; 5 independent RWs (CC9) | CC9, NB09, NB04 | Trade-schedule anomaly (569 vs 733 trades) is generative, not price-structural |
| 7 | MICROCHIP_OVAL | MICROCHIP | **probably noise** | Largest drift (means 9766→8544→6229 across days) but no cross-product structure; trending RW | NB08, CC9 | Strong downward trend; no AR(1) or basket signal to exploit |
| 8 | MICROCHIP_RECTANGLE | MICROCHIP | **probably noise** | AR(1)=−0.003, no structure beyond baseline; independent RW confirmed | CC9, NB06 | None |
| 9 | MICROCHIP_SQUARE | MICROCHIP | **probably noise** | Distributional outlier (mean 13,595 vs siblings 8,180–9,686) but AR(1)=−0.022; RW | NB01, CC9 | Price level far above siblings; idiosyncratic behavior without exploitable signal |
| 10 | MICROCHIP_TRIANGLE | MICROCHIP | **probably noise** | AR(1)=−0.008, no sum constraint, no pairwise corr; confirmed 5 independent RWs | CC9, NB03 | None |
| 11 | OXYGEN_SHAKE_CHOCOLATE | OXYGEN_SHAKE | **probably tradable** | Jump-diffusion: sq_acf_lag1=0.239, kurtosis=10.77, 38–44% zero-return ticks; AR(1)=−0.076 | NB08, NB09 | Jump origin not verified; vol clustering is jump-diffusion, not GARCH |
| 12 | OXYGEN_SHAKE_EVENING_BREATH | OXYGEN_SHAKE | **probably tradable** | Step-function (±10 grid, 39% zero-return), AR(1)=−0.112; reversal_frac=54% > 50% bounce baseline | NB09, CA_B2, CB3 | Critic B's "100% reversal" claim rebutted (computed 54%); weak MR above bounce confirmed |
| 13 | OXYGEN_SHAKE_GARLIC | OXYGEN_SHAKE | **probably noise** | AR(1)=−0.003, no structure; spread unstable day-to-day | NB02, NB03 | None |
| 14 | OXYGEN_SHAKE_MINT | OXYGEN_SHAKE | **probably noise** | AR(1) near zero, no anomaly across any lens; typical random walk | NB03, NB06 | None |
| 15 | OXYGEN_SHAKE_MORNING_BREATH | OXYGEN_SHAKE | **probably noise** | AR(1)=−0.005, no structure detected; near-baseline across all lenses | NB03, NB06 | None |
| 16 | PANEL_1X2 | PANEL | **probably noise** | Trend R²=0.766 (highest, NB03) but AR(1)=−0.002; trend without AR(1) is not tick-exploitable | NB03, CA_B3 | D4: trend R² IS marginally significant above null (p=0.0067) but no tick-level mechanism |
| 17 | PANEL_1X4 | PANEL | **probably noise** | Trend R²=0.487, AR(1) near zero; area encoding unstable (NB07 rank ρ=0.467) | NB03, NB07, CA_B3 | None |
| 18 | PANEL_2X2 | PANEL | **probably noise** | No AR(1), no feature signal, no cointegration with any sibling | NB03, NB07 | None |
| 19 | PANEL_2X4 | PANEL | **probably noise** | Trend R²=0.622, AR(1)=−0.002; trending RW only, not tick-exploitable | NB03, CA_B3 | None |
| 20 | PANEL_4X4 | PANEL | **probably noise** | Weakest trend (R²=0.231); area encoding violated (cheapest despite largest area) | NB07, NB03 | None |
| 21 | PEBBLES_XS | PEBBLES | **likely exploitable** | 5-sum=50000 (CV=0.006%, 88.8% within ±0.5); constraint enforced tick-level simultaneously (lag-0 only, CC3) | NB09, CC3, CB2 | Tri-modal sum deviation: outlier states at ±15 ticks; no lead-lag between products |
| 22 | PEBBLES_S | PEBBLES | **likely exploitable** | 5-sum=50000 replicable all 3 days; anti-corr with XL partially mechanical (pred −0.347, obs −0.483) | NB09, CA_B5, CB2 | Mechanical component explains ~70% of anti-corr; residual unexplained |
| 23 | PEBBLES_M | PEBBLES | **likely exploitable** | 5-sum=50000 all 3 days; size-price rank XS<S<M<L<XL (Spearman 1.0 on days 2/3, NB07) | NB09, CA_B5, NB07 | Mechanical anti-corr; outlier sum states at ±15 |
| 24 | PEBBLES_L | PEBBLES | **likely exploitable** | 5-sum=50000 hard constraint; size rank preserved; pred corr=−0.397, obs=−0.493 (partially mechanical) | NB09, NB07, CC3 | Outlier sum states at ±15 ticks |
| 25 | PEBBLES_XL | PEBBLES | **likely exploitable** | 5-sum=50000; XL dominates PC1 (loading +0.784); predicted corr=−0.505 matches observed −0.506 most closely | NB09, NB06, CA_B5 | Outlier sum states at ±15; no lead-lag with other PEBBLES products (CC3) |
| 26 | ROBOT_DISHES | ROBOT | **probably noise** | Day-4 structural break only (AR(1)=−0.289 day-4, var 6.7× normal days 2/3); PC3 singleton is artifact (CB6, D6) | NB08, CB6, CA_M6 | PC3 disappears per-day and with standardized PCA; not replicable across days |
| 27 | ROBOT_IRONING | ROBOT | **probably tradable** | AR(1)=−0.117 (stable all 3 days); reversal_frac=55% > 50% bounce baseline; step=10 on ±10 grid (NB09) | CA_B2, CB3, NB09 | Critic B's "100% reversal" claim rebutted (computed 55%); step > half-spread=3.2 |
| 28 | ROBOT_LAUNDRY | ROBOT | **probably noise** | No AR(1), no structure; spread regime unstable across days | NB02, NB03 | None |
| 29 | ROBOT_MOPPING | ROBOT | **probably noise** | AR(1)=−0.012, no mode prevalence, no corr structure; Ward cluster singleton | NB06, NB03 | None |
| 30 | ROBOT_VACUUMING | ROBOT | **probably noise** | Near-zero AR(1), tight spread (6.75) but no replicable MR signal | NB02, NB03 | None |
| 31 | SLEEP_POD_COTTON | SLEEP_POD | **probably noise** | No AR(1), feature R²=0.051, no cointegration; slow-drifting RW | NB07, NB03, NB05 | None |
| 32 | SLEEP_POD_LAMB_WOOL | SLEEP_POD | **probably noise** | No structure across any lens; low CV, no intraday pattern | NB03, NB06 | None |
| 33 | SLEEP_POD_NYLON | SLEEP_POD | **probably noise** | Trend R²=0.737 (2nd highest across all 50) but AR(1) near zero; trend not tick-exploitable | NB03, CA_B3 | Trend R² significant (D4, p=0.0067) but no tick mechanism |
| 34 | SLEEP_POD_POLYESTER | SLEEP_POD | **probably noise** | No AR(1), no corr, no feature signal; slow-drifting RW | NB08, NB03 | None |
| 35 | SLEEP_POD_SUEDE | SLEEP_POD | **probably noise** | No AR(1), no feature signal, no within-cat corr | NB03, NB07 | None |
| 36 | SNACKPACK_CHOCOLATE | SNACKPACK | **probably tradable** | CHOC/VAN corr=−0.916 pooled, per-day −0.92; Group A of 2+2+1 architecture (CC1) | CC1, CB5, NB09 | Pair-sum drifts −98 to −57 per day; per-day spread ADF not significant (CC7) |
| 37 | SNACKPACK_PISTACHIO | SNACKPACK | **probably tradable** | PIST/STRAW=+0.913 (Group B co-moving); PIST/RASP=−0.831; cross-group |corr|≤0.04 (CC1) | CC1, CB5 | PIST−STRAW spread non-stationary; co-move but not cointegrated (CC10) |
| 38 | SNACKPACK_RASPBERRY | SNACKPACK | **probably tradable** | STRAW/RASP=−0.924 pooled, per-day −0.93 to −0.92; Group B anti-corr confirmed (CC1) | CC1, CB5 | RASP+PIST pair-sum drifts −116 to −209 per day; no intraday stationarity |
| 39 | SNACKPACK_STRAWBERRY | SNACKPACK | **probably tradable** | STRAW/RASP=−0.924; PIST/STRAW=+0.913; both stable across all 3 days (per-day verified, CC1) | CC1, CB4, CB5 | Pair-sum not stationary within day (CC7, CA_M1) |
| 40 | SNACKPACK_VANILLA | SNACKPACK | **probably tradable** | CHOC/VAN=−0.916 pooled, per-day return corr −0.91 to −0.92; most stable SNACKPACK product | CC1, CB5, NB09 | CHOC+VAN sum drifts −57 to −98 per day; pooled cointegration spurious (CA_B4) |
| 41 | TRANSLATOR_ASTRO_BLACK | TRANSLATOR | **probably noise** | AR(1) near zero; color-darkness R²=0.388 but rank unstable (ρ(day2,day3)=0.10) | NB07, NB08 | None |
| 42 | TRANSLATOR_ECLIPSE_CHARCOAL | TRANSLATOR | **probably noise** | Low CV (0.019, NB08); AR(1) near zero; no structure across any lens | NB08, NB03 | None |
| 43 | TRANSLATOR_GRAPHITE_MIST | TRANSLATOR | **probably noise** | No structure; feature encoding unstable day-to-day | NB07, NB03 | None |
| 44 | TRANSLATOR_SPACE_GRAY | TRANSLATOR | **probably noise** | No structure; color-encoding near-zero on days 2/3 | NB07, NB03 | None |
| 45 | TRANSLATOR_VOID_BLUE | TRANSLATOR | **probably noise** | Highest price in category (mean 10,859) but AR(1) near zero; no replicable signal | NB01, NB03 | None |
| 46 | UV_VISOR_AMBER | UV_VISOR | **probably noise** | Distributional outlier (mean 7,912 vs category mean 10,500+, NB01) but AR(1) near zero | NB01, NB07 | Severe price separation from siblings unexplained; worth monitoring |
| 47 | UV_VISOR_MAGENTA | UV_VISOR | **probably noise** | No anomaly across any lens; AR(1) near zero; typical random walk | NB03, NB06 | None |
| 48 | UV_VISOR_ORANGE | UV_VISOR | **probably noise** | No AR(1); wavelength encoding day-4-only (ρ=0.800 day-4 vs ≈0 days 2/3, NB07, CA_M3) | NB07, NB03 | None |
| 49 | UV_VISOR_RED | UV_VISOR | **probably noise** | Borderline ADF stationarity (p=0.035 day-2) fails Bonferroni correction (threshold = 0.00033) | NB03, CA_m7 | None |
| 50 | UV_VISOR_YELLOW | UV_VISOR | **probably noise** | No AR(1), no structure; feature encoding not applicable | NB03, NB06 | None |

---

## Summary by Triage Call

| Call | Count | Categories |
|------|-------|------------|
| **likely exploitable** | 5 | PEBBLES (all 5) |
| **probably tradable** | 8 | OXYGEN_SHAKE (2: CHOCOLATE, EVENING_BREATH), ROBOT (1: IRONING), SNACKPACK (5) |
| **probably noise** | 37 | GALAXY_SOUNDS (5), MICROCHIP (5), OXYGEN_SHAKE (3), PANEL (5), ROBOT (4), SLEEP_POD (5), TRANSLATOR (5), UV_VISOR (5) |

---

## Unresolved Disagreements

**1. ROBOT_IRONING: triage call is disputed between Critic A and Critic B.**
- Critic A (CA_B2): "step ±10 incommensurate with half-spread 3.2 → AR(1) is genuine MR"
- Critic B (CB3): "100% reversal rate → pure bounce artifact"
- Synthesis recomputation: reversal_frac = **0.550 / 0.544 / 0.559** across days 2/3/4. This is NOT 100% (Critic B is factually wrong). But 55% is only modestly above the 50% bounce baseline. Critic A is directionally correct that step > half-spread implies the AR(1) is not purely bounce. The residual 5% excess reversal above baseline is a real but weak MR signal.
- Assigned: **probably tradable** (weak MR). The question of whether 55% reversal is "exploitable" given spread costs cannot be resolved from EDA alone — this is a structural property that requires strategy-layer evaluation.

**2. PEBBLES anti-correlation: mechanical fraction is product-dependent.**
- Theoretical prediction from sum=50000: corr(XL, PEBBLES_L) = −0.397 (predicted) vs −0.493 (observed). The gap (0.097) is non-trivial.
- Critic A (CA_B5) stated "fully determined by mechanical arithmetic" — this is true for PEBBLES_XL (pred=−0.505, obs=−0.506) but not for PEBBLES_XS (pred=−0.276, obs=−0.475, gap=0.199).
- The discrepancy for XS/S/M/L suggests the sum constraint explains most but not all of the anti-correlation. The residual may reflect co-movement in the constraint-adjustment process. This is not resolved by the available data.

**3. PANEL trend R² excess: D4 found p=0.0067 (significant above null) but effect is small.**
- P(R²>0.3 | random walk) = 62.7% (recomputed). Observed 40/50 vs expected 31.4. Excess = 8.6 products.
- NB03 framed this as evidence of "predictable drift." Critic A (CA_B3) said "consistent with pure random walks."
- Synthesis: the excess IS statistically significant but the 8.6-product effect is too diffuse to name specific products as definitely trending (as opposed to random draws). No product has AR(1) > 0.3 to confirm exploitable trend. The trend R² signal is real at the population level but insufficient for individual-product triage calls.

**4. SNACKPACK pair-spread stationarity within-day vs pooled.**
- Critic A (CA_B4, CA_M1) and Critic C (CC7) both verified that per-day ADF on CHOC/VAN and RASP/PIST spreads fail significance. NB05 reported pooled significance.
- The 2+2+1 architecture (confirmed in D3) establishes that the contemporaneous anti-correlations are real and stable. But whether the pair-spreads mean-revert within a day is unresolved — the pooled signal is spurious and per-day fails, but this does not rule out a within-day structure at shorter windows (e.g., 1,000 ticks) that the ADF (designed for long-horizon) may miss.

**5. UV_VISOR_AMBER price separation from category.**
- Mean mid = 7,912 vs next-lowest sibling = 10,427 (gap of 2,515, 32% below category mean).
- No explorer or critic identified a structural reason for this gap. The product is in the same NPC-generated category but prices 25% below all siblings. NB07 wavelength encoding is near-zero (no stable feature signal). No AR(1), no corr, no constraint.
- Possibility: the "AMBER" wavelength band is simply priced at a different level by the NPC bot. Whether this price level is stable on the hidden scoring day or shifts toward the category mean is unknown.
