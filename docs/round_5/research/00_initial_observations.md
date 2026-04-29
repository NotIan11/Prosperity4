# R5 — Initial observations (pre-EDA)

> Working notes captured 2026-04-28 from the R5 brief.
> Not authoritative — purely first-pass reactions.

## Headline shifts vs R3/R4

- **Position limit collapses from 200–300 to 10 per product.** Massive change.
  Edge no longer comes from sizing flow; it has to come from **picking
  winners** (which of the 50 are tradable patterns) and signal quality.
- **50 brand new products, 10 categories × 5.** No carry-over of
  product-specific knowledge. R3/R4 strategies are dead code for R5
  (per the brief's explicit "you can no longer trade products from previous
  rounds").
- **Brief explicitly hints some categories are rigged:** "Each group has
  its own story, but some offer more market inefficiencies than others.
  In certain groups, strong patterns are embedded in the price movements,
  waiting to be discovered by you." → first task is EDA across the 50
  products to find which groups have exploitable signal.

## Carry-overs that DO survive

- **Process discipline.** Portal stochasticity (research/17), BT vs live
  divergence (research/14), traderData hygiene (R4 bot already implements).
- **Strategy framework.** R4 bot's abstract `Strategy` + `save_state`
  pattern generalizes — drop in a new strategy per product/group.
- **Counterparty data (if it persists into R5).** Brief doesn't say
  whether `Trade.buyer/seller` are still populated in R5 — needs
  verification by inspecting R5 capsule trades CSV.

## Possible group-structure plays (speculation, not facts)

- Cross-sectional rank within group (mean-revert outliers).
- Basket / pair trades within group (e.g. PANEL_1X2 vs PANEL_4X4).
- Cosmetic feature → price (color, size, flavor) — competition has
  historically used these as red herrings or as actual features.
- Single-name signals on the "rigged" groups, naive MM on the rest.

## Manual challenge — observations

- **Hold-to-next-day directional bet** on 9 Ignith goods. Driven by news
  feed (Ashflow Alpha), not price action. This is a portfolio
  construction problem, not a market making problem.
- **Fee formula (corrected):** `fee = (v/100) * (v/100) * budget` with
  budget = 1,000,000.
  - Quadratic in `v`, linear in budget.
  - At v=100 (full allocation in one good): fee = 1 × 1 × 1M = 1M
    (entire budget consumed as fee — implies "v" is allocation
    percentage, not raw volume).
  - At v=10 (10% allocation): fee = 0.1 × 0.1 × 1M = 10k.
  - At v=50 (50% allocation): fee = 0.5 × 0.5 × 1M = 250k.
  - **Quadratic fee penalizes concentration** — diversifying across
    multiple goods has lower total fee than concentrating in one,
    given equal total allocation.
- **Underused budget evaporates** (no carry-over to PnL). So "use less
  than 100%" is a real choice — only worth using budget if expected
  edge per dollar > fee per dollar.

## Open questions

- Does `Trade.buyer/seller` persist in R5 capsule data?
- Are the "embedded patterns" in price levels (mean-rev), price
  derivatives (momentum), or cross-product (basket)?
- Is the fee formula's `v` measured in percent of budget, raw units, or
  contract count? Worth verifying via wiki/discord clarification.
- Position limit 10 — is that a HARD cap (max 10 long, max 10 short,
  net 20 inventory range) or just net?
