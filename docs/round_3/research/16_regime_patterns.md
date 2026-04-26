# R3 Regime Patterns — Exploitable Structure

Source: `notebooks/16_regime_patterns.py` over `data/round_3/prices_round_3_day_{0,1,2}.csv` (90k ticks).
Plots: `plots/16_hg_regime.png`, `16_vfe_regime.png`, `16_voucher_delta_per_strike.png`,
`16_hgvfe_rollcorr.png`, `16_intraday_vol.png`.

## TL;DR

- HG FV=9991 holds in mean but per-day std doubles (25→38). Day 1 only **31.5%** within ±20 vs day 0 56%, day 2 49%. Sub-regimes are slow drifts, not vol clustering.
- VFE FV drifts upward across days: median 5244.5 → 5248.5 → 5257.5. Hardcoded 5250 misprices day 2 by +5–7 ticks.
- Voucher delta-1 assumption is wrong every strike. Slope ΔV/ΔVFE: 4000→0.74, 5000→0.65, 5200→0.43, 5400→0.13.
- HG and VFE never co-move: rolling-500 corr in [-0.11, +0.12], 0% windows |corr|>0.2.
- No intraday seasonality (vol, spread, volume flat across 10 buckets/day).

## 1. HYDROGEL regime structure

Per-day deviation from FV=9991 (`mid - 9991`):

| Day | mean | std | min/max | %\|dev\|≤20 | %\|dev\|>40 |
|---|---|---|---|---|---|
| 0 | -0.04 | 25.3 | -63 / +80 | **56.0%** | 12.1% |
| 1 | +1.06 | **37.6** | -82 / +88 | **31.5%** | **30.2%** |
| 2 | -1.60 | 31.6 | -100 / +60 | 49.4% | 20.4% |

- Bias stable in mean (always within ±2 of 9991), dispersion is not (day 1 std 50% wider).
- Splitting by rolling-200 vol: low-vol vs high-vol regimes show **identical** %time within ±20 (46.0% vs 46.8%) and mean |dev| (26.8 vs 25.1). **No vol-clustering regime** — far-from-FV time is drift, not vol expansion.
- 35.6% of ticks live with |dev|>30; top 10 such excursions last **220–1037 ticks**.
- (implication) Don't widen passive quotes when far from FV — vol doesn't rise there. Do size derisk by absolute distance from 9991 since excursions persist 200–1000 ticks (longer than a 40-tick stop).

## 2. VFE regime structure

Per-day mid stats (FV assumed 5250):

| Day | median | mean | q25 | q75 |
|---|---|---|---|---|
| 0 | 5244.5 | 5246.5 | 5236.5 | 5255.5 |
| 1 | 5248.5 | 5248.4 | 5238.5 | 5259.0 |
| 2 | **5257.5** | **5255.4** | 5242.5 | **5269.0** |

- FV drifts +13 ticks across days. Day 2 smoothed (50t) mid sits **above 5265 for 34.2%** of the day vs 11–12% on days 0/1. Hardcoded FV=5250 = systematic short bias day 2.
- Excursion length (50-tick smoothed sign vs FV=5250): median 80, p75 360, p90 862. **70.7% of ticks live in runs >500.** Long directional regimes are typical.
- (implication) Ian's 40-tick stop on a 5250-anchored MR is structurally fragile vs 80–862 tick excursions. Either (a) adapt FV via rolling 1000-tick median, (b) exit early (don't wait for 5250 if entered at 5260), or (c) widen stop to 80+ ticks.

## 3. Voucher delta per strike (Ian's "delta-1" assumption)

Empirical slope of `ΔVoucher / ΔVFE`, OLS per day on tick diffs (avg across days, all stable to ±0.02 day-over-day):

| Strike | Slope | Corr | Notes |
|---|---|---|---|
| 4000 | **+0.74** | 0.64 | deepest ITM, but slope ≠ 1 — quote rounding compresses moves |
| 4500 | +0.66 | 0.65 | |
| 5000 | +0.65 | 0.78 | best correlation; still not 1.0 |
| 5100 | +0.58 | 0.79 | |
| 5200 | +0.43 | 0.75 | true ATM (spot ~5250), slope < 0.5 |
| 5300 | +0.27 | 0.65 | |
| 5400 | **+0.13** | 0.57 | OTM — barely tracks |
| 5500 | +0.05 | 0.37 | nearly decoupled |
| 6000/6500 | 0.00 | n/a | dead-pinned, confirmed |

- "Delta-1 of VFE" wrong for every strike. Best-tracker (5000) moves 0.65 ticks/VFE-tick. ATM 5200 = 0.43.
- Explains Ian's per-strike PnL (`15_teammate_ian_compare.md`): VEV_4000 lost 1,350 because Ian sized as delta-1 but actual response 0.74 → 26% unhedged drift.
- (implication) Strike-aware delta sizing is the next upgrade. Either scale size by `1/empirical_delta`, or restrict the chain to high-delta high-corr strikes (5000/5100/5200: slope 0.43–0.65, corr 0.75–0.79).

## 4. HG ↔ VFE co-movement

Rolling-500 return corr: mean 0.006, std 0.042, range [-0.11, +0.12]. **Zero** windows exceed |corr|=0.2. Books fully independent in every regime; confirms `06_cross_product.md` PCA result holds intraday.

## 5. Time-of-day patterns

10 buckets/day (10k ticks each). HG return std 2.12–2.23 (5% range); spread 15.66–15.77; volume 317–457. VFE return std 1.10–1.16; spread 4.96–5.03; volume 744–933. **No intraday edge.** Don't condition on timestamp; pre-flatten is risk-mgmt only, not alpha.

## Failed hypotheses

- "HG has high-vol vs low-vol regimes" — false (rv500 max/min = 1.24).
- "Voucher delta is ~1.0 ATM" — false (5000 = 0.65, 5200 = 0.43).
- "HG and VFE share regime windows" — false (no |corr|>0.2 in 90k ticks).

## Top exploitable findings (ranked)

1. Strike-aware voucher sizing — slope table is day-stable; fixes Ian's 4000/4500 leak.
2. VFE adaptive FV — day-2 drift to 5257 is a 5–7 tick miss for any 5250-anchored trader. Use rolling 1000-tick median.
3. HG derisk by distance, not vol — vol is constant; |dev| from 9991 is the actual risk signal; 200–1000 tick excursions are normal.
4. No intraday clock to lean on.
