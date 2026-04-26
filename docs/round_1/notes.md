# Round 1 Notes

## Products

- `ASH_COATED_OSMIUM` — position limit ±80
- `INTARIAN_PEPPER_ROOT` — position limit ±80

## Initial Observations (from analysis.py)

- Both products exhibit mean-reverting behavior on mid price.
- Rolling means (50 and 200 period) track the mid closely, suggesting a stable fair value.
- Spread is typically narrow; passive market-making should capture it.

## Strategy Approach

See `docs/round_1_strategy.md` once Phase 2 analysis is complete.

## Data Files

| File | Contents |
|---|---|
| `data/prices_round_1_day_-2.csv` | LOB snapshots, day -2 |
| `data/prices_round_1_day_-1.csv` | LOB snapshots, day -1 |
| `data/prices_round_1_day_0.csv` | LOB snapshots, day 0 |
| `data/trades_round_1_day_-2.csv` | Market trades, day -2 |
| `data/trades_round_1_day_-1.csv` | Market trades, day -1 |
| `data/trades_round_1_day_0.csv` | Market trades, day 0 |
