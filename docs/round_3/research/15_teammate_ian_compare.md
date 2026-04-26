# Teammate algorithm comparison — Ian's R3 trader

Sources:
- v1 Ian: `data/teammate_logs/ian/464669.{py,json,log}` — live PnL **13,267**
- v2 Ian: `data/teammate_logs/ian2/471212.{py,json,log}` — live PnL **13,528**

---

## v2 vs v1 — TL;DR

Ian widened the voucher chain from 3 strikes (5100/5200/5300) to **8 strikes**
(4000/4500/5000/5100/5200/5300/5400/5500), reusing the **same delta-1
VFE-signal strategy** for every strike. Net live PnL improved only **+261
(13,267 → 13,528)** because deep-ITM strikes lost (VEV_4000 −1,350, VEV_4500
−306) and were nearly cancelled by the new winners (VEV_5000 +1,318,
VEV_5400 +492, VEV_5500 +108). HG, VFE, and the original 3 strikes are
**byte-identical** in PnL.

## Code diff (per product)

- **HYDROGEL_PACK** — unchanged. Same fixed FAIR=9991, take/passive/derisk logic.
- **VELVETFRUIT_EXTRACT** — unchanged. Same FV=5250 mean-reversion, ±20 entry, 40-tick stop.
- **VEV_5100/5200/5300** — unchanged.
- **VevOptionStrategy class** — unchanged logic; only cosmetic reformatting and
  a deleted backtest comment.
- **PRODUCTS dict** — added `VEV_4000`, `VEV_4500`, `VEV_5000`, `VEV_5400`,
  `VEV_5500` (all pos_limit=300, same strategy instance).
- No new HG/VFE features. No strike-aware delta. No skew. No vol surface.

## Per-strike voucher PnL (final tick, day 2 portal slice)

| Product | v1 PnL | v2 PnL | Δ | Notes |
|---|---|---|---|---|
| HYDROGEL_PACK | +8,558 | +8,558 | 0 | identical |
| VELVETFRUIT_EXTRACT | +992 | +992 | 0 | identical |
| VEV_4000 | — | **−1,350** | new (deep ITM, delta≈1 but priced near intrinsic; signal noisy) |
| VEV_4500 | — | **−306** | new (ITM) |
| VEV_5000 | — | **+1,318** | new (near-ATM, signal works) |
| VEV_5100 | +1,458 | +1,458 | 0 |
| VEV_5200 | +1,087 | +1,087 | 0 |
| VEV_5300 | +1,173 | +1,173 | 0 |
| VEV_5400 | 0 | **+492** | new (slightly OTM) |
| VEV_5500 | 0 | **+108** | new (OTM, thin) |
| **Total** | **13,267** | **13,528** | **+261** | |

## What Ian learned / changed

1. **Recognised vouchers are tradeable across the chain**, not just 5100–5300.
2. **Did NOT discriminate by strike** — applied identical FV±20 trigger and
   pos_limit=300 to every voucher. Deep-ITM vouchers don't respond linearly
   to small VFE deviations the way ATM does, so VEV_4000/4500 bled.
3. Net result: marginal improvement; the broader chain is roughly a wash.

## New ideas worth porting to v8 (additions to plan)

- **Trade VEV_5000 directly with VFE-signal** (Ian's biggest new winner,
  +1,318). This is still near-ATM and behaves close to delta-1. Add to
  v10 alongside 5100/5200/5300.
- **Trade VEV_5400 cautiously** (+492). Already on our radar from v6.
  Confirms it's worth more aggressive sizing than passive bias quotes.
- **Skip VEV_4000 / 4500 / 5500** in any port. Empirically negative or thin.
  Our v6 instinct (only quote where edge is provable) was correct.
- **Strike-aware delta is the missing piece**: a proper delta×ΔS sizing
  would have made the 4000/4500 strikes profitable instead of bleeding.
  Candidate v11 if we want to push further.

## Risks Ian still has (v2)

- **All v1 risks persist**: hardcoded HG FV=9991, VFE FV=5250, end-of-portal
  positions at limit on multiple strikes.
- **New: deep-ITM strikes leak ~1.6k.** No strike-aware delta means small
  VFE deviations trigger full-size positions in vouchers that don't move
  with VFE 1:1 — the stop-loss at 40 VFE-ticks then closes them at a loss.
- **8-strike concurrent exposure** — when VFE deviates, he's max-long or
  max-short on every strike at once. If VFE genuinely trends past the
  40-tick stop, total drawdown is 8× a single strike.

---

# v1 analysis (preserved from prior session)

Source: `data/teammate_logs/ian/464669.{py,json,log}`
Live PnL on R3 portal slice: **13,267** (vs our v6 live 1,220 — **10.9× ours**).

## Per-product PnL (live portal, 1000 ticks of day 2)

| Product | Ian | Our v6 | Δ |
|---|---|---|---|
| HYDROGEL_PACK | **+8,558** | +1,238 | +7,320 |
| VELVETFRUIT_EXTRACT | +992 | -18 | +1,010 |
| VEV_5100 | +1,458 | 0 (untraded) | +1,458 |
| VEV_5200 | +1,087 | 0 (untraded) | +1,087 |
| VEV_5300 | +1,173 | ~0 | +1,173 |
| **Total** | **+13,267** | **+1,220** | **+12,047** |

Note: Ian's final positions are at the LIMIT on multiple instruments
(-300 VEV_5100, -300 VEV_5300, +200 HG, -200 VFE, -300 VEV_5200) —
significant inventory at portal-end, exposed to hidden FV mark.

## Approach differences (architecture)

### HYDROGEL — Ian's strategy (the big edge)

Hardcoded `FAIR = 9991` (not `wall_mid` like us). Three layers:

1. **Aggressive taking** when far from FV:
   - Buy any ask < `FAIR - TAKE_EDGE` (FAIR-18 = 9973)
   - Sell any bid > `FAIR + TAKE_EDGE` (FAIR+18 = 10009)
   - Capped at `MAX_TAKE=25` per tick

2. **Passive MM** at `FAIR ± PASSIVE_EDGE` (FAIR ± 20):
   - Wider than our 8 — avoids inside-wall toxicity
   - Inventory skew via `8 * pos / position_limit`

3. **Three derisking triggers** (LONG only):
   - `VERY_RICH_MID = 10046`: aggressive sell into bids
   - **Trailing drawdown**: `peak_while_long - mid >= 22` → start selling
   - **EMA break**: `mid < ema - 18` after a rich peak
   - `block_new_buys` when `mid >= RICH_MID = 10026`

### VELVETFRUIT_EXTRACT — Ian's strategy

Pure MEAN-REVERSION around `FV=5250`. ±20 trigger, sweep books, 40-tick
stop-loss. Directional, not market making.

### VEV vouchers — Ian's strategy

Treats VEV_5100/5200/5300 as **delta-1 derivatives of VFE**. Reads VFE
deviation each tick (NOT the voucher's own price). When VFE deviates
>20 ticks, take max position in the direction of reversion. Stop on
40-tick adverse VFE move.

## What Ian got right that we missed (v1)

1. HG FV is fixed at ~9991, not floating wall_mid.
2. Take aggressively when far from FV — pure passive MM leaves money on table.
3. Trailing drawdown derisk (not timestamp pre-flatten) is the right defense.
4. VFE mean-reverts hard around 5250 — directional taking captures it.
5. Vouchers are delta-1 in VFE — trade them WITH VFE, not standalone.

## What we got right that Ian doesn't have

1. **L1-L2 skew on VFE** (v4) — overlay candidate.
2. **VEV_5300 / VEV_5400 bias-aware MM** (v6) — small but real.
3. **Pre-portal calibration** — BT-vs-live ratio per submission.

## Action items (proposed v8 / v9 / v10)

- **v8** — port Ian's HYDROGEL: fixed FV + aggressive take + trailing
  drawdown derisk. KEEP our HG soft cap as a backstop.
- **v9** — port Ian's VFE MR strategy. KEEP our L1-L2 skew as a passive
  layer (overlay).
- **v10** — port Ian's voucher delta-1 strategy on VEV_5000/5100/5200/5300/5400.
  Skip 4000/4500/5500 (Ian's v2 confirmed they bleed).

---

# Variance analysis — same strategy, very different paths

Ran both Ian versions through PnL trajectory analysis on their portal logs:

| | Ian v1 | Ian v2 |
|---|---|---|
| Final PnL | +13,267 | +13,528 |
| Peak PnL | +30,916 @ t=60300 | **+52,183 @ t=60300** |
| Min PnL | -7,461 | **-19,021** |
| Peak → final drop | -17,649 | **-38,655** |

**Same code logic between v1/v2 for HG/VFE/5100/5200/5300 → identical PnL on
those.** The 5 added strikes amplify total variance proportionally because
all vouchers move directionally with VFE — when VFE deviates one way, ALL
strikes win or lose together.

**Conclusion**: his "13,528 final" is largely a sampling-time artifact. He
peaked at +52k mid-window; submitting a few thousand ticks earlier would have
shown a -19k loss. His leaderboard PnL is HIGH VARIANCE.

# Ian's strategy in OUR backtester (3 days)

```
venv/bin/prosperity4btest cli data/teammate_logs/ian2/471212.py 3 --merge-pnl
```

| Metric | Ian v2 BT | Our v7 BT |
|---|---|---|
| Total PnL (3 days) | **769,690** | 34,518 |
| Sharpe | 7.13 | 2.97 |
| Max DD | 115,257 | 3,918 |
| Calmar | 6.68 | 8.81 |
| BT day-2 first-1000-tick | 13,767 | 1,678 |
| Estimated live (BT/1.37) | 10,049 | 1,225 |
| ACTUAL live | 13,528 | 1,220 |

His take-based strategy beats our 1.37 calibration (live > predicted) — the
1.37 ratio was measured for OUR passive MM, not Ian's aggressive takes.

Per-product BT contribution (Ian v2, 3-day):
- HYDROGEL: ~108k (his fixed-FV take strategy)
- VFE: ~95k (MR sweep around 5250)
- Vouchers (8 strikes): ~470k ← biggest edge by far

We are leaving **~470k of voucher PnL on the table** by not implementing
delta-1 voucher trading.

# Cap optimality sweep on Ian's strategy

Tested voucher cap from 50 to 300 (his choice) holding all else equal:

| Cap | PnL | Sharpe | Max DD | Calmar |
|---|---|---|---|---|
| 50 | 295,042 | 6.08 | 30,263 | **9.75** |
| 100 | 391,239 | 6.52 | 46,287 | 8.45 |
| 150 | 486,765 | 6.72 | 63,462 | 7.67 |
| 200 | 587,166 | 6.84 | 80,637 | 7.28 |
| 300 (Ian's) | 769,690 | **7.13** | 115,257 | 6.68 |

- PnL scales sub-linearly with cap (50→300 = 6x cap, only 2.6x PnL).
- Max DD scales nearly linearly (6x cap → 3.8x DD).
- **Sharpe maximized at cap=300; Calmar maximized at cap=50.**
- Ian picked cap=300 = full IMC limit. That maximizes mean PnL but at the
  cost of catastrophic downside — visible in the live -19k trough.

For us, **cap=100** is the sweet spot: 11x our v7 PnL (391k vs 34k) with
Calmar 8.45 close to our 8.81. Cap=50 even safer: 8.5x our PnL at Calmar
9.75 (better than ours).

# Is any of OUR strategy portable to Ian's?

Yes — three potential overlays for v8+:

1. **Our soft inventory cap** (`soft_pos_cap` mechanism from v7) directly
   addresses his variance issue. Same logic, smaller numbers.
2. **L1-L2 skew on VFE** (our v4) — could be added as a passive layer
   alongside his MR sweep. Captures microstructure in non-trigger ticks.
3. **wall_mid as a fallback FV anchor** — Ian hardcodes 9991 (HG) and 5250
   (VFE). If those drift in unseen R3 scoring data, his strategy breaks.
   Use wall_mid as a sanity check: if `|fixed_FV - wall_mid_50tick_avg| > X`,
   trust wall_mid instead.

# Updated porting plan

- **v8** — port Ian's HG (fixed FV + take + trailing-drawdown derisk)
  with our soft cap as backstop. Test cap = full and sweep.
- **v9** — port Ian's VFE MR. Overlay our L1-L2 skew. Sweep entry threshold.
- **v10** — port Ian's voucher delta-1 with **cap=100** (NOT 300).
  Trade only VEV_5000/5100/5200/5300/5400. Skip 4000/4500/5500.
  Skip the 6000/6500 dead strikes regardless.
- **v11** — strike-aware delta sizing for vouchers (next-level). Eliminates
  the deep-ITM bleed Ian hits with naive cap=300 on VEV_4000.
