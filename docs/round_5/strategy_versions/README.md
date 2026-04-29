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
