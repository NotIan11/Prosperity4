# inv09: XGBoost / GBT Price Direction Prediction

**Goal**: Train a gradient-boosted tree model on R5 day 2 capsule data; evaluate OOS
on days 3 & 4; decide whether hand-coded tree inference is worth shipping in v9.

---

## Setup

- **Model**: sklearn `GradientBoostingRegressor` (50 trees, depth 3, lr 0.1, subsample 0.8)
  - xgboost not available in venv; GBR is equivalent for this purpose.
- **Train set**: day 2 only (10,000 ticks × 50 products).
- **OOS eval**: days 3 and 4 separately.
- **Features** (6 total per tick):
  - `bi_l1` — bid imbalance at L1: (bid_vol1 - ask_vol1) / (bid_vol1 + ask_vol1)
  - `bi_l2l3` — bid imbalance at L2+L3 (same formula)
  - `spread` — ask_price_1 - bid_price_1
  - `roll_vol` — rolling 50-tick std of mid-price returns
  - `roll_drift` — rolling 100-tick mean of mid-price returns
  - `tod` — timestamp / 10000 (normalized time-of-day)
- **Target**: forward mid-price return over next 100 ticks
- **Key metrics**: directional accuracy (sign match), R², MAE

---

## Results — All 50 Products (sorted by avg directional accuracy)

| Product | Day3 DirAcc | Day4 DirAcc | Avg DirAcc | Day3 R² | Day4 R² |
|---|---|---|---|---|---|
| TRANSLATOR_GRAPHITE_MIST | 0.5393 | 0.5538 | 0.5465 | -0.1761 | -0.0512 |
| GALAXY_SOUNDS_DARK_MATTER | 0.5316 | 0.5486 | 0.5401 | -0.0401 | -0.0713 |
| PEBBLES_M | 0.5283 | 0.5471 | 0.5377 | -0.3241 | -0.4927 |
| GALAXY_SOUNDS_BLACK_HOLES | 0.5270 | 0.5429 | 0.5350 | -0.1203 | -0.0945 |
| SLEEP_POD_SUEDE | 0.5478 | 0.5207 | 0.5343 | -0.2634 | -0.2141 |
| OXYGEN_SHAKE_CHOCOLATE | 0.5926 | 0.4673 | 0.5300 | -0.0234 | -0.2520 |
| MICROCHIP_RECTANGLE | 0.5331 | 0.5221 | 0.5276 | -0.0946 | -0.0626 |
| ROBOT_MOPPING | 0.5179 | 0.5296 | 0.5237 | -0.3112 | -0.4438 |
| ROBOT_IRONING | 0.4729 | 0.5699 | 0.5214 | -0.4931 | -0.2003 |
| OXYGEN_SHAKE_GARLIC | 0.5145 | 0.5262 | 0.5203 | -0.1279 | -0.0095 |
| UV_VISOR_YELLOW | 0.5370 | 0.5023 | 0.5196 | -0.1696 | -0.3128 |
| GALAXY_SOUNDS_SOLAR_FLAMES | 0.5149 | 0.5223 | 0.5186 | -0.2687 | -0.3443 |
| SLEEP_POD_NYLON | 0.5382 | 0.4976 | 0.5179 | -0.1952 | -0.3794 |
| PEBBLES_XL | 0.4898 | 0.5410 | 0.5154 | -0.1696 | -0.2588 |
| TRANSLATOR_ECLIPSE_CHARCOAL | 0.5278 | 0.4994 | 0.5136 | -0.2139 | -0.3351 |
| TRANSLATOR_VOID_BLUE | 0.5267 | 0.4996 | 0.5131 | -0.1049 | -0.2696 |
| UV_VISOR_AMBER | 0.5331 | 0.4906 | 0.5119 | -0.2670 | -0.2055 |
| SNACKPACK_VANILLA | 0.5698 | 0.4538 | 0.5118 | -0.0864 | -0.3680 |
| MICROCHIP_SQUARE | 0.5036 | 0.5026 | 0.5031 | -0.1745 | -0.3909 |
| OXYGEN_SHAKE_MINT | 0.5012 | 0.5049 | 0.5030 | -0.3195 | -0.1724 |
| ROBOT_LAUNDRY | 0.4979 | 0.5075 | 0.5027 | -0.1643 | -0.1221 |
| SLEEP_POD_POLYESTER | 0.5146 | 0.4904 | 0.5025 | -0.2297 | -0.2494 |
| PANEL_2X4 | 0.4853 | 0.5167 | 0.5010 | -0.3498 | -0.4337 |
| PANEL_2X2 | 0.4908 | 0.5103 | 0.5006 | -0.2482 | -0.1839 |
| SNACKPACK_CHOCOLATE | 0.5519 | 0.4487 | 0.5003 | -0.1084 | -0.2734 |
| UV_VISOR_RED | 0.5168 | 0.4831 | 0.5000 | -0.2389 | -0.3207 |
| PANEL_4X4 | 0.5243 | 0.4736 | 0.4990 | -0.2071 | -0.1642 |
| PANEL_1X2 | 0.5039 | 0.4942 | 0.4990 | -0.3309 | -0.3221 |
| ROBOT_DISHES | 0.4970 | 0.4995 | 0.4982 | -0.1870 | -0.2008 |
| SNACKPACK_RASPBERRY | 0.5332 | 0.4578 | 0.4955 | -0.2327 | -0.4792 |
| PEBBLES_L | 0.4493 | 0.5392 | 0.4942 | -0.4617 | -0.3303 |
| GALAXY_SOUNDS_SOLAR_WINDS | 0.4877 | 0.4998 | 0.4938 | -0.2703 | -0.2182 |
| TRANSLATOR_SPACE_GRAY | 0.4734 | 0.5138 | 0.4936 | -0.3920 | -0.2326 |
| MICROCHIP_CIRCLE | 0.4661 | 0.5200 | 0.4930 | -0.5250 | -0.2758 |
| PANEL_1X4 | 0.4792 | 0.4990 | 0.4891 | -0.3373 | -0.1873 |
| SNACKPACK_PISTACHIO | 0.5358 | 0.4405 | 0.4882 | -0.2922 | -0.5722 |
| MICROCHIP_OVAL | 0.4664 | 0.5006 | 0.4835 | -0.1732 | -0.2164 |
| OXYGEN_SHAKE_MORNING_BREATH | 0.4987 | 0.4672 | 0.4829 | -0.4608 | -0.5366 |
| OXYGEN_SHAKE_EVENING_BREATH | 0.4761 | 0.4897 | 0.4829 | -0.4167 | -0.3566 |
| GALAXY_SOUNDS_PLANETARY_RINGS | 0.5228 | 0.4403 | 0.4816 | -0.3381 | -0.5531 |
| PEBBLES_XS | 0.4600 | 0.4989 | 0.4795 | -0.2788 | -0.3268 |
| UV_VISOR_MAGENTA | 0.4798 | 0.4757 | 0.4778 | -0.1620 | -0.3115 |
| SLEEP_POD_COTTON | 0.4393 | 0.5155 | 0.4774 | -0.4743 | -0.2102 |
| UV_VISOR_ORANGE | 0.4863 | 0.4627 | 0.4745 | -0.1668 | -0.3364 |
| SLEEP_POD_LAMB_WOOL | 0.4835 | 0.4608 | 0.4721 | -0.4146 | -0.4719 |
| MICROCHIP_TRIANGLE | 0.4621 | 0.4820 | 0.4720 | -0.3081 | -0.2535 |
| TRANSLATOR_ASTRO_BLACK | 0.4499 | 0.4927 | 0.4713 | -0.3147 | -0.2255 |
| SNACKPACK_STRAWBERRY | 0.5160 | 0.4122 | 0.4641 | -0.3222 | -0.5590 |
| PEBBLES_S | 0.4813 | 0.4410 | 0.4612 | -0.2060 | -0.1793 |
| ROBOT_VACUUMING | 0.4154 | 0.4864 | 0.4509 | -0.3829 | -0.2743 |

---

## Key Findings

### No product clears the 55% bar on both OOS days

- **Threshold**: directional accuracy > 55% on BOTH day 3 AND day 4.
- **Zero products** pass this gate.
- Best avg is TRANSLATOR_GRAPHITE_MIST at 54.7% (53.9% / 55.4%), just under.
- Second is GALAXY_SOUNDS_DARK_MATTER at 54.0% (53.2% / 54.9%).

### All R² values are negative

Every product has negative R² on both OOS days. This means the model is
**worse than predicting the mean** in terms of magnitude. The directional
signal being marginally above 50% does not translate to useful return
predictions — it only means the model gets the sign right slightly more
than chance when there IS movement.

### Day-to-day instability is significant

Many products flip from high-accuracy on day 3 to low on day 4 (or vice
versa):
- OXYGEN_SHAKE_CHOCOLATE: 59.3% day 3, 46.7% day 4 — large collapse.
- SNACKPACK_VANILLA: 57.0% day 3, 45.4% day 4 — large collapse.
- ROBOT_IRONING: 47.3% day 3, 57.0% day 4 — inverted.

This is the signature of a model overfitting to day-2 regime patterns that
do not persist across days. The best candidates (TRANSLATOR_GRAPHITE_MIST,
GALAXY_SOUNDS_DARK_MATTER, GALAXY_SOUNDS_BLACK_HOLES) are more stable but
still weak.

### No tree dump generated

Per task spec: tree dump is only created if >3 products show >55% accuracy
OOS. Zero products passed. No `inv09_trees.py` file generated.

---

## Ship / Skip Decision

**SKIP. Do not ship XGBoost-as-IF-tree in v9.**

Reasons:
1. No product achieves the minimum 55% directional accuracy OOS on both
   held-out days. The best is ~54.7% average — barely above chance.
2. All R² < 0 on OOS data. The model cannot predict return magnitudes.
3. High day-to-day variance in directional accuracy signals the model is
   fitting day-2-specific microstructure noise, not durable structure.
4. Cost of shipping: hand-coded if/else tree adds code complexity, creates
   a hard dependency on day-2-calibrated thresholds, and violates the
   "prefer sizing tilts over binary gates" lesson (CLAUDE.md pitfalls).
5. The failure mode even at capped position size (5-10 units) is signal
   noise that could hurt MM spreads or create adverse inventory drift on
   hidden day 5.

**What marginal information this provides**:
- TRANSLATOR_GRAPHITE_MIST and the GALAXY_SOUNDS family are the most
  predictable R5 products by GBT metrics (most stable order book
  structure). These may respond better to spread-tightening or
  imbalance-based skew than to directional bets.
- Rolling drift (100-tick) appears to have the most feature importance
  across the ensemble (inferred from R² being least negative for products
  with strong autocorrelation like GALAXY_SOUNDS_DARK_MATTER). This
  aligns with momentum-based skew already in the existing strategy.

---

## Methodology Notes

- Feature engineering includes bid imbalance at two depth levels, spread,
  rolling volatility, rolling drift, and time-of-day.
- Train: ~9,900 labeled samples per product (day 2, with 100-tick lookahead
  buffer removed from end).
- GBR was used in place of XGBoost (not installed in venv); API-equivalent
  for this evaluation purpose.
- Script: `scripts/inv09_xgboost_analysis.py` (not committed).
