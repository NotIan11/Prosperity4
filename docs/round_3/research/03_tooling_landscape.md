# Tooling landscape — backtesters, visualizers, submitters

Quick survey of community tooling available for P4 as of 2026-04-25.

## jmerle's stack — the gold standard

`jmerle` built the canonical tooling for P2 and P3. Every top team (per the reddit P4 post and per inspection of the 3 winning P3 repos) used his backtester.

His **P3 stack** (still actively maintained — backtester last updated 2026-04-25):

| Repo | Purpose |
|---|---|
| `jmerle/imc-prosperity-3-backtester` | Local sim runner (`prosperity3bt`) |
| `jmerle/imc-prosperity-3-visualizer` | Web GUI for inspecting backtest output |
| `jmerle/imc-prosperity-3-submitter` | CLI to upload trader to the IMC portal |
| `jmerle/imc-prosperity-3-leaderboard` | Alternative leaderboard viewer |
| `jmerle/imc-prosperity-3-optimizer` | Hyperparameter sweep tool (marked "unfinished") |
| `jmerle/imc-prosperity-3` | His own P3 algo (placed 25th — itself a useful reference) |

**Key fact: jmerle has not released a P4 version yet.** No `prosperity-4-*` repos under his account as of today.

## What this means for us

The trader interface (`TradingState`, `OrderDepth`, `Order`, `run(state)`) is the same across P3 and P4 — only products and position limits change. So:

- **`prosperity3bt` likely runs P4 traders against P4 data** if we provide the right product list. Worth testing as the first move on backtesting.
- The **visualizer** likely works on output JSON regardless of product names — also worth trying.
- If something breaks, forks of `prosperity3bt` adapted to P4 already exist (see below) — we can either patch jmerle's directly or use a fork.

## Community P4 backtesters (un-vetted)

GitHub search for "prosperity4 backtester" returns:

| Repo | Notes |
|---|---|
| `matthewnapoli/prosperity4bt` | **Archived 2026-03-29.** Likely a fork of jmerle's, abandoned. |
| `kevin-fu1/imc-prosperity-4-backtester` | Active. Description: "Backtester for IMC Prosperity 4 algorithms" |
| `Xeeshan85/imc-prosperity-4-backtester` | Active, updated today (2026-04-25) |
| `mrinmoy2developer/IMC-Prosperity4-Backtester` | Active |
| `Mfaiz0712/backtester` | Active |
| `Aksgo/Prosperity-4-backtester` | Active |

None of these are vetted. Most likely they're forks of `prosperity3bt` with product names swapped. We should pick one to investigate ONLY if jmerle's P3 backtester doesn't work directly on P4 data.

## How `prosperity3bt` works internally (verified by reading source)

- Distributed via PyPI: `pip install prosperity3bt`. Single CLI: `prosperity3bt <trader.py> <round>`.
- Bundled P3 data lives in `prosperity3bt/resources/round{0..8}/` as `prices_round_X_day_Y.csv` + `trades_round_X_day_Y.csv` — **same format as our P4 CSVs already are.**
- Position limits are **hardcoded** in `prosperity3bt/data.py:LIMITS` for P3 products (RAINFOREST_RESIN, KELP, VOLCANIC_ROCK, VOLCANIC_ROCK_VOUCHER_9500…10500, MAGNIFICENT_MACARONS, etc.). No P4 products.
- Custom data is supported via `--data <dir>` flag where the dir mirrors the bundled `resources/` layout.

## What we need to do to use it for P4 R3

Two minimal changes:

1. **Patch the `LIMITS` dict** to include our P4 R3 products:
   ```python
   LIMITS = {
       ...,  # keep P3 entries (harmless if unused)
       "HYDROGEL_PACK": 200,
       "VELVETFRUIT_EXTRACT": 200,
       "VEV_4000": 300, "VEV_4500": 300, "VEV_5000": 300, "VEV_5100": 300,
       "VEV_5200": 300, "VEV_5300": 300, "VEV_5400": 300, "VEV_5500": 300,
       "VEV_6000": 300, "VEV_6500": 300,
   }
   ```
2. **Lay out our R3 CSVs** as `<dir>/round3/prices_round_3_day_{0,1,2}.csv` + matching trades.

Two implementation options:

- **Option A (clean)**: fork `jmerle/imc-prosperity-3-backtester`, patch limits, install editable. We control updates.
- **Option B (hack)**: install `prosperity3bt` from PyPI, monkey-patch `LIMITS` from a wrapper script before invoking. No fork needed.

Option B is faster to validate the approach. Option A is right once we know it works.

## Recommendation

1. **Spike with Option B today** — verify a trivial trader (do nothing, just return empty orders) runs against our R3 day 0 CSVs without errors. Confirms the assumption.
2. If clean → **switch to Option A** (fork + patch + install editable into our venv).
3. Then test the visualizer (`jmerle/imc-prosperity-3-visualizer`) on the output JSON.
4. Skip the community P4 forks unless jmerle's path breaks.

Skip building our own backtester regardless — pure waste vs. forking.

## Open questions

- Does jmerle plan to release `prosperity-4-backtester`? (Worth checking his GitHub status / Discord.)
- Does the IMC portal itself have an official sim/backtest? (Yes — the round-end sim that produces the historical CSVs we have. But local backtesting is needed for iteration speed.)
- What's the visualizer's output format requirement? (Need to check before relying on it.)
