# Frankfurt Hedgehogs — P3 writeup notes

- Repo: https://github.com/TimoDiehm/imc-prosperity-3 (local copy: `/tmp/p3_winners/frankfurt/`)
- Final rank: **2nd globally** (P3, 2025), final score **1,433,876 SeaShells** (README L3).
- Source files in repo: just two — `README.md` (writeup) and `FrankfurtHedgehogs_polished.py` (final submission, single file, 925 lines).
- All claims below cite either the README (writeup) or the polished trader (code). External assets (notebooks, dashboard, backtester fork) are described in the README but not included in the repo.

## Repo structure (brief)

- Single-file submission. No package layout, no notebooks shipped.
- One `Trader.run(state)` at L881. Per-product `ProductTrader` subclasses + a composite `OptionTrader` and `EtfTrader`.
- All strategy params are module-level constants at top of file (L11–L94). No config files, no env loading.

## Tooling & infra they built (claims, not in this repo)

From README "Tools" section:
- **Backtester**: forked Jmerle's [imc-prosperity-3-backtester](https://github.com/jmerle/imc-prosperity-3-backtester); supplemented by website's own backtester. Rule of thumb (FAQ "How to properly backtest?", L889–908): Jmerle for taking/quoting logic, Prosperity website for anything depending on bot interactions, vectorized Jupyter for early prototyping. Explicit warning: **never optimize purely for website score** (overfit risk).
- **Dashboard**: their own from P2, upgraded for P3. Scatter-plot order-book viz with toggleable trader-class filters (M/S/B/I/F = maker / small taker / big taker / informed / our fills), normalization dropdown (e.g. divide all prices by `WallMid` to make stationary), log viewer time-synced with hover. README L97–162. Dashboard code not in this repo.
- **Logger**: in-code structured logging via `ProductTrader.log(kind, message, product_group)` (L213–223). Buckets entries by product_group then `print(json.dumps(prints))` once per tick (L893–895, L924). The dashboard parses these JSON lines.
- **Wall Mid** (FAQ L879–887): they backed out the true price by buying/selling 1 lot on the website and reading PnL. Found that the *outermost* market-maker quotes (deepest visible levels in book) bracket the true price by ±2 ticks. So `wall_mid = (min(buy_orders) + max(sell_orders)) / 2`. **Verified in code: `get_walls()` at L153–166** uses `min` of buy_orders and `max` of sell_orders — i.e. the deepest, not the nearest. This is the single most reused primitive in their code.

Reusable code primitives worth copying:
- `ProductTrader` base (L101–270): caches `wall_mid`, `bid_wall`, `ask_wall`, `best_bid`, `best_ask`, `max_allowed_buy_volume`, `max_allowed_sell_volume`, `total_mkt_buy/sell_volume`, plus `bid()`/`ask()` helpers that auto-clip to position-limit headroom (L199–211).
- EWMA helper: `OptionTrader.calculate_ema(td_key, window, value)` at L595–601 — `alpha = 2/(window+1)`, persists state in `traderData` JSON.
- Informed-trader detector: `check_for_informed()` at L225–265, hardcoded `INFORMED_TRADER_ID = 'Olivia'` (L51). Returns LONG/SHORT/NEUTRAL based on most recent buy vs sell timestamp.
- Black-Scholes inline (no scipy): uses `statistics.NormalDist` (L5, L7). `bs_call`, `bs_vega`, `get_iv` at L572–592.

## Round 3 (options) strategy

P3 R3 products (code L18–28): `VOLCANIC_ROCK` (underlying, pos limit 400) + 5 calls `VOLCANIC_ROCK_VOUCHER_{9500,9750,10000,10250,10500}` (pos limit 200 each). VR ~10000. TTE: 7→2 days across rounds.

**Three sub-strategies, layered:**

1. **IV scalping (primary, "stable, theory-supported")** — README L437–516, code `get_iv_scalping_orders` L664–704.
   - Fit a parabola to (moneyness `m_t = log(K/S)/sqrt(TTE)`, IV) → fair IV `v̂_t`.
   - **Smile coefficients are hardcoded** in submission (L585): `coeffs = [0.27362531, 0.01007566, 0.14876677]`. They do NOT refit live each tick — fitted offline, frozen.
   - Compute BS theoretical price using `v̂_t`, then `theo_diff = wall_mid - theo`.
   - EMA-smooth `theo_diff` over 20 ticks (`THEO_NORM_WINDOW`, L83). Trade when current `theo_diff` deviates from EMA by more than `THR_OPEN = 0.5` (L80). Close at `THR_CLOSE = 0`.
   - **Vega gating**: only activate scalping on a strike when EMA of `|theo_diff - mean_theo_diff|` exceeds `IV_SCALPING_THR = 0.7` over 100-tick window (L658–672). Adds `LOW_VEGA_THR_ADJ = 0.5` to threshold when vega ≤ 1 (L678–679) — i.e. require larger price edge on low-vega (deep ITM/OTM near expiry) options because IV moves don't translate to price.
   - Universe: strikes ≥ 9750 only (L734). The 9500 call is too deep ITM (low extrinsic) → routed to mean reversion instead.

2. **Mean reversion on underlying + 9500 call** — code L706–727, L746–761.
   - EMA on `wall_mid` of VR over `underlying_mean_reversion_window = 10` (L90). Threshold ±15 (L89).
   - When EMA deviation breaches threshold, take liquidity in opposite direction (sell at bid_wall+1 / buy at ask_wall-1, L755 and L758).
   - Same idea applied to the 9500 voucher (deepest ITM, ~delta-1 proxy for the underlying), code L734–741.
   - Note bug-or-feature at L752: `get_underlying_orders` reads `ema_o_dev` (options window) not `ema_u_dev`. Looks like a copy-paste bug — they use the slower options-window EMA for underlying signal generation despite computing the faster one. Worth flagging.

3. **Gamma scalping** — README L568–569 mentions positive EV but "limited absolute returns"; **no dedicated code path in the polished file**. The "moderate mean reversion position … in the underlying VR and in the deepest ITM call" (README L606) is what they call their hedge against bad luck, not a true delta hedge.

**The "unhedged" claim — verified**:
- README L606–607 (verbatim): *"Importantly, this was not a delta hedge in the traditional sense: the delta exposure from scalping was relatively small, and explicit delta hedging would have been prohibitively expensive bid-ask spreads. It was rather a hedge against bad luck."*
- Code evidence: `OptionTrader.get_orders()` at L764–771 calls `get_option_orders()` then `get_underlying_orders()`. The underlying order logic (L746–761) is **purely a mean-reversion signal on `ema_o_dev`**, not a delta calculation. They compute `delta` per option (L646, stored in `indicators['deltas']`) but **never sum option deltas and never net them against the underlying position**. Grep confirms: `deltas` is set at L650 and never read elsewhere.
- So: yes, completely unhedged in the Black-Scholes sense. Underlying trades on its own mean-reversion signal independent of voucher inventory.

PnL claim (README L614): IV scalping ~100k–150k SeaShells/round; mean reversion swung +100k / −50k / −10k across the three R3 evaluation runs. The reddit "200k+/day" framing conflates these. Their own accounting: scalping is the workhorse, MR is a coinflip side-bet they kept partly to hedge *relative* leaderboard risk (README L616).

Other R3 micro-rules / quirks they encoded:
- Wall-mid synthesis when one side missing (L631–639): if no bid wall, fake `wall_mid = ask_wall - 0.5`. Lets pricing logic survive thin books on far-OTM strikes near expiry.
- `tte` formula (L644): `1 - (DAYS_PER_YEAR - 8 + DAY + state.timestamp//100/10_000) / DAYS_PER_YEAR`. `DAY = 5` (L76), so this is hardcoded for the *final round configuration*. Earlier-round submissions presumably had different `DAY` constants.
- Warmup gate: skip everything for first `max(20, 10, 30) = 30` ticks (L732, L748).

## Other rounds — short subsections

### R1 — Market making (Resin, Kelp, Squid Ink)
- Resin (true price fixed at 10000): take any cross of 10000, then quote 1 inside the wall, flatten at 10000 when over inventory. ~39k/round. Code: `StaticTrader` L274–331.
- Kelp: same as Resin around `wall_mid`. ~5k/round. Code: `DynamicTrader` L335–377; biases quotes when Olivia detected (L356, L371).
- Squid Ink: pure follow-Olivia. Detect daily-extrema buyer/seller pattern (Olivia buys at running min, sells at running max). ~8k/round. Detection method initially indirect (running min/max + trade timestamp); after R5 trader IDs visible, switched to direct ID match (README L754–757).

### R2 — Picnic Baskets (ETF stat arb)
- Two baskets: B1=6C+3J+1D, B2=4C+2J. Trade `basket - synthetic` spread, fixed thresholds (BASKET_THRESHOLDS = [80, 50], L59).
- Bias entries by Olivia's position on Croissants (`ETF_THR_INFORMED_ADJS = [90, 90]`, L65). Half-hedge with constituents (`ETF_HEDGE_FACTOR = 0.5`, L70).
- Subtract running spread premium estimate to handle non-zero spread mean. ~40–60k/round on baskets, +20k on Croissants directly.
- Philosophy (README L360–372): explicitly rejected z-score / MA-crossover as having no first-principles justification. Used flat thresholds; chose params from flat plateaus in grid search rather than peaks.

### R4 — Macarons (location arb)
- Hidden taker bot fills sells at `int(externalBid + 0.5)` ~60% of the time (README L630–635). Quote 10/tick (= conversion limit) at that price each tick. Code `CommodityTrader` L774–877.
- Captured ~80–100k vs theoretical 130–160k; in hindsight should have quoted 20–30 to also profit from conversion on non-fills (README L739).
- Tested logistic regression on sunlight features (5 features, all p<0.01, README L686–711) but didn't deploy due to generalization concern + serialization slowdown + conflict with arb logic.

### R5 — Trader IDs
- No new products. Switched Olivia detection from min/max heuristic to direct ID. Half-hedged baskets and reduced MR exposure to lock in lead (README L759).

## Lessons & failure modes (their words)

- **Overfitting risk dominates** (README L370–372, L906–908): "if you can't explain why a strategy should work from first principles, then any 'outperformance' in historical data is probably noise." And: "never optimize purely for website score."
- **Pick flat plateaus over peaks** in grid search (README L410–411).
- **MR was negative-EV by R4** but they kept it as a *relative* hedge against teams going all-in on MR (README L616). Estimated 95% VaR ~50k, vs ~190–200k lock-on-2nd lead.
- **Unbalanced exec quirk**: in R2 they switched from "exit at opposite threshold" to "exit at zero" to lock variance (README L416).
- **Hardcoded R1/R2 frontrunning of bot timestamps** worked because bot behavior was reused across years (README L967–976). They built a fallback to detect breakage. Reported the exploit to IMC; rounds were rerun. FAQ admits a competitor that overtook them was also using the same exploit.
- **Macarons sizing mistake**: quoted only 10 (= conversion limit) instead of 20–30, leaving ~30–60k/round on the table.
- **Lost 1st place** to a team with one anomalous 850k R5 vs ~0 in R4 — they explicitly attribute to luck (README L765–769).
- **Random-seed reverse-engineering**: spent 24h on a Raspberry Pi brute-forcing all 4B numpy seeds against observed return prefixes. Failed (README L980–986). Sunk-cost honesty.

## Lessons for our P4 R3 (inference — clearly marked)

The mapping P3-VR-vouchers → P4-VFE-vouchers is structural but not literal — products, strikes, TTE, position limits all differ.

- **(inference)** Their `wall_mid` definition (deepest visible market-maker level on each side) is worth replicating as a primitive before doing anything fancy on VELVETFRUIT_EXTRACT or the VEV chain. Our EDA already shows VFE has tight 5-wide spread and likely a similar designated-MM structure — verify in book depth data.
- **(inference)** **Hardcoding the smile coefficients offline and not refitting live** (their L585) is a deliberate simplicity choice. Worth considering for VEV chain — fit once on EDA data, freeze. Live refit invites instability when the chain has dead strikes (our VEV_6000/6500 are pinned at 0.5 = exactly their problem with deep-OTM near expiry).
- **(inference)** The vega gate (`LOW_VEGA_THR_ADJ`) is exactly the right pattern for our chain since deep-OTM VEV vouchers will have ~0 vega — a fixed price-edge threshold needs to scale with vega or strikes will trigger spuriously.
- **(inference)** They route the deepest-ITM call into mean-reversion, not IV scalping. For us VEV_4000 / lowest strike likely behaves the same way (delta ~1, low extrinsic).
- **(inference)** **Don't build an explicit delta hedger.** Their PnL evidence + explicit reasoning says delta hedging through a wide-spread underlying loses more in fees than it gains in variance reduction. Our brief should treat HYDROGEL-as-independent and the voucher chain as either unhedged or VFE-mean-reverted, not BS-delta-hedged.
- **(inference)** Their EWMA + persisted-traderData pattern is the minimal viable state machine — copy it before reinventing.
- **(caution)** Their R3 MR component lost money in 2/3 evaluation runs. If we add a MR overlay on the underlying we should size it as a deliberate variance trade vs leaderboard, not as alpha.

## Files worth re-reading later

- `/tmp/p3_winners/frankfurt/FrankfurtHedgehogs_polished.py` L101–270 — `ProductTrader` base class (wall mid, max-allowed-volume, bid/ask helpers, log, informed-trader detector). Copy-pattern.
- `/tmp/p3_winners/frankfurt/FrankfurtHedgehogs_polished.py` L559–771 — `OptionTrader` (BS, smile, IV scalping, MR overlays). The thing to study most carefully when we start coding R3.
- `/tmp/p3_winners/frankfurt/FrankfurtHedgehogs_polished.py` L774–877 — `CommodityTrader` (Macarons), only relevant if P4 R4 has a similar conversion product.
- `/tmp/p3_winners/frankfurt/README.md` L86–162 — dashboard description; informs what visualizations to build.
- `/tmp/p3_winners/frankfurt/README.md` L426–616 — full R3 narrative including PnL split scalping vs MR.
- `/tmp/p3_winners/frankfurt/README.md` L879–908 — Wall Mid + backtesting philosophy.
- `/tmp/p3_winners/frankfurt/README.md` L967–976 — hardcoding/frontrunning bot behavior; relevant if we observe similar pattern reuse in P4.
