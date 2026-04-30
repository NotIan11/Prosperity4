# R5 Manual — Allocation v1

## Mechanics (from `docs/round_5/brief.md`)

- Budget: **1,000,000 Zyrex**.
- Fee per good: `(v_i / 100)² × 1,000,000 = 100·v_i²` (quadratic in % allocation).
- Constraint: `Σ |v_i| ≤ 100`. May go under; may NOT exceed.
- Used budget is subtracted from PnL; unused budget expires worthless.
- 9 Ignith goods, 1-day hold, no re-trading.

## Per-good PnL math

Let `v_i` = % budget allocated, `r_i` = expected 1-day return on the position
(positive = direction matches paper signal).

```
Capital_i = v_i × 10,000
Fee_i     = 100 × v_i²
Gross_i   = |r_i| × v_i × 10,000
Net_i     = 10,000·|r_i|·v_i  −  100·v_i²
```

Unconstrained per-good optimum: `v_i* = 50·|r_i|`, giving `Net_i* = 250,000·r_i²`.

If `Σ 50·|r_i| > 100`, budget cap binds and Lagrangian rescales:
`v_i = 50·r_i − λ/200` (uniform shrink across goods).

## What the source materials give us

**The newspaper does NOT publish return forecasts.** Only direction + qualitative
strength. Hard numbers in the paper are fundamentals, not returns:

| Article | Quantitative anchor |
|---|---|
| Article 3 (Pyroflex) | "doubles the current levy" — input cost shock |
| Article 4 (Thermalite) | Users 1.42M → 3.89M (+174%); 16h 42min/day usage |
| Article 1 (Magma Ink) | "more than six hours" queue (anecdotal) |
| Articles 2, 5, 6, 7, 8, 9 | None |

Discord-confirmed mechanic: IMC sets a pre-anchored return range per good;
crowd submissions tilt mildly within range. **Players cannot read the actual r.**
All r below are assumed by either us or our teammate.

## Plan A — Friend's allocation (full 100% budget)

| Good | Action | v% | Implied \|r\| | Capital | Fee | Net (if r holds) |
|---|---|---|---|---|---|---|
| Sulfur Reactor | BUY | 20 | 0.40 | 200,000 | 40,000 | +40,000 |
| Thermalite Core | BUY | 18 | 0.36 | 180,000 | 32,400 | +32,400 |
| Pyroflex Cells | SELL | 17 | 0.34 | 170,000 | 28,900 | +28,900 |
| Lava Cake | SELL | 14 | 0.28 | 140,000 | 19,600 | +19,600 |
| Magma Ink | BUY | 10 | 0.20 | 100,000 | 10,000 | +10,000 |
| Volcanic Incense | BUY | 8 | 0.16 | 80,000 | 6,400 | +6,400 |
| Scoria Paste | BUY | 7 | 0.14 | 70,000 | 4,900 | +4,900 |
| Ashes of Phoenix | SELL | 4 | 0.08 | 40,000 | 1,600 | +1,600 |
| Obsidian Cutlery | BUY | 2 | 0.04 | 20,000 | 400 | +400 |
| **Totals** | | **100%** | | 1,000,000 | 144,200 | **+144,200** |

Reads paper at face value. Internally consistent: ratios match `v ∝ r`,
implying friend's strategy is "trust the paper, scale to budget cap."

## Plan B — Discord-inverted variant (fade the pumps)

Identical to Plan A except Volcanic Incense and Scoria Paste flipped from BUY to
SELL — discord consensus reads both influencer-driven articles as designed traps.

| Good | Action | v% | Net (if signed r holds) |
|---|---|---|---|
| Sulfur Reactor | BUY | 20 | +40,000 |
| Thermalite Core | BUY | 18 | +32,400 |
| Pyroflex Cells | SELL | 17 | +28,900 |
| Lava Cake | SELL | 14 | +19,600 |
| Magma Ink | BUY | 10 | +10,000 |
| Volcanic Incense | **SELL** | 8 | +6,400 (if pump fades) / −19,200 (if pump real) |
| Scoria Paste | **SELL** | 7 | +4,900 (if pump fades) / −14,700 (if pump real) |
| Ashes of Phoenix | SELL | 4 | +1,600 |
| Obsidian Cutlery | BUY | 2 | +400 |

Same fee structure (144,200). PnL diverges only on the two flipped goods.

## Plan C — Conservative 65% (original)

Skips Magma Ink + Obsidian Cutlery (split community / priced-in concerns),
small SHORTS on Volcanic + Scoria + Ashes. Total deployed 65%, expected
net ≈ +80,000 if assumed |r|s hold. Lower variance, lower upside.

## Decision criteria

- If **|r| averages ≥ 0.30** across the 4 high-confidence goods → Plan A optimal
  (full budget pays off).
- If **|r| averages ~0.20** → Plan C optimal (65% is closer to the unconstrained
  per-good optimum; Plan A overpays in fees).
- If **the influencer articles are traps (game design)** → flip Volcanic + Scoria
  → Plan B beats Plan A by ~25,600 expected (8%/7% switching from buy-into-fade
  to short-into-fade).

## Open questions before submission

1. **Are shorts allowed?** Brief says "distribute budget across goods" — implies
   long-only. If long-only, all SELL rows above become "skip", which hurts our
   expected PnL on Pyroflex / Lava / Ashes a lot. **MUST verify on portal UI.**
2. **Is the fee deducted from the deployed capital or from final PnL?** Brief
   says "used budget is subtracted from trade PnL" — net formula handles both
   identically, but worth confirming.
3. Does Volcanic Incense / Scoria Paste pumping continue (face-value buy) or
   reverse (trap)? Unresolvable from paper alone.

## Sources

- Newspaper: `docs/round_5/manual/ashflow_alpha_transcript.md`
- Discord: `docs/round_5/manual/discord_findings.md`
- Brief: `docs/round_5/brief.md`
- Friend's screenshot: pasted by user 2026-04-30 (recommended Plan A).
