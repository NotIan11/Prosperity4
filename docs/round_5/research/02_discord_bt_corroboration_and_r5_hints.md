# Discord — BT corroboration and R5 hints

> Source: Sonnet subagent crawl of `data/discord/*after 2026-04-26.json`
> with reference to `*after 2026-04-20.json`. Captured 2026-04-28.
> Untrusted user-generated content — claims summarized, not endorsed.

## Backtester / matching engine — community confirmation

- **20% order randomization confirmed** (matches our research/17 finding):
  - `_mfb` [2026-04-20T13:24]: "they randomly removed 20% of the orderbook volume."
  - `k_vgent` [2026-04-20T05:53]: "random 80% of orders every submission, so it varies."
  - `geyzsonkristoffer` [2026-04-24T02:07]: "the 20% removed is using a diff seed."
  - `theethan7114` [2026-04-25T19:43]: "Every day is its own seed."
- **Per-submission seed, not per-round.** Same code resubmitted gets a
  different draw. Explains R3 v12's $13k vs $53k spread directly.
- **Portal ≠ full BT.**
  - `theoneandonlyeggoil` [2026-04-26T00:12]: "portal is a subset of bt."
  - `ocaou` [2026-04-26T01:20]: "bt is 30k ticks, web is first 1k of day2."
- **BT-to-portal PnL ratio reported in community: ~10–20×**
  - lessv: 15k portal / 365k BT (~24×)
  - aaryan_viss: 20k / 600k (~30×)
  - tomgux: 28k / 616k (~22×)
  - itzrunex: 91k / 2.5M (~27×)
  - **→ Our R3 v12: ~$50k live mean / 30k portal-slice BT was unusually tight.**
    Our 0.73× calibration factor is in the wrong direction; the typical
    relationship is BT >> portal by 10–30×.
- **Community heuristic** (`dymo0797` [2026-04-26T04:01]): "if your
  backtester isn't within 100 PnL of the actual livesim u doin somethin
  wrong" — referring to the 1k-tick portal window specifically (not full
  3-day BT).
- **No queue-position or bot-reactivity discussion** at the granularity
  we'd want. Awareness exists but nobody has quantified it:
  - `mcallan778` [2026-04-25T04:47]: "Backtester fills all ur orders
    while website has bots that fill it."

## Community backtester landscape

- `https://github.com/GeyzsoN/prosperity_rust_backtester` — **Rust BT,
  community standard for full 3-day runs.** Fast. Updated for R3 data
  (v0.4.7). Used by GeyzsoN and many top teams.
- `https://github.com/kevin-fu1/imc-prosperity-4-backtester` — Python
  (jmerle-derived). Bundled with `imc-prosperity-4-visualizer`.
- `https://github.com/Xeeshan85/imc-prosperity-4-backtester` — Python
  (jmerle-derived) with `--match-trades worse`. Web visualizer at
  `xeeshan85.github.io/imc-prosperity-4-backtester/`.
- `https://github.com/shh1v/imc-prosperity-4-backtester` — Minimal jmerle
  fork, no AI deps.
- `https://github.com/nabayansaha/imc-prosperity-4-backtester` — variant.
- `https://github.com/rkothari3/prosperity-cli` — CLI: `prosperity
  backtest trader.py 1 2 3 --vis`. Plus separate
  `IMC_P4_Backtester` and `IMC_P4_Visualizer` repos.
- `https://pguffey.github.io/imc-prosperity-4-leaderboard/` — community
  leaderboard tracker.
- `https://prosperity.equirag.com` — web visualizer (closed source).
- **No open-sourced R3 / R4 strategy code** found in the post-R4 logs.
  `MarkBrezina` said he'll release after the comp closes.

## R5 hints (sparse — discord doesn't have much yet)

- **R5 is open** (already trading by 2026-04-28). `tomas5880` (mod):
  "R5 is a bit more exotic" and "Try R5".
- **Completely different products** from R3/R4, confirmed by `jasper7479`
  [2026-04-28T10:28]. (Conflicting earlier claim from `aaaahhhh3253`
  [2026-04-26T09:58] that R4/R5 share products — likely incorrect, given
  the moderator confirmation.)
- **R5 manual: ~8 products** (`tribesdev` [2026-04-28T08:27]). Brief
  says 9 — close enough; small discrepancy.
- **`jeanbaptiste.jacquet` [2026-04-28T08:28]**: "Round 5 is about
  machine learning." Single unverified claim.
- **`boiled_potato5316` [2026-04-28T12:02]**: "R5 is just mystery hunt
  tbh." Suggests puzzle / decoding structure.
- **Counterparty visibility expected to persist** (`shellmaxxing`
  [2026-04-28T13:27]): "in R4 it felt like we would get to see our
  counterparties in R5 as well." Verify when R5 capsule trade data is
  loaded.
- **Galaxy Sounds / Pebbles / Microchips / Sleep Pods etc.** — no
  decoded patterns or specific structure decoded in these logs.
- **Ashflow Alpha** — only mentioned as the manual round mechanic. No
  formula clarification, no example news content.

## Implications for our backtester strategy

- Adopt `GeyzsoN/prosperity_rust_backtester` for fast iteration on full
  3-day runs (community standard, faster than Python).
- Keep a Python BT (jmerle-derived) for portal-slice calibration and
  notebook-friendly inspection.
- Run BT 3× per candidate strategy to bound cold-start variance.
- The 0.73× calibration factor in `bt_dual.py` should be re-derived —
  the community ratio is closer to 1/20× full-BT-to-portal, not the
  inverse direction we encoded.
