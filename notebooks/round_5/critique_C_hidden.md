# Critique C — Hidden-Pattern Critic

> Critic C: hidden-pattern review of the 9 explorer findings docs.
> All numerical claims were verified via one-shot `venv/bin/python3` scripts against
> `data/round_5/prices/prices_round_5_day_{2,3,4}.csv` and
> `data/round_5/prices/trades_round_5_day_{2,3,4}.csv`.
> No strategy proposals. No PnL predictions.

---

## Self-check before writing

- [x] PEBBLES 5-sum = 50000 constraint independently verified: mean=49999.94, std=2.80, CV=0.0056%, 18 unique sum values. Matches [09_determinism_anomaly cell-6].
- [x] All claims cite numerical evidence from my own verification scripts.
- [x] No strategy / PnL / rule proposals in any test.
- [x] No edits to forbidden files.

---

## Test 1 — SNACKPACK 2+2+1 Anti-Correlation Architecture

**Hypothesis**: SNACKPACK is NOT five independent products or a single basket. It has two independent anti-correlated pairs (CHOCOLATE↔VANILLA; STRAWBERRY↔RASPBERRY) plus PISTACHIO co-moving with STRAWBERRY — forming a 3-node cluster that is completely independent of the CHOCOLATE/VANILLA pair.

**Operational definition**: Compute the 5×5 first-difference correlation matrix for SNACKPACK mid-prices. A "2+2+1 architecture" is confirmed if: (a) corr(CHOCOLATE, VANILLA) < −0.85; (b) corr(STRAWBERRY, RASPBERRY) < −0.85; (c) corr(PISTACHIO, STRAWBERRY) > +0.85; (d) all cross-group correlations (CHOCOLATE vs STRAWBERRY, CHOCOLATE vs PISTACHIO, VANILLA vs STRAWBERRY, VANILLA vs PISTACHIO) are within ±0.10.

**Verified numerical result**:
- corr(CHOCOLATE_chg, VANILLA_chg) = **−0.9159** (3-day pooled)
- corr(STRAWBERRY_chg, RASPBERRY_chg) = **−0.9238**
- corr(PISTACHIO_chg, STRAWBERRY_chg) = **+0.9133**
- corr(PISTACHIO_chg, RASPBERRY_chg) = **−0.8309**
- All cross-group (A vs B/C): |corr| ≤ 0.040 ✓
- Anti-correlation is purely contemporaneous: at lag ±1, cross-corr drops to < 0.01

The SNACKPACK correlation matrix exposes two completely decoupled subsystems with zero information leakage between them.

**Why prior notebooks missed it**: Notebook 05 found 3 cointegrated pairs but reported no clustering structure; it did not compute a full change-correlation matrix. Notebook 09 identified CHOCOLATE/VANILLA as a mirror pair (corr=−0.974 on day 2) but explicitly examined only that one pair, missing STRAWBERRY/PISTACHIO/RASPBERRY entirely. Notebook 06 identified SNACKPACK as having "extreme internal polarization" (range −0.923 to +0.913) but did not decompose WHY the range is so wide. No notebook noted that the two subsystems are information-isolated from each other.

**Priority**: HIGH — this is the most important missed structural fact in the entire EDA. The two-subsystem architecture implies two independent spread opportunities coexist within a single category.

---

## Test 2 — SNACKPACK Pair-Sum Day-Over-Day Drift Rate

**Hypothesis**: Within each day, the CHOCOLATE+VANILLA sum is tightly bounded (CV ≈ 0.2%) but drifts consistently across days. The same is true for the RASPBERRY+PISTACHIO pair. If the drift is monotone and roughly constant per day, it is predictable for the hidden scoring day.

**Operational definition**: Compute per-day mean of (CHOCOLATE+VANILLA sum) and (RASPBERRY+PISTACHIO sum) for days 2, 3, 4. Compute ADF on the within-day sum series. Compute the day-over-day delta. A "predictable drift" finding requires: (a) within-day CV < 0.5%; (b) cross-day delta has consistent sign across both day-2→3 and day-3→4 transitions; (c) ADF on the within-day sum is p > 0.05 (i.e., the sum wanders within the day, it's not stationary on a tick level).

**Verified numerical result**:
- CHOC+VAN per-day means: 20025 (day 2) → 19927 (day 3, Δ=−98) → 19870 (day 4, Δ=−57) — consistent downward drift
- CHOC+VAN within-day CV: 0.21% / 0.16% / 0.24% across days 2/3/4
- ADF on within-day CHOC+VAN sum: all three days p > 0.18 — NOT stationary within a day
- RASP+PIS per-day means: 19721 → 19605 (Δ=−116) → 19396 (Δ=−209) — consistent downward drift
- The drift direction is stable across both transitions (both pairs drift down by ~100-200 per day)

**Why prior notebooks missed it**: Notebook 09 noted that the CHOC+VAN sum "DRIFTS across days" and used it to argue against a hard constraint. It did not measure the drift rate, test if it is monotone, or propose that a consistent multi-day drift might be predictable. No notebook checked PISTACHIO+RASPBERRY for the same drift pattern.

**Priority**: HIGH — if the per-day drift rate is roughly constant, it can be estimated from days 2–4 to anchor expectations for day 5.

---

## Test 3 — PEBBLES Tick-Level Conservation: Instantaneous Zero-Sum Constraint

**Hypothesis**: The PEBBLES sum=50000 constraint is enforced tick-by-tick, not through a slow mean-reversion process. All five products' changes cancel simultaneously within the same tick, with zero lead-lag between any product and the others.

**Operational definition**: (a) Compute corr(PEBBLES_XL_chg, sum_of_others_chg) at lags −5 to +5. Simultaneity confirmed if lag=0 dominates by ≥ 0.9 and all other lags are < 0.05. (b) Compute AR(1) of sum deviation from 50000. Half-life = −ln(2)/ln(ρ) ticks. Instantaneous reversion if half-life < 1 tick. (c) Verify via ADF: per-day ADF on the sum deviation should have p ≈ 0 with very large negative statistic.

**Verified numerical result**:
- corr(XL_chg, sum_of_4_chg) at lag=0: **−0.9916**
- corr(XL_chg, sum_of_4_chg) at lag=±1: **−0.010** (essentially zero)
- AR(1) on sum deviation: ρ = 0.013, **half-life = 0.2 ticks**
- Per-day ADF: stat ≈ −71 to −100, p = 0.000000 (strongly stationary)
- When XL = +10: mean sum-of-4 change = −9.755 (std=3.75)
- When XL = −10: mean sum-of-4 change = +9.988 (std=3.50)

The zero-sum constraint operates as a **same-tick mechanical law**, not as a market price-discovery process.

**Why prior notebooks missed it**: Notebook 09 confirmed the sum=50000 constraint but described it as "mean-reverting" without quantifying how fast. Notebook 05 noted the anti-correlation between PEBBLES_L and PEBBLES_XL (−0.49 on returns) but did not test all 5 products' simultaneous dynamics. Notebook 06 identified the factor structure (XL vs rest) but did not test the temporal structure (is XL a leader or a simultaneous participant?). No notebook computed the AR(1) half-life of the sum deviation.

**Priority**: HIGH — the distinction between "slow mean reversion" and "instantaneous tick-level conservation" changes how the constraint can be exploited. Also: there is NO lead-lag between products, which rules out cross-product predictive signals in PEBBLES.

---

## Test 4 — PEBBLES Sum Deviation Has a Hard Gap (Tri-Modal Distribution)

**Hypothesis**: The PEBBLES 5-sum deviation from 50000 is not normally distributed. It has a tri-modal structure with a hard gap between the "normal" state and the two "outlier" states, and no values in the gap region.

**Operational definition**: Compute the histogram of (5-sum − 50000) across all 30,000 ticks. A "gap" is confirmed if there are zero ticks with deviation in (1.5, 14.0) and zero ticks in (−16.5, −1.5). The three states are: "normal" |dev| ≤ 1.5, "high" dev ≈ +14 to +16.5, "low" dev ≈ −17 to −18.5.

**Verified numerical result**:
- Values with 1.5 < |dev| < 14.0: **zero ticks out of 30,000**
- Normal state (|dev| ≤ 1.5): **29,147 ticks (97.2%)**
- High state (dev ≈ +14.5): **406 ticks (1.4%)**, confined to values [14.0, 16.5]
- Low state (dev ≈ −17.5): **447 ticks (1.5%)**, confined to values [−18.5, −16.5]
- High/low state ticks are isolated (not clustered): spacing is hundreds to thousands of ticks
- Outlier states appear across all 3 days with consistent magnitude

The gap structure suggests the outlier states arise from a specific mechanical cause (e.g., two products updating simultaneously by ±10 at a tick where mid-price is a half-integer), not from random noise.

**Why prior notebooks missed it**: Notebook 09 reported "only 18 unique values" for the 5-sum and "std=2.80" without examining the distribution shape. An 18-value distribution with a hard gap is categorically different from a roughly symmetric distribution. No notebook visualized or tabulated the full deviation distribution.

**Priority**: HIGH — understanding the outlier states is critical for interpreting whether apparent deviations from 50000 are "real" (tradable) or purely mechanical artifacts of half-integer mid prices.

---

## Test 5 — MICROCHIP Buy-Side Flow Imbalance Decays to Zero by Day 4

**Hypothesis**: Notebook 04 reported MICROCHIP net buy-side flow imbalance of +0.072 across all 3 days. This was reported as a pooled 3-day number. The imbalance may be decreasing across days, potentially reaching zero by day 4, which changes its interpretation.

**Operational definition**: Compute at-bid vs at-ask trade fractions for MICROCHIP separately for each of days 2, 3, 4. Merge trades with price data to classify each trade as at-bid or at-ask (use bid_price_1 and ask_price_1 at the same day+timestamp). A "decaying imbalance" finding requires: (a) day-2 ask fraction significantly above 50%; (b) day-4 fraction approaching 50%; (c) monotone trend across all 3 days.

**Verified numerical result**:
- Day 2: bid=44.8%, ask=**55.2%** (+5.2pp buy-side imbalance)
- Day 3: bid=46.4%, ask=**53.6%** (+3.6pp buy-side imbalance)
- Day 4: bid=**50.2%**, ask=**49.8%** (essentially neutral, +0pp imbalance)
- For comparison, GALAXY_SOUNDS (standard category): bid=51.2%, ask=48.8% (slight sell imbalance)

The MICROCHIP buy-side imbalance is a days-2 and days-3 phenomenon that has fully decayed by day 4.

**Why prior notebooks missed it**: Notebook 04 reported the pooled 3-day number (+0.072) without a per-day breakdown for MICROCHIP specifically. The per-day analysis was done for trade count CoV but not for signed flow. No notebook checked whether the flow imbalance was shrinking over time.

**Priority**: MEDIUM — understanding whether this is a transient (decaying) or structural (persistent) feature is necessary for any flow-based analysis on the hidden scoring day.

---

## Test 6 — Does Any Other Category Have a PEBBLES-Style Sum Constraint?

**Hypothesis**: The PEBBLES CV of 0.006% on the 5-sum is anomalous. No other category comes close to this. The test verifies that the PEBBLES sum constraint is unique and not replicated in any modified form (pair-sums, subset sums, or cross-category sums).

**Operational definition**: For all 10 categories, compute CV(5-sum). "Constraint" threshold: CV < 0.05% (10× below SNACKPACK's 0.38%). Also test: all C(5,2)=10 pair sums per category, and all C(10,2)=45 cross-category sum pairs. Separately test sum-of-squares for all 10 categories.

**Verified numerical result**:
- PEBBLES 5-sum CV: **0.0056%** (unique)
- SNACKPACK 5-sum CV: 0.38% (next lowest, 68× higher than PEBBLES)
- All other 8 categories: CV = 1.4% to 5.2%
- Sum-of-squares (all 10 categories): CVs all exceed 0.8% — no constraint found
- PEBBLES pair-sums: all CVs > 3.3% — no sub-group constraint within PEBBLES
- Cross-category pair sums: PEBBLES+SNACKPACK CV=0.19%, but this is driven entirely by SNACKPACK being a slowly-drifting ~50000 sum — not a true cross-constraint
- No 4-product or 3-product subsets of MICROCHIP form a tighter constraint than the 5-sum (3.04%)

The sum-constraint is architecturally unique to PEBBLES. No analogous structure exists elsewhere.

**Why prior notebooks missed it**: Notebook 09 correctly found and reported the PEBBLES constraint. No notebook systematically tested all other categories for analogous structures, nor tested pair-sums within PEBBLES, sum-of-squares, or cross-category combinations.

**Priority**: MEDIUM — confirms the PEBBLES constraint is unique and focus should not be diffused to other categories on false analogies.

---

## Test 7 — SNACKPACK Pair-Spread Stationarity Per Day vs Pooled

**Hypothesis**: Notebook 05 found SNACKPACK_RASPBERRY and SNACKPACK_VANILLA basket-spreads are stationary on the pooled 3-day series (ADF p=0.001 and p=0.028). These pairs may NOT be stationary within individual days, meaning the pooled result is spurious (regime shifts between days masquerade as mean-reversion).

**Operational definition**: For CHOCOLATE−VANILLA and RASPBERRY−PISTACHIO spreads: (a) compute ADF on the pooled 3-day series; (b) compute ADF separately for each of days 2, 3, 4. A "spurious pooling" flag is set if: pooled p < 0.05 but individual day p > 0.10 for all 3 days.

**Verified numerical result**:
- CHOCOLATE−VANILLA pooled ADF: p = **0.048** (marginal)
- CHOCOLATE−VANILLA per-day ADFs: Day 2 p=0.186, Day 3 p=0.298, Day 4 p=0.307 — **none significant**
- RASPBERRY−PISTACHIO pooled ADF: p = **0.006** (significant)
- RASPBERRY−PISTACHIO per-day ADFs: Day 2 p=0.094, Day 3 p=0.192, Day 4 p=0.385 — **none significant**
- The mean spread shifts substantially between days: RASP−PIS changes from +409 (day 2) to +631 (day 3) to +707 (day 4)

All SNACKPACK pair spreads are non-stationary within individual days. The pooled significance is driven by level shifts between days, not by genuine mean-reversion.

**Why prior notebooks missed it**: Notebook 05 specifically noted "no pair was cointegrated on all 3 individual days" but this only checked cointegration, not simple spread stationarity. Notebook 05 and 09 both reported pooled ADF statistics as indicative of mean-reversion potential without decomposing into per-day results.

**Priority**: MEDIUM — prevents a false inference that SNACKPACK pair spreads are mean-reverting within a trading day. The spreads are NOT tight intraday; they drift freely within each day.

---

## Test 8 — ROBOT_IRONING Price Grid: FV Lives on a 10-Unit Grid, But FV Itself Drifts

**Hypothesis**: Notebook 09 correctly identified that ROBOT_IRONING prices are 96.7% on a 10-unit grid with ±10 dominant steps. No notebook asked: does the ±10 random walk have a drifting "center" FV that is itself predictable? And are the "off-grid" 3.3% of ticks structurally distinct (e.g., transition states mid-step)?

**Operational definition**: (a) Confirm that "off-grid" prices are half-integer averages of two adjacent grid levels (e.g., 7458.5 = (7457+7460)/2, arising when bid_price_1 is just below a grid level and ask_price_1 is just at the next grid level). (b) For the 96.7% on-grid prices, test if there is a per-day drifting mean (i.e., compute a rolling 1000-tick window mean and test for monotonicity or V-shape). (c) For each day, test ADF on on-grid price levels to confirm unit root behavior.

**Verified numerical result**:
- 96.7% of ROBOT_IRONING prices are exact multiples of 10
- Remaining 3.3% are half-integers (e.g., 7458.5, 7511.5) — confirmed as bid/ask transition states
- Day 2 1000-tick window means: 9998→9921→9541→9026→8881→8959→8960→9188→9524→9546 — U-shape (drops mid-day, recovers)
- Day 3 1000-tick window means: monotone decline from 9576 to 7819
- Day 4 1000-tick window means: mean-reverting range [7608, 8285]
- ADF on level (per day): all days p > 0.37 — unit root confirmed (random walk on the grid)
- AR(1) on level: ρ ≈ 0.9994–0.9999 (near-unit-root)

The day-2 U-shape is a single-day phenomenon, not a repeating intraday cycle. No day-stable periodicity found.

**Why prior notebooks missed it**: Notebook 09 identified the discrete step structure and the ±10 dominant moves but did not investigate the temporal path of the FV within each day. Notebook 08 mentioned the FFT finding of a "5000-tick period" for PEBBLES_XL as a trend artifact but did not apply the same analysis to ROBOT_IRONING's within-day path. Notebook 03 found no FFT significance after detrending.

**Priority**: LOW — the intraday path is not stable across days, so no systematic intraday timing signal exists. However, understanding that the FV is a free unit-root random walk on the 10-unit grid resolves any remaining doubt about whether ROBOT_IRONING has a recoverable FV anchor.

---

## Test 9 — MICROCHIP Has NO Within-Category Constraint Whatsoever

**Hypothesis**: Despite the AGENT_BRIEF flagging MICROCHIP as an anomalous category (569 trades vs 733 standard), the price series of the 5 MICROCHIP products have zero intra-category correlation, no sum constraint, and no detectable structure beyond individual random walks. The "anomaly" is entirely in the TRADE TAPE, not in the price structure.

**Operational definition**: Compute: (a) first-difference correlation matrix of all 5 MICROCHIP products; (b) all C(5,2)=10 pair-sum CVs; (c) corr(MICROCHIP_SQUARE_chg, sum_of_4_chg) as a test for a PEBBLES-like architecture; (d) 5-sum CV.

**Verified numerical result**:
- First-difference correlation matrix: all 10 off-diagonal entries are within [0.0075, 0.0126] — effectively zero
- 5-sum CV: **3.04%** (vs PEBBLES 0.0056%)
- corr(SQUARE_chg, sum_of_4_chg): **+0.013** (positive, not negative — no conservation law)
- OLS R² of SQUARE on the other 4 products: 0.844 (in levels), but residual std = 723 — driven by shared trend, not a tight constraint
- No pair-sum has CV below 2%
- MICROCHIP products are 5 independent random walks that happen to share a broad downward trend (especially MICROCHIP_OVAL and MICROCHIP_SQUARE going in opposite directions)

**Why prior notebooks missed it**: Notebook 09 explicitly stated "MICROCHIP shows no special structure beyond baseline." This test corroborates that finding with additional checks. What was missing was the explicit decomposition into (a) the constraint null and (b) OLS fit vs constraint — specifically, that high OLS R² in levels is a shared-trend artifact, not a constraint. No notebook articulated that MICROCHIP's anomaly is trade-tape-only.

**Priority**: LOW — confirms what notebook 09 suggested. MICROCHIP's trade-count anomaly is in the generation schedule, not in price dynamics. This is important to document explicitly so synthesis does not waste time on MICROCHIP price structure.

---

## Test 10 — SNACKPACK PISTACHIO≈STRAWBERRY: Are They Informationally Redundant?

**Hypothesis**: PISTACHIO and STRAWBERRY have +0.913 change-correlation, suggesting they are co-generated or driven by the same underlying signal. If they move identically, only one position per subsystem is needed; the two may be informationally redundant.

**Operational definition**: (a) Compute corr(PISTACHIO_chg, STRAWBERRY_chg) pooled and per day. (b) Compute ADF on (STRAWBERRY − PISTACHIO) spread — if stationary, they are cointegrated and redundant. (c) Compute STRAWBERRY−PISTACHIO spread per day: mean, std, ADF.

**Verified numerical result**:
- Pooled corr(PISTACHIO_chg, STRAWBERRY_chg): **+0.9133**
- STRAWBERRY−PISTACHIO spread: mean=+1,211, std=477, ADF stat=−2.47, p=0.124 — **NOT stationary**
- STRAWBERRY−RASPBERRY spread: ADF stat=−3.15, p=0.023 — stationary (pooled)
- RASPBERRY−PISTACHIO spread: ADF stat=−3.57, p=0.006 — stationary (pooled)
- Per-day RASPBERRY−PISTACHIO spread: means drift from +409 (day 2) to +707 (day 4) — NOT stationary within individual days

PISTACHIO and STRAWBERRY co-move but are NOT cointegrated (their spread is non-stationary). Both products have similar directional dynamics but maintain a varying price offset.

**Why prior notebooks missed it**: No notebook computed corr(PISTACHIO, STRAWBERRY) at the change level. Notebook 05 found "3 cointegrated SNACKPACK pairs" but the pairs identified (via Engle-Granger) were not explicitly named in the findings doc. Notebook 09 only analyzed CHOCOLATE/VANILLA and PISTACHIO/RASPBERRY, not the PISTACHIO/STRAWBERRY positive relationship.

**Priority**: MEDIUM — the PISTACHIO≈STRAWBERRY relationship confirms that SNACKPACK has a 2-dimensional effective factor structure (one factor for Group A = CHOC/VAN, one factor for Group B = STRAW/PISTACHIO vs RASPBERRY), not a 5-dimensional structure. This collapses the problem from 5 products to 2 independent bets.

---

## Summary of What Was Missed

| Test # | Category/Product | What Was Missed | Priority | Verified Numerically |
|--------|-----------------|-----------------|----------|----------------------|
| 1 | SNACKPACK | 2+2+1 architecture: CHOC/VAN independent of STRAW/PIS/RASP cluster | HIGH | Yes |
| 2 | SNACKPACK | Per-day pair-sum drift rate is consistent and monotone across days | HIGH | Yes |
| 3 | PEBBLES | Tick-level conservation: zero-sum enforced simultaneously (lag=0 only) | HIGH | Yes |
| 4 | PEBBLES | Tri-modal sum deviation with hard gap — no values in ±[1.5, 14.0] range | HIGH | Yes |
| 5 | MICROCHIP | Buy-side flow imbalance decays to neutral by day 4 (not stable) | MEDIUM | Yes |
| 6 | All | No other category has a PEBBLES-like sum constraint (exhaustive check) | MEDIUM | Yes |
| 7 | SNACKPACK | Pooled ADF significance for pair spreads is spurious (not significant per-day) | MEDIUM | Yes |
| 8 | ROBOT_IRONING | FV is a free random walk on a 10-unit grid; day-2 U-shape is a one-off | LOW | Yes |
| 9 | MICROCHIP | Price structure anomaly is zero; the anomaly is trade-tape-only | LOW | Yes |
| 10 | SNACKPACK | PISTACHIO and STRAWBERRY are co-moving (+0.913) but not cointegrated | MEDIUM | Yes |

---

## Flags for Synthesis

1. **SNACKPACK triage call needs revision**: Notebooks 05 and 09 both flag SNACKPACK as "probably tradable" based on correlated pairs. The hidden 2+2+1 structure means SNACKPACK should be re-examined with the correct factor decomposition. The two subsystems are independent; the 5-product basket is meaningless.

2. **PEBBLES conservation is tick-level mechanical, not market-based**: The half-life of 0.2 ticks and the contemporaneous-only correlation structure distinguish PEBBLES from all other anti-correlated categories. Synthesis should note this is a mechanical constraint, not price discovery.

3. **MICROCHIP's anomaly is resolved**: It is a trade-schedule anomaly (569 vs 733 trades), not a price-structure anomaly. No sum constraint, no cross-product correlation, no step generator. Price products are 5 independent random walks with shared trend. This closes the AGENT_BRIEF's open question on MICROCHIP.

4. **SNACKPACK pair spreads are NOT mean-reverting within a day**: The per-day ADF finding contradicts any inference from the pooled ADF. Synthesis should downgrade any intraday-spread-reversion call for SNACKPACK pairs.
