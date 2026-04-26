# R3 Voucher Chain — IV Surface, Smile Drift, Static-vs-Rolling

Source: `notebooks/03_voucher_chain_eda.py` over `data/round_3/prices_round_3_day_{0,1,2}.csv`.
TTE convention: 8 / 7 / 6 days for historical day 0 / 1 / 2; year basis = 365.
Smile parameterisation: `iv = a*m^2 + b*m + c`, `m = log(K/S)/sqrt(TTE_y)`.

## TL;DR

- **Smile drifts intraday — strongly.** Per-tick `(a, b, c)` refit shows curvature `a` swinging
  between roughly **-0.21 and +0.28** within day 1; `b` flips sign repeatedly (`mean≈0` so its
  std/|mean| explodes). Level `c` is the most stable (intraday `std/mean ≈ 2-3%`, ranges
  ~0.21 to 0.25). This is the CMU smoking-gun pattern.
- **Rolling smile (window=100) beats pooled static smile by 30.6% RMSE overall.** Per-strike
  improvements: VEV_5000 +57%, VEV_5100 +47%, VEV_5200 +43%, VEV_5300 +35%, VEV_5500 +18%,
  VEV_5400 +0.6%. Static is marginally better for VEV_4000 / VEV_4500 (deep ITM — RMSE
  governed by 1-tick rounding, not smile).
- **Residuals are stationary** (ADF stat -6 to -90, p≈0 for every live voucher). Strong
  evidence the `mid - theo` series mean-reverts → exploitable as alpha contrarian signal.
- **Persistent per-strike bias under rolling smile:**
  - VEV_5300 sits **+1.83 ±0.90** rich.
  - VEV_5400 sits **-1.98 ±0.73** cheap.
  - VEV_5200 sits **+1.06 ±0.73** rich, VEV_5000 **-0.46 ±0.56** cheap.
  - These offsets exceed the typical 1-2 tick spread → durable cross-strike RV trade
    (sell 5300/5200, buy 5400/5000 — a near delta-neutral butterfly).
- **Implied < Realized**: mean IV across days is **0.249 / 0.252 / 0.252**; realized vol of
  VFE at horizons 10/50/200/500 ticks is **0.335 / 0.341 / 0.342 / 0.342** (annualised).
  Vouchers persistently underprice realised vol by ~9 vol-points → systematic long-vol /
  long-gamma should be EV-positive (subject to theta).

## Per-question answers

### Q1 — Per-voucher IV (count / mean / std)
| Voucher | n | mean IV | std |
|---|---|---|---|
| VEV_4000 | 2898 | 0.786 | 0.080 |
| VEV_4500 | 8823 | 0.450 | 0.043 |
| VEV_5000 | 29976 | 0.233 | 0.008 |
| VEV_5100 | 30000 | 0.231 | 0.008 |
| VEV_5200 | 30000 | 0.233 | 0.006 |
| VEV_5300 | 30000 | 0.236 | 0.006 |
| VEV_5400 | 30000 | 0.221 | 0.007 |
| VEV_5500 | 30000 | 0.240 | 0.006 |
| VEV_6000/6500 | — | — | — (pinned 0.5, no IV) |

VEV_4000/4500 are deep ITM → mid is essentially intrinsic, IV reflects the rounded extrinsic
~1 tick → noisy/biased. Treat them as delta-1 proxies, not IV instruments.

### Q2 — Smile drift (per-tick refit)
- Day 0: `a` mean 0.077 ± 0.056 (range −0.08 → +0.18); `c` mean 0.229 ± 0.005.
- Day 1: `a` mean 0.057 ± 0.076 (range −0.21 → +0.28); `c` mean 0.230 ± 0.006.
- Day 2: `a` mean 0.066 ± 0.070 (range −0.19 → +0.28); `c` mean 0.228 ± 0.007.
- Curvature `a` swings sign intraday repeatedly. Level `c` is stable to ~3%.
- Plot: `docs/round_3/research/plots/03_smile_drift.png`.

### Q3 — Static day-0 smile, out-of-sample
- Pooled day-0 fit: `a=0.1484, b=-0.0139, c=0.2260`.
- OOS residual means on day 1 / day 2 stay within ±3.5 across strikes (e.g. VEV_5300:
  +1.90 / +3.47 / +2.88). So *static does generalise in level*, but per-strike biases of
  3+ ticks are larger than the typical spread — Frankfurt's hardcoded smile would systematically
  misprice 5300 rich and 5400 cheap.

### Q4 — Rolling vs static
| Voucher | static RMSE | rolling RMSE | improvement |
|---|---|---|---|
| VEV_4000 | 1.27 | 1.63 | -28% |
| VEV_4500 | 0.75 | 0.98 | -31% |
| VEV_5000 | 1.67 | 0.72 | **+57%** |
| VEV_5100 | 1.68 | 0.89 | **+47%** |
| VEV_5200 | 2.27 | 1.29 | **+43%** |
| VEV_5300 | 3.12 | 2.04 | **+35%** |
| VEV_5400 | 2.12 | 2.11 | +0.6% |
| VEV_5500 | 0.70 | 0.57 | +18% |
| **Overall** | **2.01** | **1.40** | **+31%** |

Rolling wins decisively for ATM strikes (5000-5300). For deep ITM (4000/4500) the
RMSE is dominated by tick rounding so both fits are close; static is marginally better.

### Q5 — Residual stationarity (rolling-smile residuals)
ADF stat in [-93, -6], p ≈ 0 for every live voucher → strongly stationary. Mean-reverting
residuals confirm `mid - theo` is a tradable signal. Per-voucher std of residual is
0.6-1.1, so a ±1.5 threshold gives a sensible entry trigger after vega-normalisation.

### Q6 — Cointegration
Of 28 pairs, 8 are cointegrated at p<0.05. Strongest non-trivial pairs:
VEV_5400-VEV_5500 (p=0.0008), VEV_5300-VEV_5500 (p=0.009), VEV_5000-VEV_5500 (p=0.018).
VEV_4000-VEV_4500 dominates (p≈0) but that's intrinsic-driven, not real cointegration.
Take-away: VEV_5500 is the common factor for the upper wing — supports a butterfly /
calendar of `5300 / 5400 / 5500` against the persistent bias from Q5.

### Q7 — Vega-weighted residuals
Per-voucher vega (mean): 5200=2.74, 5300=2.78, 5400=1.92, 5100=1.88, 5500=1.11, 5000=0.91,
4500=0.13, 4000=0.12. Residual / vega gives strike-comparable edge:
VEV_5400 = -1.04 / vega-tick (cheapest), VEV_5300 = +0.67 (richest). Frankfurt-style
threshold should set `|resid| > k * vega` with k ≈ 0.5 to filter signal.

### Q8 — Implied vs realized
| Horizon (ticks) | Realized vol (annualised) |
|---|---|
| 10 | 0.335 |
| 50 | 0.341 |
| 200 | 0.342 |
| 500 | 0.342 |

Mean IV by day: 0.249 / 0.252 / 0.252. **Vouchers underprice realised vol by ~9 vol-points
(roughly 36% relative).** A naive long-straddle hedged would be theoretically EV-positive
in expectation, but only if executable; bid-ask + theta will erase a chunk.

### Q9 — Dead OTM
- VEV_6000 mid: 30000 / 30000 rows = exactly 0.500. Trades: 284, all at price 0.0.
- VEV_6500 same: 30000 mids of 0.500, 284 trades all at 0.0.
- **Verdict: completely dead. Exclude entirely from fitting and trading.** No free money;
  the 0.5 mid is the platform floor with no real counterparty.

### Q10 — Lead-lag (brief, defer to cross-product agent)
Using VEV_5200 vs VFE returns at 100-ts grid: lag-0 corr = **0.72**, all other lags
within ±0.01. No exploitable lead-lag at this resolution.

## Recommendations for our R3 voucher trader

1. **Use rolling smile, not Frankfurt-style hardcoded.** Window 100 ticks on per-tick
   `(a,b,c)` quadratic. Reduces RMSE by 31% overall, 40-57% on the strikes that matter.
2. **Universe**: trade VEV_5000, 5100, 5200, 5300, 5400, 5500 only.
   - Skip VEV_6000 / VEV_6500: dead-pinned at 0.5, no real market, no PnL available.
   - Treat VEV_4000 / VEV_4500 as delta-1 proxies for VFE; trade them on mean-reversion
     of the underlying or skip — IV-scalping logic is meaningless when extrinsic is ~1 tick.
3. **Cross-strike RV bias to monetise** (from rolling-smile residuals):
   - VEV_5300 persistently rich by ~+1.8, VEV_5400 cheap by ~-2.0 → fade 5300, lift 5400.
   - This is delta-near-neutral; sizing capped by 300/voucher position limit.
4. **Vega gate** entry threshold at `|resid| > 0.5 * vega` (Frankfurt pattern); confirms
   alpha-per-vega signal scale across the chain.
5. **Don't delta hedge** through VFE. Spread is 1-2 ticks on VFE; net delta from a 5300/5400
   butterfly is small. Spend the hedge budget on tighter quotes instead.
6. **IV-vs-RV gap is large but stale**: -9 vol points. Don't blindly trade vol; the gap
   is partly theta compensation for 6-8d expiry. Ship the residual-mean-reversion alpha
   first, layer vol exposure later if positions naturally align.

## Plots
- `docs/round_3/research/plots/03_iv_timeseries.png` — per-voucher IV time series (3 days).
- `docs/round_3/research/plots/03_iv_surface.png` — mean IV (day × voucher) heatmap.
- `docs/round_3/research/plots/03_smile_drift.png` — `a(t), b(t), c(t)` per day.
- `docs/round_3/research/plots/03_residuals_per_strike.png` — rolling-smile residual series.
