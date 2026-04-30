# inv01: PassiveMM Rolling-Mean Stop-Loss — Forensic Analysis

**v8 baseline BT (3 days, 30k ticks)**: $257,832  
**Variants tested**: wide_stops (2x), no_stops, widen_drifty_only  
**Data**: `data/round_5/prices/prices_round_5_day_{2,3,4}.csv` + BT runs

---

## BT Totals — Variant Comparison

1. **v8 baseline** (stops: NQ=60, WD=50, NVol=45, step=40, PEBBLES/SNACK=80): **$257,832**
2. **wide_stops** (stops: NQ=120, WD=100, NVol=90, step=80, PEBBLES/SNACK=160): **$285,620** (+$27,788, +10.8%)
3. **no_stops** (stop check completely disabled): **$266,700** (+$8,868, +3.4%)
4. **widen_drifty_only** (wide_drifty 50→100, all others same as v8): **$261,859** (+$4,027, +1.6%)

## Stop-Fire Frequency

5. Total simulated stop fires across 3 BT days and all products: **1,017 fires** (~339/day).
6. Fires by day: Day 2 = 327, Day 3 = 345, Day 4 = 345. Stable across all days.
7. Fires by regime: `narrow_volatile_mm` = 273, `wide_drifty_mm` = 279, `pebbles` = 183, `step_mr` = 144, `narrow_quiet_mm` = 138.
8. Top-firing products (all 3 days combined): MICROCHIP_SQUARE (131), PEBBLES_XL (122), MICROCHIP_RECTANGLE (65), OXYGEN_SHAKE_EVENING_BREATH (53), OXYGEN_SHAKE_CHOCOLATE (52).

## Outcome Classification — @100 and @200 Ticks Post-Fire

9. Overall save rate at +100 ticks: **50.3%** (virtually coin-flip). At +200 ticks: **47.8%** (slight bounced-majority).
10. This means the rolling-mean stop on average does not predict future direction — the stop fires at regime edges where the mean is still catching up to the new price level.

## Regime-Level Net PnL Impact (estimated)

11. `narrow_volatile_mm`: net **+$12,938** benefit (stops HELPING). MICROCHIP_SQUARE save rate 54%, avg_delta at +100t = -6.4 (mid keeps going adverse).
12. `step_mr`: net **+$14,404** benefit (stops HELPING). OXYGEN_SHAKE_CHOCOLATE avg_delta = -39.2 — strong mean-reversion post-step then continued adverse move.
13. `narrow_quiet_mm`: net **+$1,386** benefit (modest HELPING). Consistent saves across SLEEP_POD and TRANSLATOR products.
14. `wide_drifty_mm`: net **-$8,910** (stops HURTING). Most products in this regime have trending mids; stops fire on a new trend leg and then the trend continues, but the stop exits early before recovering spread income.
15. `pebbles`: net **~neutral** (saves 52% @100t but avg_delta only -2.0 — small magnitude).

## Per-Product Highlights — Most Significant

16. **MICROCHIP_SQUARE** (narrow_volatile, sl=45): 131 fires, save rate 54%@100t, avg_delta=-6.4, estimated +$2,815 benefit. BT baseline -$2,947 day4 vs wide_stops -$3,940 (wide stops WORSE here — wider stop allows larger losses to accumulate).
17. **OXYGEN_SHAKE_CHOCOLATE** (step_mr, sl=40): 50 fires, avg_delta=-39.2 @100t. Stops are strongly HELPING — mid continues adverse after step events. BT wide_stops day4: 1,755 vs baseline 2,501 (wider hurts).
18. **UV_VISOR_ORANGE** (wide_drifty, sl=50): 21 fires, avg_delta=+33.8 @100t, estimated -$1,911 total cost. BT: baseline day4 -$3,626, wide_stops day4 -$1,576 (+$2,050 improvement with wider stop).
19. **GALAXY_SOUNDS_BLACK_HOLES** (wide_drifty, sl=50): 27 fires, avg_delta=+92.5 — strong bounce after stop, estimated -$2,498 cost. BT: baseline 7,058 vs wide_stops 6,960 (minimal change despite fire cost — high base fill rate).
20. **GALAXY_SOUNDS_SOLAR_WINDS** (wide_drifty, sl=50): 19 fires, avg_delta=+93.9, estimated -$1,785 cost. BT: baseline 922 vs wide_stops 2,336 (+$1,414 improvement with wider stop).
21. **OXYGEN_SHAKE_GARLIC** (wide_drifty, sl=50): 32 fires, avg_delta=+100.3 — strongest bouncer in regime, estimated -$3,208 cost. BT: baseline -$553 vs wide_stops -$47 (+$506).
22. **PANEL_2X4** (narrow_volatile, sl=45): 32 fires, save rate only 28%@100t (avg_delta=+32.3 — mostly bouncing). BT: baseline 234 vs wide_stops 1,580 (+$1,346). Stop is HURTING here despite being in narrow_volatile regime.
23. **MICROCHIP_RECTANGLE** (narrow_volatile, sl=45): 65 fires, save rate 52%, avg_delta=-7.0. BT: baseline -$1,007 vs wide_stops -$2,528 (wider stop HURTS here too — more inventory accumulation into adverse moves).

## Key Tension: Why Wide Stops Win Overall Despite Mixed Per-Product Results

24. The wide_stops variant is better (+$27.8k) but it is NOT because all products improve. MICROCHIP products get worse with wider stops (more inventory held during adverse moves). The improvement comes disproportionately from `wide_drifty_mm` products (UV_VISOR_ORANGE, GALAXY_SOUNDS_SOLAR_WINDS, OXYGEN_SHAKE_GARLIC) where stops fire on trend continuations and kill income.
25. No_stops (+$8.9k) underperforms wide_stops (+$27.8k) because removing stops entirely allows large uncapped drawdowns on MICROCHIP products and step_mr products where stops genuinely save.

## Regime-Specific Recommendation

26. **`narrow_volatile_mm` (MICROCHIP_OVAL/RECT/SQ, PANEL_2X4)**: Split by product. MICROCHIP_OVAL/RECT/SQ benefit from stops (save 50-54%). PANEL_2X4 shows 28% save rate — consider widening PANEL_2X4 to 90 or removing separately. Keep others at 45 or tighten slightly.
27. **`step_mr` (OXYGEN_SHAKE_CHOCOLATE, EVENING_BREATH, ROBOT_IRONING)**: Stops strongly HELPING. Keep at 40. Widening (80 in wide_stops variant) is worse for these products in BT day4 (OXY_CHOC: baseline 2,501 vs wide 1,755).
28. **`wide_drifty_mm`**: Stops net HURTING (-$8.9k estimated). Recommend widening from 50 to 100. However, note the widen_drifty_only BT only recovered +$4k (vs +$27.8k for full wide) — wide_drifty products are a minority of the total improvement.
29. **`narrow_quiet_mm`**: Stops modestly HELPING (+$1.4k). Keep at 60 or tighten slightly. No regime-level change needed.
30. **`pebbles`/`snackpack`**: Near-neutral (80/80 stops). Widening to 160 in wide_stops variant improved pebbles BT (day4: PEBBLES_XL 12,674→15,083, PEBBLES_S 3,173→14,800 — large variance). Keep at 80 unless pebbles is specifically targeted.

## Final Recommendation

**Adopt a differentiated config rather than uniform 2x or no-stops:**

| Regime | Current | Recommended | Rationale |
|--------|---------|-------------|-----------|
| narrow_volatile_mm | 45 | 45 (MICROCHIP), 90 (PANEL_2X4) | PANEL_2X4 bounces; MICROCHIPs save |
| step_mr | 40 | 40 | Strongly helping; wider hurts |
| narrow_quiet_mm | 60 | 60 | Modestly helping; leave alone |
| wide_drifty_mm | 50 | 100 | Net hurting; trending products |
| pebbles | 80 | 80 | Neutral; high variance in pebbles PnL obscures signal |
| snackpack | 80 | 80 | Insufficient fire data |

**Note**: BT is deterministic. The +$27.8k for wide_stops, +$8.9k for no_stops, and +$4k for widen_drifty_only are BT-only numbers subject to live variance. Given the CLAUDE.md calibration anchor (BT ≈ 2.72× live), treat regime-specific tuning as a secondary priority unless other evidence corroborates.
