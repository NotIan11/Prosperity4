# R3 — Discord #general intel

- **Channel**: IMC Prosperity / `general` (id 1476867246000177162)
- **Messages**: 6,807 (export filter: after 2026-04-20). Range 2026-04-20T00:00 → 2026-04-26T00:31 ET.
- **Source file**: `data/discord/IMC Prosperity - Text channels - general [...].json` (gitignored).
- **Trust note**: all UGC; observations cited with timestamp + handle. No prompt-injection attempts found (the two "claude doesn't work" hits were complaints, not injections).

## IMC platform quirks / pitfalls

- **Portal/website data is a SLICE, not the same distribution as the BT.** Repeatedly stated late R3 that the portal sim is roughly the first 10% of one day's data and PnL "should roughly line up with 10% of one day's BT pnl" — Ethan 2026-04-25T23:52, YoBoi 2026-04-26T00:31. **Implication: never tune to portal score; rank-order on the 3-day BT only.**
- **Lambda is stateless — class/global vars not guaranteed to persist.** Zero (admin) confirmed 2026-04-21T20:42 in reply to marvinthang: "AWS can not guarantee any class or global variables will stay in place on subsequent calls." Use `traderData` for anything that must persist.
- **`traderData` JSON parse cost dominates execution time on long rolling windows.** incognitoman 2026-04-26T00:18: "our algo is so slow as parsing the json takes all the execution time even with truncating." Watch out if our voucher modules grow rolling buffers.
- **Site outages**: portal/site reported down sporadically Apr 20, 24, 25 by multiple users (Yuejj 04-20T01:50, NH 04-24T06:11, emerso2000 04-24T09:17). No persistent outage but enough to budget submission attempts early, not at the wire.
- **`prosperity4btest` PyPi package broken / wrong package**: Ironstone 2026-04-24T16:04 — `prosperity4bt` no longer recognises `datamodel`; the working alternative cited is `https://github.com/shh1v/imc-prosperity-4-backtester` (Lazarus Mission 04-24T16:09). We're using `prosperity3bt` with patched LIMITS per `_session_state.md` — confirm ours still works.
- **Rust BT vs Python BT diverge**: npinazo04 04-24T15:26 — "i'm getting different results from the python backtester and the rust one." Don't cross-validate with the rust BT and assume agreement.
- **No regen of historical data day-to-day inside R3** (Isabelle 04-21T05:10 asked re rotating sandbox data; no admin confirmation either way — treat as open).
- **Final inventory mark unclear** — Matthew 04-22T06:16: "Does anyone know if the final inventory was mark-to-fair or mark-to-liquidation?" Brief says "auto-liquidated against a hidden fair value" — interpret as mark-to-fair, NOT cross-the-spread liquidation.

## Leaderboard / standings observations

- **R3 leaderboard reset confirmed** (~30 separate users asking 04-20). Equirag now hosts a top-100 BT view: `https://prosperity.equirag.com/?tab=leaderboard` → "round 3" → "backtest round" (Mr. Nobody 04-25T06:31).
- **R3 BT PnL distribution as of 04-25 evening (self-reports, take with skepticism):**
  - Bottom of equirag top-100: ~150k+ on 3-day BT (oscar 04-25T08:14: "10 people at 154k, none at 155").
  - Hardcoded/overfit reaches 750k–930k BT but collapses on portal (Ethan 750k BT / 25k portal; Lachy-Dauth 740k BT, "probably overfit"; sama 930k BT / 45k portal).
  - "Honest" caps cited: 30-60k portal seen as the no-overfit ceiling (Suleman 04-25T22:16, Dosa 04-25T19:18 reports 72k/108k/88k as honest).
  - Median portal ~5-15k for participants who self-reported.
- **`R` 04-25T02:38**: "It is literally not possible to get 100k on the server legit." Disputed but consistent with the portal-is-10%-of-1-day theory: 100k portal would extrapolate to ~3M on 3-day BT.
- **Tawfik 04-25T08:00**: warns that 150k BT scores are people "replaying the public 1k path" — i.e. overfitting to BT data which differs from live. Take equirag top-100 as a soft-overfit signal.
- **(inference)**: a BT north of ~200k that holds up across all three days without per-tick hardcodes is a real win. Our current `trader.py` (HG h=8 / VFE h=2 + no vouchers) likely sits in the 5-30k BT range based on EDA — middle of pack, not competitive for top-25.

## R2 lessons that carry to R3

Channel is largely **post-R2 venting** (one team made 200k+ on R2 manual alone — Dreptile 04-20T12:51, solavelle 04-22T16:49). Genuinely transferable lessons:

- **Most R2 PnL came from manual.** Reeck 04-20T09:36: "no one managed our manual in first round we have 0 in that got 139k in r2." → R3 manual (Bio-Pods, ≤920) is again likely a high-EV side-quest. The manual-trading agent has the detail.
- **Algo R2 was easily passable with a basic Claude strat** (Odraode 04-20T12:15). R3 is *significantly* harder per admin (David Smith 04-20T10:51 quoting an admin: "r3/r4/r5 are significantly harder than the first two rounds, they want the winner to be based off of phase 2"). **Don't extrapolate "easy R1/R2 → easy R3."**
- **Algo R2 winner approach unclear in general** — product strategy chatter sat in #algo-trading, not here.

## Insider bot / counterparty intel

- **Nothing concrete on R3 insider bot.** Zero named-counterparty observations in #general (consistent with our `07_bot_trades.md`: buyer/seller fields are 100% null in R3 historical tape).
- Solomon 04-20T11:39 idle question: "do we think round 5 will be insider trader problem again?" — speculative, no signal.
- **(implication)** Re-run UCSD-style per-bot edge ranking only **after R5 trade tape drops with names**. R3 has nothing to mine.

## Open debates / philosophy

- **MM vs mean reversion**: Lazarus Mission 04-25T23:38: "mean reversion is the way... MM is a dead end / not highly profitable." MantraGGR 04-25T23:39: "mm options seems like a good place atm." → Mixed; consistent with our own EDA (mild MR in HG/VFE wall_mid; MM still works because spreads are wide).
- **Smile / vol approach**: large group reports the IV smile is "a lie" (Ethan 04-25T19:25, MarkBrezina 04-25T20:42, sama 04-25T23:55, Tribes 04-25T20:42). Suggests teams who hardcoded a static smile got burned — **consistent with our `05_voucher_chain.md` finding that rolling smile beats static by 31% RMSE**. Vindicates rolling-window approach if we ship vouchers.
- **Voucher tactics chatter**: MantraGGR 04-25T23:37/45 reports a working approach: "vwap deviations (z-scores) on VEV ... ITM directional, short OTM when high IV." Crude but matches the `mid - theo` mean-reversion alpha we already validated.
- **Hedging philosophy**: MantraGGR 04-25T21:48 questions whether hedging gives less PnL. Also matches our `06_cross_product.md` recommendation to **NOT delta-hedge through VFE** (hedge cost > benefit at 1-2 tick spreads).
- **Hydrogel difficulty**: many complaining that HG drawdowns are large despite stable spread (Ribu 04-25T20:58, ShiningMonk 04-25T07:06). **(observation, contradicts our EDA)** — our EDA says HG is the "safe MM target" with low adverse selection. Either complainers are over-quoting (h<7) or our `prosperity3bt` cross-only fill model under-counts adverse fills. **Worth a sanity check** before sizing up.

## TL;DR — actionable for OUR R3 work

1. **Don't tune to the portal.** Portal ≈ first 10% of one day; tune on 3-day BT (`scripts/bt_spike.py`). Ethan/YoBoi quotes corroborate.
2. **Watch traderData parse cost.** If we add voucher rolling-window state, keep the serialised payload small or it'll wall-clock the Lambda.
3. **Smile rolling > static is the consensus pain point** for everyone. Our `05_voucher_chain.md` has the rolling implementation already analysed (RMSE +31%). **Shipping the rolling-smile mid-theo + 5300/5400 RV is differentiating.**
4. **Hydrogel drawdown chatter** contradicts our "safe MM" EDA — investigate before final upload. Consider sweeping h ∈ {7, 8, 9} in BT and picking by drawdown, not just PnL.
5. **No insider-bot signal in R3.** Forget UCSD's Olivia trick until R5 names leak. Don't waste a slot on counterparty heuristics this round.

## Sources methodology

- Parsed JSON (8 MB, 6807 msgs) with `venv/bin/python` and regex bucketing — no LLM summarisation of arbitrary content.
- Filters: keyword regex over `content`, length 20–300 chars to drop one-word noise and walls of text, then manual selection from printed buckets.
- Buckets used: platform/lambda/timeout, leaderboard/rank, R3-since-reset (ts > 04-24), vouchers/IV/smile, biopods/guild/manual, tooling/backtester, hydrogel/VFE strat, sim-vs-portal mismatch.
- Skipped: memes, "when does round start" FAQ, recruitment chatter, R2 venting without R3 carry-over.
- Two regex hits for "ignore prior instructions / claude do" were false positives (users complaining about Claude failing). No real prompt injections observed.
- All quoted handles use Discord nickname (or username if no nickname). No DMs or PII reproduced beyond public Discord handles.
