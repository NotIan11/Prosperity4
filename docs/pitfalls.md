# Common Pitfalls

1. **Blowing position limits** — simulator hard-rejects over-limit orders. Always compute remaining capacity before submitting.

2. **Lookahead bias** — using `mid_price` or `own_trades` from the current tick to inform orders *placed* that same tick. Orders fill in the *next* clearing step.

3. **No inventory control** — pure quote-at-fair-value without position skew will accumulate a one-sided book in trending markets. Always skew quotes against your current position.

4. **Overfitting to tutorial days** — days -2, -1, 0 are warm-up data. Don't hard-code parameters that fit these exactly; they may not generalize to live days.

5. **Including dev-only imports** — `src/` is zipped for submission. Any import not available on the platform (e.g., `pandas`, `matplotlib`, `numpy`) will crash the bot.

6. **Ignoring the manual challenge** — manual challenge scores independently. Neglecting it costs free points.

7. **Single-tick history** — `state.own_trades` and `state.market_trades` only contain the *previous* tick's trades, not a rolling history. Maintain your own history in `traderData`.

8. **Wrong sign on sell orders** — `Order(symbol, price, -qty)` for sells. Positive quantity = buy.

9. **Assuming partial fills** — if your bid is below the best ask, no fill occurs. The order expires. Don't build strategies that assume partial execution.

10. **Leaderboard chasing** — the public leaderboard is noisy and updates infrequently. Optimize on your own backtest metrics, not leaderboard rank.
