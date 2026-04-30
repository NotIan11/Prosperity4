# R5 strategy versions

Each file is a self-contained `Trader` class — uploadable as `src/trader.py`.
BT runs are 3-day capsule (R5 days 2/3/4) via `prosperity4btest src/trader.py 5 --data data/bt_resources`.

| Ver | Approach | BT total | Live | Notes |
|---|---|---|---|---|
| v1 | Taker MR (PEBBLES basket take + per-product MR take) | -$395,220 | not submitted | Reconstructed from session transcript. Spread 10-17 vs MR edge 3-5 → structurally negative round-trips at limit=10. |
| v2 | Passive MM, 12 products (5 PEBBLES + 5 SNACKPACK + ROBOT_IRONING + OXYGEN_SHAKE_EVENING_BREATH) | +$109,140 | "pretty bad" | Penny-inside-touch quotes, position skew, PEBBLES basket-tilt overlay. Submitted live — bad result. |
| v3 | v2 + loosened stop-losses (40→80) + warmup 50→100 | +$110,874 | not submitted | Marginal improvement. Day-2 bleed mostly fixed via warmup gate. |
| v4 | v3 + MM expanded to all 50 products (default skew=0.4, stop=60) | +$265,168 | +$20,559 | Monotone-up curve, trough -$67. Live bleeders: TRANSLATOR_SPACE_GRAY -$1.5k, GALAXY_SOUNDS_PLANETARY_RINGS -$1.5k, ROBOT_DISHES -$1.4k, UV_VISOR_AMBER -$0.6k. |
| v5 | v4 + DirectionalStrategy on 13 products (sign-stable capsule drift, max long/short) | +$456,014 | +$11,295 | **Underperformed v4 live by $9k**. 6/13 directional bets reversed live. Trough -$9.3k. Drift signal not deterministic across days (Critic A right). |
| v6 | v4 minus 4 consistent bleeders (BT&live both negative) | +$271,175 | (tbd) | ROBOT_DISHES, OXYGEN_SHAKE_MINT, MICROCHIP_TRIANGLE, OXYGEN_SHAKE_MORNING_BREATH skipped. No directional risk; preserves v4's monotone-up curve. |
| v7 | v6 + regime-tuned MM (5 regimes) + 3 adaptive overlays: PEBBLES outlier-suppression, SNACKPACK 2+2+1 group skew, step-product post-step cooldown | +$257,046 | (tbd) | Each overlay bounded-downside (worst case: fewer fills). No capsule-drift fitting. |
| v8 | v7 + Ian-v3-style "settled" gate on 3 ROBOT narrow_quiet products (LAUNDRY, MOPPING, VACUUMING) | +$257,832 | $18,143 | Gate net -$713 vs v7 in live (ROBOT_LAUNDRY backfired). A7 confirms gate has no documented upside in any adversarial scenario. |
| v9 | v7 + 10-agent investigation findings: regime tightening (wide_drifty soft_cap 7→4 + stop 50→100, narrow_quiet soft_cap 7→5), per-product overrides (MICROCHIP_SQUARE skew 0.6→0.9 + cap 6→4, UV_VISOR_AMBER skew 0.5→0.3, PANEL_2X4 stop 45→90), PEBBLES soft_cap 8→10 | +$271,718 | (skipped) | Conservative. Found out Ian v25 lives at $52k → ours capped at ~$20k. Risk-management was overboard. |
| v10 | Port of Ian v25 architecture (EMAMarketMaker + selective take_edge + settled/trend gates), ALL DirectionalStrategy lines stripped → replaced with EMAMarketMaker(α=0.005, take_edge=150). 22 directional bets removed. | +$628,942 | not submitted | 2.3× v9 BT, rising day-trajectory (153→191→285k). 10 internal bleeders from formerly-directional products being adversely-selected. |
| v11 | v10 minus 10 BT bleeders | +$743,544 | $15,133 | 2.7× v9 BT but live cratered. Stripping all 22 directionals discarded real alpha. Day-4 per-product comparison vs Ian shows directional products (TRANSLATOR_SPACE_GRAY, SLEEP_POD_COTTON, UV_VISOR_RED, MICROCHIP_OVAL) winning under Ian, losing under v11. |
| v12 | Ian v25 + ALL 25 directionals wrapped in `trend_round5` (drift-confirmation gate). | +$1,082,877 | $49,267 | Restored directionals. 3.3× v11 live. Trend gate didn't hurt or help meaningfully (drifts on capsule pass gate). Lost vs Ian v16 due to v25's over-tuning + active products v16 had off (MICROCHIP_SQUARE −$6k, PLANETARY_RINGS −$4k, DARK_MATTER −$3k, MICROCHIP_TRIANGLE −$3k). |
| v14 | v12 + 1000-tick adverse-move stop-loss on every directional (exits + stays flat for the day if mid moves 1000 ticks against bet direction). | +$1,097,228 | (live tbd) | Net +$14k vs v12 on capsule. MICROCHIP_SQUARE +$13k (stop fired during day-4 −2,278 reversal). Cost ~$6k on false-positive exits during noise. Designed to protect against R3-day-3-style scoring-day reversals. **Active submission.** |

## Ian v18 / v25 reference (teammate, NOT our submissions)

| Ver | BT total | Live | Notes |
|---|---|---|---|
| Ian v18 | +$981,950 | $48,332 | EMAMarketMaker core + ~10 hardcoded DirectionalStrategy bets (capsule-fitted drifts). 4.9% conversion. |
| Ian v25 | +$1,099,438 | $52,288 | v18 with slower EMAs (α 0.01→0.003-0.005), 2 directional bets demoted to EMA-MM, SNACKPACK_RASPBERRY activated. 4.8% conversion. |

Ian's "secret": (a) light risk management — uses full position limit of 10, no stops, mild 0.1 inventory skew; (b) selective-fill EMA-MM (only takes liquidity at 100-200 tick gaps from EMA fair); (c) directional bets contribute ~40% of BT but carry capsule-overfit risk (proven on our v5: 6/13 directional bets reversed live).

v10/v11 keeps (a) and (b), drops (c).

## Pitfalls already encountered

- v1 lost on every active product. Lesson: at position limit 10, taker
  spread costs (10-17 ticks) consume any MR edge. Maker-only is the
  default for R5.
- v2 BT looked fine but lived "pretty bad" — confirms again that BT-vs-live
  is the dominant uncertainty (per `docs/round_3/JOURNEY.md` 2.72×
  over-prediction anchor).

## What v4 changes vs v2

- 50 products instead of 12, all on the same `PassiveMM` core.
- 5 BT bleeders identified but NOT removed in v4 (v5 attempt to drop them
  pushed BT to $278k but was halted before commit).
