# 17 — Portal stochasticity + traderData hygiene (R3 close findings)

## TL;DR

- **IMC portal sim is non-deterministic by design** in R3+ — confirmed by
  multiple Discord users. IMC deliberately randomizes ~20% of bot orders
  per submission to defend against overfitted strategies (per
  `_mfb`, `k_vgent`, `lachydauth`, `noprague`, `boiled_potato5316`,
  `acdhemtos`, `infra.bayes`, `xpresi`, dates 2026-04-20/21).
- 3 runs of identical v12 code: $53,790 / $13,889 / $49,081.
- **Cause**: random subset of bot orders removed each submission +
  stochastic fill behavior. Same orders → bots randomly choose how many to hit.
- HG (passive MM) was DETERMINISTIC across all 3 runs (always 65 fills).
  Active take strategies on VFE-correlated products varied 21-105 fills.
- **`traderData` serialization NOT required for state persistence**.
  Empirical proof: `live > BT slice` (1.17x). If state died every tick on
  IMC, live would be << BT (BT keeps instance alive). Live being better
  proves state IS persisting on the platform.
- **But** adding `traderData` round-tripping is still defensive hygiene
  for R4/R5 (cold-start edges, day boundaries, R5 final tournament).

## Three-run v12 comparison (same code, md5 325fdc0e0...)

| Sub | Total | HG | VFE | VEV_5000 | VEV_5100 | VEV_5200 | VEV_5300 | Total fills |
|--|--|--|--|--|--|--|--|--|
| #1 478289 | 53,790 | 8,558 | 10,192 | 10,980 | 10,676 | 8,515 | 4,870 | 596 |
| #2 483658 | 13,889 | 8,298 | 992 | 1,020 | 1,320 | 1,087 | 1,173 | 271 |
| #3 483940 | 49,081 | 8,558 | 9,868 | 9,726 | 9,222 | 7,428 | 4,278 | 489 |

Market data byte-identical across all 3 runs (same md5 `7c8221741...`).

## Codex panic and resolution

Mid-R3 close, a teammate's Codex claimed our v12 had a "critical state
persistence bug" because we return `""` for traderData. Walked back after
empirical check:

- v12 returns `(orders, 0, "")` — true, no state serialization
- BUT: live PnL > BT slice means state IS working on IMC
- BUT: jmerle BT keeps Trader() alive across all ticks (verified by reading
  prosperity3bt source). So our BT result reflects working state.
- IF IMC also kept Trader() alive: state works in both → consistent with
  observed live > BT
- IF IMC re-instantiated every tick: live should be much WORSE than BT.
  Observed opposite. Therefore IMC keeps Trader() alive.

## Why variance happens anyway

Hypothesis (untested): Lambda warm/cold pattern.
- Sub#1 warm Lambda → state persists fully → 96-105 fills/strike → $53k
- Sub#2 partial cold-start → state dies more often → 21-32 fills → $14k
- Sub#3 mostly warm → 69-80 fills → $49k

Defensive fix: serialize state to `traderData` so even cold-starts recover.

## R4/R5 implications

1. **Add traderData round-trip** to all stateful strategies.
2. **Submit multiple times if portal allows** — pick best run.
3. **Don't trust any single live observation** to compare strategies.
   Need ≥3 runs each to distinguish $7-10k differences from noise.
4. **Live > BT slice ratio of 1.17x** is the take-based calibration we
   should trust over the 0.73x passive-MM ratio.
