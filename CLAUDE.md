# Prosperity4 — Project Conventions

## Scope

This repo is for the IMC Prosperity 4 algorithmic trading competition, GOAT phase
(Rounds 3, 4, 5). PnL is reset at start of R3 — only R3–R5 results matter.

## Python

- Always use `.venv/bin/pip` (never global `pip3`).
- IMC platform supports the standard library of **Python 3.12** per the official wiki.
  Use any compatible version locally (3.12 or 3.13 fine); avoid 3.13-only syntax
  in code that gets submitted.

## Submission

- Submission entry point: `src/trader.py`, class `Trader`,
  method `run(state) -> (orders_dict, conversions_int, traderData_str)`.
- The IMC platform injects `datamodel` as a top-level module — `from datamodel import ...`
  works without a relative path.
- Upload only `src/trader.py` (or a flattened bundle of src/) to the portal.
  No `data/`, `docs/`, `notebooks/`, or `.venv/` should ever be in a submission.

## Data

- CSVs from the portal are **semicolon-separated** (not comma). Use `sep=";"`.

## Git

- Conventional commits: `feat:`, `chore:`, `docs:`, `fix:`, `test:`, `research:`.
- Commit bodies use bullet-point format.
- No co-author trailers.
- No remote push without explicit approval.
- Branches:
  - `main` — historical baseline. Do not touch.
  - `ben-r3` — active R3 development branch.

## Working style

- Build understanding before writing code. Read docs, explore data in notebooks,
  validate assumptions before committing to an architecture.
- Keep `docs/` as the source of truth for strategy reasoning. Code is the result;
  docs are the why.
