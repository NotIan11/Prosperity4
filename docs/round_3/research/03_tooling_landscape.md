# Tooling landscape — backtesters, visualizers, submitters

State as of 2026-04-26. Single source of truth: `prosperity4btest`.

## Backtester — `prosperity4btest`

The team's chosen backtester. Listed in `requirements.txt`.

| | |
|---|---|
| PyPI package | `prosperity4btest` |
| CLI binary | `prosperity4btest cli` |
| Python module name | `prosperity4bt` (note the mismatch: install name ≠ import name) |
| Author | Nabayan Saha |
| LIMITS | Correct P4 hardcoded — no patching needed |
| Bundled data | R3 days 0/1/2 included |
| Free metrics | Sharpe, Sortino, Calmar, max drawdown |

### Usage

```bash
# Run our trader against all 3 R3 days
venv/bin/prosperity4btest cli src/trader.py 3 --no-out

# Run a single day
venv/bin/prosperity4btest cli src/trader.py 3-0 --no-out

# Save the log
venv/bin/prosperity4btest cli src/trader.py 3
# (writes to backtests/<timestamp>.log; backtests/ is gitignored)

# Merge PnL across days
venv/bin/prosperity4btest cli src/trader.py 3 --merge-pnl --no-out
```

That's it. No harness, no monkey-patching, no staging dirs.

## How accurate is it?

**Directionally trustworthy for goods, approximate for vouchers.**

### What's trustworthy
- **Relative comparisons** between goods configurations (A beats B in BT
  → A probably beats B live).
- **Per-day breakdown** of goods PnL — useful for spotting regressions.
- **Built-in risk metrics** (Sharpe, max DD, etc.).

### What to treat as approximate
- **Absolute PnL numbers** — expect ~10–25% drift between BT and live.
  Don't tune to the last decimal.
- **Voucher PnL** — the BT does not special-case voucher liquidation
  at end of round. It marks open voucher inventory at last observed
  mid. The IMC platform marks at a hidden fair value (probably BS-theo
  with their hidden vol). Material discrepancy possible if voucher
  inventory at end of round is large. **Mitigate by ending the round
  flat on voucher positions.**

### What to NOT tune to
- **Portal score** — per Discord (theethan7114, lanister5240), the IMC
  portal sim runs ~10% of one day. Portal PnL ≈ ~3% of 3-day BT PnL.
  Don't optimize to portal numbers.

### Open caveat from Discord (shh1v 04-25 23:07)
> "no local backtester is accurate rn because the timesteps loop if
> you combine the rounds data… relevant because most algo rely on
> time to expiry calculation"

Affects voucher TTE-aware code when concatenating rounds. We don't
combine rounds (R3 only), so this doesn't bite us today. Worth
re-checking in R4/R5.

## Voucher mechanics — what the BT does NOT model

Per `docs/round_3/brief.md`:
- Vouchers cannot be exercised before expiry (European-style)
- 7-day expiry from R1 start; TTE = 5d at end of R3
- **Open positions at end of round are auto-liquidated at hidden fair
  value** — and inventory does not carry to next round
- Vouchers technically never reach TTE=0 during the competition (5
  rounds × 1 day < 7-day expiry)

Implication: **there is no exercise event during R3.** The "European"
restriction is a *pricing assumption* (no early exercise → BS works),
not a *mechanical* end-of-round event. The BT marks open vouchers at
last mid; the platform marks at hidden fair value. Difference =
liquidation risk for any voucher inventory we hold at end of round.

## Other tooling

### jmerle's P3 stack (visualizer / submitter still work)

jmerle has not released P4 versions, but his P3 viz/submitter still
work because the trader interface is unchanged across years:

| Repo | Use |
|---|---|
| `jmerle/imc-prosperity-3-visualizer` | Open BT output JSON to inspect |
| `jmerle/imc-prosperity-3-submitter` | CLI upload to portal |

### Tools to AVOID

- **`prosperity.equirag.com`** (geyzsonkristoffer's leaderboard/
  visualizer): per Discord (chirpy0, js361 + admission by author
  04-24), it stores full uploaded log files. **Do not upload our
  logs there** — alpha leakage risk.

### Other community P4 backtester forks (un-vetted)

We're not using these. Listed only so anyone evaluating later knows
the landscape:

| Repo | Notes |
|---|---|
| `kevin-fu1/imc-prosperity-4-backtester` | Active, bug reports against PyPI install (KeyError) |
| `Xeeshan85/imc-prosperity-4-backtester` | Active fork |
| `shh1v/imc-prosperity-4-backtester` | Active, recommended by some users |
| `geyzsonkristoffer/rust_backtester` | Rust, claims close-to-portal accuracy |
| `matthewnapoli/prosperity4bt` | Archived. Don't use |

Skip these unless `prosperity4btest` breaks on something specific.

## Open questions for R4/R5 prep

- Will the hidden-fair-value liquidation issue materialize at end of
  R3 if our voucher inventory is non-zero? (Watch live PnL vs BT.)
- Does the TTE-loop bug bite when we combine R3 + R4 data later?
- Will jmerle release a P4 backtester before R4?
