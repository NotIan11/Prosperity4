# Critique A — Statistical Critique

> Critic A: statistical soundness review of all 9 explorer findings docs.
> Re-derivations use `venv/bin/python3`; all numbers verified against raw data.

---

## BLOCKING Issues (claim is wrong or materially misleading)

**B1. NB01 bullet 2 — CV label inflated by between-product dispersion, not volatility.**
NB01 reports "Mean CV across the 5 products: PEBBLES = 0.2245, MICROCHIP = 0.2298."
Re-derivation: these match `std(all 5 products' mid-prices pooled) / mean(all)` — a
*category-level* CV that conflates between-product price dispersion (73% of PEBBLES pooled
variance) with within-product price volatility. The mean within-day per-product CV is 0.064
for PEBBLES and 0.050 for MICROCHIP — roughly 3-4× smaller than reported. The ranking of
PEBBLES and MICROCHIP as "highest-CV" categories holds, but the magnitude is dominated by
price-level dispersion across products (e.g. PEBBLES mean mids span 7,405–13,226), not
tick-to-tick volatility. Every downstream claim built on "CV ≈ 0.22–0.23 implies high
volatility" is overstated. [NB01 cell 9; NB08 which inherits the same numbers]
Severity: **BLOCKING**

**B2. NB03 bullet 14 — bid-ask bounce explanation for AR(1) is factually incorrect.**
NB03 claims the negative AR(1) of ROBOT_IRONING (ρ = −0.117) and
OXYGEN_SHAKE_EVENING_BREATH (ρ = −0.112) "likely reflects bid-ask bounce at the tick
level." Bid-ask bounce generates mid-price alternations of ±half-spread. Verified: ROBOT_IRONING
mean spread = 6.39, half-spread = 3.20; dominant step size is ±10.0 (73.1% of non-zero moves,
per NB09 cell 12). OXYGEN_SHAKE_EVENING_BREATH modal spread = 12, half-spread = 6.0; dominant
step size is also ±10.0 (71.1%). A ±10 step cannot be a ±3.2 half-spread bounce. Additionally,
ROBOT_IRONING reversal fractions: day 2 = 55.0%, day 3 = 54.4%, day 4 = 55.9% — all above 50%,
confirming genuine mean-reversion in the step process. The AR(1) signal is real; labelling it as
microstructure artefact incorrectly deflates its evidential weight. [NB03 cells 14–15]
Severity: **BLOCKING**

**B3. NB03 bullet 8 — trend R² > 0.3 for 40/50 products is not evidence of exploitable trend.**
NB03 reports "40 of 50 products have mean trend R² > 0.3, and 20+ have R² > 0.5" and presents
this as consistent with "slow, persistent drift that is predictable at the day level."
Re-derivation via Monte Carlo (1,000 simulations, n=10,000 Gaussian random walks):
P(R² > 0.3) = 60.3%; P(R² > 0.5) = 42.2% for a pure random walk of the same length.
A finding of 40/50 products with R² > 0.3 is entirely consistent with the null of 50 independent
random walks. The trend R² statistic has no discriminating power here. NB03 self-notes the caveat
in bullet 11 (FFT also inflated by trend) but does not apply the same logic to the trend R² itself.
[NB03 cell 6]
Severity: **BLOCKING**

**B4. NB05 bullet 3 — SNACKPACK cointegration count under-reported and the entire cointegration
finding is spurious due to pooling across days with structural level breaks.**
NB05 reports "3 out of 10 pairs cointegrated (p<0.05)" for SNACKPACK. Re-derivation on the
same pooled 3-day series finds **5 out of 10 pairs** significant (RASPBERRY/VANILLA p=0.0068,
RASPBERRY/STRAWBERRY p=0.0242, RASPBERRY/CHOCOLATE p=0.0070, RASPBERRY/PISTACHIO p=0.0217,
CHOCOLATE/PISTACHIO p=0.0453). More critically, per-day Engle-Granger tests for the flagship
pair RASPBERRY/VANILLA yield: day 2 p=0.242, day 3 p=0.231, day 4 p=0.281 — all fail to
reject the unit-root null. The SNACKPACK basket mean itself is non-stationary per day (ADF
p=0.369/0.146/0.109). Engle-Granger applied to a pooled series with inter-day structural breaks
creates spurious I(0) residuals from the break itself. Zero pairs have structural cointegration;
the pooled signal is an artefact. [NB05 cell: coint_df, stable_coint; NB05 bullet 12 partially
acknowledges this but does not retract the finding]
Severity: **BLOCKING**

**B5. NB05 bullet 4 and NB06 bullet 2 — PEBBLES anti-correlation presented as anomalous
signal; it is mechanically required by the sum constraint and variance structure.**
NB05: "PEBBLES_L/XL ret_corr = −0.4932 — anomalously strong, may indicate opposing
bookkeeping." NB06: "PEBBLES_XS vs PEBBLES_XL = −0.506 — not noise." Re-derivation:
PEBBLES_XL return std = 30.3; other 4 products std ≈ 15.0. Under a sum-constraint (sum=50,000
confirmed by NB09), cov(XL, other_i) ≈ −var(XL)/4 = −918/4 = −229.5, giving predicted
corr(XL, other_i) = −229.5 / (30.3 × 15.0) = −0.505. Observed: −0.497/−0.496/−0.512/−0.500
for XS/S/M/L vs XL. The anti-correlation is fully determined by mechanical arithmetic; it
carries no additional information beyond what NB09 already found (basket sum = 50,000).
Calling it an "anomalous signal" and requesting AR(1) corroboration from NB03 (bullet 15 of
NB05) is conceptually wrong — AR(1) is serial autocorrelation; it cannot explain a
contemporaneous cross-sectional correlation. [NB05 bullets 4 and 15; NB06 bullet 2]
Severity: **BLOCKING**

**B6. NB04 bullet 9 — MICROCHIP buy-side flow imbalance (0.0724) treated as meaningful signal;
effective sample size is 569 ticks, not 2,845 trades.**
NB04: "Microchips show strongest buy-side flow imbalance: net flow = +81 vol per product;
imbalance = +0.072." By NB04's own finding 6, all 5 MICROCHIP products trade at identical
timestamps with identical quantities — they are one generation unit, not five independent
observations. Effective independent observations = 569 ticks (3 days combined), not 5×569=2,845.
Binomial test at trade level (naively n=2,845): p=0.004. At tick level (n=569): p=0.208
(n_buy_ticks=300/569=52.7%). The imbalance is not statistically significant at the correct
sample size. NB04 reports no significance test. [NB04 bullets 6, 9; no p-value in findings]
Severity: **BLOCKING**

---

## MODERATE Issues (correct direction but needs caveat or re-framing)

**M1. NB05 bullet 8 — basket spread stationarity for SNACKPACK_RASPBERRY/VANILLA;
spurious from pooling argument applies here too.**
NB05: "SNACKPACK_RASPBERRY ADF p=0.0010, SNACKPACK_VANILLA p=0.0275 — stationary basket
spreads." Re-derivation: per-day ADF on RASPBERRY basket spread: p=0.129/0.101/0.223 (days
2/3/4). Per-day ADF on VANILLA: p=0.190/0.323/0.269. Neither is stationary on any individual
day. The pooled result is artefactual; the basket mean itself is non-stationary per day
(p=0.369/0.146/0.109). This moderates the "basket mean-reversion supported for SNACKPACK"
conclusion. [NB05 cell: basket_df, adf_pval]
Severity: **MODERATE**

**M2. NB07 bullet 7 — MICROCHIP shape encoding uses multiple ordinals without correction.**
NB07 tests "alphabetical," "vertex-count," and "area-proxy" orderings for MICROCHIP shape
and reports the best (alphabetical R²=0.296, Spearman ρ=0.500). Testing three ordinals on
n=5 data points and reporting the best is explicit p-hacking. Similarly, NB07 bullet 5 tests
both linear-area and log₂(area) for PANEL and reports the better fit (log₂ R²=0.378 vs
linear R²=0.161). With n=5 and multiple ordinals, the probability of finding at least one
significant fit by chance is material. No multiple-testing correction is applied.
[NB07 cells 5, 7, 10]
Severity: **MODERATE**

**M3. NB07 bullet 9 — UV_VISOR wavelength result driven by a single day; days 2 and 3 are
near-zero.**
NB07: "Day-4 alone has ρ=0.800 but days 2 (ρ=−0.100) and 3 (ρ=0.000) are near-zero."
The finding leads with "mean R²=0.135, Spearman ρ=0.233" which averages a signal (day 4)
with two non-signals (days 2, 3). With n=5 products and only 3 days, one outlier day of
ρ=0.800 is 1/120 probability by chance alone. The conclusion should state that UV_VISOR
wavelength encoding has no stable signal across days, not merely "negligible." [NB07 cell 11]
Severity: **MODERATE**

**M4. NB06 bullet 9 — F-norm 0.69 cited as stability evidence without normalization.**
NB06: "Frobenius norm of correlation matrix difference: Day 2 vs Day 3 = 0.690." Without
normalization this is uninterpretable. Maximum possible F-norm for a 50×50 difference of
correlation matrices = √(50×50) = 50. Observed 0.69 / 50 = 1.38% of maximum. The conclusion
(stable) is correct but the raw number should not be cited as the evidence. [NB06 cell 13]
Severity: **MODERATE**

**M5. NB04 bullet 10 — standard-category sell-side imbalance (−0.025) has the same inflated-N
problem as MICROCHIP imbalance.**
NB04: "8 standard categories show uniform sell-side imbalance: net flow = −45 vol per
product, imbalance = −0.025." All 8×5=40 standard products share the same 733 tick timestamps
per NB04 bullet 7. Effective tick-level N = 733 (not 733×40=29,320). Binomial test at tick
level for GALAXY_SOUNDS (representative standard category): 358/733 buy = 48.8%,
p=0.555 — not significant. [NB04 bullets 7, 10]
Severity: **MODERATE**

**M6. NB03 bullet 4 — ROBOT_DISHES AR(1) instability framing; the correct diagnosis is
day-4 structural break, not "outlier day".**
NB03: "ROBOT_DISHES mean |ρ₁| = 0.098 with std = 0.166 — extreme day-to-day instability."
Verified: day 2 ρ=+0.0003, day 3 ρ=−0.004, day 4 ρ=−0.289. The day-4 AR(1) is driven by a
day-4 structural break: zero-return fraction jumps from 2.9–3.7% (days 2/3) to 75.5% (day 4),
return kurtosis from ≈0 to 10.0. This is not random day-to-day variation — it is a qualitative
regime change on day 4 only. NB08 independently confirms this (bullet 2). Presenting it as
"unreliable mean" obscures the structural nature of the change. The correct label is "day 4
structural break, not replicable." [NB03 cell 5; NB08 bullet 2]
Severity: **MODERATE**

**M7. NB08 — CV=0.220 reported for MICROCHIP_OVAL is inconsistent with the data.**
NB08: "MICROCHIP_OVAL mean falls 9766→8544→6229 (CV=0.220)." Re-derivation: CV of the 3
daily means = 0.179; pooled CV (std of all 30,000 ticks / pooled mean) = 0.190. Neither
formula reproduces 0.220. By contrast, NB01's pooled-category CV for MICROCHIP (all 5
products together) = 0.2298. The 0.220 appears to be a copy error from NB01's category-level
metric applied to a single product. Directionally correct (MICROCHIP_OVAL drifts significantly)
but the specific number is wrong. [NB08 cell 4]
Severity: **MODERATE**

**M8. NB01 bullet 4 — PEBBLES_XS day-shift denominator uses 3-day mean, not day-2 baseline.**
NB01: "PEBBLES_XS day3−day2 shift = 2,221 on a mean of ~7,405 (30.0%)." The 7,405 is the
3-day pooled mean. Day-2 mean = 9,189; shift relative to day 2 = 2,221/9,189 = 24.2%, not
30.0%. The 3-day mean is artificially low because day 3 and day 4 are also low (the product
drifts downward). Using the 3-day mean as denominator inflates the apparent shift percentage
by 24%. [NB01 cell 15]
Severity: **MODERATE**

---

## MINOR Issues (cosmetic or low-impact)

**m1. NB03 bullet 11 — FFT PNR 1,556–2,717 cited without noting it is on non-detrended
series.**
NB03: "FFT peak-to-noise ratios uniformly high (top-20 range 1,556–2,717); suggests detecting
trend and harmonics." The notebook correctly self-flags this (bullets 11, 15). However, the
PNR numbers are from the raw (non-detrended) series; quoting them without an immediate
disclaimer that they are meaningless as periodicity evidence could mislead. NB09 bullet 12
confirms via shuffled-return null: only PANEL_1X2 marginally beats the proper null; all others
do not. Consistent, but NB03's raw PNR table should be labelled "trend artifact, not usable
as periodicity discriminator." [NB03 cells 7–8]
Severity: **MINOR**

**m2. NB05 bullet 10 — "no pair is day-stable at high magnitude" conclusion correct but
SLEEP_POD max pair = 0.875 is not adequately qualified.**
NB05: "SLEEP_POD has the highest maximum pair corr on any single day (0.875) but this is not
consistent." The correct framing is: one pair on one day exceeds the 0.7 "probably tradable"
threshold — but with C(5,2)=10 pairs × 3 days = 30 tests across 10 categories, at least one
extreme value is expected under the null. No multiple-testing correction is applied to this
scan. [NB05 cell: pair_stability]
Severity: **MINOR**

**m3. NB06 bullet 8 — hierarchical clustering at k=10 comparison lacks a stability assessment.**
NB06: "at Ward k=10, named categories are not recovered." k-means/Ward clustering results are
sensitive to initialization and k choice. Without a stability measure (bootstrap silhouette,
gap statistic, or comparison to k=9 or k=11), the claim that categories "do not recover"
at k=10 is one realization. The observation is likely correct but should be qualified as
sensitive to k. [NB06 cell 7]
Severity: **MINOR**

**m4. NB01 bullet 15 — 'mean-reverting or bounded process' language applied to products where
ADF rejects stationarity.**
NB01: "SNACKPACK distributions most consistent with a mean-reverting or bounded process."
NB03 bullet 7 confirms all 50 products fail consistent ADF stationarity in levels. Low CV and
low day-shift do not imply stationarity. The correct language is "slow-drifting with low
intra-day volatility," not "mean-reverting." [NB01 cells 6, 15; NB03 cell 2]
Severity: **MINOR**

**m5. NB02 bullet 1 — 'tightest spread does NOT imply easier to trade' stated as finding
without evidence.**
NB02: "Tightest spread does NOT imply easier to trade — it means NPC quotes are already
close." This editorial interpretation is added as a data finding. It may be true but is a
strategy judgment, not an EDA result. The finding should state only the spread measurement and
flag corroboration needs. [NB02 cell 3]
Severity: **MINOR**

**m6. NB07 bullet 10 — ROBOT task-complexity ordinal has wrong sign; this may be an encoding
error, not a data signal.**
NB07: "ROBOT task-complexity ordinal yields R²=0.115 with Spearman ρ=−0.400 — reversed from
encoding." With n=5 and a researcher-constructed ordinal whose correct direction is uncertain,
a reversed sign has p = 1/120 × 2 = 0.017 by chance (two-tailed, assuming any ordering equally
likely). The finding does not distinguish between "data contradicts encoding" and "encoding was
wrong." It should be flagged as ambiguous rather than interpreted as signal about the data
generating process. [NB07 cell 18]
Severity: **MINOR**

**m7. NB03 bullet 6 — "UV_VISOR_RED 2/3 days stationary" - verified correct but stated
without noting borderline p-values.**
Verified: day 2 ADF p=0.035, day 4 p=0.037 — both at the 5% margin; day 3 p=0.460. At the
standard 5% level this is exactly on the edge; with Bonferroni correction for 50×3=150 ADF
tests, the threshold would be 0.05/150=0.00033, and none of the "occasional stationary" days
would qualify. [NB03 cell 2]
Severity: **MINOR**

---

## Sanity check
- All claims cite notebook bullet or cell. ✓
- No strategy / PnL / rule proposals. ✓
- No edits to forbidden files. ✓
- No new files outside assigned location. ✓
- 30 bullets or fewer: 6 BLOCKING + 8 MODERATE + 7 MINOR = 21 bullets total. ✓
