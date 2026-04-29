# Round 5 — Official Brief

> Sources: IMC Prosperity 4 Notion brief + R5 ARIA video transcript,
> pasted by user 2026-04-28. Facts only — no inference or strategy.

## Additions from ARIA video (transcript)

- **Manual currency name: "Zyrex"** ("a separate budget of 1 million Zyrex").
- **Manual market location: Ignith** (neighboring planet, "active volcanoes and magnificent magma lakes" — flavor).
- **Manual scope confirmed:** standalone, "does not affect your algorithmic trading activities."
- **48 hours** to round close from the time of the video.
- **No clarifications on the algo mechanic** beyond the brief — same 50 products / 10 categories language.
- ARIA explicitly nudges checking the wiki, the onboard adviser, and Discord. No new mechanics revealed.

## Framing

Final round. Last chance to climb the leaderboard.

The **FTW** has introduced **50 new tradable goods** to replace previous ones for algorithmic trading. **Products from previous rounds are no longer tradable.** The 50 are evenly distributed across 10 categories of 5.

In addition: a one-day-only manual trading event on the neighboring planet **Ignith**, with a news source called **Ashflow Alpha** and 9 available goods.

## Round Objective

- Create one final Python program to trade selected goods from the 10 available categories.
- Use the Ashflow Alpha news source to devise a strategy and trade a selection of the 9 available Ignith resources for the final manual profit.

## Algorithmic challenge — "Cherry Picking Winners"

- 50 new products. Cannot trade prior-round products.
- 50 products = 10 groups × 5.
- "Each group has its own story, but some offer more market inefficiencies than others. In certain groups, strong patterns are embedded in the price movements, waiting to be discovered by you."
- "You can capitalize on these opportunities, while developing an effective trading strategy for the other products."
- **Position limit: 10 for every product.**

### Categories (10 × 5 = 50 products)

**Galaxy Sounds Recorders**
- `GALAXY_SOUNDS_DARK_MATTER`, `GALAXY_SOUNDS_BLACK_HOLES`, `GALAXY_SOUNDS_PLANETARY_RINGS`, `GALAXY_SOUNDS_SOLAR_WINDS`, `GALAXY_SOUNDS_SOLAR_FLAMES`

**Vertical Sleeping Pods**
- `SLEEP_POD_SUEDE`, `SLEEP_POD_LAMB_WOOL`, `SLEEP_POD_POLYESTER`, `SLEEP_POD_NYLON`, `SLEEP_POD_COTTON`

**Organic Microchips**
- `MICROCHIP_CIRCLE`, `MICROCHIP_OVAL`, `MICROCHIP_SQUARE`, `MICROCHIP_RECTANGLE`, `MICROCHIP_TRIANGLE`

**Purification Pebbles**
- `PEBBLES_XS`, `PEBBLES_S`, `PEBBLES_M`, `PEBBLES_L`, `PEBBLES_XL`

**Domestic Robots**
- `ROBOT_VACUUMING`, `ROBOT_MOPPING`, `ROBOT_DISHES`, `ROBOT_LAUNDRY`, `ROBOT_IRONING`

**UV-Visors**
- `UV_VISOR_YELLOW`, `UV_VISOR_AMBER`, `UV_VISOR_ORANGE`, `UV_VISOR_RED`, `UV_VISOR_MAGENTA`

**Instant Translators**
- `TRANSLATOR_SPACE_GRAY`, `TRANSLATOR_ASTRO_BLACK`, `TRANSLATOR_ECLIPSE_CHARCOAL`, `TRANSLATOR_GRAPHITE_MIST`, `TRANSLATOR_VOID_BLUE`

**Construction Panels**
- `PANEL_1X2`, `PANEL_2X2`, `PANEL_1X4`, `PANEL_2X4`, `PANEL_4X4`

**Liquid Breath Oxygen Shakes**
- `OXYGEN_SHAKE_MORNING_BREATH`, `OXYGEN_SHAKE_EVENING_BREATH`, `OXYGEN_SHAKE_MINT`, `OXYGEN_SHAKE_CHOCOLATE`, `OXYGEN_SHAKE_GARLIC`

**Protein Snack Packs**
- `SNACKPACK_CHOCOLATE`, `SNACKPACK_VANILLA`, `SNACKPACK_PISTACHIO`, `SNACKPACK_STRAWBERRY`, `SNACKPACK_RASPBERRY`

## Manual challenge — "Extra! Extra! Read all about it!"

One-day trade on the **Ignith** exchange. Hold until the next day. Use the **Ashflow Alpha** news source to inform portfolio construction.

- 9 tradable Ignith goods.
- "Be aware that trading these foreign goods comes at a price. The more you trade in one good, the more expensive it will get."

### Fee formula

```
fee = (volume_for_specific_product / 100) * (volume_for_specific_product / 100) * budget
```

(User confirmed 2026-04-28: the original brief had `**` which was a formatting artifact; the correct operator is `*`. Quadratic in volume, scaled linearly by budget.)

- **Budget = 1,000,000.**
- May distribute **less than 100%** of the budget.
- May **not** distribute more than 100%.
- Used budget is subtracted from trade PnL.
- Unused budget expires worthless (not added to profit).

### Submission

- Input order details directly in Manual Challenge Overview. Re-submittable until round ends. Last submitted orders are locked in.
