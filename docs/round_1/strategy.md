# Round 1 Strategy

## Products

| Product | Position Limit | Strategy Class | Final Params |
|---|---|---|---|
| ASH_COATED_OSMIUM | ±80 | `OsmiumStrategy` | FAIR_VALUE=10000 |
| INTARIAN_PEPPER_ROOT | ±80 | `MeanReversionStrategy` | window=2, spread=1 |

---

## ASH_COATED_OSMIUM

### Behavior
Extremely stable: mean 10,000.20, std 5.35, range 9977–10023 across all 3 tutorial days.
Market maker holds a ~16-tick spread (bids ~9992, asks ~10008). Mid mean-reverts strongly to 10,000.

### Strategy: hardcoded fair value
1. **Take** any sell order priced < 10,000 (guaranteed edge).
2. **Take** any buy order priced > 10,000 (guaranteed edge).
3. **Post** remaining gross capacity at 9,999 / 10,001 passively.

This is identical to the AMETHYSTS approach used by top P2/P3 teams.

### Backtest results (tutorial days)
| Day | P&L |
|---|---|
| -2 | 5,190 |
| -1 | 6,164 |
| 0 | 5,146 |
| **Total** | **16,500** |

---

## INTARIAN_PEPPER_ROOT

### Behavior
Highly volatile: std ~866 across all 3 days, range 9,998–13,007. Price trends up ~1,000/day
(day -2: 9998→11001, day -1: 10998→11998, day 0: 11998→13000). Market spread ~13 ticks.
Strong negative lag-1 autocorrelation (−0.59) — price bounces at tick level even while trending.

### Strategy: near-immediate EWM market-making
Uses a very fast EWM (window=2, α=2/3) which tracks actual mid with <0.1 tick average lag.
Quotes at EWM±1 — well inside the 13-tick market spread, attracting fills on both sides.

**Why spread=1 (not wider):**
- Our quotes are still 5–6 ticks better than the market maker's 6.5-tick half-spread.
- In a trending market, being near-zero lag prevents directional accumulation.
- Both buyers (who'd pay up to 6.5) and sellers (who'd accept down to -6.5) prefer our ±1 quotes.

**Why near-immediate EWM (not longer):**
- Longer EWM (e.g., window=10) lags ~0.5 ticks in the trending market.
- With spread=2 and 0.5 lag, our ask ends up ~1.5 ticks above actual mid (still gets hit by buyers)
  while our bid ends up ~2.5 ticks below (sellers prefer the market maker's 6.5-tick bid over our
  2.5-tick bid). Result: systematic short accumulation on trending days → losses.
- window=2 eliminates this asymmetry.

**Capacity tracking:**
Both strategies track gross buy/sell quantities separately (not net position) to avoid the
backtester's limit check: `current_pos + sum(all_buy_orders) > limit → all orders rejected`.

### Parameter sweep results (total P&L across all 3 days)
| window | spread=1 | spread=2 | spread=3 |
|---|---|---|---|
| 2 | **142,728** | 57,828 | 64,562 |
| 5 | 101,724 | 109,354 | 66,452 |
| 10 | 76,245 | 95,816 | 65,872 |
| 20 | 75,477 | — | — |

### Backtest results (tutorial days)
| Day | P&L | Pepper Root |
|---|---|---|
| -2 | 45,748 | 40,558 |
| -1 | 49,224 | 43,060 |
| 0 | 47,756 | 42,610 |
| **Total** | **142,728** | **126,228** |

Sharpe ratio: 27.3 (annualized). Zero limit violations. All 3 days positive.

---

## Submission Checklist

- [ ] Confirm no pandas/numpy/matplotlib imports in `src/trader.py` or strategy files
- [ ] Run `./tools/run_backtest.sh` from project root and confirm positive P&L
- [ ] Upload `src/trader.py` + `src/strategies/` + `src/datamodel.py` via IMC portal
- [ ] Do NOT include `.venv/`, `data/`, `notebooks/`, `docs/` in submission zip
