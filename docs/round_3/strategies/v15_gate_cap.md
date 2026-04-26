# v15 — v11 flow gate + v12 cap=160 (ABANDONED, gate kills upside live)

**Status**: tested live, abandoned. Gate cost $7,634 vs v12.
**Date**: 2026-04-26

## Hypothesis

v11's flow gate gave free Sharpe at low leverage (8.59→9.29). Stacking
on top of v12's leverage bump should defend the bigger inventory.

## BT vs LIVE

| | BT slice (day 2 first 1000) | LIVE | Live - BT |
|--|--|--|--|
| v12 | 46,113 | **53,790** | +7,677 |
| v15 | 46,113 | **46,156** | +43 |

BT slice was **byte-identical** for v12 vs v15 → gate doesn't fire in BT
replay. Live it fires and blocks the exact trades v12 caught for $7.6k.

## Per-product live diff (v15 - v12)

| Product | v12 LIVE | v15 LIVE | Δ |
|--|--|--|--|
| HG | 8,558 | 8,558 | 0 (gate doesn't touch HG) |
| VFE | 10,192 | 8,469 | -1,722 |
| VEV_5000 | 10,980 | 9,294 | -1,686 |
| VEV_5100 | 10,676 | 8,742 | -1,934 |
| VEV_5200 | 8,515 | 7,047 | -1,468 |
| VEV_5300 | 4,870 | 4,046 | -824 |
| **TOTAL** | **53,790** | **46,156** | **-7,634** |

Every VFE-correlated product dropped ~$1.5-2k under v15. HG identical
(gate doesn't touch it).

## Why the gate failed

EDA #7 found buy-aggressors predict +0.63 ticks/50t (t=2.64). Real signal
but TINY. We used it as a hard binary GATE blocking 20-tick MR edges.
Killing a 20-tick edge to defend against a 0.63-tick drift is a terrible
trade.

## Better unbuilt uses for the same signal (R4 candidates)

1. **Sizing tilt, not gate** — adverse flow → take 50% of cap, not 0%.
2. **Stop-loss accelerator** — tighten stop from 40→20 ticks when flow
   turns adverse mid-trade.
3. **Follow, don't fight** — take voucher LONG when buy-flow strong
   regardless of dev (use as directional, not defensive).

## Decision

**Stay on v12.** v15 is a real-world cautionary tale: BT silence on a
gate is not the same as live silence. Defensive overlays need their own
empirical validation before stacking.
