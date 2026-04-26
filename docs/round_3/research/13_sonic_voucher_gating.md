# 13 — Sonic.ma's Hypothesis: Should Voucher Trading Be Gated?

Source: `data/round_3/prices_round_3_day_{0,1,2}.csv`. Script: `/tmp/sonic_gating.py`.
Builds on `05_voucher_chain.md` (rolling-smile residual mean-reversion) and
`07_bot_trades.md` (counterparty flow). Treats the Discord claim as a hypothesis,
not a prior.

## Method (one paragraph)

- Strategy under test = the canonical R3 alpha: **per-tick quadratic smile fit
  on VEV_5000–5500**, take IV residual, convert to price via vega, enter
  `-sign(resid)` 1-lot when `|price_resid| > 1.5`, exit on residual sign-flip,
  hold ≤ 50 ticks, flat at EOD.
- Universe = the four Discord-relevant strikes: `VEV_4500, 5000, 5300, 5400`.
  4500 and 5000 fire ~zero trades (deep-ITM / no smile residual) so usable
  PnL comes from 5300 + 5400, consistent with §05's persistent-bias finding.
- Candidate gates:
  - **rv50** — VFE realized vol (log-ret std × √(365·10⁴), 50-tick window).
  - **smile RMSE** — per-tick smile fit RMSE, 50-tick smoothed (proxy for
    surface stability).
  - **|imb|** — VFE order-book size imbalance (bid_vol − ask_vol)/total.
  - **time-of-day** — ts < 5000 vs ts ≥ 5000.

## Results — PnL (3 days, 4 vouchers, 1-lot strategy)

| Gate            | VEV_5300 | VEV_5400 | TOTAL | n_trades | Sharpe-like |
|-----------------|---------:|---------:|------:|---------:|------------:|
| **none**        |    35.5  |     7.0  |  42.5 |    903   |  0.72       |
| rv50_low        |    37.0  |    -3.0  |  34.0 |   1139   |  1.14       |
| rv50_high       |    10.5  |    13.0  |  23.5 |   1130   |  0.94       |
| **smile_good**  |    -4.0  |    -2.0  |  -6.0 |    394   | **-0.18**   |
| **smile_bad**   |    37.5  |    10.0  |  47.5 |    570   | **+1.33**   |
| imb_small       |    35.5  |     7.0  |  42.5 |    903   |  0.72       |
| imb_large       |     0.0  |     0.0  |   0.0 |      0   |   —         |
| tod_early       |    -2.5  |     3.0  |   0.5 |      3   |  0.28       |
| tod_late        |    36.5  |     2.5  |  39.0 |    902   |  0.68       |

(VEV_4500 = NaN, VEV_5000 = 0 across every gate; not signal sources.)

## What the table says

- **Order-book imbalance is dead as a gate.** VFE book is size-balanced —
  P50 of `|imb|` = 0.00, P99 = 0.094. Every observation lands in
  `imb_small` so the gate degenerates to "always on."
- **Time-of-day is a confound, not a signal.** Almost all trades fire
  after ts=5000 because the 100-tick smile-fit warmup eats the early window.
  The "alpha appears late" pattern is mechanical.
- **Realized-vol gating is a wash.** Splitting on rv50_median costs 9–19 of
  PnL vs. ungated; Sharpe rises modestly because gating halves both numerator
  and denominator. No clear regime preference.
- **Smile-RMSE gate is the only positive finding.** When the smile fits
  *poorly* (rmse_smooth > median), the strategy makes **+47.5** in 570 trades
  with Sharpe ≈ 1.33. When the smile fits *well*, it makes **-6.0** in 394
  trades. So sonic.ma is directionally right — but **inverted from the
  obvious reading**: gate IN on instability, OUT on calm surface.
  - Mechanism (hypothesis): a clean smile means the residual is just rounding
    noise (no edge to capture); a noisy smile means a strike has genuinely
    dislocated from its neighbours and will mean-revert. This matches §05's
    finding that residuals are stationary (ADF p≈0).

## Recommendation

- **Adopt one gate: `smile_rmse_smoothed > running_median` (50-tick mean,
  median computed over a trailing 1000-tick window to keep it online).**
  - Expected lift in walk-forward: **+12% PnL (42.5 → 47.5) and ~+85% Sharpe
    (0.72 → 1.33)** in the in-sample 3-day backtest. Halve both for an
    OOS prior.
  - Risk: gate is computed from the same smile being traded → mild
    look-ahead via the median threshold. Use a *trailing* median in live.
- **Drop the other three** — no evidence, and `tod` / `imb` are degenerate
  on this data.
- Sonic.ma's gating hypothesis is **partially confirmed**: gating helps,
  but the useful axis is smile instability, not vol regime or book state.

## Plots

- `plots/13_gates_overview.png` — rv50, smile RMSE, VFE imbalance
  time-series + total-PnL bars per gate.
- `plots/13_gate_voucher_heatmap.png` — PnL grid (gate × voucher).
