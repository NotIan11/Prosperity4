# R5 ship decision — briefing for review agents

## Round mechanics (verified facts, do not re-derive)

- IMC Prosperity 4 algorithmic trading competition. **R5 is the final round.**
  PnL was reset at R3 — only R3-R5 results count toward final ranking.
- Each team submits ONE Python `Trader` class. Position limit = **10 per
  product**. 50 products in 10 categories of 5.
- Submissions trade independently against IMC's NPC bots. No team-vs-team.
- **Platform randomly drops ~20% of NPC orders per submission** with a
  fresh seed each time. Same code resubmitted varies 4×+ in PnL. NPC
  randomization gives **±$20k variance baseline** across same-strategy
  resubmissions.
- **Portal sandbox preview = first 1,000 ticks of capsule day 4.** Final
  scoring = full **10,000 ticks of hidden day 5** (not in capsule).
  Different days, different lengths.
- Per R3 history: BT $210k → live $77k = **2.72× over-prediction**.
  BT-to-live conversion rate ~5-7% for capsule-fitted strategies.
  Use as floor: live ≈ BT × 0.37 for v12-class strategies.
- Trade counterparty IDs are blank in R5 capsule data. Cannot replicate
  R4-style "friend bot follow" strategies from capsule.

## Key empirical findings from EDA

- **76% of R5 products flip drift sign at least once across capsule days
  2/3/4.** Only 12/50 products have consistent-sign drifts.
- **R3 day 3 (the actual scoring day, not in capsule) reversed direction
  from R3 days 0-2.** Hardcoded directional bets fitted to days 0-2 would
  have lost on scoring. Our R3 strategy was passive-MM-only and survived.
- PEBBLES sum=50,000 is enforced tightly (std 2.8, max deviation ±18).
  Hardcoded directionals (XS,S=-1, XL=+1) implicitly drain this constraint.
  Dynamic basket-arb on top is not worth the spread cost.
- SNACKPACK_CHOCOLATE / SNACKPACK_VANILLA cointegrated (sum~19,941, σ=76).
  Pair-tradeable. All three candidates exploit this.
- NPC trade signature differs by category:
  - 8 categories: 733 trades / 1805 volume per product
  - PEBBLES: 644 trades / 2283 volume
  - MICROCHIPS: 569 trades / 1119 volume
  → Different mechanics per category.

## Three strategy candidates

All three share Ian's `EMAMarketMaker` core (passive quoting + selective
take at 100-200 tick gaps from EMA fair) and ~25 hardcoded directional
bets fit to capsule cumulative drifts. Differences are in risk management.

### Candidate A: Ian v25

- 18 bare `DirectionalStrategy` (slam to ±10 at tick 0, hold to EOD).
- 6 `trend_round5(DirectionalStrategy)` (drift-confirmation gate before slamming).
- 20 EMA-MM products. SNACKPACK CHOC/VANILLA pair trade.
- Slower EMAs than Ian v16 (α=0.003-0.005 vs 0.01).
- **No stop losses on any directional bet.**
- File: `docs/round_5/strategy_versions/ian_v25.py`
- BT total: **$1,099,438** (per-day 472/312/315, decaying)
- Portal preview live (day 4, 1k ticks): **$52,288**
- Visualizer: Sharpe 4.32, Sortino 6.33, Min PnL -$4,275, MaxDD 4.0%

### Candidate B: Aadi v1

- Ian v25 base + new `ScaledDirectionalStrategy` class.
- Scales 5 weak-drift directional bets to smaller `effective_position_limit`
  (5 or 7 instead of 10): ROBOT_IRONING, PANEL_2X4, SLEEP_POD_POLYESTER,
  UV_VISOR_MAGENTA, ROBOT_DISHES.
- Same 25 directionals, but those 5 take smaller positions.
- **Still no stop losses.**
- File: `docs/round_5/strategy_versions/aadi_v1.py`
- BT total: **$1,058,183** (per-day 453/298/307)
- Portal preview live: **$52,519** (only $231 more than Ian v25 = noise)

### Candidate C: r5_v14_directional_stops

- Ian v25 base + ALL 25 bare directionals wrapped in `trend_round5`
  (drift-confirmation gate on every directional, not just 6).
- ALL 25 directionals get **`stop_loss_ticks=1000`**: tracks entry mid,
  exits and stays flat for the day if mid moves 1000 ticks adverse.
- No position scaling (full 10 lots on every directional that fires).
- File: `docs/round_5/strategy_versions/r5_v14_directional_stops.py`
- BT total: **$1,097,228** (per-day 469/306/322)
- Portal preview live: **$49,267**
- Visualizer: **Sharpe 4.55** (best), Sortino 6.70 (best), Min PnL **-$3,449** (best),
  MaxDD 4.0%

## Live results comparison (all measured on same day-4 portal preview)

| Strategy | BT | Live | Sharpe | Min tick PnL | Mechanism |
|---|---|---|---|---|---|
| Ian v16 (raw) | $1,010k | **$62,618** | n/a | n/a | mostly bare directionals |
| Ian v25 (A) | $1,099k | $52,288 | 4.32 | -$4,275 | subset gated, no stops |
| Aadi v1 (B) | $1,058k | $52,519 | n/a | n/a | scaled 5 weak bets |
| **v14 (C)** | $1,097k | $49,267 | **4.55** | **-$3,449** | all gated + stops |

Note: v14's stops never fire on the 1k-tick portal preview because the
adverse moves don't reach 1000 ticks in 10% of a day. They only matter
on the full 10,000-tick scoring run. So v14's portal score = same as
v12 (gated only, no stops).

## Decision criteria (from operator)

- **High PnL but stable** — not chasing peak, want consistency.
- **Reactive enough to catch product-switch cases** — when a capsule-fitted
  drift reverses on scoring day, want exit/protection.
- **Not protecting against catastrophic crashes specifically, just normal
  day-to-day flips.**

## What we don't know

- Whether scoring day 5's drifts will follow capsule pattern or reverse.
- Whether NPC bot patterns (counterparty IDs) will appear live.
- True NPC variance for these specific strategies (only one sample each).
