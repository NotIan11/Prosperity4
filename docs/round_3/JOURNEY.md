# R3 Retrospective

## What shipped

**v12** (`docs/round_3/r3_trader.py`, `vfe_equiv_target=160`). Live result: $53,790 first sub, mean ~$50k across 3 reruns (portal bot fills are stochastic, ±$10k). Shipped live ~4× Ian ($13.5k).

BT summary:
```
v1 baseline:    31,606  PnL  Sharpe 2.50  Calmar 7.09
v12 final:     460,722  PnL  Sharpe 5.20  Calmar 7.62  | LIVE $53,790
```

Vs teammate live results:
- v12 (us): ~$50k mean
- v15 (us + gate): $46k — gate cost $7.6k
- v16 (friend live-delta): $33k — noisy small-sample deltas
- Ian v2 (cap=300 uniform): $13.5k — bots dodge over-aggression

## Lessons (with evidence)

**HG/VFE are independent** (PCA: PC2 = 100% HG, max CCF ≤ 0.02). No cross-asset hedging needed.

**VFE buy-aggressors are informed** (+0.63 ticks over 50t, t=2.64). Use defensively as asymmetric quote edge (ask_edge=3 > bid_edge=2), NOT as a directional skew. Flow skew (v3) was too sticky and lost PnL on benign days.

**VFE L1-L2 spread differential predicts micro-direction** (r=−0.21 at h=1, t=−37, 30k samples). Less sticky than flow — usable as quote skew (v4).

**Portal sim = first 1000 ticks of day 2** (verified byte-identical against live log; Discord: theethan7114). BT is ~37% optimistic vs live for passive MM (calibration 0.73); closer to 1.0 for take-based strategies.

**VFE FV drifts day-by-day** (5244 → 5258). Rolling-1000 median FV reduces false "extreme deviation" signals from 20.7% → 13.1% vs hardcoded 5250 (v9).

**Voucher delta is NOT 1.0.** OLS empirical deltas: 4000=0.74, 5000=0.65, 5100=0.58, 5200=0.44, 5300=0.27, 5400=0.13, 5500=0.06. Uniform cap=300 (Ian's approach) gives deep-ITM strikes ~3× the VFE-equivalent exposure of OTM. Strike-aware caps (`cap = round(target / delta)`) equalize per-strike VFE exposure; per-strike PnL came out ~$42-45k each — confirms sizing works.

**Skip 4000/4500 (R²~0.36) and 5400/5500 (signal too weak).** Trade only 5000/5100/5200/5300.

**HG dip is MTM on short inventory**, not bot toxicity. When we're chronically short ~30 HG and mid drifts up, that's pure mark-to-market loss. Position cap (|pos| ≤ 40) stops the worst MTM without costing much spread capture (v7).

**Binary informed-flow gate: −$7.6k vs v12 live (v15 post-mortem).** Gate fired against profitable take-based trades. → Use as sizing tilt (50% cap on adverse flow), not binary block.

**Pure live-delta recompute: −$20k vs v12 live (v16 post-mortem).** Noisy small-sample OLS fits in early ticks; hardcoded deltas are more stable until samples accumulate. → Hybrid warm-start.

**Portal bot fills are stochastic.** Identical code produced $53,790 / $13,889 / $49,081 across 3 reruns. BT is deterministic; live is not. TraderData state DOES persist on IMC (confirmed: live > BT slice is the tell). See `docs/round_3/research/17_portal_stochasticity_and_state.md`.

## R4/R5 carry-overs (priority order)

1. Add `traderData` JSON round-trip to all stateful strategies (defensive hygiene).
2. Hybrid delta: start with hardcoded, blend toward live OLS as samples accumulate. Pure live-delta (v16) lost $20k; pure hardcoded is baseline.
3. Informed-flow as **sizing tilt** (50% cap on adverse flow), not binary gate (gate cost $7.6k live; v15).
4. Defensive cap reduction if rolling FV drifts > 50 ticks from 5250.

## Key files

- Ship code: `docs/round_3/r3_trader.py` (= `src/trader.py`)
- Ship strategy doc: `docs/round_3/r3_strategy.md`
- Research deep-dives: `docs/round_3/research/01-17_*.md` (see INDEX.md)
- Live logs: `data/round_3/live_logs/v12/` (3 runs), `data/round_3/live_logs/v15/`
- Teammate logs: `data/round_3/teammate_logs/{ian,ian2,rohit,rohit_wack,friend_live_delta}/`
- BT tools: `notebooks/99_trader_bt_explorer.ipynb`, `scripts/bt_dual.py`
