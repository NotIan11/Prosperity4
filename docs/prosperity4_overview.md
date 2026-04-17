# IMC Prosperity 4 — Overview

## Competition Format

- **5 rounds**, each with an algorithmic challenge + independent manual challenge.
- **Team size:** up to 5.
- **Currency:** XIRECs (renamed from "seashells" in prior editions).

## Schedule

| Round | Dates |
|---|---|
| R1 | Apr 14–17 |
| R2 | Apr 17–20 |
| Intermission | Apr 20–24 |
| R3 | Apr 24–26 |
| R4 | Apr 26–28 |
| R5 | Apr 28–30 |

## Prize Pool

$50k total: 1st $25k · 2nd–5th $5k each · Best Manual Trader $5k.

## Algo Submission

A Python `Trader` class with `run(state: TradingState) -> (orders_dict, conversions, traderData)`. Uploaded to the portal; simulated against bots. The platform injects `datamodel` as a top-level module.

## Round Progression (inferred from P3 precedent)

| Round | Expected Theme |
|---|---|
| R1 | Simple mean-reverting products |
| R2 | Basket / ETF arbitrage |
| R3 | Options / voucher pricing (Black-Scholes) |
| R4 | Cross-market conversions with tariffs/fees |
| R5 | Counterparties revealed → signal extraction / copy trading |

## R1 Products

- `ASH_COATED_OSMIUM` — position limit 80
- `INTARIAN_PEPPER_ROOT` — position limit 80

## Data Format

```
day;timestamp;product;bid_price_1;bid_volume_1;...;ask_price_1;...;mid_price;profit_and_loss
```

Days `-2, -1, 0` in tutorial files = three warm-up days.

## Community Tools

- Backtester: `pip install prosperity4btest` (data bundled for all rounds)
- Visualizer: https://jmerle.github.io/imc-prosperity-3-visualizer/ (compatible)

## Top Pitfalls

1. Overfitting to leaderboard noise
2. Ignoring that orders clear each timestep (no partial fills carried)
3. Blowing position limits (80/product for R1)
4. Neglecting the manual challenge (independent scoring)
5. No inventory risk control on market-making
6. Using lookahead on market data
7. Including dev-only imports in submission zip
