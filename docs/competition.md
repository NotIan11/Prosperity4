# Prosperity 4 — Competition Mechanics

Sourced from the IMC Prosperity 4 Game Mechanics docs. Evergreen — cross-round.

---

## Round structure

- **5 rounds total**, **16 simulation days**.
- R1, R2: **72 hours each**.
- R3, R4, R5: **48 hours each**.
- Each round contains both an **algorithmic challenge** and a **manual challenge** running concurrently.
- **Tutorial round**: manual trading is **inactive**.
- Manual trades **have no effect on the algorithmic trade** — separate challenges, separately scored.

---

## Submissions

### Algorithmic

- Submit a Python program before the round timer ends.
- **Last successfully processed submission is locked in** at round end.
- Multiple uploads allowed during the round; only the **active** algorithm runs.
- Past uploads visible in Upload & Changelog window with status + uploader; **debug logs downloadable** for any past upload.
- Once the round closes, the submission **cannot be changed**.

### Manual

- Submit through the Manual Challenge Overview window.
- Multiple resubmissions allowed; only the **last submitted** trade is processed.
- Once the round closes, the submission **cannot be changed**.

---

## Execution

- After the round timer ends, all algorithms run for **"a full day of trading"** against the Prosperity trading bots.
- **Each team's algorithm trades independently** — no interaction between different teams' algorithms.
- When a new round starts, previous round results are disclosed and the **leaderboard updates**.
- Past rounds remain visible in the dashboard for review.
- After **R5** ends, final results are processed and the winner is announced **within 2 weeks**.

---

## Information sources

- **A.R.I.A. Uplinks**: video briefings released at the start of every round; cover all essential per-round info for algo and manual challenges.
- **Algorithmic Challenge Overview**: in-platform window with everything needed to build the algorithm, including the **Data Capsule** containing historical trade data for the round's tradable goods.
- **Manual Challenge Overview**: in-platform window with manual challenge info + submission inputs.

---

## Leaderboard

Four ranking tabs:

- **Overall**: total PnL per team (canonical ranking).
- **Algorithmic**: algo PnL only.
- **Manual**: manual PnL only.
- **Country**: vs. teams with the same country set.

---

## On-Board Advisors

- Choose one of three available advisors during the **tutorial round**.
- Selection **locks** when the tutorial ends; cannot switch from R1 onward.
- Advisors offer perspectives and guidance throughout the rounds.
- Located in the bottom-right corner of the Outpost View.

---

## Cosmetic / UI

- **Outpost View**: shows team name, PnL indicator, overall rank; outpost grows with profit. No trading impact.
- **Crew Honors**: badges earned for actions/achievements. Shareable. No trading impact.
