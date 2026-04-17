# Submissions

Each folder contains the debug log zip from the IMC portal for that submission version.
Zips are gitignored — drop them into the matching folder manually.

To recover any trader: `git checkout <commit> -- src/trader.py`

| Version | Zip | Commit | Status | P&L (test run) | Notes |
|---|---|---|---|---|---|
| v1 | 235324.zip | `30ef741` | ERROR | — | Failed: `No module named 'strategies'` |
| v2 | 235663.zip | `30ef741` | FINISHED | 3,123.75 | First working submission. OSM spread=1, MeanReversionStrategy |
| v3 | — | `01a2cd9` | pending | — | TrendBiasedMMStrategy + OSM spread=3. Backtest: 194,618 |
| v4 | 246232.zip | `2b218bd` | FINISHED | 8,935 | IPRDirectionalStrategy (max long, no MM). Backtest: 262,747. OSM: 1,649, IPR: 7,286 |
| v5 | — | `c89cd7b` | pending | — | OSM wall-mid FV + wall-anchored passive. Backtest: 262,534. Should close OSM gap vs Ian |
| v6 | 246952.zip | `540d470` | FINISHED | 10,303 | OSM pennying. Backtest: 290,454. OSM: 3,017, IPR: 7,286. Saved: submissions/v6/trader_v6.py |
| v7 | — | `af6ffc8` | pending | — | OSM tight passive wall_mid±1. Backtest: 252,020 (tutorial bots dont cross tight). Targets avg fill ~2.3 like top leaderboard |
