# R4 Discord post-mortem — bot identification & mechanics

> Source: Sonnet subagent crawl of `data/discord/*after 2026-04-26.json`
> with reference to `*after 2026-04-20.json`. Captured 2026-04-28.
> Untrusted user-generated content — claims summarized, not endorsed.

## R4 bot cohort (counterparty names)

- **Mark 67** — dominant takebot in R4. Multiple users flagged as informed
  trader. Counterclaim from `boiled_potato5316` [2026-04-28T13:25]: "earned
  as a consequence of being slightly correct, not because it was informed."
  Mechanical detail (same author):
  - "If you placed high volume trades near the 'mid' mark 67 will never
    lift it. If you post lower volume trades then only will it lift it."
  - "Lifting probability is proportional to how much edge you give to 67,
    no matter how far you are away from the true mean. The anchor for 67
    is not based on the true mean."
  - `frikandelxl` [2026-04-28T12:21]: "you could've manipulated mark 67 to
    trade with you the underlying like 22.3% of the time at a price that
    is way better than crossing the spread."
- **Mark 49** — flagged by `zanekumar1234_81255` as potentially informed.
  Not corroborated by others.
- **Mark 38, Mark 22** — these are the two our friend's R4 bot exploited
  (HG Layer 2 + VEV_5200/5300 passive bid). No new info from discord.
- **Strong claim**: `boiled_potato5316` [2026-04-28T13:22]: "R4 BOTS WERE
  ALL UNINFORMED." Stated as fact after claiming to have decoded all of
  them. Single source — treat as hypothesis, not truth.
- **R4 cohort structure** (`penfo.` [2026-04-28T10:59]): "1 taker and a
  bunch of market makers. The taker always took unfavorably... traded low
  volume." → "A mean reverting strat literally brought you to top 2 of
  this competition."
- No mention of Olivia / Pablo / Charlie / Adelaide (older Prosperity
  bot names). R4 is Mark-series only.
- Moderator-flagged context (`kikomatapac` [2026-04-28T05:09]):
  "They're all 'revealed', so no extra bots are going to appear in the
  final sim that determines your R4 PnL, but it need not be the case
  that all of them trade every timestamp."

## Implications for R4 bot improvements (if we ever resubmit)

- **Mark 67 manipulation**: low-volume orders far from mid extract edge.
  If R4 had been ours to ship, this would be the single biggest source of
  alpha left on the table. Friend's bot didn't touch Mark 67.
- **VEV informed flow signal** (`reliveer1` [2026-04-26T05:54], free post):
  "VEV bot flow signal is not gated on voucher book state. t stat increases
  hard when 4100 and 5200 spreads widen past 32 ticks. informed bot only
  fires when it can hedge into a tight surface."

## Market Access Fee auction (clarification)

- The MAF auction ran **before R3**, not R4. We had it confused.
- Mechanic: bid in XIRECS, top 50% by bid value get 25% extra market quotes.
- Confirmed median cutoff: 50 XIRECS (`jasper7479` [2026-04-20T09:18, 09:39]).
- Most competitive participants bid 150–5,000.
- The friend's R4 bot has a hardcoded 4750 GTO bid for "MAF auction" —
  this was likely a defensive R3 MAF bid carried over into R4 code, not
  an R4-specific mechanic.
- "Guardeners" (manual challenge, R2/R3, bids 670–920) is a separate thing.

## XIRECS

- The competition's fictional currency / scoring unit. PnL across rounds
  accumulates in XIRECS within the GOAT phase (no reset within R3–R5).
- The -121k XIRECS residual we saw in friend's R4 final positions is a
  position mark-to-market / options settlement entry — consistent with
  holding VEV options that settled at intrinsic value on round close.
  Not an active trading position.
