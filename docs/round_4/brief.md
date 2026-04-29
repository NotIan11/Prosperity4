# Round 4 — Official Brief

> Source: IMC Prosperity 4 Notion brief, pasted by user 2026-04-28.
> Facts only — no inference or strategy.

## Framing

Second round of the Great Orbital Ascension Trials. The **Frontier Trade Watch (FTW)** has disclosed counterparty information. Counterparty IDs are now present in the historical trade data in the Data Capsule.

Continue trading:
- `HYDROGEL_PACK`
- `VELVETFRUIT_EXTRACT`
- `VELVETFRUIT_EXTRACT_VOUCHER` (10 vouchers)

In addition, a one-time **manual** trade on `AETHER_CRYSTAL` and a collection of option contracts. Exotic options operate independently from algorithmic trading.

## Round Objective

- Optimize the Python program for HYDROGEL_PACK, VELVETFRUIT_EXTRACT, and VELVETFRUIT_EXTRACT_VOUCHER, incorporating disclosed counterparty info.
- Select Aether Crystal and option contracts and submit orders for additional profit.

## Algorithmic challenge — "Hello, I'm Mark"

- Same products as Round 3.
- New: counterparty information available. Every market participant is identifiable; their behavior can be studied.
- In `datamodel.py`, the `Trade` class has `self.buyer` and `self.seller` fields (`UserId`). In rounds 1–3 these were always `None`. From R4 onward they contain participant **names**.

`Trade` class definition (from brief):

```python
class Trade:
    def __init__(self, symbol: Symbol, price: int, quantity: int, buyer: UserId = None, seller: UserId = None, timestamp: int = 0) -> None:
        self.symbol = symbol
        self.price: int = price
        self.quantity: int = quantity
        self.buyer = buyer
        self.seller = seller
        self.timestamp = timestamp
```

### Position limits (unchanged from R3)

- `HYDROGEL_PACK`: 200
- `VELVETFRUIT_EXTRACT`: 200
- `VELVETFRUIT_EXTRACT_VOUCHER`: 300 for each of the 10 vouchers

Example from brief: `VEV_5000` is an option with strike 5000, has TTE=4 days in round 4, position limit 300.

## Manual challenge — "Vanilla Just Isn't Exotic Enough"

One-time trade. All products are written on `AETHER_CRYSTAL`. Available:

- Underlying `AETHER_CRYSTAL`
- Vanilla calls and puts with **2-week** and **3-week** expiries
- Exotics (see below)

### Time conventions (from brief)

```python
TRADING_DAYS_PER_YEAR = 252
STEPS_PER_DAY = 4
STEPS_PER_YEAR = TRADING_DAYS_PER_YEAR * STEPS_PER_DAY

def weeks_to_years(weeks: float) -> float:
    return (weeks * 5) / TRADING_DAYS_PER_YEAR

def steps_for_weeks(weeks: float) -> int:
    return int(round(weeks * 5 * STEPS_PER_DAY))
```

- A "week" = 5 trading days. "2 weeks" = 10 trading days. "3 weeks" = 15 trading days.
- 4 steps per trading day.

### Exotics offered

**Chooser Option**
- Expires in 3 weeks. After 2 weeks, buyer chooses whether it becomes a call or a put — selecting whichever is in the money at that time. Behaves like a standard option for the final week until expiry.

**Binary Put Option**
- All-or-nothing payoff. If underlying is below strike at expiry, pays the specified amount. Otherwise expires worthless.

**Knock-Out Put Option**
- Behaves like a regular put unless the underlying ever trades below the knockout barrier before expiry. If the barrier is breached at any point, the option immediately becomes worthless.

### Mechanics

- Volume cap per product: as displayed in the manual challenge UI.
- Contract size = 3000 across all products. Only used to scale PnL proportionally to R3/R5 — i.e. a PnL multiplier on the per-unit PnL of each listed product.
- Prices shown are per individual option.
- **No buying/selling across days.** Decision is made at t=0 (start of R4) and held to expiry. Marked to "fair" value at expiry = average value across **100 simulations**.
- Final score = average PnL across 100 simulations of the underlying.

### Underlying simulation

- `AETHER_CRYSTAL` follows **Geometric Brownian Motion** with zero risk-neutral drift and fixed annualized volatility of **251%**.
- Discrete grid: 4 steps per trading day, 252 trading days per year.
- No continuous modeling — knock-out barriers checked only at discrete points.

### Submission

- Input orders directly in Manual Challenge Overview. Re-submittable until round ends. Last submitted orders are locked in.

### Note on "price" column

- The "price" column in the manual UI is cosmetic, represents notional "investment cost," and is unrelated to PnL. Ignore it for trading decisions.
