# inv05 — Book Imbalance: Predictive Power and Adverse-Selection Analysis

**Source data**: `data/round_5/prices/prices_round_5_day_{2,3,4}.csv` (1,500,000 rows, 50 products, days 2–4).
**Fill data**: `data/round_5/live_logs/v7/556038.log` (day 4 live, 1,149 our fills).
**Method**: OLS correlation on entire tick population (n=29,997 per product); 5-tick forward mid-change window for adverse-selection.

---

## 1. L1 Book Imbalance Regression

`BI_L1 = (bid_vol_1 − ask_vol_1) / (bid_vol_1 + ask_vol_1)`

Next-tick mid change regressed on BI_L1. All 50 products, days 2–4 pooled.

**Key structural observation**: For most products the NPC bots post symmetric volumes (bid_vol == ask_vol 96–97% of ticks), so BI is exactly 0 on ~96.7% of observations. This inflates denominator and suppresses the headline R² dramatically. The meaningful signal lives on the sparse non-zero ticks (3.3% of ticks).

### Full R² Table (all-tick regression)

| Product | R²_all | Slope | NonZero% | R²_nonzero | DirAcc_nz |
|---|---|---|---|---|---|
| SNACKPACK_PISTACHIO | 0.01753 | 4.97 | 3.32 | 0.3446 | 77.3% |
| SNACKPACK_CHOCOLATE | 0.01388 | 5.56 | 3.32 | 0.2886 | 74.5% |
| SNACKPACK_VANILLA | 0.01291 | 5.31 | 3.32 | 0.2740 | 73.7% |
| SNACKPACK_RASPBERRY | 0.01039 | 5.91 | 3.32 | 0.2378 | 71.2% |
| SNACKPACK_STRAWBERRY | 0.00942 | 5.66 | 3.32 | 0.2248 | 71.7% |
| OXYGEN_SHAKE_GARLIC | 0.00433 | 6.67 | 3.32 | 0.1115 | 63.2% |
| GALAXY_SOUNDS_SOLAR_WINDS | 0.00417 | 5.74 | 3.32 | 0.1133 | 64.7% |
| UV_VISOR_YELLOW | 0.00372 | 5.66 | 3.32 | 0.0995 | 63.1% |
| UV_VISOR_MAGENTA | 0.00351 | 5.60 | 3.32 | 0.0868 | 63.0% |
| UV_VISOR_RED | 0.00349 | 5.50 | 3.32 | 0.0908 | 63.8% |
| UV_VISOR_AMBER | 0.00347 | 3.95 | 3.41 | 0.0937 | 62.8% |
| GALAXY_SOUNDS_PLANETARY_RINGS | 0.00347 | 5.40 | 3.32 | 0.0892 | 62.6% |
| GALAXY_SOUNDS_BLACK_HOLES | 0.00345 | 5.69 | 3.32 | 0.0870 | 61.7% |
| UV_VISOR_ORANGE | 0.00334 | 5.10 | 3.32 | 0.0917 | 64.0% |
| OXYGEN_SHAKE_CHOCOLATE | 0.00331 | 5.28 | 3.32 | 0.1098 | 66.7% |
| PANEL_1X2 | 0.00321 | 4.33 | 3.32 | 0.0876 | 62.2% |
| OXYGEN_SHAKE_MINT | 0.00299 | 4.56 | 3.32 | 0.0854 | 64.0% |
| OXYGEN_SHAKE_EVENING_BREATH | 0.00291 | 5.00 | 3.32 | 0.0938 | 70.9% |
| GALAXY_SOUNDS_DARK_MATTER | 0.00275 | 4.53 | 3.32 | 0.0747 | 64.3% |
| GALAXY_SOUNDS_SOLAR_FLAMES | 0.00271 | 4.87 | 3.32 | 0.0735 | 60.5% |
| ROBOT/MICROCHIP/PANEL families | <0.001 | <2 | 8–40 | <0.01 | ~51% |

**Verdict**: No product exceeds R²=0.05 on the full-population all-tick regression. However, conditioning on the 3.3% of ticks where BI is non-zero reveals strong signal — SNACKPACKs reach R²=0.22–0.34 and 71–77% direction accuracy. The imbalance event itself is rare and informative; when it happens it strongly predicts the next tick.

**Products with predictive BI (non-zero ticks):**
- Tier 1 (R²_nz > 0.20, dir_acc > 70%): SNACKPACK_PISTACHIO, SNACKPACK_CHOCOLATE, SNACKPACK_VANILLA, SNACKPACK_RASPBERRY, SNACKPACK_STRAWBERRY
- Tier 2 (R²_nz 0.08–0.12, dir_acc 63–70%): OXYGEN_SHAKE_GARLIC, OXYGEN_SHAKE_CHOCOLATE, OXYGEN_SHAKE_EVENING_BREATH, GALAXY_SOUNDS_SOLAR_WINDS, UV_VISOR family
- Noise (R²_nz < 0.02): ROBOT, MICROCHIP, TRANSLATOR with high BI variation — imbalance is structural/random, not predictive

---

## 2. L2/L3 Marginal Contribution

Adding L2 volume to form `BI_12 = (BI_L1 + BI_L2) / 2` produces essentially no improvement:

| Product | R²_L1 | R²_L1+2 | Delta |
|---|---|---|---|
| SNACKPACK_PISTACHIO | 0.01753 | 0.01784 | +0.00032 |
| SNACKPACK_CHOCOLATE | 0.01388 | 0.01380 | −0.00008 |
| SNACKPACK_VANILLA | 0.01291 | 0.01307 | +0.00017 |
| SNACKPACK_RASPBERRY | 0.01039 | 0.01031 | −0.00008 |
| SNACKPACK_STRAWBERRY | 0.00942 | 0.00954 | +0.00012 |

L3 imbalance (only available on a small fraction of ticks) shows higher apparent R² for products like UV_VISOR_YELLOW (R²_L1+2+3 = 0.056) and GALAXY_SOUNDS_SOLAR_FLAMES (0.051), but the sample size collapses to a few hundred ticks — not reliable.

**Conclusion**: L2/L3 do not add meaningful predictive power for these products. L1 captures the signal. Multi-level features are not worth the complexity for R5.

---

## 3. Adverse Selection Rate — v7 Fills (5-tick window)

**Setup**: v7 log covers day 4. For each fill where buyer=SUBMISSION or seller=SUBMISSION, check whether the mid-price 500ms later moved against the fill direction.

**Overall**: 1,149 fills, **adverse=49.7%, favorable=49.1%** — essentially a coin flip, suggesting our current MM is not systematically adversely selected at the aggregate level.

### Per-product adverse selection (sorted by adverse%)

| Product | N Fills | Adverse% | Fav% | BI≠0% at fill |
|---|---|---|---|---|
| SNACKPACK_STRAWBERRY | 21 | 71.4 | 28.6 | 0.0 |
| PEBBLES_S | 12 | 66.7 | 33.3 | 0.0 |
| UV_VISOR_AMBER | 22 | 63.6 | 36.4 | 0.0 |
| ROBOT_VACUUMING | 30 | 63.3 | 36.7 | 53.3 |
| PEBBLES_M | 15 | 60.0 | 40.0 | 0.0 |
| MICROCHIP_RECTANGLE | 32 | 59.4 | 40.6 | 25.0 |
| GALAXY_SOUNDS_DARK_MATTER | 29 | 58.6 | 41.4 | 0.0 |
| UV_VISOR_MAGENTA | 28 | 57.1 | 42.9 | 0.0 |
| SNACKPACK_CHOCOLATE | 23 | 56.5 | 43.5 | 0.0 |
| SLEEP_POD_SUEDE | 39 | 56.4 | 43.6 | 0.0 |
| PANEL_1X2 | 20 | 55.0 | 45.0 | 0.0 |
| PANEL_2X2 | 20 | 55.0 | 30.0 | 5.0 |
| TRANSLATOR_VOID_BLUE | 24 | 54.2 | 45.8 | 0.0 |
| SLEEP_POD_NYLON | 34 | 52.9 | 47.1 | 5.9 |
| SNACKPACK_PISTACHIO | 25 | 52.0 | 44.0 | 0.0 |
| MICROCHIP_CIRCLE | 24 | 50.0 | 50.0 | 16.7 |
| GALAXY_SOUNDS_SOLAR_WINDS | 26 | 50.0 | 50.0 | 0.0 |
| UV_VISOR_ORANGE | 39 | 48.7 | 51.3 | 0.0 |
| UV_VISOR_RED | 37 | 48.6 | 51.4 | 0.0 |
| SLEEP_POD_COTTON | 42 | 47.6 | 52.4 | 0.0 |
| GALAXY_SOUNDS_BLACK_HOLES | 30 | 46.7 | 53.3 | 3.3 |
| SLEEP_POD_POLYESTER | 30 | 46.7 | 53.3 | 0.0 |
| SLEEP_POD_LAMB_WOOL | 22 | 45.5 | 54.5 | 0.0 |
| TRANSLATOR_ASTRO_BLACK | 38 | 44.7 | 55.3 | 7.9 |
| GALAXY_SOUNDS_SOLAR_FLAMES | 36 | 44.4 | 50.0 | 5.6 |
| UV_VISOR_YELLOW | 27 | 44.4 | 55.6 | 0.0 |
| GALAXY_SOUNDS_PLANETARY_RINGS | 23 | 43.5 | 56.5 | 0.0 |
| TRANSLATOR_ECLIPSE_CHARCOAL | 33 | 42.4 | 54.5 | 3.0 |
| ROBOT_LAUNDRY | 19 | 42.1 | 52.6 | 52.6 |
| OXYGEN_SHAKE_GARLIC | 35 | 40.0 | 60.0 | 0.0 |
| SNACKPACK_RASPBERRY | 20 | 40.0 | 55.0 | 0.0 |
| MICROCHIP_OVAL | 28 | 39.3 | 60.7 | 57.1 |
| PANEL_1X4 | 21 | 38.1 | 61.9 | 14.3 |
| MICROCHIP_SQUARE | 29 | 37.9 | 62.1 | 0.0 |
| SNACKPACK_VANILLA | 23 | 34.8 | 65.2 | 0.0 |
| TRANSLATOR_SPACE_GRAY | 21 | 33.3 | 66.7 | 0.0 |

**Notables**:
- SNACKPACK_STRAWBERRY (71.4% adv) and several PEBBLES are the worst adverse-selection victims despite BI being 0 at fill time — the adverse selection is not BI-explained; likely mean-reversion timing or spread skew issues.
- Products with favorable outcomes (adv < 40%): SNACKPACK_VANILLA (34.8%), TRANSLATOR_SPACE_GRAY (33.3%), MICROCHIP_OVAL (39.3%). These may have better spread capture.
- The v7 overall near-50% split means the raw MM is break-even on adverse selection — spread capture is the profit source, not directional alpha.

---

## 4. v8 Wrong-Side Analysis

v8 fills also cover day 4. On the SNACKPACKs (highest BI predictive power), **BI = 0.000 at every fill tick** — meaning all fills landed on ticks where volumes were symmetric. There were no cases in v8 SNACKPACK fills where BI was non-zero. The high-R² signal events are exceedingly rare (3.3% of ticks) and our fills simply didn't coincide with them.

**Implication**: v8 is not systematically wrong-side on BI signal for SNACKPACKs. The adverse selection in SNACKPACKs (51–71%) is happening on zero-BI ticks and is therefore not addressable via BI gating for our current fill distribution.

When conditioning v7 fills on absolute BI > 0 (all products), only 72 of 1,149 fills occurred on non-zero BI ticks. Of those 72:
- |BI| ≤ 0.5: 56.9% adverse (slightly elevated vs 49.7% baseline)
- |BI| > 0.5: 44.0% adverse (slightly lower — high-magnitude BI ticks are actually less adverse for us, possibly because they resolve quickly and we capture the spread before the move)

---

## 5. BI-Based Quote Skew Proposal

### Proposal
On ticks where `BI < −T` (book leaning strongly ask/sell), pull the bid quote one tick further inside. On ticks where `BI > +T`, pull the ask quote one tick further. Do not cancel the quote entirely (binary gate risk from CLAUDE.md pitfalls).

### Threshold recommendation: T = 0.3

**BI-conditioned adverse selection at |BI| > 0.3**:
- 33 fills at BI ≤ −0.3: **66.7% adverse** (vs 49.7% baseline) — our buys at sell-leaning books are materially worse
- 39 fills at BI ≥ +0.3: 48.7% adverse — sells at buy-leaning books only marginally elevated

**Simulated skew benefit (v7 fills, half-spread units)**:
- Skip fills at |BI| > 0.1: avoid 34 fills, net +10 half-spread units
- Skip fills at |BI| > 0.3: avoid 34 fills (same set — all nonzero is > 0.1), net +10 units
- At half-spread ~7–8 per product, net benefit ≈ +70–80 PnL units over one day — modest

### Bounded failure mode
- If BI is non-zero but uninformative (as it is for ROBOT/MICROCHIP families), pulling quote on a wide book could cause us to miss favorable fills. The proposal only fires on the 3.3% of ticks where BI ≠ 0, limiting downside.
- Worst case: BI fires, we skip, but mid reverts and the "adverse" move recovers. This costs 0 (we didn't trade). No position risk.
- The signal is stronger for SNACKPACKs (dir_acc 71–77% on nonzero ticks) — if implementation is limited to SNACKPACKs only, the false-positive rate is minimized.
- Do NOT hard-cancel quotes on BI; reduce quote size or widen by 1 tick. Binary gates are documented to cost ~$7.6k (CLAUDE.md pitfall).

### Implementation sketch
```python
bi = (bid_vol_1 - ask_vol_1) / (bid_vol_1 + ask_vol_1)  # 0 most of the time
if bi < -0.3:
    # book leans sell; widen our bid by 1 tick (less aggressive)
    bid_price -= 1
elif bi > 0.3:
    # book leans buy; widen our ask by 1 tick
    ask_price += 1
```
Cost: 1 addition/comparison per tick. No state needed.

### Priority assessment
- Benefit is **marginal** (net +10 half-spread units / day = ~$70–80 on v7 fill rate). Not a game-changer.
- The fills that *do* land on nonzero-BI ticks are slightly worse on average — worth correcting but not a primary lever.
- Larger opportunity is the per-product adverse selection spread: SNACKPACK_STRAWBERRY at 71.4% adverse vs TRANSLATOR_SPACE_GRAY at 33.3% suggests position-sizing or quote-width differentiation across products is a bigger unlock than BI gating.

---

## Summary

- **No product** reaches R² > 0.05 in the all-tick L1 BI regression. The signal is concentrated in the 3.3% of ticks where bid/ask volumes differ.
- **On those non-zero BI ticks**, SNACKPACKs show R² = 0.22–0.34 and 71–77% next-tick direction accuracy — a genuine signal.
- **L2/L3 add no value** (ΔR² < 0.001 consistently).
- **v7 adverse selection is 49.7% overall** — near-random. Per-product range is 33–71%, driven by factors other than BI (most fills are at BI=0 ticks).
- **v8 is not wrong-side on BI** for SNACKPACKs — fills never coincided with nonzero-BI ticks.
- **BI-skew proposal is valid but modest**: at T=0.3, adverse rate at those ticks is 66.7%, justifying widening the bid. Expected PnL improvement ~+$70–80/day in a single live run — small relative to overall noise floor.
