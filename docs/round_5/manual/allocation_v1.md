# R5 Manual — Allocation v1

## Final recommendation: **Plan B (Middle path)**

| # | Good | Action | % |
|---|---|---|---|
| 1 | Obsidian cutlery | Buy | 2 |
| 2 | Pyroflex cells | Sell | 17 |
| 3 | Thermalite core | Buy | 18 |
| 4 | Lava cake | Sell | 14 |
| 5 | Magma ink | Buy | 10 |
| 6 | Scoria paste | — | **0** |
| 7 | Ashes of the Phoenix | Sell | 4 |
| 8 | Volcanic incense | — | **0** |
| 9 | Sulfur reactor | Buy | 20 |

**Total: 85% · Fee: 131,700 · Expected PnL: +132,900**

### Cells to update from current portal state

```
Lava cake:        Sell 12 → Sell 14
Magma ink:        Buy  13 → Buy  10
Scoria paste:     Buy   6 → 0      (skip — likely trap)
Volcanic incense: Buy   9 → 0      (skip — likely trap)
Sulfur reactor:   Buy  19 → Buy  20
```

---

## Mechanics (verified from `docs/round_5/brief.md` + portal screenshot)

- Budget: 1,000,000 Zyrex.
- Fee per good: `100·v²` (quadratic in % allocation). Confirmed exact on portal.
- Constraint: `Σ |v_i| ≤ 100`. Under is allowed; over isn't.
- BUY/SELL allowed per good (portal has dropdown).
- Used budget subtracted from PnL; unused expires worthless.
- 9 Ignith goods, 1-day hold, no re-trading.

## PnL math

```
Per good i:
  Capital = v_i × 10,000
  Fee     = 100 × v_i²
  Gross   = (sign-correct?) × |r_i| × v_i × 10,000
  Net     = (2p_i − 1)·|r_i|·v_i·10,000  −  100·v_i²
```

where `p_i` = probability the paper's direction is correct.

Unconstrained optimum: `v* = 50·|r_i|·(2p_i − 1)`. Net at optimum = `(2p−1)²·250,000·r²`.
At `p=1.0`: half of gross is fee. At `p=0.5`: skip is optimal.

## What we don't know — by design

- Actual `r_i` values are NOT in the newspaper. Paper gives signal direction +
  qualitative strength only. Hard numbers (Pyroflex cost doubles, Thermalite
  user-base 2.7×) are fundamentals, not stock returns.
- IMC anchors per-good return ranges; crowd submissions tilt mildly inside.
- Traps vs real signals on Volcanic + Scoria is a meta-judgement, unprovable
  from materials.

All `r` values below are **friend's calibration** (assumed by reverse-engineering
their allocation through `v* = 50r`). We use these as our best estimate.

## Three plans considered

### Plan A — Friend's full (100% deployed)

| Good | Action | v% | Implied \|r\| | Fee | Net (paper-honest) |
|---|---|---|---|---|---|
| Sulfur Reactor | Buy | 20 | 0.40 | 40,000 | +40,000 |
| Thermalite Core | Buy | 18 | 0.36 | 32,400 | +32,400 |
| Pyroflex Cells | Sell | 17 | 0.34 | 28,900 | +28,900 |
| Lava Cake | Sell | 14 | 0.28 | 19,600 | +19,600 |
| Magma Ink | Buy | 10 | 0.20 | 10,000 | +10,000 |
| Volcanic Incense | Buy | 8 | 0.16 | 6,400 | +6,400 |
| Scoria Paste | Buy | 7 | 0.14 | 4,900 | +4,900 |
| Ashes of Phoenix | Sell | 4 | 0.08 | 1,600 | +1,600 |
| Obsidian Cutlery | Buy | 2 | 0.04 | 400 | +400 |
| **Totals** | | **100** | | **144,200** | **+144,200** |

### Plan B — Middle (skip Volcanic + Scoria) ⭐

Same as A except V/S set to 0. **Total 85% deployed, fee 131,700, net +132,900.**

### Plan C — Inverted (flip V+S to Sell)

Same as A except V Sell 8 / S Sell 7. Total 100%, fee 144,200, net +99,000 if
paper honest, +143,200 if traps.

## Scenario matrix — total PnL

| Plan | Paper honest | Pumps are traps |
|---|---|---|
| A (full) | **144,200** | 99,000 |
| **B (middle)** | 132,900 | 132,900 |
| C (inverted) | 99,000 | **143,200** |

## Regret matrix — vs the best plan in each scenario

| Plan | If honest | If trap | Worst-case |
|---|---|---|---|
| A (full) | 0 | −45,200 | **−45,200** |
| **B (middle)** | **−11,300** | **−11,300** | **−11,300** |
| C (inverted) | −45,200 | 0 | −45,200 |

## EV-vs-median competitor (assumed = Plan A)

| Plan | If honest | If trap | EV at p(trap) = 0.55 |
|---|---|---|---|
| A (full) | 0 | 0 | 0 (no leaderboard climb) |
| **B (middle)** | −11,300 | **+33,900** | **+13,560** |
| C (inverted) | −45,200 | +45,200 | +4,520 |

## Why Plan B

1. **Smallest worst-case regret** (−11,300 vs −45,200 for A or C).
2. **Highest EV-vs-median** across realistic `p(trap) ∈ [0.40, 0.70]`.
3. **Big-4 (where ~91% of PnL lives) is unchanged.** Sizing on
   Sulfur/Thermalite/Pyroflex/Lava is friend's, which we agree on.
4. **Skip is mathematically dominant** for goods where direction confidence
   is in [0.25, 0.75] — exactly where Volcanic + Scoria sit per discord and
   paper meta-cues. Threshold derivation: at `v* = 50r`, hold beats skip iff
   `p > 0.75`; flip beats skip iff `p < 0.25`.

## When NOT to pick Plan B

- Pick A if you have strong conviction the paper is fully honest (e.g., other
  signals or insider info we don't have).
- Pick C if you have strong conviction `p(trap) ≥ 0.65` on Volcanic + Scoria
  and want maximum leaderboard climb at higher variance.

## Sources

- Newspaper: `docs/round_5/manual/ashflow_alpha_transcript.md`
- Discord: `docs/round_5/manual/discord_findings.md`
- Brief: `docs/round_5/brief.md`
- Friend's allocation screenshot: pasted by user 2026-04-30.
- Portal state screenshot: pasted by user 2026-04-30 (BUY/SELL confirmed,
  fee formula verified, current state = friend's pre-revised values).
