# Regime Analysis v7 — PassiveMM Tuning by Regime

> Source: price data from `data/round_5/prices/prices_round_5_day_{2,3,4}.csv` (semicolon-separated).
> Live PnL cross-reference: `data/round_5/live_logs/v4/555525.log` activitiesLog (day 4 sandbox, v4 submission).
> EDA source: `docs/round_5/research/EDA_FINAL_TRIAGE.md`.
> Regime labels derived from price-data features only (spread, abs_ret, stdev, zero_ret_frac, AR(1) from EDA).
> Live PnL used ONLY as a sanity check after regime assignment — NOT as an input to regime labeling.

---

## 1. Category-Level Stats

| Category      | Mean L1 Spread | Mean |Δmid| | Mean Day Stdev | Mean |Drift Slope| | Zero-Ret % |
|---------------|----------------|--------------|----------------|------------------|------------|
| GALAXY_SOUNDS | 13.73          | 8.64         | 393            | 0.039            | 2.4%       |
| MICROCHIP     | 8.79           | 11.07        | 486            | 0.086            | 2.2%       |
| OXYGEN_SHAKE  | 12.90          | 8.11         | 399            | 0.074            | 12.5%      |
| PANEL         | 9.40           | 7.86         | 387            | 0.044            | 2.7%       |
| PEBBLES       | 12.81          | 14.46        | 641            | 0.140            | 1.6%       |
| ROBOT         | 7.13           | 7.82         | 341            | 0.056            | 15.0%      |
| SLEEP_POD     | 9.65           | 8.80         | 400            | 0.045            | 2.4%       |
| SNACKPACK     | 16.79          | 5.51         | 163            | 0.023            | 3.9%       |
| TRANSLATOR    | 8.78           | 7.92         | 335            | 0.040            | 2.8%       |
| UV_VISOR      | 13.13          | 8.23         | 361            | 0.037            | 2.7%       |

Spread units: raw price ticks. Drift slope: ticks per timestamp. Zero-ret %: fraction of consecutive mid-price differences equal to zero.

---

## 2. Per-Product Stats + v4 Live PnL Cross-Reference

| Product                         | Spread | |Δmid| | Day Stdev | |Drift| | Zero% | v4 Live PnL |
|---------------------------------|--------|---------|-----------|---------|-------|-------------|
| GALAXY_SOUNDS_BLACK_HOLES       | 14.5   | 9.11    | 470       | 0.110   | 2.4%  | +$860       |
| GALAXY_SOUNDS_DARK_MATTER       | 13.1   | 8.18    | 298       | 0.022   | 2.6%  | -$685       |
| GALAXY_SOUNDS_PLANETARY_RINGS   | 13.7   | 8.66    | 383       | 0.015   | 2.3%  | -$1,504     |
| GALAXY_SOUNDS_SOLAR_FLAMES      | 14.1   | 8.86    | 423       | 0.021   | 2.3%  | +$958       |
| GALAXY_SOUNDS_SOLAR_WINDS       | 13.3   | 8.39    | 391       | 0.026   | 2.4%  | -$43        |
| MICROCHIP_CIRCLE                | 8.3    | 7.35    | 403       | 0.049   | 2.8%  | +$291       |
| MICROCHIP_OVAL                  | 7.4    | 9.75    | 489       | 0.125   | 2.2%  | +$787       |
| MICROCHIP_RECTANGLE             | 7.9    | 10.42   | 428       | 0.075   | 2.1%  | -$142       |
| MICROCHIP_SQUARE                | 11.7   | 16.31   | 772       | 0.129   | 1.5%  | +$2,778     |
| MICROCHIP_TRIANGLE              | 8.6    | 11.50   | 339       | 0.053   | 2.1%  | -$355       |
| OXYGEN_SHAKE_CHOCOLATE          | 12.2   | 7.69    | 380       | 0.061   | 15.9% | +$229       |
| OXYGEN_SHAKE_EVENING_BREATH     | 11.9   | 7.36    | 353       | 0.057   | 39.2% | -$275       |
| OXYGEN_SHAKE_GARLIC             | 15.1   | 9.55    | 543       | 0.148   | 2.3%  | +$344       |
| OXYGEN_SHAKE_MINT               | 12.6   | 7.90    | 313       | 0.030   | 2.6%  | +$92        |
| OXYGEN_SHAKE_MORNING_BREATH     | 12.8   | 8.04    | 408       | 0.074   | 2.5%  | -$595       |
| PANEL_1X2                       | 11.5   | 7.21    | 372       | 0.028   | 2.8%  | -$141       |
| PANEL_1X4                       | 8.4    | 7.52    | 500       | 0.038   | 3.0%  | +$74        |
| PANEL_2X2                       | 8.5    | 7.65    | 290       | 0.000   | 3.0%  | -$591       |
| PANEL_2X4                       | 9.8    | 9.01    | 406       | 0.111   | 2.2%  | +$645       |
| PANEL_4X4                       | 8.8    | 7.94    | 366       | 0.041   | 2.6%  | +$689       |
| PEBBLES_L                       | 13.0   | 11.99   | 558       | 0.081   | 1.8%  | +$1,855     |
| PEBBLES_M                       | 13.1   | 12.08   | 466       | 0.066   | 1.7%  | +$3,702     |
| PEBBLES_S                       | 11.6   | 11.99   | 409       | 0.093   | 1.9%  | +$387       |
| PEBBLES_XL                      | 16.6   | 24.20   | 1168      | 0.284   | 0.8%  | +$2,389     |
| PEBBLES_XS                      | 9.7    | 12.03   | 602       | 0.176   | 1.8%  | +$438       |
| ROBOT_DISHES                    | 7.4    | 8.06    | 280       | 0.040   | 27.4% | -$1,371     |
| ROBOT_IRONING                   | 6.4    | 6.96    | 428       | 0.103   | 40.4% | -$353       |
| ROBOT_LAUNDRY                   | 7.2    | 7.84    | 244       | 0.009   | 2.4%  | -$373       |
| ROBOT_MOPPING                   | 8.0    | 8.87    | 499       | 0.092   | 2.2%  | +$285       |
| ROBOT_VACUUMING                 | 6.8    | 7.34    | 256       | 0.039   | 2.6%  | +$546       |
| SLEEP_POD_COTTON                | 10.1   | 9.29    | 499       | 0.037   | 2.2%  | -$85        |
| SLEEP_POD_LAMB_WOOL             | 9.4    | 8.51    | 371       | 0.026   | 2.5%  | +$165       |
| SLEEP_POD_NYLON                 | 8.6    | 7.64    | 316       | 0.039   | 2.6%  | +$1,333     |
| SLEEP_POD_POLYESTER             | 10.3   | 9.47    | 432       | 0.065   | 2.1%  | +$1,920     |
| SLEEP_POD_SUEDE                 | 9.9    | 9.08    | 383       | 0.056   | 2.4%  | +$1,119     |
| SNACKPACK_CHOCOLATE             | 16.5   | 5.23    | 155       | 0.023   | 4.2%  | +$26        |
| SNACKPACK_PISTACHIO             | 15.9   | 4.18    | 138       | 0.030   | 5.2%  | +$679       |
| SNACKPACK_RASPBERRY             | 16.8   | 6.46    | 167       | 0.012   | 3.3%  | -$5         |
| SNACKPACK_STRAWBERRY            | 17.8   | 6.49    | 192       | 0.024   | 3.2%  | +$758       |
| SNACKPACK_VANILLA               | 16.9   | 5.19    | 162       | 0.026   | 4.0%  | +$1,038     |
| TRANSLATOR_ASTRO_BLACK          | 8.4    | 7.52    | 274       | 0.053   | 2.9%  | +$823       |
| TRANSLATOR_ECLIPSE_CHARCOAL     | 8.7    | 7.84    | 311       | 0.022   | 2.7%  | +$175       |
| TRANSLATOR_GRAPHITE_MIST        | 8.9    | 8.08    | 385       | 0.042   | 2.8%  | +$1,665     |
| TRANSLATOR_SPACE_GRAY           | 8.4    | 7.52    | 377       | 0.037   | 2.7%  | -$1,526     |
| TRANSLATOR_VOID_BLUE            | 9.5    | 8.63    | 325       | 0.045   | 2.6%  | +$384       |
| UV_VISOR_AMBER                  | 10.3   | 6.35    | 283       | 0.073   | 3.3%  | -$630       |
| UV_VISOR_MAGENTA                | 14.1   | 8.91    | 330       | 0.052   | 2.5%  | +$345       |
| UV_VISOR_ORANGE                 | 13.3   | 8.33    | 353       | 0.036   | 2.7%  | +$61        |
| UV_VISOR_RED                    | 14.0   | 8.80    | 281       | 0.021   | 2.3%  | +$179       |
| UV_VISOR_YELLOW                 | 13.9   | 8.77    | 560       | 0.004   | 2.5%  | +$1,219     |

---

## 3. Regime Classification

**Regime definitions — features only (no live PnL used in assignment):**

- `wide_stable_mm`: spread ≥ 14, abs_ret < 8, day_stdev < 250, AR(1) ≈ 0. Pure wide-spread RW; easy capture, low adverse risk.
- `wide_drifty_mm`: spread ≥ 13, abs_ret 8–10, day_stdev 300–600, AR(1) ≈ 0. Wide spread but moderate volatility; drift bleeds are possible.
- `narrow_quiet_mm`: spread 6–9, abs_ret < 8.5, day_stdev < 300, AR(1) ≈ 0. Tight spread, low vol; small capture per fill.
- `narrow_volatile_mm`: spread 7–9, abs_ret 9–17, day_stdev 400–800, AR(1) ≈ 0, no step structure. Higher vol means more adverse inventory; need faster skew response.
- `step_mr`: spread 6–12, zero_ret% ≥ 15%, AR(1) ≤ −0.076 (EDA confirmed). Mid moves in discrete steps; weak-to-moderate MR above bounce.
- `basket_constrained`: 5-sum = 50000 (CV < 0.01%), intra-basket coordination possible, abs_ret 12–24.
- `pair_anticorr`: within-category |corr| ≥ 0.91, wide spread ≥ 16, low abs_ret < 7, low day_stdev < 200.

### Regime Assignments

| # | Product                         | Regime              | Justification |
|---|---------------------------------|---------------------|---------------|
| 1 | GALAXY_SOUNDS_BLACK_HOLES       | wide_drifty_mm      | spread=14.5, abs_ret=9.1, stdev=470; AR(1)=−0.017 (EDA: noise RW) |
| 2 | GALAXY_SOUNDS_DARK_MATTER       | wide_drifty_mm      | spread=13.1, abs_ret=8.2, stdev=298; AR(1)=−0.012 |
| 3 | GALAXY_SOUNDS_PLANETARY_RINGS   | wide_drifty_mm      | spread=13.7, abs_ret=8.7, stdev=383; AR(1)=−0.003 |
| 4 | GALAXY_SOUNDS_SOLAR_FLAMES      | wide_drifty_mm      | spread=14.1, abs_ret=8.9, stdev=423; AR(1)=−0.012 |
| 5 | GALAXY_SOUNDS_SOLAR_WINDS       | wide_drifty_mm      | spread=13.3, abs_ret=8.4, stdev=391; AR(1)=−0.007 |
| 6 | MICROCHIP_CIRCLE                | narrow_quiet_mm     | spread=8.3, abs_ret=7.3, stdev=403; AR(1)≈0 |
| 7 | MICROCHIP_OVAL                  | narrow_volatile_mm  | spread=7.4, abs_ret=9.8, stdev=489; strong downward drift; no step |
| 8 | MICROCHIP_RECTANGLE             | narrow_volatile_mm  | spread=7.9, abs_ret=10.4, stdev=428; AR(1)≈0 |
| 9 | MICROCHIP_SQUARE                | narrow_volatile_mm  | spread=11.7, abs_ret=16.3, stdev=772; outlier within category; largest jump vol |
| 10| MICROCHIP_TRIANGLE              | narrow_volatile_mm  | spread=8.6, abs_ret=11.5, stdev=339; AR(1)≈0 |
| 11| OXYGEN_SHAKE_CHOCOLATE          | step_mr             | spread=12.2, zero_ret%=15.9%, AR(1)=−0.076 (EDA); jump-diffusion confirmed (kurtosis=10.77) |
| 12| OXYGEN_SHAKE_EVENING_BREATH     | step_mr             | spread=11.9, zero_ret%=39.2%, AR(1)=−0.112 (EDA); reversal_frac=54% > 50% baseline |
| 13| OXYGEN_SHAKE_GARLIC             | wide_drifty_mm      | spread=15.1, abs_ret=9.6, stdev=543; AR(1)≈0; no step structure |
| 14| OXYGEN_SHAKE_MINT               | wide_drifty_mm      | spread=12.6, abs_ret=7.9, stdev=313; AR(1)≈0 |
| 15| OXYGEN_SHAKE_MORNING_BREATH     | wide_drifty_mm      | spread=12.8, abs_ret=8.0, stdev=408; AR(1)≈0 |
| 16| PANEL_1X2                       | narrow_quiet_mm     | spread=11.5, abs_ret=7.2, stdev=372; AR(1)≈0; trend R² high but not tick-exploitable |
| 17| PANEL_1X4                       | narrow_quiet_mm     | spread=8.4, abs_ret=7.5, stdev=500; AR(1)≈0 |
| 18| PANEL_2X2                       | narrow_quiet_mm     | spread=8.5, abs_ret=7.6, stdev=290; |drift|=0.0005 (lowest of all 50) |
| 19| PANEL_2X4                       | narrow_volatile_mm  | spread=9.8, abs_ret=9.0, stdev=406; |drift|=0.111 — highest in PANEL |
| 20| PANEL_4X4                       | narrow_quiet_mm     | spread=8.8, abs_ret=7.9, stdev=366; AR(1)≈0 |
| 21| PEBBLES_XS                      | basket_constrained  | 5-sum=50000 CV=0.006%; abs_ret=12.0, stdev=602 |
| 22| PEBBLES_S                       | basket_constrained  | 5-sum=50000; abs_ret=12.0, stdev=409; partial mechanical anti-corr |
| 23| PEBBLES_M                       | basket_constrained  | 5-sum=50000; size-price rank preserved; abs_ret=12.1 |
| 24| PEBBLES_L                       | basket_constrained  | 5-sum=50000; abs_ret=12.0, stdev=558 |
| 25| PEBBLES_XL                      | basket_constrained  | 5-sum=50000; abs_ret=24.2, stdev=1168; XL dominates PC1; most volatile pebble |
| 26| ROBOT_DISHES                    | step_mr             | spread=7.4, zero_ret%=27.4%; day-4 structural break (CB6/D6); elevated stop-loss risk |
| 27| ROBOT_IRONING                   | step_mr             | spread=6.4, zero_ret%=40.4%, AR(1)=−0.117 (EDA); reversal_frac=55% > 50% baseline; step=10 on ±10 grid |
| 28| ROBOT_LAUNDRY                   | narrow_quiet_mm     | spread=7.2, abs_ret=7.8, stdev=244; AR(1)≈0; |drift|=0.009 (near-zero) |
| 29| ROBOT_MOPPING                   | narrow_quiet_mm     | spread=8.0, abs_ret=8.9, stdev=499; AR(1)≈0 |
| 30| ROBOT_VACUUMING                 | narrow_quiet_mm     | spread=6.8, abs_ret=7.3, stdev=256; AR(1)≈0; tightest spread in ROBOT |
| 31| SLEEP_POD_COTTON                | narrow_quiet_mm     | spread=10.1, abs_ret=9.3, stdev=499; AR(1)≈0 |
| 32| SLEEP_POD_LAMB_WOOL             | narrow_quiet_mm     | spread=9.4, abs_ret=8.5, stdev=371; AR(1)≈0 |
| 33| SLEEP_POD_NYLON                 | narrow_quiet_mm     | spread=8.6, abs_ret=7.6, stdev=316; AR(1)≈0; trend R²=0.737 but no tick mechanism |
| 34| SLEEP_POD_POLYESTER             | narrow_quiet_mm     | spread=10.3, abs_ret=9.5, stdev=432; AR(1)≈0 |
| 35| SLEEP_POD_SUEDE                 | narrow_quiet_mm     | spread=9.9, abs_ret=9.1, stdev=383; AR(1)≈0 |
| 36| SNACKPACK_CHOCOLATE             | pair_anticorr       | CHOC/VAN corr=−0.916 stable; spread=16.5, abs_ret=5.2, stdev=155 |
| 37| SNACKPACK_PISTACHIO             | pair_anticorr       | PIST/STRAW=+0.913; spread=15.9, abs_ret=4.2, stdev=138 |
| 38| SNACKPACK_RASPBERRY             | pair_anticorr       | STRAW/RASP=−0.924; spread=16.8, abs_ret=6.5, stdev=167 |
| 39| SNACKPACK_STRAWBERRY            | pair_anticorr       | STRAW/RASP=−0.924; spread=17.8, abs_ret=6.5, stdev=192 |
| 40| SNACKPACK_VANILLA               | pair_anticorr       | CHOC/VAN=−0.916; spread=16.9, abs_ret=5.2, stdev=162; most stable in category |
| 41| TRANSLATOR_ASTRO_BLACK          | narrow_quiet_mm     | spread=8.4, abs_ret=7.5, stdev=274; AR(1)≈0 |
| 42| TRANSLATOR_ECLIPSE_CHARCOAL     | narrow_quiet_mm     | spread=8.7, abs_ret=7.8, stdev=311; lowest |drift| in TRANSLATOR |
| 43| TRANSLATOR_GRAPHITE_MIST        | narrow_quiet_mm     | spread=8.9, abs_ret=8.1, stdev=385; AR(1)≈0 |
| 44| TRANSLATOR_SPACE_GRAY           | narrow_quiet_mm     | spread=8.4, abs_ret=7.5, stdev=377; AR(1)≈0 |
| 45| TRANSLATOR_VOID_BLUE            | narrow_quiet_mm     | spread=9.5, abs_ret=8.6, stdev=325; AR(1)≈0 |
| 46| UV_VISOR_AMBER                  | wide_drifty_mm      | spread=10.3, abs_ret=6.3, stdev=283; price outlier (7,912 vs cat mean 10,500+); |drift|=0.073 |
| 47| UV_VISOR_MAGENTA                | wide_drifty_mm      | spread=14.1, abs_ret=8.9, stdev=330; AR(1)≈0 |
| 48| UV_VISOR_ORANGE                 | wide_drifty_mm      | spread=13.3, abs_ret=8.3, stdev=353; day-4-only wavelength encoding (unstable) |
| 49| UV_VISOR_RED                    | wide_drifty_mm      | spread=14.0, abs_ret=8.8, stdev=281; AR(1)≈0; borderline ADF p=0.035 fails Bonferroni |
| 50| UV_VISOR_YELLOW                 | wide_drifty_mm      | spread=13.9, abs_ret=8.8, stdev=560; |drift|=0.004 (flattest UV_VISOR) |

**Regime counts:** `narrow_quiet_mm`=18, `wide_drifty_mm`=11, `basket_constrained`=5, `pair_anticorr`=5, `narrow_volatile_mm`=5, `step_mr`=4, (dropped from v6: ROBOT_DISHES is step_mr but also structural-break risk)

---

## 4. Per-Regime PassiveMM Parameters

**One tuple per regime. No per-product overrides.**

| # | Regime              | Products (n) | skew | soft_cap | stop_loss_ticks | Rationale |
|---|---------------------|--------------|------|----------|-----------------|-----------|
| 1 | `narrow_quiet_mm`   | 18           | 0.4  | 7        | 60              | Baseline. Tight spread means lower per-fill capture; standard skew and stop suffice. |
| 2 | `wide_drifty_mm`    | 11           | 0.5  | 7        | 50              | Wide spread provides cushion, but day_stdev 300–600 means drift can build quickly; higher skew and tighter stop limit inventory bleed on adverse runs. |
| 3 | `step_mr`           | 4            | 0.6  | 8        | 35              | AR(1) < 0 means we benefit from posting aggressively (higher soft_cap) and pulling quotes faster on adverse moves (tighter stop); spread half-width ≈ 3–6 ticks so stop at 35 is ~6–10× half-spread and won't over-trigger on normal steps. |
| 4 | `basket_constrained`| 5            | 0.4  | 8        | 80              | PebblesCoordinator handles basket overlay skew. Base PassiveMM needs loose stop because XL day_stdev=1168; hard stop at 80 avoids triggering on normal basket excursions. Soft_cap raised because basket correction flows are large and fast. |
| 5 | `pair_anticorr`     | 5            | 0.5  | 7        | 80              | Wide spreads (mean 16.8) with low abs_ret (mean 5.5) and low day_stdev (mean 163) make MR-style stops too tight; set stop loosely at 80 to absorb within-day pair-sum drift. Higher skew (0.5) because anti-correlated flow can build one-sided inventory rapidly. |
| 6 | `narrow_volatile_mm`| 5            | 0.6  | 6        | 45              | abs_ret 9–16 with narrow spread means adverse ticks hurt more per unit inventory. Highest skew to shed inventory faster; lower soft_cap to cap exposure; stop at 45 ≈ 3–4× abs_ret to filter noise while cutting regime breaks. |

---

## 5. Sanity Checks

- **Regime labels are feature-derived only:** step_mr from zero_ret% + AR(1) (EDA), basket_constrained from 5-sum CV, pair_anticorr from within-category corr coefficient, narrow/wide/volatile from spread + abs_ret thresholds. No live PnL used in labeling.
- **Live PnL cross-check (does not reverse any label):** v4 live PnL variance within a regime is large (e.g., TRANSLATOR_GRAPHITE_MIST +$1,665 vs TRANSLATOR_SPACE_GRAY −$1,526 both in narrow_quiet_mm). This is expected — the 20% NPC order randomization dominates within-session variance (R3 calibration anchor: BT/live ratio ≈ 2.72×). Regime labels do not attempt to explain this variance.
- **MICROCHIP_SQUARE outlier:** abs_ret=16.3 and stdev=772 vs category mean abs_ret=11.1 and stdev=486. Assigned to narrow_volatile_mm alongside its siblings — the regime tuple (skew=0.6, soft_cap=6, stop=45) is the correct conservative response to its elevated vol, without a per-product override.
- **PEBBLES_XL outlier:** abs_ret=24.2 and stdev=1168 (2× siblings). Within basket_constrained regime; the loose stop_loss_ticks=80 accommodates XL's outsized swings without premature flattening. PebblesCoordinator's BETA=0.6 overlay already provides extra skew correction.
- **Dropped products (v6):** ROBOT_DISHES (step_mr), OXYGEN_SHAKE_MINT (wide_drifty_mm), MICROCHIP_TRIANGLE (narrow_volatile_mm), OXYGEN_SHAKE_MORNING_BREATH (wide_drifty_mm) — dropped because they bled in both BT and live; their regime assignments are listed for completeness but they are not active in v6.
