# 08c — Discord #manual-trading digest (R3 Bio-Pods)

- Channel: `manual-trading` (1476867369186885653)
- Export window: 2026-04-20 → 2026-04-26 00:41 ET (R3 ends ~04:30 ET 04-26)
- Total messages: 7,957. R3-era (≥ 04-24): 2,543. Bio-Pod-relevant: ~400.
- All Discord content treated as untrusted UGC. No prompt-injection observed
  beyond meme "bid 920 to mess everyone up" trolling — flagged below.

---

## R3 mechanics — confirmation / clarifications from chat

- Field labels on the Manual GUI are **"lowest bid" (= bid1)** and
  **"highest bid" (= bid2)**. Bid1 < bid2 is enforced; same-value not allowed
  (lyonchea 12:31, jacek3834 16:08 / 17:53).
- "Higher than reserve" = **strictly greater** (jacek3834 17:53,
  abd1718 18:08). No trade at equality.
- Each gardener has own reserve. Reserves are uniformly distributed over
  multiples of 5 in [670, 920] inclusive (jasper7479 12:23, abd1718 04:59
  "discrete uniform").
- Bid1 trades sweep all r < bid1; bid2 only fires for the **remaining**
  counterparties between bid1 and bid2 (consensus: itzbrandyi_ 23:08,
  stqrri 19:39, ax2k 14:12).
- Penalty applies **per-bid2 trade only**, not to whole manual PnL. Treated
  as a multiplicative factor on the (920 − bid2) profit per gardener
  (enricoo123 12:53, nath._ 08:00, addyy 07:16). Wiki ambiguity unresolved
  by mods in chat — but consensus among the math-literate is per-trade.
- Penalty formula taken at face value: `((920 − avg_b2)/(920 − bid2))^3`,
  multiplied into the (920 − bid2) profit on each gardener where
  `bid1 ≤ r < bid2` and `bid2 ≤ avg_b2`. If `bid2 > avg_b2`, factor = 1
  (uncapped boost is **not** applied — confirmed by enricoo123 12:35).
- Cannot lose money on manual; floor at 0 (vencezzz 23:42).
- Counterparty count is unknown but irrelevant to the optimal bid pair —
  PnL just scales with N (lyonchea 07:50/12:42).

## avg_b2 crowd estimates

| Source / handle | Time (04-24/25) | avg_b2 estimate |
|---|---|---|
| addyy_m13 | 04-24 13:18 | "around 860s" |
| bimbambom6100 | 04-24 14:45 | "835 optimal", "≤835 ceiling" |
| minogo | 04-24 14:45 | "867" |
| abd1718 | 04-25 03:17/11:05 | "850", later EV ≈ 838 → bid 841 |
| nath._ | 04-25 11:15 | "doesn't go past ~853" |
| .veeral | 04-25 20:17 / 21:11 | "841", "guaranteed ≤ 850" |
| perrupi | 04-25 21:11 | "855" |
| barakuda5250 | 04-25 08:08 | "not lower than 850" |
| waa1k_fps | 04-25 17:36 | "around 850" |
| oscar_250 | 04-25 17:42 | "high 840s onwards safe" |
| infra.bayes | 04-25 21:21 | "maxing 820–830" |
| _ravioliboi | 04-26 00:39 | "nobody bids <835, most >835" |
| sutu7239 | 04-25 20:20 | notes "836 = 2/3 of [670,920]" |

Crowd central tendency: **~840–855**. Skew upward driven by the cubic
penalty fear and a non-trivial fringe of `920/920` meme bidders.

## Bid strategy proposals

Single-bid Nash / textbook results stated (numbers that match math):
- **bid1 = 791** if bid1 used alone (odraode02 10:34: "794"; close).
- **bid1 = 751, bid2 = 836** = the no-penalty two-bid optimum on uniform
  reserves (matches my recompute below; bimbambom6100 12:03 "835 optimal").
- abd1718 17:17 / 13:54: "Optimal bid2 determines bid1" — correct.

Concrete pairs people stated they were submitting:
- hlucas: 920/920 (deterministic 0 PnL; troll/safe)
- 670/920, 670/671, 920/920: meme/joke pairs
- m4tti4_ 04-24: "distance 670→b1 should equal b1→b2" (heuristic)
- mr.man0909 / .anand__: 750/815 ish
- promethazinepipedup 23:09: "b1 ~790, b2 ~820"
- kaptainkool2627 04-25 22:56: **790 / 865**
- lethal6 23:07: **760 / 847**
- vikku0060 14:35: 765 / 920 ("baseline guarantee")
- armor.clad.venus.liberates 22:55: **730 / 840**
- infra.bayes (multi-msg): safe-low-PnL pair **675 / 920** = ~24.5k
  "deterministic"
- abd1718 11:05: **bid2 = 841** (EV under his beta-mix prior)

## Math / formulas / code shared (verbatim)

- meet001 15:25 (no-penalty derivative):
  `derivate N × (b2-b1)/250 × (920-b2)`
- ax2k 11:34 wave-up: penalty `((920-avg_b2)/(920-b2))^3` multiplied
  into per-trade pnl (920-b2).
- dk1189 12:25: alt-reading `(920-avg_b2)^3 / (920-b2)^2` if "penalised
  by" is a discount. **Likely wrong** — chat consensus (and brief.md
  literal reading) is the multiplicative form.
- higgsino55 08:57: explained the bid1=792.5 single-bid optimum and why
  the two-bid optimum lowers b1.
- vedik_77348 23:01: "nash eq normal pop = 836; nash among prosperity
  participants = 920". Hyperbolic but captures the over-bidding pressure.

## Edge cases & loopholes

- Strict `>` means **bid one above your target reserve**: bidding 700
  does NOT trade with reserve=700 (asdfg1234098, jacek3834). So
  "751" is preferred over "750" if you want to clear the 750 reserve.
- Reserve at exactly 920 is in the distribution — no bid can clear it
  (`bid > 920` not allowed and would be 0 profit anyway).
- 670 reserve also unclearable except by bidding 671+ (no wins from 670
  since 920-670 max = 250 profit, but only if bid=671: profit=249).
- Non-multiples-of-5 bids appear allowed (chat consensus, never
  contradicted by mods). Bidding `b+1` where `b` is a reserve level is
  the cheapest way to clear that level — recommend integer bids ending
  in 1 or 6.
- Submission is re-submittable until round end; **last submission locks**
  (per brief.md).

## Open debates / unresolved

- Is penalty per-trade or applied once to total bid2 PnL? Chat consensus:
  per-trade. Mods did not confirm in scraped window.
- Whether avg_b2 is over **all** players' b2 or only b2's that "fired".
  Chat default assumption: all-players global average.
- Counterparty count: nobody has hard intel. Doesn't affect optimal pair
  (only scales PnL).

## Recompute — optimal (b1, b2) by avg_b2 (verified locally)

51 reserves uniform on {670, 675, …, 920}, one counterparty per level
(scale-invariant). Strict-greater rule. Penalty per trade.

| avg_b2 | best (b1,b2) | PnL units |
|---:|:---:|---:|
| ≤835 | (751, 836) | 4301 |
| 840 | (751, 841) | 4295 |
| 845 | (756, 846) | 4284 |
| 850 | (756, 851) | 4263 |
| 855 | (761, 856) | 4237 |
| 860 | (761, 861) | 4201 |

Sensitivity of `(756, 851)` to true avg_b2:
- avg=820–850: 4263 (no penalty zone)
- avg=855: 4048 (-5%)
- avg=860: 3814 (-11%)
- avg=865: 3616 (-15%)

`(751, 836)` is great if avg_b2 ≤ 835 but cratrers at 850+ (3699 = -14%).

## TL;DR — recommended (bid1, bid2) for OUR submission

**Submit `(756, 851)`** (or equivalently `(751, 851)`).

Rationale:
- Crowd estimate of avg_b2 clusters **840–855**. Cubic penalty makes
  under-shooting brutal; over-shooting only costs flat margin.
- `(756, 851)` is exactly optimal at avg_b2 = 845–850 and penalty-free
  for any avg ≤ 851. Captures **~99%** of the no-penalty optimum
  (4263/4301).
- If you want one notch more safety (in case avg drifts to 855 from
  meme-920s), use **`(761, 856)`**. Sacrifices ~30 PnL but is
  penalty-free up to 856.
- Avoid the textbook no-penalty answer (751, 836): one-shot regret
  if avg_b2 ≥ 850 (very plausible from chat).
- Ignore 920/920 trolls — non-trivial fraction but they will not move
  avg_b2 above ~860 absent mass coordination (not visible in chat).

Bids are integers ending in 1 or 6 to exploit the strict-greater rule
on multiples-of-5 reserves.

## Sources methodology

- Parsed `IMC Prosperity - Text channels - manual-trading [...].json`
  with `venv/bin/python`. Filtered messages timestamp ≥ 2026-04-24
  containing any of `{bio-pod, gardener, reserve, 670, 920, bid1/bid2,
  manual, penalty, optimal, b1/b2, mean, ranges 750-880}`.
- 400 candidate messages reviewed in chronological order; quotes above
  cite handle + HH:MM.
- Optimal bid table recomputed independently from brief.md mechanics —
  not taken from any chat claim.
- No private user info beyond Discord handles (already public in the
  channel).
