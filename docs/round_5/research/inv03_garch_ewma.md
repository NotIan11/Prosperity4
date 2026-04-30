# INV-03: GARCH(1,1) vs EWMA Vol — Dynamic Quote Width Assessment

**Data**: `data/round_5/prices/prices_round_5_day_{2,3,4}.csv`
**Fit**: in-sample day 2 (10,000 ticks/product), validation days 3+4 (20,000 ticks)
**Method**: hand-coded, stdlib only. GARCH via grid search; EWMA λ=0.94 (RiskMetrics).

---

## 1. GARCH(1,1) Fit Results

σ²_t = ω + α·r²_{t-1} + β·σ²_{t-1}, fitted per product on day 2.
Persistence = α + β. Grid: α∈[0.01,0.50], β∈[0.10,0.98], ω = σ̄²(1−α−β).

| Product | ω | α | β | α+β | GARCH IS LL | EWMA IS LL | LL diff |
|---|---|---|---|---|---|---|---|
| MICROCHIP_TRIANGLE | 1.06e-08 | 0.042 | 0.954 | **0.995** | 50,914 | 51,603 | −689 |
| MICROCHIP_RECTANGLE | 2.23e-08 | 0.020 | 0.970 | **0.990** | 50,896 | 51,564 | −668 |
| OXYGEN_SHAKE_EVENING_BREATH | 1.71e-08 | 0.020 | 0.970 | **0.990** | 52,900 | 54,136 | −1,236 |
| PEBBLES_L | 2.34e-08 | 0.010 | 0.980 | **0.990** | 50,634 | 51,044 | −410 |
| PEBBLES_S/M/XS | ~2-3e-08 | 0.010 | 0.970–0.980 | **0.980–0.990** | ~49-51k | ~50-51k | ~−420 |
| ROBOT_IRONING | 1.68e-08 | 0.020 | 0.970 | **0.990** | 52,950 | 53,947 | −997 |
| Most others | ~1e-07 | 0.010 | 0.05–0.90 | 0.06–0.87 | 54-62k | 55-62k | −380–−430 |

**Key finding**: GARCH grid search hits boundary values (α=0.01, β near upper bound). This indicates the grid optimum is at the constraint edge — not a well-identified interior maximum. The true MLE likely has even higher β but the grid can't resolve it. GARCH LL is **consistently worse** than EWMA LL (negative LL-diff) for every single product, both in-sample and on validation days 3+4.

---

## 2. Validation Results (Days 3+4)

EWMA beats GARCH on log-likelihood on every product in validation:

| Product | GARCH val LL | EWMA val LL | Diff (EWMA wins by) |
|---|---|---|---|
| MICROCHIP_TRIANGLE | 101,603 | 102,626 | 1,023 |
| MICROCHIP_RECTANGLE | 101,545 | 102,420 | 875 |
| OXYGEN_SHAKE_EVENING_BREATH | 107,809 | 108,750 | 941 |
| PEBBLES_L | 102,178 | 103,051 | 873 |
| ROBOT_IRONING | 107,553 | 108,470 | 917 |
| All 50 products | — | — | EWMA wins all 50 |

One anomaly: ROBOT_DISHES has a val LL diff of −19,601 (GARCH much worse) — the grid found a degenerate parameter set for that product. Confirms GARCH overfits or misfits with coarse grid.

---

## 3. GARCH vs EWMA Fit Quality

**EWMA dominates GARCH on every metric here.** Reasons:

1. GARCH grid search (no scipy, no gradient) is coarse. The optimum sits on constraint boundaries (α=0.01 or β=0.97), meaning the grid cannot find a strictly interior solution — the LL surface isn't well-curved in this region with 10k ticks.
2. For highly persistent processes (α+β≈0.99), GARCH and EWMA are near-equivalent. EWMA is effectively GARCH(1,1) with α+β=1 and ω=0. The EWMA parameterization fits the data distribution of R5 products more naturally.
3. The persistent products (MICROCHIP, PEBBLES, ROBOT_IRONING) all have high β in GARCH — i.e., they converge to EWMA-like behavior.

**Conclusion**: EWMA (λ=0.94) is the correct model here. No need for GARCH in R5.

---

## 4. Vol Clustering Strength

Squared-return autocorrelation (AC(r²)) is the canonical vol clustering test:

| Product | AC(1) r² | AC(5) r² | AC(10) r² | AC(1) r (directional) |
|---|---|---|---|---|
| OXYGEN_SHAKE_EVENING_BREATH | **0.259** | 0.048 | 0.048 | −0.163 |
| ROBOT_IRONING | **0.237** | 0.149 | −0.023 | −0.156 |
| MICROCHIP_RECTANGLE | 0.011 | 0.004 | 0.019 | −0.003 |
| MICROCHIP_TRIANGLE | 0.011 | −0.002 | 0.011 | −0.000 |
| PEBBLES_L | 0.003 | 0.001 | −0.001 | 0.006 |

**Genuine vol clustering (AC(r²) >> 0):**
- OXYGEN_SHAKE_EVENING_BREATH: AC(1)=0.26, strong vol clustering. Negative AC(1) on raw returns (−0.16) = mean-reversion with vol bursts.
- ROBOT_IRONING: AC(1)=0.24, AC(5)=0.15, persistent clustering. Same pattern.

**No meaningful vol clustering:**
- MICROCHIP_{TRIANGLE,RECTANGLE,OVAL,SQUARE}: AC(r²) ≈ 0.01 — comparable to low-clustering products. The high GARCH persistence is an artifact of the grid, not genuine ARCH effects.
- PEBBLES family: AC(r²) ≈ 0.003 — essentially no clustering.
- All other products: AC(r²) ≈ 0.01–0.03 — noise level.

---

## 5. Implementation Cost Assessment

| Model | Compute per tick | MLE fit | Shippable? |
|---|---|---|---|
| EWMA | O(1): one multiply + one add | None — λ=0.94 fixed | **Yes** |
| GARCH(1,1) | O(1) runtime, but requires MLE fit | Nonlinear optimization (no scipy on platform) | No — grid fit is impractical at runtime |

GARCH fit at submission time would require hand-coded optimization over ~400 grid points × 50 products = 20,000 LL evaluations over 10,000 returns each = 200M operations at tick 0. Too slow.

**EWMA is the only shippable dynamic vol model.**

---

## 6. High-Vol Period Fills and Vol Distribution

### Top-5 products by GARCH persistence

| Product | % ticks > 1.5×median σ | Mean |r| high-vol | Mean |r| low-vol | Ratio |
|---|---|---|---|---|---|
| MICROCHIP_TRIANGLE | 4.6% | 0.001917 | 0.001152 | 1.66× |
| MICROCHIP_RECTANGLE | 4.3% | 0.001969 | 0.001159 | 1.70× |
| OXYGEN_SHAKE_EVENING_BREATH | 6.7% | 0.001167 | 0.000768 | 1.52× |
| PEBBLES_L | 7.0% | 0.001850 | 0.001133 | 1.63× |
| ROBOT_IRONING | 6.2% | 0.001265 | 0.000770 | 1.64× |

High-vol periods are 5–7% of ticks but adverse moves are 1.5–1.7× larger. For a static quote, this means ~6% of ticks carry ~65% more adverse selection risk.

### EWMA sigma scaling (mid-price ≈ 10,000)

| Product | σ p50 (pts) | σ p90 (pts) | σ p99 (pts) | Dynamic width k=2 at p99 |
|---|---|---|---|---|
| MICROCHIP_TRIANGLE | 14.7 | 17.2 | 19.6 | 39.2 |
| MICROCHIP_RECTANGLE | 14.8 | 17.3 | 19.5 | 39.0 |
| OXYGEN_SHAKE_EVENING_BREATH | 10.9 | 12.9 | 28.1 | 56.2 |
| PEBBLES_L | 14.6 | 17.4 | 20.0 | 40.0 |
| ROBOT_IRONING | 11.0 | 13.0 | 26.9 | 53.8 |

Note OXYGEN_SHAKE and ROBOT_IRONING have fat p99 tails (28 and 27 pts) vs their p50 (11 pts) — 2.5× spike. MICROCHIP/PEBBLES are tighter (p99 only 1.33× p50).

---

## 7. Recommendation

### Products that should use dynamic skew = k·σ_EWMA in v9

**Tier 1 — Strong signal, implement:**
- **OXYGEN_SHAKE_EVENING_BREATH**: AC(r²)=0.26, p99 σ=28 pts (2.6× p50). Static quote gets badly picked off during vol spikes. Dynamic width would widen significantly (×2.6) during bursts, reducing adverse selection.
- **ROBOT_IRONING**: AC(r²)=0.24, p99 σ=27 pts (2.5× p50). Same profile. Same recommendation.

Formula: `half_spread = k * math.sqrt(ewma_sigma2)` where σ_EWMA updates per tick as `σ²_t = 0.94·σ²_{t-1} + 0.06·r²_{t-1}`.

Suggested k: start with k=1.5 so median half-spread ≈ 1.5×σ (≈16 pts for OXYGEN_SHAKE), widening to ~42 pts at p99 spike. This matches the ~1.5× adverse-move ratio during high-vol.

**Tier 2 — Marginal, low priority:**
- MICROCHIP family (TRIANGLE, RECTANGLE): persistence is high but AC(r²)≈0.01 — no true vol clustering, just globally high vol. Static config tuned to their unconditional σ is adequate.
- PEBBLES family: AC(r²)≈0.003, effectively i.i.d. vol. No benefit.

**Do not use dynamic vol for:**
- SNACKPACK family, PANEL, TRANSLATOR, SLEEP_POD, UV_VISOR, GALAXY_SOUNDS, ROBOT_{DISHES,LAUNDRY,MOPPING,VACUUMING}: all show AC(r²)≈0.01–0.03 (noise level), no vol clustering.

### Implementation note (stateful warmup)

Per CLAUDE.md pitfall: "pure live-derived parameters are noisy early." Warm-start σ² at the unconditional variance (computed from BT days 2–4) rather than tick-0 returns. Blend: use hardcoded σ²_init for first ~200 ticks, then let EWMA take over. This avoids the R3 v16 failure mode.

```python
# Stateful EWMA vol — store in traderData
LAM = 0.94
EWMA_INIT = {
    'OXYGEN_SHAKE_EVENING_BREATH': 1.307e-6,  # unc_var from day2 fit
    'ROBOT_IRONING': 1.298e-6,
}
EWMA_K = 1.5  # half_spread = K * sqrt(sigma2)
EWMA_WARMUP = 200  # ticks before EWMA fully trusted

def update_ewma(sigma2, ret, tick_n, product):
    unc = EWMA_INIT.get(product, 1e-6)
    if tick_n < EWMA_WARMUP:
        w = tick_n / EWMA_WARMUP  # ramp in
        sigma2 = w * (LAM * sigma2 + (1-LAM) * ret**2) + (1-w) * unc
    else:
        sigma2 = LAM * sigma2 + (1-LAM) * ret**2
    return sigma2
```

### Expected gain

High-vol periods (≈6% of ticks) carry 1.5–1.7× mean adverse move. For an MM strategy, this directly translates to adverse selection. Widening by ~1.5× during these periods reduces fill rate but cuts adverse fill ratio. Net: moderate gain on OXYGEN_SHAKE and ROBOT_IRONING; negligible elsewhere.

**Caveat**: the platform drops ~20% of NPC orders randomly per submission. Vol-adaptive width reduces fill frequency — already-sparse fills getting further reduced by wider quotes may not compensate. Test explicitly in BT before shipping.
