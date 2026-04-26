# BT vs Live Portal — calibration & dip verification

## TL;DR

- **The IMC portal sim is the first 1,000 ticks of historical day 2** —
  verified byte-perfect against our local CSV (Discord claim from
  `theethan7114` and `zhng.harry`, see `08a_discord_algo_trading.md`).
- **The "dip" everyone reports is real and reproducible in BT** at day-2
  ticks 91,000–99,900. Same peak tick (91,100) in BT and live portal.
- **BT systematically over-reports our PnL by ~37%** vs live (calibration
  factor ≈ 0.73). Use `scripts/bt_dual.py` to track both numbers per version.

## Verification — market data identity

Comparing live portal log (v4 submission `465613.json`) against BT day-2
output (`prosperity4btest cli src/trader.py 3-2`):

| Comparison | Result |
|---|---|
| Tick range in portal | `0` to `99,900` step `100` (1,000 ticks) |
| Tick range in BT day 2 | `0` to `999,900` step `100` (10,000 ticks) |
| Day field in portal | `2` |
| Day field in BT cropped | `2` |
| **Market data rows** (12,000 rows × 17 market columns at tick ≤ 99,900) | **byte-identical** |
| Sample tick-0 quotes (HG, VFE, VEV_5300) | exact match across all 3 |

So the portal slice is **literally** running our trader against the same data
the BT runs against (just truncated to the first 1/10 of day 2).

## The dip — same in BT and live

| | BT (cropped to 0-99,900) | Live portal |
|---|---|---|
| Peak PnL | +3,108.5 | +2,397.0 |
| **Peak tick** | **91,100** | **91,100** ← same |
| Final PnL @ 99,900 | +1,678.0 | +1,220.1 |
| Peak → final drop | -1,430.5 (-46% of peak) | -1,176.9 (-49% of peak) |

The dip is **a real market event** at day-2 ticks 91k-99k. Not a portal
artifact, not a hidden-FV liquidation mark. BT can investigate fixes for it.

## Why BT > Live in PnL despite identical data

Same market data, different fill matching:

| Layer | BT | Live portal |
|---|---|---|
| Orderbook + market trades | Real day-2 data | Same real day-2 data |
| Bot fleet | Frozen historical replay | Real bots in real-time |
| Our quote → fill matching | Matched against historical trades that printed at our price | Matched against bots who can see our orders and may avoid them |

Two structural reasons live < BT:

1. **Bot avoidance**: real bots see our resting quote and may step around it.
   In BT, bot trades are pre-recorded — they fill us regardless.
2. **Adversarial response**: real bots may shift their own quotes when ours
   land inside the wall. BT has no such reactivity.

## Calibration factor

For trader v4 (HG sym + VFE asymmetric + L1-L2 skew):

```
BT day-2 first-1000-tick PnL:  1,678
Live portal PnL:               1,220
Ratio (live / BT_slice):       0.727
```

Estimating live for v6 using the v4 ratio:
```
v6 BT_slice = 1,678 (we'll re-measure post-trade); live ≈ 1,225
```

We should refine this ratio with each fresh live submission; it may shift
with code changes.

## Dual-BT runner

`scripts/bt_dual.py` runs both modes per version and prints:

```
Full 3-day BT total:           ← ranking metric
BT day-2 only:                 ← isolates day-2 effects
BT day-2 first-1000-tick PnL:  ← portal-equivalent BT
Estimated live portal PnL:     ← BT_slice / 1.37
```

Use this on every version going forward.

## Open questions / risks

- **Calibration factor stability**: 0.73 measured on v4 only. Could drift
  with more aggressive strategies (more inside-wall quoting → more bot
  avoidance → lower ratio). Re-measure per submission.
- **Dip mechanism**: still unidentified. Possibilities:
  - Inventory MTM hit (positions accumulated 50-90k get marked down at 91-99k)
  - Specific bot regime change at those ticks (informed flow burst)
  - Spread regime change (book widens, our quotes go stale)
  - Pure underlying mid drift against our position bias
- **Generalizability**: the dip is at a SPECIFIC location in day-2 data.
  R3 scoring uses *new* unseen data — will the same dip exist there?
  We can't know without seeing the new data. But the *mechanism* (whatever
  it is) might recur. Per-product PnL decomposition during the dip will
  tell us if it's a tunable defense or just bad luck on this slice.
