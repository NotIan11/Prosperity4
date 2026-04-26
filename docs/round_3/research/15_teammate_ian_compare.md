# Teammate algorithm comparison — Ian's R3 trader

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
   - Buy any ask < `FAIR - TAKE_EDGE` (FAIR-18 = 9973) — sweep cheap asks
   - Sell any bid > `FAIR + TAKE_EDGE` (FAIR+18 = 10009) — sweep rich bids
   - Capped at `MAX_TAKE=25` per tick

2. **Passive MM** at `FAIR ± PASSIVE_EDGE` (FAIR ± 20):
   - Much wider than our 8 — gives up close-touch fills, captures bigger spreads
   - Inventory skew via `8 * pos / position_limit`

3. **Three derisking triggers** for LONGS only (he runs net long, not short like us):
   - `VERY_RICH_MID = 10046`: aggressive sell into bids
   - **Trailing drawdown**: `peak_while_long - mid >= 22` → start selling
   - **EMA break**: `mid < ema - 18` after a rich peak → sell cautiously
   - `block_new_buys` when `mid >= RICH_MID = 10026`

**Why it works:**
- Take edge captures spread when bots cross hard
- Wide passive edge avoids inside-wall toxicity
- Trailing-drawdown is the SAME defense logic we tried (v5 pre-flatten) but
  fired on a meaningful signal (drawdown from peak), not an arbitrary timestamp
- block_new_buys = "don't keep buying as price climbs" — exactly the opposite
  failure mode from our chronic shorts

### VELVETFRUIT_EXTRACT — Ian's strategy

Pure MEAN-REVERSION around `FV=5250` (verified empirically via deep-ITM
voucher: `C_4000 + 4000 = S` exactly).

- When `mid - FV < -20` → sweep all asks (buy aggressively)
- When `mid - FV > +20` → sweep all bids (sell aggressively)
- Stop-loss: close if mid moves 40 ticks against entry

This is a **directional bet**, not market making. Works because VFE is
strongly mean-reverting around 5250 with std ≈ 15. Very different from our
passive MM with L1-L2 skew.

### VEV vouchers — Ian's strategy

Treats VEV_5100/5200/5300 as **delta-1 derivatives** of VFE.

- Reads VFE deviation each tick (NOT the voucher's own price)
- When VFE deviates from FV=5250 by > 20 ticks, take max position in the
  voucher in the direction of VFE reversion
- Stop-loss on VFE moving 40 ticks adverse

This explicitly leverages the no-theta no-vega structure we observed in
EDA #5 — voucher prices are deterministic functions of S only. Ian
exploited it for big PnL on three strikes.

## What Ian got right that we missed

1. **HYDROGEL FV is fixed at ~9991, not floating wall_mid.** Wall_mid bobs
   with the order book. A fixed FV anchored to the long-run mean (we
   observed mean ~9990 in EDAs) is more stable.
2. **Take aggressively when far from FV.** Pure passive MM leaves money on
   the table. Bots cross the spread when prices are mispriced — we should
   take those mispricings ourselves.
3. **Trailing drawdown derisk** is the right mechanism for inventory
   defense, not timestamp pre-flatten (our v5 mistake).
4. **VFE mean-reverts around FV=5250 hard.** We treated it as MM-only.
   Directional taking captures the reversion.
5. **Vouchers are delta-1 in VFE.** Trade them WITH VFE, not standalone.
   We were leaving 3 instruments × ~1000 PnL each on the table.

## What we got right that Ian doesn't have

1. **L1-L2 skew on VFE** (our v4) — Ian's MR-only approach doesn't use
   microstructure. We could overlay this on his framework.
2. **VEV_5300 / VEV_5400 bias-aware MM** (our v6) — Ian only trades
   5100/5200/5300. Our 5400 contribution (+81) is small but real.
3. **Pre-portal calibration methodology** — we measure BT-vs-live ratio
   per submission. Ian doesn't (he has 1 data point).

## Ian's risks

- **Final position at LIMIT on 4+ instruments.** Hidden FV liquidation at
  end-of-portal could materially change his number. Either he doesn't care
  or he's verified that final-tick mid ≈ hidden FV.
- **Hardcoded FV=9991 for HG and FV=5250 for VFE.** Could break if those
  values drift in the unseen R3 scoring data.
- **VFE stop-loss at 40 ticks** = ~2.7σ. If VFE genuinely trends in scoring
  data, this stop-loss fires often.

## Action items (proposed v8 / v9 / v10)

- **v8** — port Ian's HYDROGEL: fixed FV + aggressive take + trailing
  drawdown derisk. KEEP our HG soft cap as a backstop.
- **v9** — port Ian's VFE MR strategy. KEEP our L1-L2 skew as a passive
  layer (overlay).
- **v10** — port Ian's voucher delta-1 strategy on VEV_5100/5200. KEEP our
  5400 bias quoting (small but free).

These should be ported and BT'd ONE AT A TIME so we can attribute the
gains and avoid stacking-bug confusion.
