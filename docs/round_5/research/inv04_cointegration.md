# inv04 — Cointegration Scan: All 1225 Pairs, R5 Days 2–4

> Investigation agent #4. All numbers computed from scratch via stdlib + numpy-free Python
> against `data/round_5/prices/prices_round_5_day_{2,3,4}.csv`.
> No strategy-level PnL predictions. No live-data fitting.

---

## Methodology

- **Return correlation**: first-difference (mid-price changes), per day separately.
- **Cointegration**: Engle-Granger two-step. OLS residuals from `p2 ~ alpha + beta*p1`,
  then ADF (no trend) on residuals. Both directions tested; lower p-value direction used.
- **Day-stable criterion**: |ρ| > 0.5 on all 3 days AND range(|ρ|) ≤ 0.10.
- **Cointegrated on day X**: ADF p < 0.05 on that day's per-day series.
- **Half-life**: OU AR(1) fit on residuals: HL = −ln(2)/ln(φ).
- **ADF p-value**: piecewise linear interpolation from MacKinnon (1994) critical values.

---

## Section 1: Full 1225-Pair Scan Results

### Pairs with mean |return-ρ| > 0.30 across days 2/3/4

Only **8 pairs** passed the 0.30 mean |ρ| threshold. All are within-category SNACKPACK or PEBBLES.
**Zero cross-category pairs** reached |ρ| > 0.15 on 2+ days.

| Pair | Cat | d2_ρ | d3_ρ | d4_ρ | ρ_range | d2 ADF-p | d3 ADF-p | d4 ADF-p | Coint days | Mean HL |
|------|-----|--------|--------|--------|---------|----------|----------|----------|-----------|---------|
| CHOC / VAN | SNACKPACK | −0.920 | −0.915 | −0.912 | 0.008 | **0.002** | **0.004** | 0.168 | 2/3 | 300 |
| PIST / RASP | SNACKPACK | −0.834 | −0.830 | −0.829 | 0.005 | 0.148 | **0.049** | **0.031** | 2/3 | 673 |
| RASP / STRAW | SNACKPACK | −0.932 | −0.922 | −0.918 | 0.014 | 0.269 | **0.010** | 0.245 | 1/3 | 739 |
| PIST / STRAW | SNACKPACK | +0.913 | +0.913 | +0.914 | 0.001 | 0.113 | **0.049** | 0.157 | 1/3 | 727 |
| PEBBLES_M / XL | PEBBLES | −0.511 | −0.514 | −0.516 | 0.012 | 0.196 | 0.242 | 0.128 | 0/3 | 626 |
| PEBBLES_L / XL | PEBBLES | −0.500 | −0.500 | −0.500 | 0.008 | 0.436 | 0.086 | 0.170 | 0/3 | 935 |
| PEBBLES_XL / XS | PEBBLES | −0.497 | −0.497 | −0.497 | 0.008 | 0.195 | 0.302 | 0.209 | 0/3 | 696 |
| PEBBLES_S / XL | PEBBLES | −0.496 | −0.496 | −0.496 | 0.002 | 0.204 | 0.118 | 0.176 | 0/3 | 607 |

**No pair passes the strictest filter (cointegrated on all 3 days).**
Best: CHOC/VAN and PIST/RASP each pass on 2 of 3 days.

### Cross-category search
Exhaustive scan of all 1225 pairs including all 625 cross-category pairs:
- **Zero cross-category pairs** with |ρ| > 0.15 on even 2 of 3 days.
- The 50-product universe effectively decomposes into 10 independent categories.

---

## Section 2: Deep Analysis — Top 5 Candidates

### Candidate 1: CHOC / VAN (SNACKPACK_CHOCOLATE / SNACKPACK_VANILLA)

**Return correlation**: d2=−0.920, d3=−0.915, d4=−0.912. Extremely stable (range 0.008). Best-in-class.

**OLS hedge ratio**: beta varies d2=−1.17, d3=−0.96, d4=−0.95. Approaches −1 (symmetric mirror pair).

**Spread statistics**:
| Day | Spread std | ADF stat | ADF p | Half-life |
|-----|-----------|----------|-------|-----------|
| 2 | 36.0 | −4.12 | **0.004** | 196 |
| 3 | 30.8 | −4.16 | **0.004** | 195 |
| 4 | 47.2 | −2.30 | 0.174 | 533 |

**Day-4 breakdown explained**: Overall day-4 ADF fails (p=0.174), but 2500-tick sub-windows
all pass individually (p=0.009, 0.001, 0.011, 0.036). The sum CHOC+VAN shifts intra-day
(mean shifts: 19871 → 19811 → 19869 → 19929 across quarters), causing the pooled day-4
ADF to fail — not a structural breakdown but a mid-day level shift. Each quarter is
cointegrated; only the full-day stationarity fails.

**Bid-ask spread**: CHOC = 16.7 (half = 8.3), VAN = 16.8 (half = 8.4). Combined 2-leg cost ≈ 17 per
1-for-1 trade on mid-price basis. Entry at |z|>1.5 captures ≈54 gross units of spread per trade.
Net per trade after execution ≈ 54 − 17 = **37 units** (1-for-1 position).

**CHOC+VAN sum**: Drifts consistently downward: d2=20025, d3=19927, d4=19870. Δ per day ≈ −77.
Forecast day 5: ~19813. This drift means the spread mean is a slowly changing quantity —
use rolling mean, not all-day mean, for z-score normalization.

**Z-score simulation** (gross PnL, 1 unit each leg, no spread cost):
| Entry threshold | D2 | D2 trades | D3 | D3 trades | D4 | D4 trades | Total | Win rate |
|----------------|-----|-----------|-----|-----------|-----|-----------|-------|----------|
| \|z\|>1.0 | 534 | 20 | 322 | 14 | 75 | 3 | 930 | 100% |
| \|z\|>1.5 | 370 | 9 | 154 | 5 | 60 | 2 | 584 | 100% |
| \|z\|>2.0 | 201 | 3 | 222 | 5 | 0 | 1 | 423 | 100% |

Day 4 is weak (only 2–3 trades); days 2 and 3 are productive. 100% win rate across all
thresholds reflects stable mean-reversion within each sub-window.

---

### Candidate 2: PIST / RASP (SNACKPACK_PISTACHIO / SNACKPACK_RASPBERRY)

**Return correlation**: d2=−0.834, d3=−0.830, d4=−0.829. Very stable (range 0.005). Anti-correlated Group B pair.

**OLS beta**: highly unstable across days: d2=−0.484, d3=−0.898, d4=−1.307. Beta changes by 2.7× across days.
This is the key risk: the hedge ratio is not stable, meaning the EG residual computed on day 2 parameters
would be miscalibrated on day 4.

**Spread statistics**:
| Day | Spread std | ADF stat | ADF p | Half-life |
|-----|-----------|----------|-------|-----------|
| 2 | 144.5 | −2.12 | 0.230 | 769 |
| 3 | 91.5 | −2.87 | **0.049** | 445 |
| 4 | 79.1 | −3.06 | **0.031** | 398 |

Day 2 is NOT cointegrated. Days 3–4 improve significantly with HL trending down from 769→398.
This suggests the pair becomes more mean-reverting over the round, not less.

**Z-score simulation** (1 unit each leg):
| Entry threshold | D2 | D3 | D4 | Total | Win rate |
|----------------|-----|-----|-----|-------|----------|
| \|z\|>1.0 | 760 | 631 | 661 | 2052 | 100% |
| \|z\|>1.5 | 729 | 580 | 423 | 1732 | 100% |
| \|z\|>2.0 | 251 | 490 | 427 | 1168 | 100% |

Larger gross PnL than CHOC/VAN because spread_std is 2–4× larger.
But execution cost at |z|>1.5 entry: 1.5 × 144 = 216 units gross on day 2 vs 2×8.3 ≈ 17 cost.
Net is strong, but beta instability means the hedge ratio must be re-estimated per day.

---

### Candidate 3: RASP / STRAW (SNACKPACK_RASPBERRY / SNACKPACK_STRAWBERRY)

**Return correlation**: d2=−0.932, d3=−0.922, d4=−0.918. Highest magnitude (STRAW/RASP is the
strongest anti-correlation in the dataset), but cointegrated only on day 3.

**OLS beta**: d2=−1.147, d3=−0.936, d4=−0.719. Very unstable (varies 1.6×).

**Spread statistics**: std = 161 / 72 / 106. High variability across days.
ADF p: 0.269 / 0.010 / 0.245. Only day 3 is cointegrated.

**Z-score simulation**: produces PnL (gross 1204 at |z|>1.0), but the spread instability and
single-day cointegration make this unreliable. Only 2 trades/day at |z|>1.5 thresholds.

**Assessment**: This pair has the largest return correlation but the most unstable spread.
Not recommended as a standalone pair trade.

---

### Candidate 4: PIST / STRAW (SNACKPACK_PISTACHIO / SNACKPACK_STRAWBERRY)

**Return correlation**: d2=+0.913, d3=+0.913, d4=+0.914. Perfectly stable (range 0.001). Positive co-movement.

**OLS beta**: d2=−0.122, d3=+0.646, d4=+0.909. Sign changes between days 2 and 3. This means the hedge
ratio is completely unreliable — day 2 shows no linear relationship, days 3/4 show a positive one.

**Spread statistics**: std = 244 / 136 / 124. Huge spread on day 2 (std=244), converging.
ADF p: 0.113 / 0.049 / 0.157. Only day 3 marginally cointegrated.

**Assessment**: High correlation but the OLS regression is unstable (beta changes sign and magnitude 7×).
This pair co-moves (Group B: STRAW and PIST move together) but their spread drifts freely — they are
not cointegrated in the trading sense. Consistent with critique_C Test 10 finding.

---

### Candidate 5: PEBBLES_L / PEBBLES_XL

**Return correlation**: d2=−0.500, d3=−0.500, d4=−0.500. Artificially stable (mechanical constraint).

**Spread statistics**: std = 1005 / 471 / 773. Huge, variable. Not cointegrated on any day (p > 0.08).

**PEBBLES basket analysis**: The sum constraint XS+S+M+L+XL=50000 is an instantaneous law
(ADF stat ≈ −98, HL ≈ 0.2 ticks per day). However, individual pairs like L/XL are NOT cointegrated
because the constraint distributes the sum across 5 variables simultaneously — knowing XL moves
doesn't tell you which other products absorbed the offset. The basket deviation (50000 − sum) is
perfectly stationary, but pairwise spreads are not.

**Assessment**: PEBBLES pair-trading in the EG sense is not viable. The correct exploitation is
the full 5-product basket (already identified in PEBBLES strategy). PEBBLES_L/XL is not a standalone
cointegrated pair.

---

## Section 3: Sortable Candidate Table

All pairs with mean |ρ| > 0.30, sorted by composite score (n_coint_days desc, mean |ρ| desc):

| Rank | Pair | Category | Cross? | d2_ρ | d3_ρ | d4_ρ | ρ_range | d2 ADF-p | d3 ADF-p | d4 ADF-p | Coint N | HL_d2 | HL_d3 | HL_d4 | Beta stable? |
|------|------|----------|--------|------|------|------|---------|---------|---------|---------|---------|-------|-------|-------|--------------|
| 1 | CHOC/VAN | SNACKPACK | No | −0.920 | −0.915 | −0.912 | 0.008 | **0.002** | **0.004** | 0.168 | **2** | 196 | 195 | 533 | Partial (−1.17→−0.95) |
| 2 | PIST/RASP | SNACKPACK | No | −0.834 | −0.830 | −0.829 | 0.005 | 0.148 | **0.049** | **0.031** | **2** | 769 | 445 | 398 | Poor (−0.48→−1.31) |
| 3 | RASP/STRAW | SNACKPACK | No | −0.932 | −0.922 | −0.918 | 0.014 | 0.269 | **0.010** | 0.245 | 1 | 2630 | 456 | 973 | Poor (−1.15→−0.72) |
| 4 | PIST/STRAW | SNACKPACK | No | +0.913 | +0.913 | +0.914 | 0.001 | 0.113 | **0.049** | 0.157 | 1 | 1012 | 623 | 856 | Very poor (sign flip) |
| 5 | PEB_M/XL | PEBBLES | No | −0.511 | −0.514 | −0.516 | 0.012 | 0.196 | 0.242 | 0.128 | 0 | 626 | — | — | Unstable |
| 6 | PEB_L/XL | PEBBLES | No | −0.500 | −0.500 | −0.500 | 0.008 | 0.436 | 0.086 | 0.170 | 0 | 935 | — | — | Very unstable |
| 7 | PEB_XL/XS | PEBBLES | No | −0.497 | −0.497 | −0.497 | 0.008 | 0.195 | 0.302 | 0.209 | 0 | 696 | — | — | Unstable |
| 8 | PEB_S/XL | PEBBLES | No | −0.496 | −0.496 | −0.496 | 0.002 | 0.204 | 0.118 | 0.176 | 0 | 607 | — | — | Unstable |

**No cross-category pairs.** All candidates within SNACKPACK (4) or PEBBLES (4).

---

## Section 4: Cross-Category Verdict

**Zero cross-category pairs** with |return ρ| > 0.15 on even 2 of 3 days. The full 625
cross-category pair space is consistent with 10 independent random-walk markets. No hidden
cross-category cointegration exists in this dataset.

This is consistent with the competition structure: each category appears to be driven by an
independent NPC pricing process with no coupling to other categories.

---

## Section 5: Within-Category Pairs Beyond SNACKPACK

The only within-category pairs with mean |ρ| > 0.30 outside SNACKPACK are the 4 PEBBLES_XL
anti-correlated pairs. As established:
- They are mechanically anti-correlated via the sum=50000 constraint.
- The constraint is instantaneous (HL=0.2 ticks on the basket).
- Individual pair spreads are non-stationary (ADF p > 0.08 on all days).
- **No PEBBLES pairwise cointegration exists.** The correct PEBBLES play is the full basket.

No other category (ROBOT, MICROCHIP, PANEL, SLEEP_POD, etc.) produces any pair with
|ρ| > 0.15 on multiple days. Confirmed by exhaustive search.

---

## Section 6: Pair-Trading Rules for Top 5 Candidates

### Rule A: CHOC/VAN (Recommended if shipping)

**Rationale**: Best day-stable cointegration (2/3 days), most stable beta (~−1), tightest spread.

**Proposed rule**:
1. Re-estimate OLS beta and alpha daily from the first 500 ticks of the day.
2. Compute rolling 200-tick spread mean and std for z-score normalization.
3. **Entry**: |z| > 1.5. Long CHOC + short VAN when z < −1.5; short CHOC + long VAN when z > 1.5.
4. **Exit**: z crosses back through 0 (or |z| < 0.3 to avoid noise).
5. **Position size**: 1 unit each leg (beta ≈ −1, so symmetric). Max position = 1 long / 1 short.
6. **Stop**: if z > 3.5 in direction of trade (spread diverging), exit immediately (protect vs breakdown).

**Expected gross** per trade (|z|>1.5 entry): ~40–70 spread units. Execution cost: ~17. Net: ~25–55.
**Failure mode**: Day-4 style intra-day level shift causes z-score to misfire; rolling window mean
absorbs this within ~200 ticks. The sub-window ADF results (all pass) show the pair is still
cointegrated in short windows — the 200-tick rolling mean handles the level drift.

### Rule B: PIST/RASP (Secondary — beta instability is the key risk)

**Rationale**: 2/3 days cointegrated, larger spread = more PnL potential, but beta unstable.

**Proposed rule**:
1. Use the returns-based hedge ratio (regress return(RASP) ~ return(PIST)), which is more
   stable than the level-OLS beta.
2. **Entry**: |z| > 2.0 (higher threshold to offset beta estimation error).
3. **Exit**: z crosses through ±0.5.
4. **Position size**: Smaller than CHOC/VAN due to larger spread std. Scale by 0.5.
5. **Stop**: |z| > 4.0 in trade direction.

**Failure mode**: Beta flip (d2=−0.48 vs d4=−1.31) means the hedge ratio may be wrong by 2×.
An under-hedged position on a large spread excursion could lose 200+ units without reverting.
The returns-based hedge reduces but does not eliminate this risk.

### Rule C: RASP/STRAW and PIST/STRAW (Not recommended)

Both pairs have only 1/3 days cointegrated and unstable betas (including sign flip for PIST/STRAW).
These are return-correlated but spread-non-stationary — the anti-/co-correlation is a real
structural feature (2+2+1 architecture) but not exploitable via spread mean-reversion.

### Rule D: PEBBLES pairs (Not recommended as pair trades)

Individual PEBBLES pairs are not cointegrated. The basket is the correct vehicle.

---

## Section 7: Recommendation for v9

### Ship: CHOC/VAN with rolling z-score (Rule A above)

**Verdict**: The CHOC/VAN spread is the only pair with day-stable cointegration (2/3 individual days)
and a near-unit beta (≈−1). The day-4 breakdown is explained by intra-day level shifts, not a
structural failure — 2500-tick sub-windows remain cointegrated throughout day 4. The 200-tick
rolling mean normalization handles this.

**Expected gross PnL at |z|>1.0** (3 days simulated): 930 spread units (1-unit positions).
At position size scaled to position limits, this is viable signal.

**Scale-up caveat**: The gross PnL of 930 is for 1 unit each leg. If position limits allow
5–10 units per product, gross scales proportionally. At 5 units each leg, gross ≈ 4,650.
After execution cost (5 × 17 ≈ 85 per round-trip), net remains substantial.

### Conditional: PIST/RASP as supplemental

Consider adding if position limit budget remains available. Use returns-based hedge, entry |z|>2.0,
smaller size. Gross at |z|>1.0 = 2052 (larger than CHOC/VAN), but execution cost is similar
and beta instability requires conservative sizing.

### Do not ship: RASP/STRAW, PIST/STRAW, PEBBLES pairs

Insufficient evidence of per-day spread stationarity.

---

## Section 8: Failure Mode Analysis

| Failure Mode | Probability | Impact | Mitigation |
|-------------|-------------|--------|------------|
| Beta shifts mid-day (CHOC/VAN) | Seen on day 4 | Moderate: z miscalibrated, fewer trades | Rolling 200-tick mean absorbs drift |
| Cointegration breaks on day 5 | Low (2/3 days held) | Severe: all positions go adverse | Stop at |z|>3.5; size conservatively |
| Spread mean shifts intra-day | Seen on day 4 | Moderate: 0–3 trades vs 14–20 on stable days | Rolling mean normalization |
| Beta instability (PIST/RASP) | High (observed 2.7× range) | Moderate: under-hedge | Returns-based hedge, entry |z|>2.0 |
| 20% order drop (portal randomization) | Always | ~20% PnL variance | Acknowledged; cannot mitigate |
| SNACKPACK architecture changes day 5 | Unknown | Severe: all signals fail | Monitor first 100 ticks before committing |

---

## Key Negative Findings

1. **Zero cross-category cointegrated pairs** exist in R5. The market is segmented into 10 independent categories.
2. **PEBBLES pairs are not individually cointegrated** despite mechanical anti-correlation. Only the full basket is.
3. **SNACKPACK spread pooled significance is spurious** (CC7 confirmed): per-day ADF fails for all pairs except CHOC/VAN d2/d3 and PIST/RASP d3/d4.
4. **All spreads have HL >> 200 ticks** (CHOC/VAN HL ≈ 196 is barely under the 200-tick threshold on days 2/3). The 200-tick HL filter eliminates all PEBBLES pairs and RASP/STRAW.
5. **No novel pairs discovered beyond the known SNACKPACK 2+2+1 structure**. The investigation confirms the prior EDA triage rather than extending it.
