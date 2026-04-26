# 11 — HYDROGEL_PACK adverse-fill quantification

**Question:** Is our HYDROGEL_PACK MM losing more in live than backtest because fills are toxic? Do fills systematically precede adverse mid drift, and what `half_edge` survives that drift?

## Data

- `prices_round_3_day_{0,1,2}.csv` (semicolon-sep), `trades_round_3_day_{0,1,2}.csv`. 30,000 book snapshots, 1,010 HYDROGEL_PACK tape prints across 3 days.
- `wall_mid` defined as midpoint of deepest visible level (L3 when present, else L2, else L1). L3 is filled <2% of snapshots, so wall_mid ≈ L2 mid ≈ L1 mid in practice.
- L1 spread is 16 ticks ≈ flat (median 16, std 1.5). So `wall_mid ± 8` is the wall edge; ±7 / ±9 are one tick inside / outside.

## Trade-offset distribution (price − wall_mid)

| offset | n     | side                 |
|--------|-------|----------------------|
| −8     | 476   | passive buy at wall  |
| −7     | ~236  | passive buy 1 inside |
| −6     | 2     |                      |
| −2..+1 | ~19   | mid-cross noise      |
| +6     | 4     |                      |
| +7     | ~238  | passive sell 1 inside|
| +8     | 503   | passive sell at wall |

> Fills are bimodal at ±8 (the wall). Almost no flow at offset 0, ±5, or ±10+. A maker quoting outside ±9 essentially never fills; a maker at ±6 catches near-zero flow because the wall sits at ±8.

## Mid drift after fill (mean ticks, signed in maker's favor when negative-for-buy / positive-for-sell)

| offset | side | n   | drift+1 | drift+5 | drift+20 | drift+50 |
|--------|------|-----|---------|---------|----------|----------|
| 7      | buy  | 236 | −0.07   | +0.04   | +0.29    | +0.26    |
| 7      | sell | 238 | −0.09   | +0.02   | −0.38    | −0.28    |
| 8      | buy  | 476 | +0.07   | +0.00   | +0.37    | +0.91    |
| 8      | sell | 503 | −0.10   | −0.13   | −0.19    | −0.27    |
| 9      | buy  | 221 | +0.24   | −0.04   | +0.54    | +1.48    |
| 9      | sell | 251 | −0.32   | −0.51   | −0.26    | −0.36    |

> Mid drift is **slightly favorable** for the maker on both sides at every offset and horizon. There is no measurable adverse-selection bleed in the historical tape; the worst single cell is ~0.4 ticks, dwarfed by the 7–9 tick gross capture. Buy-side drift is even mildly positive (mid moves up after we buy), sell-side mildly negative (mid moves down after we sell) — the mean-reversion regime is in the maker's favor.

## half_edge sweep, net edge per fill (gross capture − mean drift, h=20)

| half_edge | n_buy | n_sell | net_buy | net_sell | net / fill | total fills |
|-----------|-------|--------|---------|----------|------------|-------------|
| 5         | 0     | 0      | —       | —        | —          | 0           |
| 6         | 2     | 4      | 18.5    | 9.8      | 12.7       | 6           |
| 7         | 236   | 238    | 7.29    | 7.38     | **7.33**   | 474         |
| 8         | 476   | 503    | 8.37    | 8.19     | **8.27**   | **979**     |
| 9         | 221   | 251    | 9.54    | 9.26     | **9.39**   | 472         |
| 10–12     | 0     | 0      | —       | —        | —          | 0           |

Plots: `plots/11_offset_histogram.png`, `plots/11_drift_by_offset_side.png`, `plots/11_half_edge_sweep.png`.

## Conclusions

- **No evidence of adverse selection in the historical tape.** Mean post-fill mid drift is within ±0.5 ticks at all horizons, much smaller than any reasonable half-edge. The "live drawdowns > backtest" Discord chatter is **not** explained by toxic fill flow on this product, at least in R3 history.
- Likely live-vs-backtest gap drivers to investigate next: (a) inventory accumulation / position-limit forcing us to lift/hit, (b) bot opponents reacting to *our* quote inside the wall (not present in replay), (c) slippage when liquidating end-of-day.
- **Recommended `half_edge` = 8** (quote at the wall). 979 historical fills, ~8.27 ticks net per fill, ≈ 8,094 ticks of gross theoretical edge per 3-day replay before inventory / hedging cost.
- `half_edge = 7` (quote one inside the wall) trades volume for nothing: **fewer fills (474 vs 979) and lower per-fill edge (7.33 vs 8.27)** — strictly dominated unless we want inventory-rotation faster.
- `half_edge = 9` (one outside the wall) gives a bit more per fill (9.39) but only 472 fills — total ~4,432 ticks, ~45% less than ±8. Useful as a quote layer alongside ±8, not a replacement.
- `half_edge ≤ 5` or `≥ 10` see zero historical fills — out of regime.

## Suggested next experiments

- Repeat this analysis on **live R3 logs** to see if the live tape shows the adverse drift the historical tape lacks.
- Add inventory-aware skew: if drift conditional on |position| is what's biting us live, ±8 with a skew term may dominate static ±8.
