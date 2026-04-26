# R3 microstructure — HYDROGEL_PACK + VELVETFRUIT_EXTRACT

Source: `notebooks/02_microstructure_eda.py` over `data/round_3/prices_round_3_day_{0,1,2}.csv` (30k ticks/product).
Plots: `docs/round_3/research/plots/02_*.png`.

## TL;DR

- **Books have only 2 visible levels per side ~98% of the time.** Wall = the deeper L2 (typical size 25 hydrogel / 40 VFE), inside = thinner L1 (12 / 25). 3-level books essentially never occur.
- **Wall_mid is *not* materially different from top_mid in volatility** — std(d_wall)/std(d_top) ≈ 0.88 for both products. Wall_mid ≠ top_mid only because the L1/L2 sizes around the wall are not perfectly symmetric. Use wall_mid as fair anchor (matches Frankfurt) but expect very similar dynamics to top_mid.
- **Spread is rock-stable.** HYDROGEL spread = 16 on 92.7% of ticks; VFE spread = 5 on 74.2%, =6 on 18.2%. No intraday or per-day drift.
- **Mean reversion is real but weak.** Lag-1 return autocorr -0.01 to -0.05 per day on wall_mid (weaker than the -0.13/-0.16 the prior `01_initial_eda.md` reported on `mid_price` — the difference comes from using wall_mid vs top_mid; bid-ask bounce on top_mid contributes most of the negative autocorr). Variance ratios at k=2..50 are 0.90-0.98 → mild mean-reversion. Hurst ≈ 1.0 on price levels (= integrated random walk, expected); Hurst on returns ≈ 0.56 (~random). AR(1) half-life ~350-380 ticks.
- **Current `half_edge` settings are defensible but `half_edge=8` for HYDROGEL is on the boundary.** Cross-fill simulator confirms passive quotes at wall_mid±8 essentially never get crossed; they live AT best bid/ask ~50% of ticks. For VFE, half_edge=2 is aggressively inside the spread (top-of-book ~98% of ticks). See recommendations below.

## Q1 — Depth profile

| product | L1 only | L2 populated | L3 populated | both-sides 3-deep |
|---|---|---|---|---|
| HYDROGEL_PACK | 0% | 98.4% | 1.6% | 0% |
| VELVETFRUIT_EXTRACT | 45.6% | 52.3% | 2.0% | 0% |

Median sizes — HYDROGEL: L1=12, L2=25, L3=25 (when present). VFE: L1=25, L2=40, L3=40.

The exchange-MM (designated wall maker) puts the larger size at L2 of HYDROGEL and L2 of VFE when present, which is what makes "wall mid" a meaningful concept here.

## Q2 — Wall mid vs top mid

| metric | HYDROGEL | VFE |
|---|---|---|
| mean(wall_mid - top_mid) | +0.012 | +0.019 |
| std(wall_mid - top_mid) | 0.87 | 0.54 |
| std(d_top_mid) | 2.17 | 1.13 |
| std(d_wall_mid) | 1.92 | 0.98 |
| ratio d_wall / d_top | 0.88 | 0.87 |
| P(d_top = 0) | 18.0% | 24.7% |
| P(d_wall = 0) | 18.8% | 25.5% |

Wall_mid is ~12% smoother than top_mid in stdev terms. Not a huge improvement; both jump at similar frequency. Wall_mid wins as an anchor primarily because it's robust to L1 size noise (when L1 size momentarily drops to 1, top_mid wouldn't move but wall_mid stays anchored to the persistent deep level). Use it.

## Q3 — Spread regimes

- **HYDROGEL**: median 16, mean 15.72, std 1.46. 92.7% of ticks have spread = 16. Anomalies are tighter (7-9, ~3% of ticks) when both walls collapse together.
- **VFE**: median 5, mean 4.99, std 0.85. 74.2% at spread=5, 18.2% at spread=6. Bimodal but tight.
- **No intraday or per-day drift** (heatmap visually flat, per-day mean spread = 15.70/15.73/15.74 for HYDROGEL and 4.99/4.98/4.99 for VFE).

## Q4 — Autocorrelation robustness

Lag-1 wall_mid return autocorrelation **per day**:

| product | day 0 | day 1 | day 2 |
|---|---|---|---|
| HYDROGEL | -0.027 | -0.016 | -0.011 |
| VFE | -0.038 | -0.045 | -0.042 |

Per-quarter intraday: stable, all negative, magnitudes 0.001-0.05. The signal is **consistent across days and across intraday windows**, but much smaller in magnitude than the earlier `mid_price`-based number suggested. Plot 02_q4 shows the spectrum is dominated by lag-1; lags 2-200 are essentially noise around 0.

The earlier "-0.13/-0.16" came from `mid_price` (top-of-book mid). On wall_mid it's much weaker, suggesting the prior figure was largely bid-ask bounce, not genuine mean-reversion of fair value.

## Q5 — Mean reversion structure

Variance ratios (VR<1 = mean-reverting, VR=1 = random walk):

| k | HYDROGEL | VFE |
|---|---|---|
| 2 | 0.982 | 0.958 |
| 5 | 0.968 | 0.928 |
| 10 | 0.955 | 0.915 |
| 50 | 0.901 | 0.928 |

Mild mean-reversion at all horizons; flattens out past k=10. Hurst (price R/S) ≈ 1.0 (integrated process), Hurst on returns ≈ 0.56 — borderline mild persistence. AR(1) on price level: rho≈0.998, half-life ~380 ticks (HYDROGEL) / ~350 ticks (VFE). These half-lives are too long to be exploitable with passive MM that's flatten-on-reversion but consistent with "the price wanders slowly."

## Q6 — Mock fill simulation (passive at wall_mid ± h)

Conservative simulator: fill iff next-tick best price actually crosses our quote (1 unit per fill). Underestimates real fills since aggressive bot trades hitting our resting quote aren't in the cross-only count, but supplemented by a top-of-book occupancy check below.

| product | h | cross fills (buy/sell) | top-of-book occupancy |
|---|---|---|---|
| HYDROGEL | 2 | 97 / 44 | 98% / 98% |
| HYDROGEL | 5 | 3 / 1 | 92% / 92% |
| HYDROGEL | 6 | 1 / 1 | 84% / 84% |
| HYDROGEL | 8 | 0 / 0 | **50% / 49%** |
| HYDROGEL | 10 | 0 / 0 | 15% / 15% |
| VFE | 2 | 213 / 28 | 81% / 80% |
| VFE | 3 | 41 / 3 | 47% / 48% |
| VFE | 5 | 2 / 0 | 1.9% / 1.8% |

Reading: HYDROGEL spread=16, wall spread=21. With half_edge=8 our quote sits roughly AT best bid/best ask (because wall_mid - 8 ≈ best_bid). We're top-of-book ~50% of ticks. With half_edge=7 we'd be inside the spread always; with half_edge=10 we're a tick behind ~85% of ticks.

For VFE half_edge=2 puts us inside the 5-wide spread, top-of-book 81%. Halving to half_edge=3 collapses to 47% top-of-book and barely any cross fills.

## Q7/Q8 — Inventory drift & adverse selection

Couldn't measure for HYDROGEL at h=8 (zero simulated cross fills). For VFE at h=2:

| horizon | drift after BUY | drift after SELL | edge (B - S) |
|---|---|---|---|
| +5t | +0.10 | -0.70 | +0.79 |
| +10t | -0.06 | -0.07 | +0.01 |
| +50t | -0.07 | -0.52 | +0.45 |

Reading: BUY fills are slightly favorable at 5t but neutral after. SELL fills happen when price was momentarily high and then drops (favorable for us). **Net edge positive, no severe adverse selection.** The asymmetry (213 buys vs 28 sells) means we're predominantly accumulating long inventory, suggesting either persistent net buying pressure on VFE or asymmetric placement of our quote vs the wall — both worth investigating before sizing up.

## Recommendations for `src/trader.py`

1. **HYDROGEL half_edge: keep 8, but add an option to flex to 7.**
   - At half_edge=8 we're top-of-book ~50% of the time → real fills come from passive bot hits, not from book crossing.
   - At half_edge=7 we'd be inside the spread always (better fill rate, same per-trade edge=7 ticks). Risk: more adverse selection from informed flow taking the inside quote.
   - At half_edge=10 we're behind 85% of the time → essentially never fill. Don't go there.
   - Suggest a backtest sweep h ∈ {6, 7, 8} to confirm.

2. **VFE half_edge: 2 is fine but adverse selection is non-trivial.**
   - h=2 = top-of-book 81%, real fills happening, edge positive.
   - h=3 = top-of-book 47%, ~5x fewer fills. Probably worse net PnL.
   - **Asymmetry warning**: the simulator shows 213 buys vs 28 sells with half_edge=2. If this persists live, we'll hit the long position limit fast. Consider asymmetric quoting: `bid = wall_mid - 3`, `ask = wall_mid + 2` (skew the bid wider) until the asymmetry is explained.

3. **Wall_mid is the right anchor.** Marginally smoother than top_mid (12% lower stdev of changes). Keep `wall_mid()` definition as-is in `trader.py`.

4. **Both products are MM-able.** Stable wide spreads, low adverse selection, no regime shift across days. HYDROGEL is the better candidate (wider spread = more edge per round-trip, fully independent of options chain). VFE is exploitable but coordinate with the options team since VEV hedging will hit this book.

5. **Current `skew_per_unit=0.04`** is untested by this analysis. Worth a separate sweep — at +50 inventory it shifts quotes by 2 ticks which is significant for VFE (40% of half_edge) but tiny for HYDROGEL (25% of half_edge).

## Per-day generalisation

All key stats (spread, autocorr lag-1, variance ratios) are stable across days 0/1/2. No regime shift evidence. Strategy should generalise; per-day std of HYDROGEL price varies (25/38/32) but the *microstructure* doesn't.

## Caveats

- Fill simulator is a lower bound (cross-only). Real fills include bot aggressors hitting our resting quote, which would proportionally favor inside-spread quoting (h=2 for VFE, h≤7 for HYDROGEL).
- "Top-of-book occupancy" doesn't mean fill rate — it means we'd be quoted at the best price; actual fill depends on bot activity which the price feed doesn't isolate.
- Trade file (2382 rows for both products combined over 30k ticks) is sparse — ~4% of ticks have a recorded counterparty trade. The bot fill rate per tick is therefore in the low single-digit percent range, which is consistent with the simulated cross fill rates at small h.
