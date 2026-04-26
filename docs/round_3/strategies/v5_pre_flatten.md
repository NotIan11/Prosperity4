# v5 — End-of-day pre-flatten (ABANDONED)

**Status**: tested, abandoned (BT regression -9.9%)
**Commit**: not committed
**Date**: 2026-04-26

## Hypothesis

Live portal log shows PnL trajectory: +2397 peak at tick 91100 → +1220 final at
tick 99900. Lost ~1180 PnL in the last ~9% of the portal window. Discord
(`08a_discord_algo_trading.md` line 53, **rsr7128** [04-25 21:19]):
*"mean reversion on hydrogel + IV on velvet voucher → goes up to 5k then plunges
at end"* — pre-mortems our exact pattern. Hypothesis: end-of-window inventory
liquidation at hidden FV. Fix: stop adding to inventory in last 10% of day.

## Changes

- Added `pre_flatten_after_ts` kwarg to `PassiveMarketMaker`.
- When `state.timestamp >= pre_flatten_after_ts`, skip the side that would
  build inventory (`bid_size=0` if long, `ask_size=0` if short).
- Set on both HG and VFE at threshold `900000` (last 10% of BT day).

## Backtest

| Day | v4 | v5 | Δ |
|-----|------|------|------|
| 0 | 15,713 | 13,706 | -2,007 |
| 1 | 11,616 | 11,158 | -458 |
| 2 | 6,854 | 5,948 | -906 |
| **Total** | **34,182** | **30,812** | **-3,370 (-9.9%)** |

| Metric | v4 | v5 |
|---|---|---|
| Sharpe | 2.57 | 2.60 |
| Max DD% | 0.85 | 0.85 |
| Calmar | 8.02 | 7.23 |

## Why it failed

The portal sim is the **first 10% of day 2** (per Discord theethan7114).
So the live "dip" at portal tick 99900 corresponds to **BT day-2 tick 999** —
NOT end-of-BT-day. Pre-flatten at BT ts >= 900000 was firing in the wrong
temporal location and just left fills on the table during otherwise productive
periods.

Two open questions remain:
1. Is the dip a portal-only **hidden-FV liquidation** mark applied at portal
   window-end? BT cannot test this.
2. Is it a real intraday event at day-2 ticks ~91k-99k? Would need finer
   instrumentation to detect — fire only inventory-flatten at that specific
   timestamp range, but that overfits to a single observation.

## Decision

**Abandon for now.** Don't ship v5. Move to v6 (vouchers).

If we want to revisit later: try **inventory cap** (always cap |position| at
some threshold, regardless of time) — addresses inventory drift without time
overfitting. Or **upload v4 + monitor live**: if dip persists across multiple
submissions, it's portal mechanics; if it varies, it's intraday.
