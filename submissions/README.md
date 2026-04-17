# Submissions

Each folder contains the debug log zip from the IMC portal for that submission version.
Zips are gitignored — drop them into the matching folder manually.

To recover any trader: `git checkout <commit> -- src/trader.py`

| Version | Zip | Commit | Status | P&L (test run) | Notes |
|---|---|---|---|---|---|
| v1 | 235324.zip | `30ef741` | ERROR | — | Failed: `No module named 'strategies'` |
| v2 | 235663.zip | `30ef741` | FINISHED | 3,123.75 | First working submission. OSM spread=1, MeanReversionStrategy |
| v3 | — | `01a2cd9` | pending | — | TrendBiasedMMStrategy + OSM spread=3. Backtest: 194,618 |
