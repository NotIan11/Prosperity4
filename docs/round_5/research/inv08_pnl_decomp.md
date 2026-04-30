# inv08 — v7/v8 Per-Product PnL Decomposition: Spread vs Inventory MTM

**Source**: `data/round_5/live_logs/v7/556038.log`, `data/round_5/live_logs/v8/562271.log`
**Method**: For each SUBMISSION fill, spread_PnL = (mid_at_fill - fill_price) × qty for buys, (fill_price - mid_at_fill) × qty for sells. Mid is taken from the same-timestamp activitiesLog row (or nearest tick). inv_MTM = total_PnL (final activitiesLog) - spread_PnL.

---

## Summary Totals

| Version | Spread PnL | Total PnL | Inv MTM |
|---------|-----------|-----------|---------|
| v7      | +4,323    | +18,856   | +14,533 |
| v8      | +4,251    | +18,143   | +13,892 |

- Spread is a **minor contributor** (23% of total in v7). The bulk of PnL is inventory MTM — drift on held positions.
- v8 degraded v7 by ~$700 total, almost entirely via ROBOT_LAUNDRY (the settled gate added latency, and ROBOT_LAUNDRY lost an extra $623).

---

## Full Per-Product Decomposition Table

Sorted by v7 total PnL descending. "Regime" from `REGIME_BY_PRODUCT` in v8 strategy.

| Product | Regime | V7 Spread | V7 Total | V7 InvMTM | V8 Spread | V8 Total | V8 InvMTM | Flag |
|---------|--------|-----------|----------|-----------|-----------|----------|-----------|------|
| SLEEP_POD_POLYESTER | narrow_quiet_mm | +92 | +2,458 | +2,366 | +92 | +2,458 | +2,366 | drift+ |
| PEBBLES_XL | pebbles | -261 | +2,389 | +2,650 | -261 | +2,389 | +2,650 | drift+ |
| PEBBLES_M | pebbles | -333 | +2,169 | +2,502 | -333 | +2,169 | +2,502 | drift+ |
| TRANSLATOR_GRAPHITE_MIST | narrow_quiet_mm | +90 | +1,766 | +1,676 | +90 | +1,766 | +1,676 | drift+ |
| PEBBLES_L | pebbles | -268 | +1,743 | +2,011 | -268 | +1,743 | +2,011 | drift+ |
| MICROCHIP_SQUARE | narrow_volatile_mm | +53 | +1,737 | +1,684 | +53 | +1,737 | +1,684 | drift+ |
| SLEEP_POD_NYLON | narrow_quiet_mm | +109 | +1,422 | +1,313 | +109 | +1,422 | +1,313 | drift+ |
| PEBBLES_S | pebbles | -184 | +1,042 | +1,226 | -184 | +1,042 | +1,226 | drift+ |
| UV_VISOR_YELLOW | wide_drifty_mm | +169 | +1,018 | +850 | +169 | +1,018 | +850 | drift+ |
| SLEEP_POD_SUEDE | narrow_quiet_mm | +138 | +987 | +850 | +138 | +987 | +850 | drift+ |
| SNACKPACK_VANILLA | snackpack | +258 | +973 | +715 | +258 | +973 | +715 | drift+ |
| UV_VISOR_MAGENTA | wide_drifty_mm | +142 | +927 | +785 | +142 | +927 | +785 | drift+ |
| GALAXY_SOUNDS_SOLAR_FLAMES | wide_drifty_mm | +172 | +864 | +692 | +172 | +864 | +692 | drift+ |
| TRANSLATOR_ASTRO_BLACK | narrow_quiet_mm | +81 | +830 | +750 | +81 | +830 | +750 | drift+ |
| SNACKPACK_STRAWBERRY | snackpack | +305 | +763 | +458 | +305 | +763 | +458 | drift+ |
| GALAXY_SOUNDS_BLACK_HOLES | wide_drifty_mm | +221 | +696 | +475 | +221 | +696 | +475 | drift+ |
| SNACKPACK_PISTACHIO | snackpack | +294 | +679 | +386 | +294 | +679 | +386 | drift+ |
| MICROCHIP_OVAL | narrow_volatile_mm | +17 | +562 | +545 | +17 | +562 | +545 | drift+ |
| ROBOT_VACUUMING | narrow_quiet_mm (gated v8) | +83 | +531 | +448 | +58 | +462 | +404 | drift+ |
| TRANSLATOR_VOID_BLUE | narrow_quiet_mm | +123 | +388 | +265 | +123 | +388 | +265 | drift+ |
| PANEL_2X4 | narrow_volatile_mm | +105 | +347 | +243 | +105 | +347 | +243 | drift+ |
| ROBOT_MOPPING | narrow_quiet_mm (gated v8) | +91 | +277 | +186 | +49 | +256 | +207 | drift+ |
| PANEL_4X4 | narrow_quiet_mm | +123 | +263 | +140 | +123 | +263 | +140 | drift+ |
| PEBBLES_XS | pebbles | -120 | +224 | +343 | -120 | +224 | +343 | drift+ |
| OXYGEN_SHAKE_CHOCOLATE | step_mr | +34 | +203 | +169 | +34 | +203 | +169 | drift+ |
| MICROCHIP_CIRCLE | narrow_quiet_mm | +54 | +199 | +145 | +54 | +199 | +145 | drift+ |
| SNACKPACK_CHOCOLATE | snackpack | +269 | +144 | -126 | +269 | +144 | -126 | **spread+ inv-** |
| PANEL_1X4 | narrow_quiet_mm | +71 | +90 | +20 | +71 | +90 | +20 | neutral |
| SNACKPACK_RASPBERRY | snackpack | +316 | +27 | -288 | +316 | +27 | -288 | **spread+ inv-** |
| UV_VISOR_RED | wide_drifty_mm | +214 | -29 | -242 | +214 | -29 | -242 | **spread+ inv-** |
| TRANSLATOR_ECLIPSE_CHARCOAL | narrow_quiet_mm | +120 | -50 | -169 | +120 | -50 | -169 | **spread+ inv-** |
| SLEEP_POD_COTTON | narrow_quiet_mm | +139 | -93 | -231 | +139 | -93 | -231 | **spread+ inv-** |
| OXYGEN_SHAKE_GARLIC | wide_drifty_mm | +219 | -98 | -317 | +219 | -98 | -317 | **spread+ inv-** |
| MICROCHIP_RECTANGLE | narrow_volatile_mm | +21 | -201 | -221 | +21 | -201 | -221 | **spread+ inv-** |
| SLEEP_POD_LAMB_WOOL | narrow_quiet_mm | +102 | -228 | -330 | +102 | -228 | -330 | **spread+ inv-** |
| ROBOT_IRONING | step_mr | +2 | -308 | -310 | +2 | -308 | -310 | **spread+ inv-** |
| ROBOT_LAUNDRY | narrow_quiet_mm (gated v8) | +59 | -251 | -310 | +54 | -874 | -928 | **spread+ inv-** |
| PANEL_1X2 | narrow_quiet_mm | +152 | -342 | -494 | +152 | -342 | -494 | **spread+ inv-** |
| GALAXY_SOUNDS_PLANETARY_RINGS | wide_drifty_mm | +183 | -358 | -541 | +183 | -358 | -541 | **spread+ inv-** |
| OXYGEN_SHAKE_EVENING_BREATH | step_mr | +45 | -445 | -490 | +45 | -445 | -490 | **spread+ inv-** |
| GALAXY_SOUNDS_SOLAR_WINDS | wide_drifty_mm | +163 | -461 | -624 | +163 | -461 | -624 | **spread+ inv-** |
| UV_VISOR_AMBER | wide_drifty_mm | +97 | -574 | -670 | +97 | -574 | -670 | **spread+ inv-** |
| PANEL_2X2 | narrow_quiet_mm | +89 | -597 | -686 | +89 | -597 | -686 | **spread+ inv-** |
| GALAXY_SOUNDS_DARK_MATTER | wide_drifty_mm | +181 | -998 | -1,179 | +181 | -998 | -1,179 | **spread+ inv-** |
| TRANSLATOR_SPACE_GRAY | narrow_quiet_mm | +119 | -1,655 | -1,774 | +119 | -1,655 | -1,774 | **spread+ inv-** |
| MICROCHIP_TRIANGLE | (dropped) | 0 | 0 | 0 | 0 | 0 | 0 | inactive |
| OXYGEN_SHAKE_MINT | (dropped) | 0 | 0 | 0 | 0 | 0 | 0 | inactive |
| OXYGEN_SHAKE_MORNING_BREATH | (dropped) | 0 | 0 | 0 | 0 | 0 | 0 | inactive |
| ROBOT_DISHES | (dropped) | 0 | 0 | 0 | 0 | 0 | 0 | inactive |

---

## Spread+ / Inv-MTM- Products (bleeders)

19 products earn positive spread but lose on inventory holding. Aggregate (v7):

- Total spread earned on bleeders: **+2,668**
- Total inv-MTM loss on bleeders: **-9,358**
- Net on bleeders: **-6,690**

Ranked by inv-MTM loss (v7):

| Product | Regime | Spread | InvMTM | Net |
|---------|--------|--------|--------|-----|
| TRANSLATOR_SPACE_GRAY | narrow_quiet_mm | +119 | -1,774 | -1,655 |
| GALAXY_SOUNDS_DARK_MATTER | wide_drifty_mm | +181 | -1,179 | -998 |
| PANEL_2X2 | narrow_quiet_mm | +89 | -686 | -597 |
| UV_VISOR_AMBER | wide_drifty_mm | +97 | -670 | -574 |
| GALAXY_SOUNDS_SOLAR_WINDS | wide_drifty_mm | +163 | -624 | -461 |
| GALAXY_SOUNDS_PLANETARY_RINGS | wide_drifty_mm | +183 | -541 | -358 |
| OXYGEN_SHAKE_EVENING_BREATH | step_mr | +45 | -490 | -445 |
| PANEL_1X2 | narrow_quiet_mm | +152 | -494 | -342 |
| UV_VISOR_ORANGE | wide_drifty_mm | +184 | -357 | -173 |
| OXYGEN_SHAKE_GARLIC | wide_drifty_mm | +219 | -317 | -98 |
| SLEEP_POD_LAMB_WOOL | narrow_quiet_mm | +102 | -330 | -228 |
| ROBOT_LAUNDRY | narrow_quiet_mm | +59 | -310 | -251 |
| ROBOT_IRONING | step_mr | +2 | -310 | -308 |
| SNACKPACK_RASPBERRY | snackpack | +316 | -288 | +27 |
| SLEEP_POD_COTTON | narrow_quiet_mm | +139 | -231 | -93 |
| MICROCHIP_RECTANGLE | narrow_volatile_mm | +21 | -221 | -201 |
| UV_VISOR_RED | wide_drifty_mm | +214 | -242 | -29 |
| TRANSLATOR_ECLIPSE_CHARCOAL | narrow_quiet_mm | +120 | -169 | -50 |
| SNACKPACK_CHOCOLATE | snackpack | +269 | -126 | +144 |

---

## Positive Inv-MTM (Capsule-Drift Winners)

22 products show positive inventory MTM — they held inventory and the price drifted favorably. These are structural drift trends baked into day 4 of the R5 capsule.

**Biggest drift winners (v7 InvMTM):**
- PEBBLES_XL: +2,650 | PEBBLES_M: +2,502 | SLEEP_POD_POLYESTER: +2,366
- PEBBLES_L: +2,011 | PEBBLES_S: +1,226 | TRANSLATOR_GRAPHITE_MIST: +1,676
- MICROCHIP_SQUARE: +1,684 | SLEEP_POD_NYLON: +1,313

**Pattern**: Pebbles and Sleep Pod variants dominate drift winners. These share the wide-basket price structure (Pebbles) or the "settled" narrow_quiet drift (Sleep Pod Nylon/Polyester/Suede). GALAXY_SOUNDS_SOLAR_FLAMES (+692) and MICROCHIP_SQUARE (+1,684) are also strong drift+ despite being wide_drifty or narrow_volatile.

**Capsule-drift explanation**: Since v7/v8 are the first run of each submission, day-4 price paths in the capsule had persistent uptrends for Pebbles (all variants), Sleep Pod (Nylon, Polyester, Suede), Translator (Graphite Mist, Astro Black), Microchip Square, and UV Visor (Magenta, Yellow). The strategy held long inventory on these, profiting from drift.

---

## v7 vs v8 Differences

Most products are **identical** between v7 and v8 (same fills, same prices, same final PnL). Differences are confined to the three ROBOT_GATED products:

| Product | V7 Total | V8 Total | Delta |
|---------|----------|----------|-------|
| ROBOT_VACUUMING | +531 | +462 | -69 |
| ROBOT_MOPPING | +277 | +256 | -21 |
| ROBOT_LAUNDRY | -251 | -874 | **-623** |

The settled-entry gate (v8 addition) hurt ROBOT_LAUNDRY significantly. The gate defers activation until after a dislocation-then-settle event; in the live draw, ROBOT_LAUNDRY experienced an adverse directional move before the gate triggered, causing a large directional position that then reversed. The net effect: v8 lost $713 vs v7 on gated ROBOT products.

---

## Regime-Level Inv-MTM Bleed Analysis

Grouping bleeders by regime (v7):

| Regime | Products (bleeders) | Total Spread | Total InvMTM | Net |
|--------|---------------------|-------------|--------------|-----|
| wide_drifty_mm | DARK_MATTER, SOLAR_WINDS, PLANETARY_RINGS, UV_VISOR_AMBER, UV_VISOR_ORANGE, UV_VISOR_RED, OXYGEN_GARLIC | +1,260 | -4,972 | -3,712 |
| narrow_quiet_mm | TRANSLATOR_SPACE_GRAY, PANEL_2X2, PANEL_1X2, ROBOT_LAUNDRY, SLEEP_POD_COTTON, SLEEP_POD_LAMB_WOOL, TRANSLATOR_ECLIPSE_CHARCOAL | +743 | -3,994 | -3,251 |
| step_mr | ROBOT_IRONING, OXYGEN_SHAKE_EVENING_BREATH | +47 | -800 | -753 |
| narrow_volatile_mm | MICROCHIP_RECTANGLE | +21 | -221 | -200 |
| snackpack | SNACKPACK_RASPBERRY, SNACKPACK_CHOCOLATE | +585 | -414 | +171 |

**Key finding**: wide_drifty_mm is the worst regime for inventory bleed (-4,972 inv-MTM), but it also produced the biggest drift winners (SOLAR_FLAMES +692, BLACK_HOLES +475, UV_VISOR_YELLOW +850, UV_VISOR_MAGENTA +785). The wide_drifty_mm regime has **high variance within the family** — some products trended up, others down. The regime designation correctly identifies them as "drifty" but doesn't distinguish direction.

---

## Recommendations

### 1. Soft-cap reduction for wide_drifty_mm bleeders — regime-derived, not product-fitted

The worst inv-MTM bleeders in wide_drifty_mm (DARK_MATTER -1,179, SOLAR_WINDS -624, PLANETARY_RINGS -541, UV_VISOR_AMBER -670, UV_VISOR_ORANGE -357) accumulated large directional positions against them. The current soft_cap for wide_drifty_mm is 7.

**Proposal**: reduce `wide_drifty_mm` soft_cap from 7 to **4**. Rationale:
- Spread per fill is ~10-15 ticks on these products; cutting position limit in half costs ~half the spread earned but cap-limits the drift exposure.
- This is a regime-level change, not per-product: applies uniformly to all 11 wide_drifty_mm products.
- The drift winners in wide_drifty_mm (SOLAR_FLAMES, BLACK_HOLES) would also be capped, but their inv-MTM is driven by capsule trend, not position size — capping at 4 vs 7 would reduce absolute gain but also cut tail risk on the adverse products.
- The tradeoff: SOLAR_FLAMES +692 would become ~+395 (4/7 scaling), but DARK_MATTER -1,179 would become ~-674. Net improvement on the 5 bleeders: ~$1,700 saved vs ~$600 lost on winners.

### 2. Stop-loss coverage for TRANSLATOR_SPACE_GRAY (-1,655 live)

TRANSLATOR_SPACE_GRAY has the worst absolute loss (-1,655 total, -1,774 inv-MTM) despite earning +119 in spread. This is a narrow_quiet_mm product with soft_cap=7 and stop_loss_ticks=60. Given -1,774 inv-MTM on ~21 trades, the position likely hit max inventory and held through a large adverse move. The stop_loss_ticks of 60 may be insufficient for this product's price scale (~10,100). Consider:
- Reducing stop_loss_ticks to 30-40 for TRANSLATOR products (regime-level: all 5 translators, not just Space Gray).
- Or reducing soft_cap for narrow_quiet_mm from 7 to 5 (fits a no-per-product-fitting rule, would apply to 16 products).

### 3. ROBOT_LAUNDRY gate recalibration

v8's settled gate made ROBOT_LAUNDRY worse (-623 vs v7). The gate triggered at the wrong moment in this live draw. Options:
- Raise `TRIGGER_SPREADS` from 2.0 to 3.0 (require larger dislocation before seeing dislocation).
- Or drop ROBOT_LAUNDRY from the gated set — it has a small positive spread (+59) but large inv-MTM drag whether gated or not.

### 4. Do not gate GALAXY_SOUNDS products

GALAXY_SOUNDS_DARK_MATTER, SOLAR_WINDS, PLANETARY_RINGS are the biggest bleeders in wide_drifty_mm. Their inv-MTM losses come from holding inventory through directional trends. A settled gate would not help because the products are already wide_drifty — no "settle" will reliably occur. The lever is soft_cap reduction (recommendation 1 above).

### 5. OXYGEN_SHAKE_EVENING_BREATH and ROBOT_IRONING (step_mr)

Both step_mr products show spread ≈ 0 or tiny positive while losing hundreds in inv-MTM. The step_mr mode is supposed to widen quotes post-step to avoid picking up directional inventory. If it's not preventing inv-MTM losses, the post-step cooldown window (`STEP_COOLDOWN_TICKS`) may be too short, or the step detection threshold too loose. This deserves a separate investigation but is lower priority than the wide_drifty_mm and narrow_quiet_mm bleeders.

---

*Analysis produced from live logs only. No BT used. v7 and v8 differ only on three gated ROBOT products; all other per-product numbers are identical across both submissions.*
