# R3 strategy journey — what we did and why

Plain-English narrative of how we got from a baseline 31k BT to a 362k BT.
Read this if you want the story; read individual `strategies/vN_*.md` for
per-iteration detail.

## TL;DR

We started with a vanilla passive market-maker and iteratively layered
in: defensive informed-flow handling, voucher mispricing capture, position
caps, then ported and improved on a teammate's aggressive take-based
strategy. **End state: 11.4× the PnL with comparable risk-adjusted metrics.**

Final ship-candidate: `docs/round_3/strategies/snapshots/v10_trader.py`.

```
v1 baseline:    31,606  PnL  Sharpe 2.50  Calmar 7.09
v10 current:   361,705  PnL  Sharpe 8.59  Calmar 8.48
```

## The 12-step story

### Step 1 — Understand the game (research notebooks 04-13, docs 02-08)

12 products: 2 goods (HYDROGEL_PACK, VELVETFRUIT_EXTRACT = "VFE") and
10 vouchers (VEV_4000 to VEV_6500, call options on VFE).

Position limits: 200 for goods, 300 for vouchers.

We did EDA on order-book microstructure (spread, depth, autocorr), the
voucher implied-vol smile, cross-product correlations (HG is fully
independent of everything; vouchers are a single VFE-driven factor),
bot trade tape (VFE buy-aggressors are informed; vouchers are dumped
by bots without much intelligence).

### Step 2 — Baseline trader (v1, +0%)

Pure passive market-maker on goods only. Quote at `wall_mid ± half_edge`
with linear position skew. Never hit position limit. **31,606 PnL.**

The "PnL workhorse" is HYDROGEL (~23k of 31k). VFE adds ~8k, vouchers
contribute zero (untraded).

### Step 3 — VFE asymmetric edges (v2, +6.5%)

EDA #7 found VFE buy-aggressors predict +0.63 ticks of mid drift over
50 ticks (t=+2.64). That means: when the smart bots buy, mid goes up
afterward. If we're selling at our ask, we get picked off.

**Defense**: quote ask 1 tick farther than bid (bid_edge=2, ask_edge=3).
Sells are slightly less likely when prices are about to move up.
Result: **33,676 PnL (+6.5%).** VFE day 1 nearly tripled.

### Step 4 — Tried VFE flow skew (v3, ABANDONED)

Used the same informed-flow signal as a *quote skew* — when buy-flow is
high, lean both quotes up. Failed: too sticky, lost PnL on benign days.

**Lesson**: directional skews from sticky signals create their own
problems. Better to use them as gates ("don't trade") than as biases.

### Step 5 — VFE L1-L2 microstructure skew (v4, +8.2% vs v1)

EDA #10 found that on VFE, when L1 spread is much narrower than L2 (`diff
<= -3`), mid drifts up over the next 1-5 ticks (r=-0.21, t=-37 across 30k
samples). Used this as a quote skew — much less sticky than flow.

Result: **34,182 PnL.** Calmar 7.90 (best so far).

### Step 6 — Tried end-of-day pre-flatten (v5, ABANDONED)

Tried to address the "dip" pattern people described on Discord. Discord
user `rsr7128` had pre-mortemed our exact pattern. We added pre-flatten
near end-of-day. **BT regression -9.9%.** Investigation revealed: the
portal sim is just the FIRST 10% of day 2 (verified byte-perfect against
Discord claims), so "end of portal" is actually the start of BT day 2.
Wrong temporal location.

**Lesson**: verify what data the portal/BT runs on before deciding when
to defend.

### Step 7 — Voucher bias-aware MM (v6, +10.1%)

EDA #5 found persistent biases: VEV_5300 historically rich +1.83 ticks,
VEV_5400 cheap -2.0 ticks. Added asymmetric MM quotes that bias us
short-5300 / long-5400. Result: **34,790 PnL.** Tiny voucher contribution
(~600) but real.

### Step 8 — HG soft inventory cap (v7, Calmar-optimal)

Investigated the dip mechanism: pure mark-to-market on accumulated short
inventory. We chronically run short ~30 HG; when mid drifts up, our
shorts eat the loss. Position barely changes during the drop — pure MTM.

**Fix**: cap |position| at 40 (just below historical max 54). Stops the
worst MTM exposure without costing much spread capture.

Result: **34,518 PnL, Sharpe 2.97, Calmar 8.81 (best yet).** Slight PnL
hit for big risk reduction.

### Step 9 — BT vs live calibration (research, no PnL change)

Discord verified: portal sim = first 1000 ticks of day 2 (theethan7114).
We compared our local BT day-2 first-1000 ticks against actual live
portal log. Same orderbook (12,000 rows × 17 cols byte-identical). But
our PnL differs: BT is ~37% optimistic vs live (calibration 0.73).

**Why**: BT matches our quotes against frozen historical bot trades; live
matches against real bots that can avoid our orders. Built `bt_dual.py` to
report full BT + portal-slice + live estimate per version.

### Step 10 — Port Ian's HG strategy (v8, PnL-optimal)

Teammate Ian's live PnL was 13,267 vs our 1,220. Investigation showed his
HG approach is fundamentally different: hardcoded FAIR=9991 + aggressive
TAKE when far from FV + passive MM at FAIR±20 + three derisking triggers
(VERY_RICH_MID, trailing drawdown, EMA break).

Ported it (replacing our pure-passive HG). Result: **119,578 PnL** (3.5×
v7) but DD jumped from 0.86% to 9.91%. Classic leverage tradeoff — we
sacrificed risk-adjusted metrics for raw PnL.

Tested cap on top of Ian's logic — redundant (his takes bypass passive
caps; only hard `position_limit` lowering binds, but proportionally costs
PnL).

### Step 11 — VFE MR taker with rolling FV (v9, +57.6%)

Ported Ian's VFE strategy: directional MR sweep when far from FV=5250
with 40-tick stop-loss. Added our regime-aware twist: **rolling-1000
median FV** instead of his hardcoded 5250.

Why: regime EDA #16 found VFE FV drifts 5244 → 5258 across days.
Hardcoded 5250 produces day-2 short bias. Rolling FV reduces false
"extreme deviation" signals from 20.7% → 13.1% of ticks.

Result: **188,449 PnL, Sharpe 6.86, Calmar 8.39.** Day 1 VFE jumped
from 1,652 (v8) to 35,581 (v9) — the regime fix nailed it.

### Step 12 — Strike-aware voucher taker (v10, Pareto-best)

Ian trades 8 vouchers with uniform cap=300. EDA #16 measured empirical
delta per strike via OLS: 4000=0.74, 5000=0.65, 5100=0.58, 5200=0.44,
5300=0.27, 5400=0.13, 5500=0.06. Uniform cap means deep-ITM strikes get
~3× the VFE-equivalent exposure of OTM strikes.

**Our fix**: strike-aware caps. `cap = round(80 / delta)`, capped at 300.
Trade only the high-R² strikes (5000/5100/5200/5300). Skip 4000/4500
(R² ~0.36) and 5400/5500 (signal too weak).

Per-strike voucher PnL: **~42-45k each** (roughly equal — confirms the
sizing is doing its job).

Result: **361,705 PnL, Sharpe 8.59, Calmar 8.48.** Beats every prior
version on PnL, Sharpe, AND Calmar.

## Where we beat / lose to Ian

| | Ian v2 BT | Our v10 BT |
|---|---|---|
| Total PnL | 769,690 | 361,705 (47%) |
| Sharpe | 7.13 | **8.59** |
| Max DD | 115,257 | **42,668** (37%) |
| Calmar | 6.68 | **8.48** |

We have ~half the PnL but better risk-adjusted metrics. His extra PnL
comes from leverage (cap=300 + 8 strikes including dead ones). The
diff is closable with `vfe_equiv_target` raised from 80 → 160.

## Key research findings that drove decisions

- **HG/VFE are independent** (PC2 = 100% HG, max CCF ≤ 0.02).
  No cross-asset hedging worth doing.
- **VFE buy-aggressors are informed** (+0.63 ticks/50t, t=2.64).
  Used defensively (asymmetric quote, not skew).
- **L1-L2 spread differential predicts VFE micro-direction**
  (r=-0.21 at h=1, t=-37). Used as a quote skew.
- **VFE FV drifts day-by-day** (5244 → 5258). Use rolling-1000
  median, not hardcoded 5250.
- **Voucher delta is NOT 1.0** — it's 0.74/0.65/0.44/0.27/0.13 across
  strikes. Strike-aware caps required.
- **Vouchers are deterministic functions of S**: no theta, no IV
  variation. Trade as leveraged VFE bets, not as options.
- **Portal sim is first 1000 ticks of day 2** — our BT can replicate
  exactly. Calibration ratio live/BT_slice ≈ 0.73 for passive MM,
  closer to 1.0 for take-based strategies.
- **HG dip is MTM on shorts**, not bot toxicity. Position cap is the
  only viable defense; vol/return regime detection failed.

## Files & where to look

- **Strategy iteration log**: `docs/round_3/strategies/README.md`
- **Per-version docs**: `docs/round_3/strategies/v1_baseline.md` ... `v10_voucher_taker.md`
- **Snapshot files (paste-ready)**: `docs/round_3/strategies/snapshots/vN_trader.py`
- **Research deep-dives**: `docs/round_3/research/01-16_*.md`
- **EDA notebooks**: `notebooks/04-13_*.ipynb` (one per research doc)
- **Overview notebook**: `notebooks/00_overview.ipynb` (start here if new)
- **BT explorer notebook**: `notebooks/99_trader_bt_explorer.ipynb` (change
  TRADER_PATH at top, run all, see plots)
- **Live portal logs**: `data/live_logs/v2/`, `data/live_logs/v4/`
- **Teammate logs**: `data/teammate_logs/{ian,ian2,rohit}/`

## Open candidates not yet tested

- **v11**: informed-flow gate — pause adding inventory during VFE
  buy-aggressor bursts. Defensive overlay.
- **v12**: cap sweep — try `vfe_equiv_target` 80 → 120 → 160. Find the
  PnL/Calmar elbow. Could close the gap to Ian's 770k BT.
- **v13**: add 4000/4500 with R²-discounted smaller caps.

## Submission checklist

1. Open `notebooks/99_trader_bt_explorer.ipynb`, set
   `TRADER_PATH = "docs/round_3/strategies/snapshots/v10_trader.py"`,
   run all cells. Confirm plots render.
2. Copy contents of `docs/round_3/strategies/snapshots/v10_trader.py`.
3. Paste into IMC portal. Submit.
4. After live result lands, download log, drop in `data/live_logs/v10/`.
5. Compare actual live vs estimated 26,050. Refine calibration.
