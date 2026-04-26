# Round 3 — Brief

Sourced from the IMC R3 wiki text and ARIA Uplink R3 video transcript.

---

## Meta

- R3 starts the **GOAT phase** (Great Orbital Ascension Trials).
- **Leaderboard resets to 0** at start of R3. Pre-R3 PnL discarded.
- Each round = **48 hours** (Solvenarian day).
- Like in previous rounds, any open positions at end of round are **automatically liquidated against a hidden fair value**.

---

## Algorithmic challenge — "Options Require Decisions"

Two asset classes:
- `HYDROGEL_PACK` and `VELVETFRUIT_EXTRACT` are **"delta 1"** products (similar to tutorial / R1 / R2 products).
- 10 `VELVETFRUIT_EXTRACT_VOUCHER` products are **options**.

All products trade independently, even though voucher price may relate to VFE due to the nature of options.

**VEV** = **V**elvetfruit **E**xtract **V**oucher. Suffix = strike price.

### Products

| Symbol | Class | Position limit |
|---|---|---|
| `HYDROGEL_PACK` | delta-1 | 200 |
| `VELVETFRUIT_EXTRACT` | delta-1 | 200 |
| `VEV_4000` | option, strike 4000 | 300 |
| `VEV_4500` | option, strike 4500 | 300 |
| `VEV_5000` | option, strike 5000 | 300 |
| `VEV_5100` | option, strike 5100 | 300 |
| `VEV_5200` | option, strike 5200 | 300 |
| `VEV_5300` | option, strike 5300 | 300 |
| `VEV_5400` | option, strike 5400 | 300 |
| `VEV_5500` | option, strike 5500 | 300 |
| `VEV_6000` | option, strike 6000 | 300 |
| `VEV_6500` | option, strike 6500 | 300 |

### Voucher rules

- Each voucher gives the right to buy VFE at a later point for the strike price.
- **Cannot be exercised before expiry.**
- All 10 vouchers share a **7-day expiration** measured from start of R1 (1 round = 1 day).
- TTE schedule:
  - Historical day 0 (tutorial): TTE = 8d
  - Historical day 1 (R1): TTE = 7d
  - Historical day 2 (R2): TTE = 6d
  - **R3 final sim: TTE = 5d**
- Voucher inventory does not carry over into the next round.

---

## Manual challenge — "The Celestial Gardeners' Guild"

### Setup

- Guild appears in **R3 only**; departs after.
- Trade **at most once** with each of a **secret number** of counterparties (the "gardeners" / "Guardeners"); each has a hidden **reserve price**.
- Acquired Bio-Pods are auto-sold next trading day at fixed fair price **920**.
- Submitted via Manual Challenge Overview GUI, separate from algo upload. Re-submittable until round end; last submission locks.

### Reserve price distribution

- Uniformly distributed over integers in increments of **5** between **670 and 920** (inclusive on both ends).
- Example: reserves at 675 and 680 are valid; 676/677/678/679 are not.
- Guild superstition: "Power of the flowering fives" — reflects the 5-step spacing.

### Bid mechanics

Submit **two bids**. For each gardener with reserve `r`:

1. **If `bid1 > r`** → trade at `bid1`.
2. **Else if `bid2 > r`**:
   - **If `bid2 > avg_b2`** (mean of all players' second bids) → trade at `bid2`.
   - **If `bid2 ≤ avg_b2`** → trade at `bid2`, but PnL is penalised by:

```
( (920 - avg_b2) / (920 - bid2) )^3
```

3. **Else** → no trade.
