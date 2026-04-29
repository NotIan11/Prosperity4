# Critique B — Cross-Cutting Contradictions

> Critic B | Stage 2 | All contradictions resolved by re-deriving from raw CSV data.
> All numerical evidence re-computed via one-shot scripts unless noted otherwise.
> No strategy proposals. No PnL claims.

---

## Contradiction 1 — MICROCHIP: anomalous trade-signature (NB04) vs no price-level determinism (NB09)

**Stated tension.** NB04 (bullet 2–4) flags MICROCHIP as one of three distinct NPC generators: 569 trades vs 733
for standard categories, qty capped at 3, independent timestamp set, buy-side net flow imbalance +0.072 (bullet 9).
NB09 (bullet 14) explicitly states: "MICROCHIP shows no special structure beyond baseline.
5-sum CV = 3.0%, zero-return rate = 2.1–2.8% (baseline), no grid discreteness, no FFT significance."

**Resolution: BOTH are correct. These are complementary claims, not contradictions.**

Verification:
- MICROCHIP zero-return rates (days 2/3/4, per product): 0.018–0.033 — consistent with baseline ~2%.
  Compare to ROBOT_IRONING (0.407/0.383/0.422) and OXYGEN_SHAKE_EVENING_BREATH (0.440/0.372/0.363),
  which are the true step-function products.
- MICROCHIP non-zero returns show no grid discretization: fraction on 10-unit grid is only 0.035–0.058
  (i.e., roughly what you'd expect by chance for integer-priced assets, not a structural grid).
- MICROCHIP basket sum (5-product, timestamp-aligned) CV: 1.56% / 1.60% / 1.73% on days 2/3/4 —
  roughly 250× noisier than the PEBBLES basket (CV = 0.006%).

The trade-count anomaly (NB04) is a generation-process feature (separate NPC bot schedule, different qty
distribution) that does NOT map to any detectable price-level structure. The two notebooks investigate
different aspects of the same products.

**NB09 bullet 14's framing is slightly misleading** — it says "no special structure" as if this resolves
the AGENT_BRIEF flag. The correct framing is: the trade-count anomaly is real (NB04 verified), but it
does not manifest as a hardcoded FV, grid discretization, or periodic step in price. The mechanism behind
the trade-count difference (whatever NPC bot or schedule difference it reflects) does not constrain prices.

**Severity: MINOR.** The findings are not contradictory; NB09 should clarify scope of "no special structure."

---

## Contradiction 2 — PEBBLES sum=50000 (NB09) vs PEBBLES_L/XL anti-corr (NB05) vs PEBBLES PC1/PC2 dominance (NB06)

**Stated tension.** NB09 (bullet 1–2) reports a hard basket sum = 50,000 ± 2.8 std. NB05 (bullet 4) reports
"PEBBLES_L/PEBBLES_XL ret_corr = −0.4932" as the key PEBBLES signal. NB06 (bullets 1, 2, 12) reports
PEBBLES dominates PC1 (12.70%) and PC2 (5.80%), with XL loading +0.784 on PC1, XS loading −0.468 on PC1.

**Resolution: All three claims are independently verified and reinforce each other.**

Verification of NB09 basket constraint:
- Day 2: exact hits = 39.6%, within ±0.5 = 88.8%, within ±1.5 = 97.1%, unique sum values = 17.
- Day 3: 41.2%, 89.3%, 97.2%, 18 unique values.
- Day 4: 41.1%, 88.6%, 97.1%, 17 unique values.
- The basket constraint is a confirmed structural fact, replicable across all 3 days.

Verification of NB05's anti-corr claim — NB05 is UNDER-REPORTING:
- Pooled return correlations for ALL PEBBLES pairs: XS/XL = −0.497, S/XL = −0.496, M/XL = −0.511,
  L/XL = −0.500. All four pairs involving XL are approximately equal in magnitude.
- NB05 bullet 4 highlighted only the L/XL pair and said "every other category has returns corr in
  [−0.10, +0.10]" — correct for cross-category, but NB05 itself missed that it's ALL four
  XL-inclusive pairs, not just L/XL.
- Per-day corr for XL/XS: day 2 = −0.495, day 3 = −0.495, day 4 = −0.503. Stable.

Verification of NB06 PCA:
- Pooled unstandardized log-return PCA reproduced exactly: PC1 = 12.70%, top loading = PEBBLES_XL
  (+0.784), PC2 = 5.80%, top loading = PEBBLES_XS (+0.816). PC3 = 4.28%, top = ROBOT_DISHES (+0.995).

Mechanistic connection: the basket sum constraint (NB09) mathematically REQUIRES negative
return correlations among the 5 products. If XL goes up, the sum can only stay at 50,000 if at least
one other product goes down. XL has the highest weight in PC1 (+0.784); the rest load negatively.
This is the same signal observed three different ways: the findings are corroborative, not duplicative.

**Additional note — NB05 bullet 14 is FACTUALLY WRONG (see Contradiction 5 below for the full call).**
NB05's median-based summary (bullet 5: median = 0.021 for SNACKPACK) correctly reports the median but
erroneously claims no high-corr pairs exist outside PEBBLES_L/XL.

**Severity: MINOR for the PEBBLES-specific part. The three findings reinforce each other.
NB05's under-reporting of the 4 symmetric XL-inclusive pairs is a gap, not a contradiction.
See Contradiction 5 for the BLOCKING issue in NB05 Bullet 14.**

---

## Contradiction 3 — ROBOT_IRONING + OXYGEN_SHAKE_EVENING_BREATH: step-function (NB09) vs mean-reversion (NB03) vs spread-pinned (NB02)

**Stated tension.** NB09 (bullets 4–5) says both products have a discretized step-function generator:
40.4% and 39.2% zero returns respectively, with ~97% of non-zero returns on the ±10 grid.
NB03 (bullets 2–3) says both have consistent negative AR(1) on returns (ROBOT_IRONING ρ₁ = −0.117,
OXYGEN_SHAKE_EVENING_BREATH ρ₁ = −0.112) — labeling them "probably tradable" by mean-reversion.
NB02 (bullet 3, 9) says OXYGEN_SHAKE_EVENING_BREATH has 93.4% of ticks at modal spread = 12, and
ROBOT_IRONING has 40–96.5% at modal spread = 6 (varying by day).

**Resolution: All three observations are correct and describe the same underlying process.**

Verification:
- ROBOT_IRONING per day: zero_ret = 0.407/0.383/0.422; on_10grid = 0.898/0.893/0.882; AR(1) = −0.162/−0.077/−0.114.
- OXYGEN_SHAKE_EVENING_BREATH: zero_ret = 0.440/0.372/0.363; on_10grid = 0.892/0.895/0.893; AR(1) = −0.174/−0.094/−0.077.
- Both have modal spread pinned: ROBOT_IRONING spread = 6 (50–96.5% at modal across days),
  OXYGEN_SHAKE_EVENING_BREATH spread = 12 (87–96.6% at modal across days).
- ADF on levels: mostly fail to reject unit root (ROBOT_IRONING p = 0.428, 0.989, 0.376 on days 2/3/4;
  OXYGEN_SHAKE day 2 p=0.755, day 3 p=0.045, day 4 p=0.262). Both are best treated as random walks in levels.

**Critical mechanistic finding from reversal analysis:**
- ROBOT_IRONING: consecutive non-zero returns show 100.0% reversal rate (3,264/3,264 reversals on day 2,
  3,353/3,353 on day 3, 3,232/3,232 on day 4). Every single non-zero move is immediately reversed.
- OXYGEN_SHAKE_EVENING_BREATH: 54.0%/55.0%/53.5% reversal rate on days 2/3/4 — much weaker.

This is decisive: ROBOT_IRONING's negative AR(1) = −0.117 is 100% explained by tick-level bid-ask
bounce. The step size (+10 or −10) exceeds the spread width (modal spread = 6), so after a +10 hop,
the mid overshoots and the next non-zero move is virtually always −10. This is pure microstructure
artifact, NOT mean-reversion in any economic sense.

OXYGEN_SHAKE_EVENING_BREATH has only 54% reversals, suggesting a weaker but partially microstructural AR(1).

NB03 (bullet 14) acknowledges this interpretation: "The negative AR(1) likely reflects a bid-ask bounce
at the tick level — a well-known microstructure artifact. Notebook 02 must corroborate or contradict
this before any exploitability call." The data now confirms: for ROBOT_IRONING, it IS entirely bounce.
For OXYGEN_SHAKE_EVENING_BREATH, the bounce is partial.

The three labels (step-function / mean-reversion / spread-pinned) are all facets of the same phenomenon:
- Step-function (NB09): correct, the generator outputs ±10 hops.
- Spread-pinned (NB02): correct, the spread is narrow and constant.
- Mean-reversion (NB03): for ROBOT_IRONING, this is 100% microstructure bounce; the triage call of
  "probably tradable" is likely OVERSTATED unless the reversal is itself predictable.
- For OXYGEN_SHAKE_EVENING_BREATH, the picture is less clean.

**NB03's triage call of "probably tradable" for ROBOT_IRONING may be inflated by the bounce artifact.**

**Severity: MODERATE.** The three claims are consistent observations of the same process; no contradiction
on the facts. But NB03's exploitability framing may be misleading for ROBOT_IRONING specifically
(bounce-driven AR(1) is not freely exploitable without hitting the spread every trade).

---

## Contradiction 4 — SNACKPACK CHOCOLATE/VANILLA mirror corr −0.97 (NB09) vs NB05 pooled cointegration: does the pair hold daily?

**Stated tension.** NB09 (bullet 7) says CHOC/VAN corr = −0.974 (day 2), −0.980 (day 3), −0.962 (day 4)
and their sum drifts across days (20,025 → 19,927 → 19,870; multi-day ADF p = 0.40 — NOT stationary).
NB05 (bullet 3, 12) says SNACKPACK has 3 cointegrated pairs (p<0.05) on the pooled series, but zero
pairs cointegrated on ALL 3 individual days. NB05 says "no pair was cointegrated on all 3 individual days."

**Resolution: No contradiction. Claims are consistent and mutually corroborating.**

Verification:
- Per-day level corr: day 2 = −0.9737, day 3 = −0.9801, day 4 = −0.9616. (Strong negative daily.)
- Per-day return corr: day 2 = −0.9200, day 3 = −0.9154, day 4 = −0.9123. (Also very strong daily.)
- Per-day sum mean: 20,025 / 19,927 / 19,870. Sum drifts downward ~155 units across 3 days.
- Per-day sum ADF p-values: 0.271 / 0.058 / 0.688. No day individually stationary at p<0.05.
- Per-day Engle-Granger cointegration p: day 2 = 0.118, day 3 = 0.400, day 4 = 0.959. NOT
  cointegrated on any individual day.

The pooled 3-day cointegration that NB05 reports (3 pairs at p<0.05) arises from the highly correlated
within-day movement; the pooled series is long enough to push the test statistic past the threshold
even though the sum drifts day-over-day. NB05 bullet 12 correctly flags this as possibly spurious.
NB09 bullet 7's framing (sum ADF = 0.40, not stationary) is also correct.

PISTACHIO/RASPBERRY also verified: per-day return corr = −0.834/−0.830/−0.829. Strong and stable.
PISTACHIO/STRAWBERRY return corr = +0.913 (pooled), which implies those two co-move positively.
The SNACKPACK structure is a 2×2 cluster: {CHOC, VAN} anti-correlated, {RASP, PISTACHIO, STRAW} 
internally split with PISTACHIO/STRAW co-moving and RASP anti-correlated with both.

**Severity: MINOR.** No factual contradiction. NB09's "corr = −0.97" refers to level corr;
the return corr is equally strong (−0.92). The pair does NOT hold as a cointegrated pair on
individual days, consistent with both notebooks.

---

## Contradiction 5 — NB05 Bullet 14: PEBBLES_L/XL claimed to be the "only" high-ret-corr pair — BLOCKING ERROR

**Stated contradiction.** NB05 (bullet 14): "All lag-0 returns correlations (CCF at lag=0) are < 0.013
in absolute value except PEBBLES_L/XL (−0.4932). This is the only pair with a practically meaningful
contemporaneous return co-movement signal."

**Resolution: NB05 Bullet 14 is factually wrong.**

Verification — ALL pairs across all 50 products with |pooled_ret_corr| > 0.10:

| Pair | Pooled ret corr |
|---|---|
| SNACKPACK_RASPBERRY / SNACKPACK_STRAWBERRY | −0.9238 |
| SNACKPACK_CHOCOLATE / SNACKPACK_VANILLA | −0.9159 |
| SNACKPACK_PISTACHIO / SNACKPACK_STRAWBERRY | +0.9133 |
| SNACKPACK_RASPBERRY / SNACKPACK_PISTACHIO | −0.8309 |
| PEBBLES_M / PEBBLES_XL | −0.5115 |
| PEBBLES_L / PEBBLES_XL | −0.5000 |
| PEBBLES_XS / PEBBLES_XL | −0.4973 |
| PEBBLES_S / PEBBLES_XL | −0.4956 |

8 pairs exceed |0.10|. Only 4 PEBBLES pairs and 4 SNACKPACK pairs — NB05 missed all of the SNACKPACK ones.
NB05's median for SNACKPACK = 0.021 (correct, because 6 of 10 SNACKPACK pairs are near zero), but the
four extreme pairs (3 anti-correlated around −0.83 to −0.92, one co-correlated at +0.91) are completely
absent from NB05's bullet 14.

NB05 Bullet 5 separately reports "Median returns corr per category: SNACKPACK=0.021" — this is technically
correct but by using the median, NB05 concealed the bimodal distribution. The 10 SNACKPACK pairs split as:
{6 near-zero (0.014–0.040)} and {4 extreme (−0.924 to +0.913)}.

NB06 bullet 5 correctly reports: "SNACKPACK within-category return corr: mean = −0.160, range = −0.923
to +0.913." NB06's range reflects the true structure. However NB06 does not enumerate the 4 extreme
pairs explicitly (uses range, not a list).

**Root cause of NB05's error:** NB05 appears to have computed CCF at lag=0 on the pooled dataset and
may have had a sorting/display bug that showed only the top pair rather than all pairs above a threshold.
Alternatively, NB05 computed lag-0 CCF differently from Pearson return correlation. The return corr
computed from raw price differences, log-differences, and second-differences all yield −0.83 to −0.92 
for the four extreme SNACKPACK pairs — this is not methodology-sensitive.

**Impact:** NB05 Bullet 14 must be rejected entirely. The correct statement is: "8 pairs across 50 products
have |pooled_ret_corr| > 0.1 — 4 PEBBLES XL-inclusive pairs (−0.497 to −0.511) and 4 SNACKPACK pairs
(−0.924 to +0.913)." Both NB09 and NB06 are correct about SNACKPACK's strong internal structure.

**Severity: BLOCKING.** NB05 Bullet 14 propagates a false claim. Any synthesis relying on
"PEBBLES_L/XL is the only meaningful return-corr pair" will undercount SNACKPACK's structural signal.

---

## Contradiction 6 — ROBOT_DISHES: PC3 singleton (NB06) vs distributional outlier (NB01) — same cause?

**Stated tension.** NB06 (bullet 3, 13) says ROBOT_DISHES is a singleton factor on PC3 (4.28% variance,
loading +0.995). NB01 (bullet 7) says ROBOT_DISHES has the highest avg mode prevalence (5.63%) with FV
candidate 10,600. The question is whether these two observations reflect the same underlying cause.

**Resolution: They share a common cause (day-4 structural regime shift) but describe different effects.
Not a contradiction; partial corroboration of independent phenomena.**

Verification:
- Pooled unstandardized log-return PCA reproduced NB06 exactly: PC3 = 4.28%, ROBOT_DISHES loading =
  +0.9950, all other products < 0.07. This is confirmed.
- However, per-day PCA tells a very different story: on days 2 and 3, ROBOT_DISHES loading on PC3 is
  0.017 and −0.002 — essentially zero. On day 4, ROBOT_DISHES loading on PC3 = +0.019, also near zero.
  The per-day PC3 is dominated by SNACKPACK_CHOCOLATE/VANILLA (loadings +0.70/+0.70) each day.
- The root cause of the pooled PC3 anomaly: ROBOT_DISHES has day-4 log-return variance = 6.7×10⁻⁶
  (days 2+3 variance = 1.0×10⁻⁶), a 6.7× spike. The unstandardized PCA is dominated by products with
  the highest raw variance. ROBOT_DISHES' day-4 variance makes it the 4th-highest variance product
  in the pooled matrix (after PEBBLES_XL, PEBBLES_XS, PEBBLES_S).
- Day-4 structure: ROBOT_DISHES price oscillates between ~10,200 and 10,300 in ticks 1,150–1,200
  (600+ consecutive ticks of rapid ±100 steps), driving the variance spike. This is the same
  "one-day structural shift" NB08 identified (bullet on ROBOT_DISHES AR(1) = −0.289 on day 4 only,
  sq_acf_lag1 = 0.235, step pattern in ticks 145,000–148,300).

NB01's distributional observation (5.63% mode prevalence at 10,600 pooled across all 3 days) is consistent:
day 4 has 16.1% of ticks at 10,600 (driven by the pinning at the end of the day-4 regime shift), while
days 2 and 3 each contribute only ~0.3% prevalence at that level.

**Key finding for synthesis:** NB06's PC3 singleton is an artifact of using unstandardized log-returns.
When standardized returns are used, ROBOT_DISHES has no singleton PC — PC3 belongs to SNACKPACK_CHOCOLATE/
VANILLA instead (+0.704/+0.703 loadings). **The ROBOT_DISHES PC3 singleton in NB06 is a methodology-
dependent artifact of day-4 variance inflation, not a stable structural feature.**

**Severity: MODERATE.** NB06's PC3 singleton claim is misleading without the per-day caveat. The synthesis
must note that ROBOT_DISHES' factor isolation is driven entirely by one anomalous day and disappears when
returns are standardized. The distributional finding in NB01 (mode prevalence) is valid but driven by the
same transient day-4 effect.

---

## Contradiction 7 — "8/10 categories noise in returns" (NB06) vs "all 5 in a category share trade timestamps" (NB04): does shared trade structure imply correlated prices?

**Stated tension.** NB04 (bullets 5–7, 14) says all 5 products in every category trade at 100% identical
timestamps with identical quantities on every tick. NB06 (bullets 6–7) says 8 of 10 categories have near-
zero within-category return correlations (range −0.016 to +0.007), consistent with 40 independent random
walks.

**Resolution: No contradiction. Shared trade timing does not imply correlated price dynamics.**

Verification of return independence: GALAXY_SOUNDS pairwise return correlations (all days combined):
All 10 pairs are in the range [−0.015, +0.027] — consistent with NB06's claim of near-zero.

The mechanistic explanation: in IMC's NPC-bot architecture, the trade-timestamp synchronization (NB04)
reflects a shared "generation clock" for when trades occur, but each product's price is set
independently by its own pricing function. The fact that all 5 GALAXY_SOUNDS products trade at the
same timestamps means the NPC bot "fires" for the whole category simultaneously, but the price
it quotes for each product is independently determined. Shared timing ≠ shared price movement.

This is further supported by NB02 (bullet 14): within-category book structure is cloned (identical
imbalance statistics, depth asymmetry), yet NB06 shows returns are uncorrelated. The NPC bot template
produces structurally identical order book shapes across category members but prices them independently.

The two notebooks (NB04 and NB06) are probing different layers of the same NPC generation model:
- NB04 observes the trade-scheduling layer (shared clock, shared qty).
- NB06 observes the price-setting layer (independent price functions).

These claims are independently corroborative about structure, not contradictory.

**Severity: MINOR.** No factual contradiction. Synthesis should note that shared trade timestamps
provide zero cross-product predictability in return space, but the shared scheduling structure is
itself a useful architectural fact.

---

## Summary table

| # | Products | Notebooks | Verdict | Severity |
|---|---|---|---|---|
| 1 | MICROCHIP | NB04 vs NB09 | Complementary, not contradictory | MINOR |
| 2 | PEBBLES | NB09 + NB05 + NB06 | All correct; NB05 under-reports 4-pair structure | MINOR |
| 3 | ROBOT_IRONING, OXYGEN_SHAKE_EVENING_BREATH | NB09 vs NB03 vs NB02 | All correct; ROBOT_IRONING AR(1) = 100% bounce artifact | MODERATE |
| 4 | SNACKPACK CHOC/VAN | NB09 vs NB05 | Consistent; daily anti-corr holds but sum drifts, no daily cointegration | MINOR |
| 5 | SNACKPACK (all pairs) | NB05 vs NB06/NB09 | NB05 Bullet 14 factually wrong; 4 strong SNACKPACK pairs missed | **BLOCKING** |
| 6 | ROBOT_DISHES | NB06 vs NB01 | Same day-4 cause; NB06 PC3 singleton is artifact of unstandardized PCA | MODERATE |
| 7 | 8 standard categories | NB04 vs NB06 | No contradiction; trade timing ≠ price co-movement | MINOR |

---

## Sanity check

- [x] All claims cite a notebook bullet or a specific number from re-derived computation.
- [x] No strategy / PnL / rule proposals.
- [x] No edits to forbidden files.
- [x] No new files outside the assigned location.
- [x] AGENT_BRIEF checklist confirmed: all 6 specific contradictions investigated.
