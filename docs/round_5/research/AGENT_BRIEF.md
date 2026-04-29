# R5 Agent Brief — Shared Charter

> Read this entire doc before doing anything. This is the contract every
> agent (explorer, critic, synthesizer) must obey. Treat it as authoritative.

## Mission

Find every exploitable inefficiency in Round 5's 50 products by running
a battery of 50+ analytical lenses across 10 explorer notebooks, then
adversarially auditing the findings. Output: a final triage table for
the 50 products and a list of unresolved disagreements.

You are NOT writing strategy. You are mining data for signal.

## R5 facts (verified, do not re-derive)

- **50 products in 10 categories of 5.** Position limit = **10 per
  product** (down from 200/300 in R3/R4). Edge has to come from picking
  winners, not sizing.
- **Brief says: "some groups offer more market inefficiencies than
  others. In certain groups, strong patterns are embedded in the price
  movements, waiting to be discovered by you."** This is the explicit
  hint to find. Treat it as a stated fact.
- **Counterparty IDs are blank in R5 historical data.** All `buyer` and
  `seller` columns in `data/round_5/prices/trades_round_5_day_*.csv` are
  empty. **Do not waste cycles looking for counterparty patterns in the
  capsule data.** May appear in live `state.market_trades` but we won't
  know until submission.
- **Trade-count signatures already imply category structure:**
  - 8 categories: 733 trades / 1,805 volume per product (uniform)
  - Pebbles: 644 trades / 2,283 volume per product
  - Microchips: 569 trades / 1,119 volume per product
  → Pebbles and Microchips are generated differently. Highest-priority
    candidates for embedded patterns.
- **Algo currency = XIRECS. Manual currency = Zyrex.** Don't conflate.
- **Architecture (from `docs/competition.md`):** every team trades
  independently against IMC's NPC bots. No team-vs-team interaction.
  The 20% per-submission NPC-order randomization is the main BT/live
  divergence source. Same code re-submitted gives 4×+ PnL spread.
- **Calibration anchor**: BT $210,908 vs live $77,539 on R3 day 3 (same
  data) = 2.72× over-prediction for v12-class strategies. Use as sanity
  floor: live ≈ BT × 0.37. **DO NOT predict PnL in your output anyway.**

## Triage rubric (operational definitions)

For each of 50 products, every notebook contributes evidence toward one
of these calls. Final synthesis assigns ONE call per product:

- **likely exploitable**: at least one of: hardcoded FV (mid pinned ≥90%
  of ticks), strong AR(1) on returns (|ρ| > 0.3), within-category corr
  > 0.95 forming a basket, or detectable periodicity (FFT peak >>
  baseline). Plus replicable across all 3 days.
- **probably tradable**: clear MR or trend (AR(1) ρ between -0.3 and
  -0.1, or trend R² > 0.3), or category basket with corr 0.7–0.95. May
  yield small edge with naive MM/MR.
- **probably noise**: AR(1) |ρ| < 0.1, no clear trend, no within-category
  cointegration, no detectable structure. Don't trade.

## Hard constraints

- **Read-only on `data/`.** Never modify or delete capsule files.
- **Write only the file you were assigned.** Each agent has a specific
  notebook + findings doc. Do not write strategy code, do not modify
  CLAUDE.md, do not commit.
- **Use `venv/bin/python3`** (pandas, numpy, scipy, matplotlib all
  installed). Read CSVs with `pd.read_csv(path, sep=';')`.
- **No PnL predictions.** No "this would make $X." Triage call only.
- **No strategy proposals.** No cap sizes, thresholds, or trading rules.
  Synthesis can identify *what to look at* but never *what to do*.
- **No reconstruction from training memory.** If you don't know an IMC
  mechanic, say so. Don't fill in.
- **Cite numerical evidence for every claim.** "MICROCHIP_OVAL has a
  hardcoded FV at 8000" must be backed by "8000 appears in 12,847 / 12,855
  ticks (99.94%)."
- **Triangulate before claiming exploitability.** If only one lens
  finds a pattern, mark it as "needs corroboration" not "exploitable."

## Workflow stages

### Stage 1 — Exploration (10 explorer agents, parallel)

Each writes ONE executed Jupyter notebook in `notebooks/round_5/` plus
a tiny findings file in `notebooks/round_5/<name>_findings.md` (≤15
bullets max, each: claim + numerical evidence + which other notebooks
should corroborate or contradict).

| # | Notebook file | Family | Lenses |
|---|---|---|---|
| 01 | `01_per_product_distrib.ipynb` | Distributional | mid stats, distinct prices, hardcoded-FV check, range/CV, mode prevalence |
| 02 | `02_per_product_microstructure.ipynb` | Order book | spread regime, book imbalance, depth asymmetry, missing levels, queue stickiness |
| 03 | `03_per_product_timeseries.ipynb` | Time-series | ADF stationarity, AR(1)/AR(5), trend slope+R², FFT top-5 frequencies |
| 04 | `04_per_product_trades.ipynb` | Trade tape | volume distribution, trade-count by hour, signed flow proxy via spread-cross detection, no-counterparty flagged |
| 05 | `05_within_category_corr.ipynb` | Category cohesion | pairwise corr (returns + levels), cointegration, lead-lag CCF, basket spread |
| 06 | `06_cross_category_factors.ipynb` | Global structure | full 50×50 corr heatmap, hierarchical clustering, PCA scree + loadings |
| 07 | `07_categorical_features.ipynb` | Name-as-signal | does size / color / flavor / etc. encode price level? linear regression on parsed features per category |
| 08 | `08_time_regime.ipynb` | Regime | day-over-day stability (compare days 2/3/4), time-of-day patterns, vol clustering |
| 09 | `09_determinism_anomaly.ipynb` | Red-herring hunting | hardcoded FV detection, periodic step pattern detection, outlier ticks > 5σ, gap detection, near-identical timeseries (corr > 0.99), random-product control (synthetic GBM baseline) |
| 10 | (waits for stage 3) | Synthesis | — |

Each explorer:
1. Reads this brief + `docs/round_5/brief.md` + `docs/round_5/research/00_initial_observations.md`.
2. Writes the notebook with markdown intros per cell, plots inline.
3. Executes via `jupyter nbconvert --to notebook --execute --inplace`.
4. Writes `<name>_findings.md` next to the notebook.

### Stage 2 — Adversarial review (3 critic agents, parallel)

Three independent skeptics, each reads ALL 9 explorer findings docs:

- **A. Statistical critic** — flags unsound stats: missing multiple-
  testing correction, tiny samples driving conclusions, p-hacking,
  causal claims from correlation, FFT peaks not tested for significance,
  AR(1) computed on non-stationary series, etc. Output:
  `notebooks/round_5/critique_A_statistical.md` (≤30 bullets).
- **B. Cross-cutting critic** — finds contradictions BETWEEN notebooks
  ("notebook 5 says Pebbles cluster, notebook 6 says they're outliers")
  and resolves which is right by re-reading the underlying data. Output:
  `notebooks/round_5/critique_B_crosscutting.md`.
- **C. Hidden-pattern critic** — looks at what nobody investigated.
  Proposes 5–10 follow-up tests with concrete operational definitions.
  Particular suspicion of Pebbles, Microchips (per trade-signature
  asymmetry above) and any product whose name suggests a feature
  hierarchy. Output: `notebooks/round_5/critique_C_hidden.md`.

### Stage 3 — Reconciliation + synthesis (1 agent)

Reads everything (9 explorer findings + 3 critique docs). Writes:

1. `notebooks/round_5/10_synthesis.ipynb` — recomputes any disputed
   metric the critics flagged, makes the final triage call per product,
   produces a sortable dataframe.
2. `docs/round_5/research/EDA_FINAL_TRIAGE.md` — 1-page executive table:
   50 rows × {category, triage call, 1-sentence reason, lens that drove
   the call, unresolved concerns}.

## Cross-reference rules

- Every claim in findings must cite the cell that produced it
  (e.g. `[01_per_product_distrib.ipynb cell 7]`).
- Every critic claim must cite the explorer claim it disputes.
- Synthesis must cite both the explorer and critic that bear on each
  triage decision.

## Forbidden practices

- Training-memory reconstruction of IMC mechanics not in our docs.
- "Probably" or "seems like" without a number.
- Any strategy proposal (caps, thresholds, rules).
- Any PnL claim (predicted or otherwise).
- Editing CLAUDE.md, JOURNEY.md, briefs, or this AGENT_BRIEF.
- Committing.
- Modifying `src/trader.py` or anything in `src/`.

## File paths reference

- Data (read only): `data/round_5/prices/prices_round_5_day_{2,3,4}.csv`,
  `data/round_5/prices/trades_round_5_day_{2,3,4}.csv`
- Notebooks (write yours only): `notebooks/round_5/`
- Plots (optional, write yours only): `notebooks/round_5/plots/`
- Findings (write yours only): `notebooks/round_5/<your_name>_findings.md`
- Final triage (synthesizer only): `docs/round_5/research/EDA_FINAL_TRIAGE.md`
- Reference reading: `docs/round_5/brief.md`,
  `docs/round_5/research/00_initial_observations.md`,
  `docs/round_5/research/03_r3_vs_r4_lessons.md`
- Mechanics: `docs/competition.md`

## Sanity check before completing

Before declaring done, every agent confirms:
- [ ] All claims cite a notebook cell or specific row count.
- [ ] No strategy / PnL / rule proposals leaked in.
- [ ] No edits to forbidden files.
- [ ] No new files outside the assigned location.
- [ ] Notebook executes cleanly (cells produced output without errors).
