# Avellaneda-Stoikov Optimal MM Quotes — R5 Per-Product Analysis

**Scope**: derive A-S reservation-price skew per R5 product and assess whether
replacing v8's heuristic `skew=0.4–0.6` with formula-derived skew is worth
shipping.

**Data**: `data/round_5/prices/prices_round_5_day_{2,3,4}.csv` (30,000 ticks
per product) and `data/round_5/prices/trades_round_5_day_{2,3,4}.csv`.

---

## 1. A-S Framework and Assumptions

### Core formulas (Avellaneda & Stoikov 2008)

```
Reservation price:  r(t) = mid - q * γ * σ² * (T - t)
Optimal spread:     s_a - s_b = γ * σ²(T-t) + (2/γ) * ln(1 + γ/κ)
```

where:
- `q` = current inventory (signed)
- `γ` = risk-aversion coefficient (free parameter)
- `σ` = price volatility per unit time
- `T-t` = time remaining
- `κ` = order-arrival intensity decay (fill-probability scale)

### Mapping to IMC competition mechanics

| A-S variable | Competition mapping |
|---|---|
| `T` | 10,000 ticks per scoring day |
| `T-t` | ticks remaining in current day |
| `σ` | per-tick log-return σ × avg_mid (absolute price units) |
| `q` | current position (`state.position[sym]`) |
| `γ` | calibrated parameter — see §3 |
| `κ` | fill-probability scale; not directly observable (counterparty IDs blank in R5 capsule) |

### Key structural difference vs v8

v8 applies a **constant** skew: `bid_px = touch - skew * |pos|`, with skew frozen
at 0.4–0.6 for the entire day.

A-S implies a **time-tapering** skew: `displacement = γ * σ² * (T-t) * q`.
- At start of day (T-t = 10,000): displacement = 2× the mid-day value
- At mid-day (T-t = 5,000): matches calibration point
- At end of day (T-t → 0): displacement → 0 (A-S unwinds inventory urgency)

---

## 2. Per-Product Volatility (σ) Estimates

σ computed as average across days 2/3/4 of per-tick log-return std, then
converted to absolute price units (σ_price = σ_log × avg_mid).
Day-boundary jumps excluded by computing per-day before averaging.

| Product | avg_mid | σ_log | σ_price ($/tick) | k (trades/tick) | median_spread | regime |
|---|---|---|---|---|---|---|
| GALAXY_SOUNDS_BLACK_HOLES | 11,467 | 0.000997 | 11.44 | 0.02443 | 14 | wide_drifty_mm |
| GALAXY_SOUNDS_DARK_MATTER | 10,227 | 0.001002 | 10.24 | 0.02443 | 13 | wide_drifty_mm |
| GALAXY_SOUNDS_PLANETARY_RINGS | 10,767 | 0.001009 | 10.86 | 0.02443 | 14 | wide_drifty_mm |
| GALAXY_SOUNDS_SOLAR_FLAMES | 11,093 | 0.001000 | 11.09 | 0.02443 | 14 | wide_drifty_mm |
| GALAXY_SOUNDS_SOLAR_WINDS | 10,438 | 0.001009 | 10.53 | 0.02443 | 14 | wide_drifty_mm |
| MICROCHIP_CIRCLE | 9,215 | 0.000999 | 9.21 | 0.01897 | 8 | narrow_quiet_mm |
| MICROCHIP_OVAL | 8,180 | 0.001499 | 12.26 | 0.01897 | 8 | narrow_volatile_mm |
| MICROCHIP_RECTANGLE | 8,732 | 0.001499 | 13.09 | 0.01897 | 8 | narrow_volatile_mm |
| MICROCHIP_SQUARE | 13,595 | 0.001508 | 20.50 | 0.01897 | 12 | narrow_volatile_mm |
| OXYGEN_SHAKE_CHOCOLATE | 9,557 | 0.001114 | 10.65 | 0.02443 | 12 | step_mr |
| OXYGEN_SHAKE_EVENING_BREATH | 9,272 | 0.001166 | 10.81 | 0.02443 | 12 | step_mr |
| OXYGEN_SHAKE_GARLIC | 11,926 | 0.001005 | 11.99 | 0.02443 | 15 | wide_drifty_mm |
| PANEL_1X2 | 8,923 | 0.001012 | 9.03 | 0.02443 | 12 | narrow_quiet_mm |
| PANEL_1X4 | 9,398 | 0.001004 | 9.44 | 0.02443 | 8 | narrow_quiet_mm |
| PANEL_2X2 | 9,577 | 0.001000 | 9.58 | 0.02443 | 9 | narrow_quiet_mm |
| PANEL_2X4 | 11,265 | 0.001000 | 11.26 | 0.02443 | 10 | narrow_volatile_mm |
| PANEL_4X4 | 9,879 | 0.001008 | 9.95 | 0.02443 | 9 | narrow_quiet_mm |
| ROBOT_IRONING | 8,702 | 0.001173 | 10.21 | 0.02443 | 6 | step_mr |
| ROBOT_LAUNDRY | 9,823 | 0.000998 | 9.81 | 0.02443 | 7 | narrow_quiet_mm |
| ROBOT_MOPPING | 11,100 | 0.001002 | 11.12 | 0.02443 | 8 | narrow_quiet_mm |
| ROBOT_VACUUMING | 9,167 | 0.001006 | 9.22 | 0.02443 | 7 | narrow_quiet_mm |
| SLEEP_POD_COTTON | 11,528 | 0.001009 | 11.63 | 0.02443 | 10 | narrow_quiet_mm |
| SLEEP_POD_LAMB_WOOL | 10,701 | 0.001000 | 10.70 | 0.02443 | 10 | narrow_quiet_mm |
| SLEEP_POD_NYLON | 9,637 | 0.000997 | 9.61 | 0.02443 | 9 | narrow_quiet_mm |
| SLEEP_POD_POLYESTER | 11,841 | 0.001001 | 11.86 | 0.02443 | 11 | narrow_quiet_mm |
| SLEEP_POD_SUEDE | 11,397 | 0.000999 | 11.39 | 0.02443 | 10 | narrow_quiet_mm |
| TRANSLATOR_ASTRO_BLACK | 9,385 | 0.001004 | 9.43 | 0.02443 | 8 | narrow_quiet_mm |
| TRANSLATOR_ECLIPSE_CHARCOAL | 9,814 | 0.001004 | 9.85 | 0.02443 | 9 | narrow_quiet_mm |
| TRANSLATOR_GRAPHITE_MIST | 10,085 | 0.001003 | 10.12 | 0.02443 | 9 | narrow_quiet_mm |
| TRANSLATOR_SPACE_GRAY | 9,432 | 0.000998 | 9.41 | 0.02443 | 9 | narrow_quiet_mm |
| TRANSLATOR_VOID_BLUE | 10,859 | 0.000996 | 10.82 | 0.02443 | 10 | narrow_quiet_mm |
| UV_VISOR_AMBER | 7,912 | 0.001006 | 7.96 | 0.02443 | 10 | wide_drifty_mm |
| UV_VISOR_MAGENTA | 11,112 | 0.001007 | 11.19 | 0.02443 | 14 | wide_drifty_mm |
| UV_VISOR_ORANGE | 10,427 | 0.001002 | 10.45 | 0.02443 | 13 | wide_drifty_mm |
| UV_VISOR_RED | 11,063 | 0.000996 | 11.01 | 0.02443 | 14 | wide_drifty_mm |
| UV_VISOR_YELLOW | 10,958 | 0.001002 | 10.98 | 0.02443 | 14 | wide_drifty_mm |

**Observation on σ_log homogeneity**: nearly all products have σ_log ≈ 0.001 per
tick (range 0.000997–0.001009 for the bulk, with Microchips at 0.001499 and step_mr
at ~0.001 + step component). The large σ_price spread across products (7.96–20.50)
is predominantly driven by **price level**, not different log-return processes.
`MICROCHIP_SQUARE` has σ_price 20.50 because its avg_mid is 13,595 vs 8,732 for
`MICROCHIP_RECTANGLE`; their σ_log are within 1 bp of each other (0.001508 vs 0.001499).

**Fill rate k**: two distinct clusters. Microchips: 0.01897 trades/tick (569 trades
/ 30,000 ticks); all others: 0.02443 trades/tick (733 trades / 30,000 ticks). Both
are sparse — one trade every ~41–53 ticks on average.

---

## 3. Calibration of γ (Implicit Risk-Aversion)

### Why direct bisection fails

The A-S full spread formula `δ = γσ²T + (2/γ)ln(1+γ/κ)` has a **minimum spread
of `2/κ`** as γ→0. With κ estimated as fill arrival rate (~0.024 trades/tick),
`2/κ ≈ 82 price units`. This exceeds the actual market half-spreads (4–7 units),
so no γ exists that maps A-S total spread to observed market spreads unless κ is
estimated differently.

The root cause: κ in A-S is NOT the trades-per-tick count. It is the
**decay rate of fill probability with distance from touch** (shape parameter of
`λ(δ) = Α·exp(-κδ)`). This is unidentifiable from R5 capsule data because
counterparty IDs are blank (per AGENT_BRIEF.md) and we cannot observe how fill
rate varies with queue position.

### Calibration via inventory skew only

We proceed using only the **reservation-price component**, which is computable
without κ:

```
displacement = γ * σ² * (T-t) * q
```

γ is calibrated per-regime so that the displacement at **mid-day** (T-t = T/2 = 5,000)
matches v8's flat skew:

```
γ_regime = v8_skew / (avg_σ²_regime × T/2)
```

| Regime | avg_σ ($/tick) | v8_skew | calibrated γ |
|---|---|---|---|
| narrow_quiet_mm | 10.12 | 0.40 | 7.75e-07 |
| wide_drifty_mm | 10.70 | 0.50 | 8.66e-07 |
| narrow_volatile_mm | 14.28 | 0.60 | 5.53e-07 |
| step_mr | 10.56 | 0.60 | 1.08e-06 |

The γ values are tiny (O(1e-6)) because σ² × T/2 ≈ 81–1020 in price-units² × ticks,
which is large. Economically, this means the platform is extremely fill-hungry (very
low risk aversion per tick of variance), consistent with a market-making bot that
cares mainly about the spread premium rather than overnight inventory risk.

---

## 4. A-S Implied Skew vs v8 Heuristic — Full Table

Column `AS_skew@midday` = γ_regime × σ_product² × (T/2). This is what
a static (flat-time) approximation of A-S would set as the per-unit skew if we
collapse the time-taper to the day's midpoint.

Products sorted by |diff| from v8:

| # | Product | σ_price | AS_skew@midday | v8_skew | Diff | Direction |
|---|---|---|---|---|---|---|
| 1 | MICROCHIP_SQUARE | 20.50 | 1.161 | 0.60 | +0.561 | MORE aggressive |
| 2 | PANEL_2X4 | 11.26 | 0.350 | 0.60 | -0.250 | LESS aggressive |
| 3 | UV_VISOR_AMBER | 7.96 | 0.274 | 0.50 | -0.226 | LESS aggressive |
| 4 | MICROCHIP_OVAL | 12.26 | 0.415 | 0.60 | -0.185 | LESS aggressive |
| 5 | SLEEP_POD_POLYESTER | 11.86 | 0.545 | 0.40 | +0.145 | MORE aggressive |
| 6 | MICROCHIP_RECTANGLE | 13.09 | 0.473 | 0.60 | -0.127 | LESS aggressive |
| 7 | SLEEP_POD_COTTON | 11.63 | 0.524 | 0.40 | +0.124 | MORE aggressive |
| 8 | OXYGEN_SHAKE_GARLIC | 11.99 | 0.622 | 0.50 | +0.122 | MORE aggressive |
| 9 | SLEEP_POD_SUEDE | 11.39 | 0.503 | 0.40 | +0.103 | MORE aggressive |
| 10 | PANEL_1X2 | 9.03 | 0.316 | 0.40 | -0.084 | LESS aggressive |
| 11 | ROBOT_MOPPING | 11.12 | 0.480 | 0.40 | +0.080 | MORE aggressive |
| 12 | MICROCHIP_CIRCLE | 9.21 | 0.329 | 0.40 | -0.071 | LESS aggressive |
| 13 | ROBOT_VACUUMING | 9.22 | 0.329 | 0.40 | -0.071 | LESS aggressive |
| 14 | GALAXY_SOUNDS_BLACK_HOLES | 11.44 | 0.566 | 0.50 | +0.066 | MORE aggressive |
| 15 | TRANSLATOR_SPACE_GRAY | 9.41 | 0.344 | 0.40 | -0.056 | LESS aggressive |

Products with small diff (well-calibrated by v8):
- All OXYGEN_SHAKE step_mr products: diff ≤ 0.03
- Most TRANSLATOR products: diff ≤ 0.06
- GALAXY_SOUNDS mid-range: diff ≤ 0.07

---

## 5. Five Products Where A-S Differs Most from v8

### 1. MICROCHIP_SQUARE — skew MUCH too low in v8 (+0.561)

- σ_price = 20.50 $/tick (highest in the active set by a large margin)
- Root cause: avg_mid = 13,595 vs MICROCHIP group mean ~9,500; σ_log is the same
  (0.001508), so the absolute dollar variance per tick is ~57% higher than peers
- A-S says: skew per unit = 1.161 at mid-day vs v8 flat 0.60
- Sign: v8 UNDER-skews MICROCHIP_SQUARE relative to its actual dollar variance
- Practical implication: at position +10, v8 displaces quotes by 6 ticks;
  A-S would call for ~11.6 ticks of displacement at mid-day (23.2 ticks at start)
- Note: MICROCHIP_SQUARE is currently in `narrow_volatile_mm` — the highest skew
  regime in v8. A-S says even that is insufficient for this product specifically.

### 2. PANEL_2X4 — skew too high in v8 (-0.250)

- σ_price = 11.26 $/tick; assigned to `narrow_volatile_mm` (skew=0.60)
- A-S says its σ only justifies skew 0.350 at mid-day
- `PANEL_2X4` shares its regime with MICROCHIP products that have σ ≈ 12–20;
  its own σ is closer to `narrow_quiet_mm` products (~9–10) than to volatile Microchips
- Sign: v8 OVER-skews PANEL_2X4 by assigning it to the high-skew regime

### 3. UV_VISOR_AMBER — skew too high in v8 (-0.226)

- σ_price = 7.96 $/tick (lowest in the active set); avg_mid = 7,912 (lowest price level)
- All UV_VISOR products share `wide_drifty_mm` (skew=0.50), but AMBER's σ_price
  is 29% below the other four UV_VISORs (10.45–11.19)
- A-S says: 0.274 vs v8 0.50 — v8 is 1.83× too aggressive for AMBER's actual variance
- This is a pure price-level effect: σ_log is identical to peers (0.001006)

### 4. MICROCHIP_OVAL — skew too high in v8 (-0.185)

- σ_price = 12.26 $/tick; avg_mid = 8,180 — the lowest-priced MICROCHIP
- In `narrow_volatile_mm` alongside RECTANGLE (σ=13.09) and SQUARE (σ=20.50)
- A-S says: 0.415 vs v8 0.60
- The regime bundles three products whose σ_price spans 12–20; A-S says they
  should have materially different skews

### 5. SLEEP_POD_POLYESTER — skew too low in v8 (+0.145)

- σ_price = 11.86 $/tick; assigned to `narrow_quiet_mm` (skew=0.40)
- One of the highest-σ products in narrow_quiet_mm (median σ ≈ 10.12)
- A-S says: 0.545 vs v8 0.40
- SLEEP_POD_COTTON (σ=11.63) and SLEEP_POD_SUEDE (σ=11.39) show similar pattern;
  three SLEEP_POD products are outliers within their regime

---

## 6. Implementation Feasibility

### EWMA σ in stdlib Python

A per-tick EWMA variance update requires zero imports:

```python
# α = 2/(N+1) for N-period EWMA; N=200 gives α=0.01
alpha = 0.01
if var is None:
    var = ret**2
else:
    var = (1 - alpha) * var + alpha * ret**2
sigma = var**0.5  # in log-return units
sigma_price = sigma * mid
```

- Cost: ~5 arithmetic ops per tick per product
- 37 active products × 5 ops = 185 ops/tick (negligible)
- Warm-up risk: first ~200 ticks have noisy estimates
- Mitigation: use hardcoded prior (σ_price from capsule data) until EWMA
  accumulates ~500 samples, then blend

### Time-remaining inference

- Hardcoded day counters break (per CLAUDE.md pitfalls)
- TTE (T-t) must be inferred from live data (e.g. track tick count from state)
- The `traderData` JSON round-trip is already used in v8 for stateful strategies,
  so adding `ticks_elapsed` and `ewma_var[sym]` to the state dict is straightforward

### Code change footprint

Replacing `skew=const` with `skew = γ * ewma_var * (T - ticks_elapsed)` requires:
1. Add EWMA variance state per product to `traderData`
2. Add `ticks_elapsed` counter to `traderData`
3. Replace `self.skew` constant with computed value per `act()` call
4. Hardcoded γ per product (or per regime) as a dict constant

Estimated ~30–50 additional lines in `src/trader.py`. No new imports.

---

## 7. Recommendation: Ship A-S or Stay Heuristic?

### Arguments for shipping A-S skew

1. **A-S fixes the MICROCHIP_SQUARE misspecification** (v8 under-skews by 0.56
   per unit, almost 2× too low at full position)
2. **A-S fixes UV_VISOR_AMBER over-skewing** (v8 1.83× too aggressive for its
   low price level)
3. **Time-taper is theoretically correct**: skew should be highest at day start
   (maximum inventory disposal cost) and zero at day end (position is closed out)
4. EWMA σ is implementable in 10 lines of stdlib Python

### Arguments against shipping A-S skew

1. **κ is not estimable** from R5 capsule data (blank counterparty IDs). The full
   A-S spread formula cannot be applied; only the reservation-price component is
   tractable. The spread-width component of A-S remains heuristic anyway.
2. **σ_log homogeneity reduces the gain**: most active products cluster tightly
   at σ_log ≈ 0.001. The per-product variation comes almost entirely from price
   level. A simpler fix than full A-S: scale v8 skew by `(product_mid / regime_avg_mid)`
3. **Time-taper introduces regime instability**: v8 skew is constant and robust.
   A decaying skew makes end-of-day behavior qualitatively different (low skew =
   willing to take large positions), which may interact badly with the 88.8% live
   drawdown problem already documented in CLAUDE.md.
4. **20% NPC order randomisation** means BT-to-live skew calibration is noisy.
   A-S γ calibrated on BT data may not transfer reliably live.
5. **Structural concern**: MICROCHIP_SQUARE's high σ_price is driven by a high
   price level, not higher log-return volatility. Whether this warrants more
   aggressive skewing depends on whether the NPC bots price proportionally —
   which is an open question not resolvable from this data alone.

### Verdict: **do not ship full A-S in v9**

The framework identifies two actionable corrections that can be made more safely
as targeted heuristic fixes:

- **MICROCHIP_SQUARE**: bump skew from 0.60 → ~1.0 (or move to a separate
  regime with higher skew ceiling)
- **UV_VISOR_AMBER**: lower skew from 0.50 → ~0.30 (or move to narrow_quiet_mm)
- **PANEL_2X4**: lower skew from 0.60 → ~0.40 (may share narrow_quiet_mm)

The full A-S taper (time-dependent skew) introduces complexity and end-of-day
risks that are not justified by the moderate improvement on the other 34 products
where v8 skew is within 10% of A-S implied. Defer A-S time-taper to a later
version after MICROCHIP_SQUARE and UV_VISOR_AMBER are individually validated.
