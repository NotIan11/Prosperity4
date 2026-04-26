# R3 — Cross-product structure (cointegration / lead-lag / PCA)

Source: `notebooks/04_cross_product_eda.py` over `data/round_3/prices_round_3_day_*.csv`.
Plots: `plots/04_leadlag_ccf_top.png`, `04_voucher_coint_heatmap.png`,
`04_pca_scree_loadings.png`, `04_basket_vs_vfe.png`.

## TL;DR

- **HYDROGEL is independent.** Treat as standalone MM book. No cross-asset hedge needed.
- **No exploitable lead-lag.** Every meaningful pair peaks at lag 0; off-zero CCF magnitudes are at noise level (≤0.02).
- **No clean cross-product stat-arb.** Voucher↔voucher "cointegration" is dominated by deep-ITM pairs (mechanical) and dead-strike VEV_5500 (low-variance artifact). No actionable spread trade we'd take from this notebook alone.
- **Factor structure**: PC1 = 60% = single VFE/voucher factor; **PC2 = 10% = HYDROGEL alone** — its own orthogonal axis. Confirms 2 separable trading books.
- **All structure is stable across days 0/1/2** to 2 decimals. Generalisation risk for any signal we did find is low.

## 1. HYDROGEL independence (verdict: confirmed)

| Test | Result |
|---|---|
| Engle-Granger cointegration with each other product | p < 0.0001 for all |
| ADF on HYDROGEL levels | p = 0.0000 → stationary |
| KPSS on HYDROGEL levels | p = 0.01 → reject stationarity |
| 1-tick return correlation with anything | ~0.00 |
| Max \|CCF\| over ±50 lags vs every other product | ≤ 0.020 (noise) |
| Per-day return corr (days 0/1/2) | identical, all ~0.00 |

- (observation) EG cointegration p<0.0001 looks alarming but is **degenerate**: HYDROGEL is already mean-reverting in levels (ADF rejects unit root), so EG residual is trivially stationary. Combined with zero return correlation and zero CCF, no real economic linkage exists.
- (inference) HYDROGEL = pure independent MM target. PC2 confirms it occupies its own dimension.

## 2. Lead-lag (verdict: nothing actionable)

- VFE↔voucher and voucher↔voucher: peak \|corr\| always at **lag 0** (0.66–0.91). CCF symmetric and decaying — pure contemporaneous co-movement.
- HYDROGEL vs everything: peak \|corr\| over ±50 lags ranges 0.01–0.02. Indistinguishable from noise.
- Granger tests on top-correlated pairs (max lag 5) reject H0 in **both directions** with p≈0 — that's Granger picking up persistence in the contemporaneous return process, not directional information.
- (inference) No "this voucher leads VFE by N ticks" signal. Quoting one product off another's stale mid will not produce alpha.

## 3. Voucher cointegration (verdict: limited usefulness)

Engle-Granger p-value matrix (`04_voucher_coint_heatmap.png`):

- **VEV_4000 ↔ VEV_4500: p ≈ 0.000** — deep-ITM, both ~delta-1 on VFE. Cointegrated by construction (both ≈ VFE − K + small extrinsic). Not free alpha — it's the underlying twice.
- **VEV_5500 ↔ everything: p < 0.05.** VEV_5500 is near-dead (very low variance like VEV_6000/6500). The "cointegration" is a low-variance artifact. Treat with suspicion.
- 4500–5400 belly strikes: pairwise p ≈ 0.10–0.89 — **not cointegrated** in levels. Each strike has its own idiosyncratic component that the voucher-chain agent should model via IV smile.
- (recommendation) Defer voucher-vs-voucher RV trades to the voucher chain agent who has BS / IV machinery. Only obvious candidate from raw-price cointegration is **VEV_4000 / VEV_4500 spread = strike-difference parity** (trade if it deviates from the constant 500).

## 4. Basket vs underlying

- Delta-weighted basket Σ(δᵢ·Vᵢ) at σ=0.15: mean ≈ 2489 vs VFE mean ≈ 5250.
- Spread = basket − VFE has mean −2761, std 62, ADF p = 0.000 (stationary).
- (observation) Mean is intrinsic-value of the deep strikes; the construction is not a synthetic-underlying replication. Stationary spread is mean-reverting but driven by a quantity that has no economic equivalence to VFE.
- (inference) Not directly tradeable. Proper synthetic underlying via put-call parity / strike spread is the voucher-chain agent's job.

## 5. PCA on returns (10 live products)

Explained variance: PC1=60.5%, PC2=10.0%, PC3=8.5%, PC4=6.4%, …, **7 PCs for ≥95%**.

| PC | Loading pattern | Interpretation |
|---|---|---|
| PC1 (60%) | uniform negative on VFE + all vouchers, ≈0 on HYDROGEL | **VFE/voucher level factor** |
| PC2 (10%) | -1.00 on HYDROGEL, ≈0 on everything | **HYDROGEL standalone factor** |
| PC3 (8.5%) | -0.95 on VEV_5500, small on others | wing/skew (mostly the dead-ish 5500) |
| PC4 (6.4%) | -0.80 on VEV_5400, +0.32/+0.38 on 4000/4500 | curvature (deep-ITM vs OTM-wing) |
| PC5–PC10 | per-strike idiosyncratic | residual noise |

- (inference) The board cleanly decomposes into **{VFE+vouchers} ⊥ {HYDROGEL}**. No hidden joint factor. Long tail (7 PCs to 95%) means each voucher carries non-trivial idiosyncratic noise — consistent with no broad voucher-residual mean reversion to harvest.

## 6. Stationarity (sanity check)

ADF p ≈ 0 on **levels** for every product — surprising but consistent with finite ranges and tick-scale mean reversion (lag-1 autocorr negative per `01_initial_eda.md`). KPSS rejects stationarity for the same series → series is mean-reverting but with slow regime drift. Returns: ADF p=0, KPSS p=0.10 → stationary as expected.

## 7. Vol clustering (ACF of r², lag 1)

VEV_4000=0.41, VEV_4500=0.35, VEV_5500=0.31, VEV_5400=0.16, HYDROGEL=0.13, VFE=0.11.

- (observation) Strong vol clustering only in deep-ITM and far-wing strikes — inherited from VFE's level moves under the option Greeks (gamma flips on/off as strike crosses spot).
- (inference) HYDROGEL/VFE clustering is mild — no need for GARCH-style adaptive sizing as a first iteration.

## 8. Day-to-day stability

Per-day return correlation matrices for {VFE, VEV_5000, VEV_5200, HYDROGEL} are **identical to 2 decimals across days 0/1/2**. Whatever cross-product structure exists is stable. (Whether absolute IVs / smile shape are stable is a separate question for the voucher agent.)

## Recommended cross-product strategies

1. **HYDROGEL: pure standalone MM.** No need to look at any other book. Confirmed by both correlation and PCA decomposition.
2. **VFE: standalone delta-1 product**, but be aware the voucher chain agent's hedging flow will hit this book — coordinate inventory limits, not strategy.
3. **No cross-product alpha overlay**: no lead-lag signal to forecast voucher from VFE (or vice versa) at 1-tick scale. Don't waste a slot on it.
4. **VEV_4000 / VEV_4500 strike-spread guardrail**: if the spread between these two adjacent deep-ITM vouchers ever deviates meaningfully from 500 (the strike difference), that's a put-call-parity-style arb. Worth a sanity check, low-EV.
5. **Defer voucher RV to the voucher-chain agent.** This notebook found no clean voucher↔voucher cointegration in the belly (5000–5400) — IV-space modelling is required.
