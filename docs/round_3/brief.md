# Round 3 Brief

Source: IMC Prosperity 4 wiki, R3 (transcribed).

---

## Leaderboard reset

R3 begins the **Great Orbital Ascension Trials** (R3+R4+R5). All teams start at zero PnL.
Only R3–R5 PnL counts toward the final ranking. R1+R2 results are discarded.

Round length: **48 hours** each.

---

## Algorithmic challenge — "Options Require Decisions"

### Products

| Symbol | Class | Position Limit |
|---|---|---|
| `HYDROGEL_PACK` | delta-1 | 200 |
| `VELVETFRUIT_EXTRACT` | delta-1 (option underlying) | 200 |
| `VEV_4000` … `VEV_6500` | call options on VFE | 300 each |

Voucher strikes (10 total):
**4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500**

Note the tight cluster from 5100–5500 (5 strikes) — implies the underlying trades around there.
4000/4500 deep ITM, 6000/6500 deep OTM.

### Time to expiry

- 7-day expiration measured from start of R1 (1 round = 1 day).
- **At start of R3 final simulation: TTE = 5 days.**
- Historical data: TTE=8d (day 0 / tutorial), 7d (day 1 / R1), 6d (day 2 / R2).
- Vouchers cannot be exercised early.
- Inventory does NOT carry between rounds. End-of-round positions liquidate against hidden fair value.

### Implied tasks

1. **HYDROGEL_PACK** — analyse spot dynamics, market-make.
2. **VELVETFRUIT_EXTRACT** — analyse spot dynamics, market-make.
3. **Vouchers** — Black-Scholes (or similar) pricing using VFE as underlying. Trade against bot mispricing. With TTE=5d and 10 strikes spread across moneyness, classic vol-surface trade.

---

## Manual challenge — "Celestial Gardeners' Guild"

Sealed two-bid auction, separate from algo submission.

### Mechanics

- Counterparties (secret number) have reserve prices uniformly distributed on **{670, 675, 680, …, 915, 920}** — i.e. multiples of 5 from 670–920.
- You sell biopods next round at fixed **920**.
- Submit **two bids** per session.

**Bid resolution:**
- If `bid1 > reserve` → trade at `bid1`, profit = `920 - bid1`.
- Else if `bid2 > reserve` AND `bid2 > mean_of_all_players_bid2` → trade at `bid2`, profit = `920 - bid2`.
- Else if `bid2 > reserve` AND `bid2 ≤ mean_of_all_players_bid2` → trade at `bid2` BUT profit multiplied by:

```
( (920 - avg_b2) / (920 - bid2) )^3
```

- Else → no trade.

### Strategy notes

- The penalty formula creates a soft cliff: bidding below the average b2 still trades, but profit collapses cubically as you go further below.
- Optimal b2 ≈ predicted average of other players' b2s (so multiplier ≈ 1).
- Bid 1 should be aggressive-low to capture cheap counterparties; bid 2 is the "safety net" that scoops the rest.
- This is a meta-game — depends on what other teams will do.

---

## Open questions to resolve

1. **Are R1/R2 products still tradable in R3?** Wiki only lists the 3 new products. Likely NO, but confirm by inspecting `state.order_depths` in the first backtest run.
2. **Velvetfruit price level + volatility** — need to load the historical CSVs.
3. **Voucher market structure** — how wide are spreads, what's the implied vol surface look like?
