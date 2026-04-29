# v7 Brainstorm — Robust Enhancements to Passive MM Core

> Basis: v6 passive MM on 46 products + PEBBLES basket-tilt.
> Hard constraints: no directional bets, no bot-fill quirks, no ML,
> position limit = 10. All enhancements must be live-adaptive with
> bounded failure modes.

---

## Idea 1 — PEBBLES Outlier-State Quote Suppression

**Hypothesis**: The PEBBLES 5-sum tri-modal distribution (normal ±1.5,
outlier +14–16.5 or −17–18.5, hard gap in between) indicates the NPC
occasionally injects a simultaneous multi-product repricing event. During
these ~2.8% of ticks the spread widens anomalously and adverse selection
spikes. Suppressing new quotes during outlier states avoids picking up bad
inventory during mechanically-driven repricing.

**Mechanism**:
1. Each tick, compute `basket_dev = sum(five_pebble_mids) - 50000`.
2. If `|basket_dev| > 8` (deep inside the gap: gap starts at 14, threshold
   at 8 gives buffer), skip all new PEBBLES orders that tick.
3. Existing position is held; stop-loss still fires if triggered.
4. Resume normal quoting once `|basket_dev| ≤ 8` for two consecutive ticks.

**Why robust OOS**: The tri-modal structure and the hard gap are observed
across all 3 days with consistent magnitude (±14–18 band, zero values in
gap). This is a mechanical property of the NPC generator, not a
learned capsule pattern. The threshold at 8 is well inside the gap — if
the gap closes on day 5, the worst case is we quote normally again (no
loss from the threshold itself).

**Failure mode**: Gap exists but is narrower on day 5 → false suppression
reduces fill opportunities. Bounded: worst case = fewer fills, not adverse
fills. No inventory accumulation risk.

**Complexity**: Low. One extra `sum()` per tick in `PebblesCoordinator.act()`.
**Robustness**: High.

---

## Idea 2 — SNACKPACK 2+2+1 Intra-Group Inventory Balancing

**Hypothesis**: SNACKPACK has two completely decoupled subsystems: Group A
(CHOC↔VAN, corr=−0.916) and Group B (STRAW↔RASP anti-corr=−0.924,
PIST↔STRAW co-move=+0.913). Since Group A and B share zero cross-group
correlation (|corr| ≤ 0.04), a position in CHOC provides no hedge for a
position in STRAW. Today's v6 treats all five as independent PassiveMM
instances, which means the bot can simultaneously be long CHOC (+10) and
long STRAW (+10) — positions in the same direction within a group are fine
but positions pointing the same direction on both sides of an anti-corr
pair waste inventory.

The structural insight: within each anti-corr pair, if you are long A you
should also be short B (they move opposite). If you are long both A and B
simultaneously, one will lose on adverse moves while the other wins — but
at position limit = 10 both legs are already capped so you cannot
rebalance. The fix: use within-group inventory imbalance to apply a
counter-skew that keeps net group inventory near zero.

**Mechanism**:
1. Each tick, compute `group_a_net = pos(CHOC) + pos(VAN)`.
2. `extra_skew_choc = 0.3 * group_a_net / 2` (split equally across both).
   Apply this as `extra_skew` to both CHOC and VAN PassiveMM.
3. Same for Group B: `group_b_net = pos(STRAW) + pos(RASP)`.
   `extra_skew_straw = extra_skew_rasp = 0.3 * group_b_net / 2`.
4. PISTACHIO is treated independently (co-moves with STRAW so gets its
   own skew; no cross-pairing needed since PIST↔RASP anti-corr already
   captured by the group-B skew).

**Why robust OOS**: The anti-correlation structure is confirmed stable
across all 3 days (per-day corr ±0.01). Group independence is exhaustively
verified (CC1). The skew factor 0.3 is a soft tilt, not a gate — if
anti-corr weakens, the group skew does less but causes no harm.

**Failure mode**: SNACKPACK's pair-sum drifts across days, so there is no
mean FV anchor. The group skew ONLY manages inventory, not price
prediction. Failure mode: if correlations flip sign on day 5 (no evidence
for this), the group inventory skew pushes quotes in the wrong direction.
Bounded: skew magnitude = 0.3 × max 20 / 2 = 3 ticks, which shifts quotes
3 ticks inside a spread of ≥6. Cannot push quotes to inversion.

**Complexity**: Low. Two new counters per tick, plugged into existing
`extra_skew` argument.
**Robustness**: High.

---

## Idea 3 — Step-Product Quote Widening After a Step Event

**Hypothesis**: ROBOT_IRONING and OXYGEN_SHAKE_EVENING_BREATH have ±10
discrete steps with 40% zero-return ticks. After a ±10 step occurs, the
reversal rate is ~55% (not 100%), meaning 45% of the time the price keeps
moving. v6 quotes at `best_bid+1 / best_ask-1` uniformly, which means
immediately after a step the bot may quote at a price that is 1-tick inside
a new, shifted spread. The adverse selection on the post-step tick is
higher than baseline because the NPC is more likely to trade through the
new level if price is moving directionally.

Widening the quote spread for 2–3 ticks after a step event absorbs the
elevated post-step adverse selection without stopping participation.

**Mechanism**:
1. Per-tick, detect a step: `|mid_t - mid_{t-1}| >= 8` (threshold below 10
   to catch half-integer transitions too).
2. Set `post_step_cooldown = 3` when detected.
3. While `post_step_cooldown > 0`: apply `extra_skew += 4` to widen quotes
   by ~4 ticks on both sides (effectively post bid at `best_bid` rather
   than `best_bid+1`, ask at `best_ask` rather than `best_ask-1`). Decrement
   each tick.
4. After cooldown = 0, resume penny-inside quoting.

**Why robust OOS**: The ±10 discrete step generator is confirmed on all 3
days. The reversal fraction of 55% is per-day stable. Widening quotes for
3 ticks after a step is a structural response to a confirmed mechanical
property. If the step structure disappears on day 5, `post_step_cooldown`
simply never triggers and behavior reverts to v6 baseline.

**Failure mode**: Step events are rare (60% of ticks are zero-return; steps
= ~40% of the non-zero ticks). Missed fills during the 3-tick cooldown are
a small opportunity cost. The downside is bounded by the 3-tick window.

**Complexity**: Low. One extra `deque(maxlen=2)` per step-product to track
the last mid, plus a cooldown counter per product.
**Robustness**: High.

---

## Idea 4 — OXYGEN_SHAKE_CHOCOLATE Jump-Vol Spread Scaling

**Hypothesis**: OXYGEN_SHAKE_CHOCOLATE has confirmed jump-diffusion behavior
(kurtosis=10.77, sq_acf_lag1=0.239, 38–44% zero-return ticks, AR(1)=−0.076).
v6 already assigns a wide stop_loss_ticks=100 and soft_cap=5, but quotes
the same penny-inside spread as other products. During high-volatility
regimes (post-jump vol clustering), the passive MM's capture-per-fill is
unchanged while adverse selection increases. Scaling the quote spread up
when realized vol is elevated captures more per-fill and reduces adverse
selection simultaneously.

**Mechanism**:
1. Maintain a rolling window of `|return|` for the last 50 ticks
   (stored in traderData via existing `mids` deque).
2. Compute `sigma = std(|returns|)` over the window (use sample std of
   deltas from `self.mids`).
3. Compute a spread multiplier: `mult = max(1.0, min(2.5, sigma / base_sigma))`
   where `base_sigma` is the long-run median (learned live as
   `percentile_50 of recent 500-tick sigma estimates`).
4. Modify quote positions: instead of `bid = best_bid + 1`,
   use `bid = best_bid + 1 - int(mult - 1)` (i.e., pull bid back by
   `(mult-1)` ticks when vol is elevated). Same for ask.
5. The soft_cap=5 and stop_loss=100 are unchanged.

**Why robust OOS**: Jump-diffusion products have higher adverse selection
during vol clusters by construction — this is a structural property, not a
capsule artifact. The multiplier is computed entirely from live data in the
current session. The `base_sigma` anchor is the running median of realized
vol, so it adapts if the distribution shifts on day 5.

**Failure mode**: If vol collapses and `sigma < base_sigma` consistently,
`mult = 1.0` and behavior is pure v6 baseline. Maximum widening is capped
at `mult = 2.5` (prevents quotes from being pulled so far they never fill).

**Complexity**: Medium. Requires tracking `|return|` over a 50-tick window
and a running median of sigma estimates (approximated cheaply with a sorted
deque or EMA).
**Robustness**: Medium-high.

---

## Idea 5 — PEBBLES Size-Rank Skew Asymmetry

**Hypothesis**: The PEBBLES size rank is perfectly stable: XS < S < M < L < XL
(Spearman = 1.0 on days 2/3, confirmed in NB07). XL has the highest price
and the dominant PC1 loading (+0.784). Since XL moves most (widest range:
9188–17240) and all other products must partially offset XL, inventory
risk in XL is mechanically amplified — when XL goes to an extreme, some
OTHER product is at the opposite extreme.

v6 applies the same `skew=0.4` to all five PEBBLES. XL warrants a higher
skew (faster inventory unwind) because a large XL position means the
basket constraint forces other products toward extremes, increasing
cross-product adverse selection.

**Mechanism**:
1. In `PebblesCoordinator`, set XL skew = 0.6 (vs 0.4 for XS-L).
2. Compute `xl_pos = state.position.get("PEBBLES_XL", 0)`.
3. Apply extra_skew += `0.2 * xl_pos` specifically to PEBBLES_XS through
   PEBBLES_L (not XL itself). This tilts the other four away from building
   inventory in the same direction as XL, since the sum constraint means
   they must absorb an offsetting move.
4. XL gets its own higher skew; the residual correction is applied to the
   others.

**Why robust OOS**: XL's dominant PC1 loading and widest range are
confirmed across all 3 days. The sum constraint means XL position imbalance
mechanically propagates to the others — the skew asymmetry is a response to
a day-stable structural fact, not a drift pattern.

**Failure mode**: If XL's variance contracts on day 5 (e.g., prices
converge), the extra_skew on the siblings is triggered less often.
Bounded: `0.2 * 10 = 2` ticks of extra sibling skew at maximum XL position,
within the existing quote-inversion guard.

**Complexity**: Low. Change three parameter values and add one cross-product
skew line in `PebblesCoordinator.act()`.
**Robustness**: High.

---

## Idea 6 — Live Spread Percentile Gating (Anti-Taker Filter)

**Hypothesis**: v6 always quotes penny-inside the current touch. When the
NPC temporarily widens the spread abnormally (e.g., 3× the normal spread),
posting penny-inside still captures the full extra spread — but it also
signals that the NPC is repricing, increasing adverse selection. When the
spread is TIGHTER than normal (e.g., tick spread = 2 vs typical 6–10), the
per-fill PnL is too low to cover the position-accumulation risk.

A live spread percentile filter skips quoting when the current spread is
in the bottom 20% of the rolling spread distribution (too thin to be
worth the inventory risk).

**Mechanism**:
1. Per product, maintain a rolling 200-tick deque of `spread = ask - bid`.
2. Compute `spread_p20 = sorted(deque)[len//5]` (or approximate with an
   EMA low-pass).
3. If `current_spread <= spread_p20`, skip this product's orders that tick
   (returns empty list, same as soft_cap gate).
4. Resume quoting once spread rises above `spread_p20`.

**Why robust OOS**: The relationship between spread width and per-fill
capture is structural (wider spread = more captured per fill). This is not
a capsule-specific signal; it's a microstructure identity. The p20 threshold
is computed from live data in the same session, adapting to whatever spread
distribution day 5 shows.

**Failure mode**: If spreads systematically compress on day 5, the filter
suppresses quoting too aggressively. Bounded: worst case is fewer fills
and lower PnL, but not adverse inventory. Can tune to p10 if too aggressive.

**Complexity**: Low. One extra deque per product, one percentile lookup.
**Robustness**: Medium-high.

---

## Idea 7 — Soft Cap Tightening for Consistent Bleeders Under Adverse Conditions

**Hypothesis**: Four products were dropped from v6 for bleeding in both BT
and live. The remaining 46 products include some that bled in BT but
survived in live (or vice versa), which were kept as a judgment call. A
live-adaptive soft cap that reduces exposure after observing adverse
position outcomes (mark-to-market loss beyond a small threshold) applies
a corrective taper in-session rather than relying on the static BT triage.

**Mechanism**:
1. Per product, track `session_pnl_proxy = sum(mid_change * position)` via
   the rolling mids and position log (already available in `PassiveMM.mids`
   and `state.position`).
2. Estimate tick-by-tick mark-to-market: `delta_pnl = pos * (mid_t - mid_{t-1})`.
3. Accumulate over last 500 ticks into `rolling_pnl_500`.
4. If `rolling_pnl_500 < -threshold` (set threshold = 15 ticks × POSITION_LIMIT
   = 150 for default products), reduce soft_cap by 2 (floor = 3).
5. If `rolling_pnl_500 > +threshold / 2` for 200+ ticks, restore soft_cap += 1
   (ceiling = default soft_cap).

**Why robust OOS**: This does not predict future price direction. It
observes that we are currently losing money with inventory and reduces
exposure. The recovery condition is conservative (needs sustained profitability
over 200 ticks before restoring). It adapts to whatever regime day 5 presents.

**Failure mode**: A temporary adverse move could reduce soft_cap before the
stop-loss fires, missing a mean-reversion bounce. Bounded: soft_cap floor = 3
means we still quote (just smaller), and the stop-loss still protects against
large adverse moves. The two mechanisms are complementary.

**Complexity**: Medium. Requires cumulative pnl tracking per product.
**Robustness**: Medium.

---

## Ranking Summary

| Idea | Robustness | Complexity | Priority |
|------|-----------|------------|----------|
| 1 — PEBBLES outlier-state suppression | High | Low | **Ship** |
| 2 — SNACKPACK 2+2+1 group inventory skew | High | Low | **Ship** |
| 3 — Step-product post-step cooldown | High | Low | **Ship** |
| 5 — PEBBLES XL skew asymmetry | High | Low | **Ship** |
| 4 — CHOCOLATE jump-vol spread scaling | Med-High | Medium | Consider |
| 6 — Live spread percentile gating | Med-High | Low | Consider |
| 7 — Live adaptive soft_cap | Medium | Medium | Defer |

Top 3 to implement first: ideas 1, 2, 3 (all Low complexity, High robustness,
orthogonal failure modes, add to existing structures without replacing them).
