# 10 — Iacobus L1 vs L2 spread signal

Source: Discord user "iacobus" (untrusted) — claim: when L1 spread is wide vs L2, mid mean-reverts. Tested on R3 days 0/1/2 for `HYDROGEL_PACK` and `VELVETFRUIT_EXTRACT`. Script: `scripts/eda_10_iacobus.py`. Plots: `docs/round_3/../../../notebooks/round_3/plots/10_*.png`.

## Setup
- L1_spread = ask1 − bid1; L2_spread = ask2 − bid2; `diff = L1 − L2`.
- Forward mid returns at h ∈ {1, 5, 20} ticks, computed within day (no day-boundary leakage).
- n = 29,940 ticks/product (3 days × ~10k).

## Distribution
- HYDROGEL_PACK: L1 mean 15.7, L2 mean 20.9, `diff` mean −5.18, std 1.06. ~88% of ticks have diff = −5; tails are thin and sparse (−12, −11, −10, −9, −6, −4 only).
- VELVETFRUIT_EXTRACT: L1 mean 4.99, L2 mean 6.85, `diff` mean −2.26, std 0.68. ~77% at diff = −2; tail values −3, −4, −5.
- "L1 wider than L2" basically never happens; the signal lives entirely in *how much narrower* L1 is.

## Linear correlation (diff vs forward ret)
| product | r₁ | r₅ | r₂₀ |
|---|---|---|---|
| HYDROGEL_PACK | −0.053 (t=−9.2) | −0.026 (t=−4.5) | −0.016 (t=−2.9) |
| VELVETFRUIT_EXTRACT | −0.209 (t=−37.0) | −0.108 (t=−18.8) | −0.047 (t=−8.1) |

Negative slope = consistent with iacobus: L1 wider (more negative diff) → positive forward mid move. Strong on VFE, marginal on HYDROGEL.

## Conditional means (mean ret_5 by `diff` bucket, n)
HYDROGEL_PACK (3-day pooled, stable across days):
- diff=−12 → r₅=+4.12 (n=253)  ·  −11 → −2.71 (n=260)  ·  −10 → +2.70 (n=267)  ·  −9 → −3.55 (n=210)
- diff=−6 → −0.01 (n=1286)  ·  −5 → −0.01 (n=26212)  ·  −4 → +0.05 (n=1452)
- Tail buckets **alternate sign with parity** of diff. This is a tick-grid / midpoint-rounding artifact (mid sits on a half-tick when L1 is odd), not a tradeable directional edge.

VELVETFRUIT_EXTRACT (stable across days):
- diff=−5 → r₅=+1.89 (n=174, t≈9)  ·  −4 → +0.51 (n=585, t≈6)  ·  −3 → −0.65 (n=441, t≈−6)  ·  −2 → −0.07 (n=6930)
- Monotonic, sign-stable, statistically real. The diff=−5 bucket gives a +1.9-tick expected mid move over 5 ticks.

## Tradeability after costs
- HYDROGEL_PACK L1 spread is 15.7 ticks → crossing cost ~7.8 ticks/side. Tail effect (max ~+4 ticks at diff=−12) is well under spread cost, and the parity flip kills any directional take. Even passive resting orders would need to skew quotes by +4 in 0.9% of ticks — not worth a special branch.
- VELVETFRUIT_EXTRACT L1 spread mean ~5 ticks → ~2.5/side. Effect at diff∈{−4,−5} is +0.5 to +1.9 ticks (n≈760, ~2.5% of ticks). Crossing burns the edge. **Passive** quote skew (lift the bid / pull the ask) when diff ≤ −4 could capture a fraction without paying the spread, but the rare-event count (~250/day) limits PnL.

## Verdict
**Tradeable? Marginal — N for HYDROGEL_PACK, weak-Y for VELVETFRUIT_EXTRACT (passive only).**
- HYDROGEL: tail "signal" is a midpoint-parity artifact, not directional. Skip.
- VFE: real, stable, monotonic edge in the diff∈{−4,−5} tails (~2.5% of ticks, +0.5–1.9 tick expected move over 5t). Too thin to cross the spread; only worth wiring as a quote-skew bias inside an existing MM loop. Not a standalone strategy.
