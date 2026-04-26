# 08d — Discord #open-source digest

- **Channel**: `open-source` (id 1476867549181513851)
- **Messages**: 491 total in window
- **Time range**: 2026-04-20T01:03 → 2026-04-26T00:45 ET (last msg ~3h before R3 close)
- **Source file**: `data/discord/IMC Prosperity - Text channels - open-source [...] (after 2026-04-20).json`
- **Trust**: all UGC, all repos UNVETTED — do not clone/run without explicit user approval.

## Backtester landscape — consensus is fragmented

No single fork has won. Three names recur as recommended by other users (not just the authors):

| Fork | Author handle | Recommenders observed |
|---|---|---|
| `kevin-fu1/imc-prosperity-4-backtester` | kfudaman_48582 | chirpy0 (×2, "i like…", "open source visualizer, safer"), cobor, others ("kevin's backtester") |
| `shh1v/imc-prosperity-4-backtester` | shh1v | self-pitched as "jmerle's adapted version with minimal changes… does not use AI" — readme-only diff |
| `GeyzsoN/prosperity_rust_backtester` | geyzsonkristoffer | mamke. ("rust backtester is peak"), chirpy0 ("rust backtester is actually good too"). Author claims "PnL is close to portal submission" (2026-04-24T22:53). |

Other forks mentioned in passing (lower signal): `Xeeshan85/imc-prosperity-4-backtester` (PyPI `prosperity4btx`, R3 added 2026-04-24), `nabayansaha/imc-prosperity-4-backtester` (prasadthemaverik reported "no data for round 3" 2026-04-25T08:02), `rkothari3/IMC_P4_Backtester` (PyPI `imc_p4_bt`, see rsk1201 below).

**Bug reports against specific forks**:
- `nabayansaha`: R3 data not bundled (prasadthemaverik 2026-04-25T08:02).
- `kevin-fu1`: KeyError `HYDROGEL_PACK` if user installs older PyPI build instead of pulling latest source — limits not in `data.py` (.awesomeap 2026-04-25T22:40, shh1v 2026-04-25T22:46/23:06: "you will have to change something in data.py which exists in the package… no one has updated their backtester").
- `imc_p4_bt` (rsk1201): combined-day log PnLs not cumulative without `--merge` flag (thincthru 2026-04-21T20:06, fixed 2026-04-22T01:51).

**Critical accuracy caveat (shh1v 2026-04-25T23:07)**:
> "no local backtester is accurate rn because the timesteps loop if you combine the rounds data. its not adjusted to reflect continuous data. This is relevant because most algo rely on time to expiry calculation"

This matches our own concern with VEV time-to-expiry across day boundaries.

mselarm to geyzsonkristoffer (2026-04-25T16:09): "any reason why we are getting total different PnL using your backtest on HG than using that one?" — no resolution observed.

markbrezina (2026-04-25T17:12): "If the backtester is telling you you will get 100K and you end out with -2K something in the assumptions is wrong" — generic warning, but consistent.

## jmerle status (any P4 release?)

**No P4 release from jmerle observed in this window.** Multiple users explicitly note this; stephxo___20402 (2026-04-25T21:07): "make your own clone of jaspers repo". shh1v's fork advertises itself as a minimal-diff jmerle adaptation. No announcements, no `prosperity-4-*` repo references under jmerle's handle.

## Visualizer / optimizer tools available

- `kevin-fu1/imc-prosperity-4-visualizer` — https://kevin-fu1.github.io/imc-prosperity-4-visualizer/ (chirpy0 promotes as "safer, open source").
- `rkothari3/IMC_P4_Visualizer` — https://imc-prosperity-4-visualizer.vercel.app/ (rsk1201, "inspired by jmerle's, kept updated, no data stored").
- `prosperity.equirag.com` (geyzsonkristoffer) — leaderboard + visualizer + R3 backtest leaderboard. **PRIVACY FLAG**: stores uploaded full log files (admitted 2026-04-24T13:05). chirpy0/js361 publicly warned "Equirag downloads log files, not safe… can steal alpha from the log files" (2026-04-24T12:54, 2026-04-25T09:55).
- `pguffey/imc-prosperity-4-leaderboard` — https://pguffey.github.io/imc-prosperity-4-leaderboard/ — derivative of jmerle's P3 leaderboard, no R1 data.
- robin.c. (2026-04-21T22:38): visualizer mismatch was caused by accidentally using P3 visualizer on P4 logs — confirms log format compatibility across versions if you pick the right one.
- No P4-specific optimizer / parameter sweep tool announced. No IV smile fitter shared.

## Useful code snippets (verbatim, untrusted)

No substantive code blocks (Black-Scholes, smile fitters, position trackers, log-trimmers) were posted in this channel during the window. The only fenced-code messages are install commands and import-error pastes.

infra.bayes (2026-04-26T00:30, ~3h before deadline) is hitting the classic `from datamodel import …` failure when running the IMC-style trader file outside the platform — implies many late entrants don't realise that backtesters bundle their own `datamodel.py`. Boilerplate observation only, no fix posted.

## Submission gotchas / tips

- IMC log uploads to equirag rejected with "did not pass IMC submission legitimacy checks" / "row-by-row PnL consistency checks" if user uploads anything other than the raw `.log` extracted from the zip (matt_22740 / opainhammer 2026-04-24T09:01–09:02; geyzsonkristoffer reply: extract `.log` from zip first).
- equirag leaderboard rejects backtests >1k ticks / 100k timestamps (geyzsonkristoffer 2026-04-24T14:30) — full 3-day backtests won't appear there.
- matt_22740 (2026-04-25T21:10) summary of simulator quirks (no source, just claims):
  - Can't exercise options
  - Vol smile changes between historical CSVs and live simulator
  - Options market behaves independently of underlying in sim
- No mention of CMU-style 100MB Lambda log truncation problem in this window.
- No bundling/single-file submission tips shared.

## Repo links to investigate (UNTRUSTED — require user approval before clone/run)

- https://github.com/kevin-fu1/imc-prosperity-4-backtester
- https://github.com/kevin-fu1/imc-prosperity-4-visualizer
- https://github.com/shh1v/imc-prosperity-4-backtester
- https://github.com/Xeeshan85/imc-prosperity-4-backtester (PyPI `prosperity4btx`)
- https://github.com/GeyzsoN/prosperity_rust_backtester (crates.io `rust_backtester`)
- https://github.com/rkothari3/IMC_P4_Backtester (PyPI `imc_p4_bt`)
- https://github.com/rkothari3/IMC_P4_Visualizer
- https://github.com/rkothari3/prosperity-cli (PyPI `prosperity-cli`)
- https://github.com/PGuffey/imc-prosperity-4-leaderboard
- https://github.com/nabayansaha/imc-prosperity-4-backtester (R3 broken per user report)
- https://prosperity.equirag.com/ (PRIVACY FLAG — stores uploaded logs)
- https://github.com/DataAthleteChamp/IMC_Prosperity_discord_scraper (off-topic, scraper)

## TL;DR — should we switch backtesters?

**Stay on `prosperity3bt` + monkey-patched `LIMITS`.** Reasons:

1. The community forks are mostly thin re-skins of jmerle's P3 codebase — same approach we already took. We get nothing new by switching.
2. Active bug reports against `kevin-fu1` (HYDROGEL_PACK KeyError on PyPI install) and `nabayansaha` (R3 data missing) confirm forks are being patched live and not all paths work end-to-end.
3. shh1v's repo description is the closest to ours: "jmerle's adapted version with minimal changes". We are already there.
4. **Universal accuracy caveat applies regardless of fork**: shh1v warns no fork handles cross-day time-to-expiry continuity correctly; matt_22740 warns the simulator's vol smile differs from historical CSVs. Switching forks doesn't fix this.

**Optional adoptions before round ends** (low risk):
- The `kevin-fu1` visualizer (https://kevin-fu1.github.io/imc-prosperity-4-visualizer/) for plotting our log output if our P3 visualizer choice doesn't render P4 correctly. Static HTML, no upload.
- Avoid equirag for both backtest leaderboard AND visualizer — confirmed-by-author log retention, multiple credible warnings about alpha leakage.

**Do NOT** spend remaining R3 time wiring up a new backtester or rust toolchain.

## Sources methodology

- Parsed all 491 messages with `venv/bin/python` from the JSON export.
- Keyword filter: `jmerle|backtest|prosperity[34]bt|fork|visuali[sz]er|optimi[sz]er|github|repo|smile|black.?scholes|IV|implied|truncat|submit|bundle|file size|lambda|monkey.?patch|LIMITS|leaderboard|prosperity-?[34]` → 118 hits.
- Secondary filter on `pnl|portal|accurate|smile|log|truncat|mismatch|exercise|expir` for accuracy/submission claims.
- All cited handles + ISO timestamps preserved from DCE export.
- Distinguished observation (quoted message) from inference (my synthesis) inline.
