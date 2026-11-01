# Sprint 2: Deterministic scouting search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give scouts a deterministic, explainable shortlist of central midfielders from the imported Premier League 2015/16 sample, with adjustable role/minute filters and separately sortable progression metrics.

**Architecture:** FastAPI runs a static, parameterized query over existing local PostgreSQL tables and source JSON fields. Python validates typed filters, computes rates from aggregate counts, applies role/minute eligibility, and sorts by an allowlisted displayed metric with a stable tie-break. React fetches that evidence and renders the filters and shortlist. This sprint makes no model call and needs no database migration.

**Tech Stack:** Python 3, FastAPI, Pydantic, psycopg 3, PostgreSQL, React 19, TypeScript, Vite, Python `unittest`.

**Spec:** [docs/scouting-profile-design.md](../../scouting-profile-design.md)

## Global Constraints

- Keep candidate eligibility, metric calculation, and sorting deterministic. Do not add a composite score or model-generated ranking.
- Query only the pinned competition 2 / season 27 sample. Display Premier League 2015/16 prominently and describe the results as historical.
- Use only verified normalized columns and retained StatsBomb event JSON. Missing coordinates cannot be guessed.
- Treat positions 9, 10, 11, 13, 14, and 15 as central-midfield roles. Role share is an approximation based on one primary position per appearance; explain that in the response and UI.
- Count a progressive action only when its end x-coordinate is at least 10 units greater than its start x-coordinate. A completed pass is a pass with no StatsBomb outcome.
- Calculate every per-90 value using total season minutes. Return percentages as 0–100 values with clear labels; use null for a rate or percentage whose denominator is zero.
- Enforce profile, sort metric, filter bounds, and result limit with typed validation. Keep SQL static and parameterized; never interpolate user-provided identifiers or sort strings.
- Keep StatsBomb data, database exports, and captured query outputs local. Commit only scenario inputs and synthetic test data; do not commit real player-result snapshots or generated evaluation outputs.
- Do not add any paid provider, model, or API dependency.

## Review Focus

1. **Progression boundary and missing locations:** `test_progressive_action_requires_ten_forward_units_and_known_coordinates` proves +10 qualifies, +9 and backward movement do not, and missing endpoints are excluded.
2. **Pass outcomes and denominator mistakes:** `test_completed_passes_follow_statsbomb_outcome_and_rates_use_season_minutes` distinguishes attempted/completed passes, checks null percentages for zero attempts, and verifies a known per-90 calculation.
3. **Candidate role/minute mistakes:** `test_role_share_and_minimum_minutes_are_inclusive_and_use_total_minutes` verifies the six position IDs, inclusive 50% and 450-minute boundaries, and role share divided by total season minutes.
4. **Unsafe or unstable sorting and invalid filters:** `test_filters_reject_unknown_profile_sort_and_out_of_range_values` plus `test_sort_is_allowlisted_and_ties_have_a_stable_order` cover validation, SQL parameterization, and deterministic ties.
5. **Empty and unavailable states:** `test_empty_search_returns_a_valid_empty_response` covers an empty shortlist; the frontend acceptance check verifies empty/error/loading states and integration confirms a database failure is surfaced as service unavailable rather than a fabricated result.

---

## File Map

- Create `backend/scouting.py`: profile and metric definitions, typed filter/response models, static SQL, aggregate-to-response calculations, candidate filtering, and stable sorting.
- Create `backend/tests/test_scouting.py`: fast unit coverage for metric definitions, filter boundaries, validation, null handling, sorting, and empty results.
- Create `backend/tests/test_scouting_integration.py`: opt-in PostgreSQL tests against the imported local sample, including five repeatable saved scenarios.
- Create `backend/tests/scouting_scenarios.json`: five accepted filter/sort inputs only; never store real player IDs, names, or result snapshots in Git.
- Modify `backend/main.py`: expose `GET /api/scouting/players`, response-model validation, and a clear 503 on database connection failure.
- Modify `frontend/src/App.tsx`: add the midfield profile, filters, data scope, shortlist, metric sorting, and loading/error/empty states while preserving system status.
- Modify `frontend/src/styles.css`: style the shortlist in the established dark-console/electric-lime visual system and make the table usable on narrow screens.
- Modify `docs/scouting-profile-design.md`: mark the approved design and record implementation clarifications without changing its metric contract.
- Modify `docs/data.md`: document progression metrics, role-share caveat, sorting, and historical scope.
- Modify `docs/sprint-plan.md`: check Sprint 2 items and add observed results only after those checks pass.

## Tasks

### Task 1: Define the typed scouting contract and pure selection logic

**Files:** `backend/scouting.py`, `backend/tests/test_scouting.py`

- [x] Write unit tests first. Cover the exact +10 threshold, +9 and backward movement, missing coordinates, successful versus unsuccessful StatsBomb passes, zero-denominator percentages, per-90 arithmetic, role-share calculation, inclusive minimum boundaries, unknown profile/sort rejection, out-of-range values, empty results, and deterministic tie-breaking. Run them and confirm the new behavior tests fail before implementation.
- [x] Add one profile definition for `ball_progressing_midfielder`, its six position IDs, five separately named performance metrics, metric descriptions/units, fixed data scope, default thresholds (450 minutes and 50% central-midfield share), default sort, and maximum result count.
- [x] Add typed filters for profile, minimum minutes, minimum role share, sort metric, sort direction, and limit. Constrain values at the API boundary and keep allowed sort fields explicit.
- [x] Add typed response models for scope/provenance, applied filters, metric definitions, result count, and player rows. Represent unavailable completion percentages as null.
- [x] Implement pure functions to turn raw aggregate counts into percentages and per-90 values, filter by total minutes and central-role share, and sort by the requested visible metric. Return null for any zero-denominator rate, keep null sort values last in either direction, and use player name then player ID as stable tie-breaks.
- [x] Run `backend/.venv/bin/python -m unittest discover -s backend/tests -v` and make all unit tests pass.

### Task 2: Query PostgreSQL and expose the scouting API

**Files:** `backend/scouting.py`, `backend/main.py`, `backend/tests/test_scouting_integration.py`, `backend/tests/scouting_scenarios.json`

- [x] Build the database query from existing `statsbomb_appearances`, `statsbomb_events`, `statsbomb_matches`, `statsbomb_players`, and `statsbomb_teams`. Aggregate appearances, total minutes, central-role minutes, teams, pass counts, progressive pass counts, and progressive carry counts for competition 2 / season 27 only.
- [x] Read pass/carry end x from `source_payload` JSONB and start x from `location_x`. Exclude missing coordinates from progression counts; use the same inclusive threshold as the unit contract. Count successful passes only when `pass_completed IS TRUE`.
- [x] Keep SQL static and bind season scope and progression threshold as parameters. Return unfiltered aggregates to Python, where typed eligibility, rates, ordering, and limit rules from Task 1 are applied consistently.
- [x] Add `GET /api/scouting/players` with typed query filters and a stable response model. Return a clear 503 if PostgreSQL is unavailable; invalid filters must return 4xx and never partial/fabricated candidates.
- [x] Add opt-in PostgreSQL integration tests that skip clearly when the local database is not configured. Verify eligibility, documented formulas, stable sorting/ties, valid empty results, and the 503 response when a mocked database connection fails.
- [x] Run integration tests against the imported local database. Execute five saved scenarios (default, higher minutes, higher role share, broad role share, high minutes) twice; compare ordered player IDs in memory, verify each result satisfies its filters and sort order, and do not persist or log the returned player list.
- [x] Start FastAPI and smoke-test default/custom filters, invalid profile/sort/bounds, empty results, and database unavailable. Verify the response contains profile definition and pinned historical scope.

### Task 3: Build the React scouting shortlist

**Files:** `frontend/src/App.tsx`, `frontend/src/styles.css`

- [x] Add TypeScript response types matching the API contract and a request helper that serializes only typed filters. Cancel or ignore stale requests when filters change.
- [x] Add the approved profile and labelled controls for minimum season minutes and central-midfield role share. Show Premier League 2015/16 scope and primary-position role-share caveat beside results.
- [x] Render candidate count and separate columns for progressive passes attempted/90, progressive passes completed/90, progressive-pass completion, progressive carries/90, overall pass completion, minutes, role share, teams, and appearances. Do not create a composite score.
- [x] Make metric headings keyboard-operable sort buttons with visible direction and correct `aria-sort`; format counts, rates, percentages, and null values clearly.
- [x] Implement loading, API/database error, no-match, and populated states. On a failed request, explain how to restore the local service without presenting stale results as matching current filters.
- [x] Keep the dark console/electric-lime design. At mobile widths, make the wide table intentionally scrollable or transform it into a readable layout; preserve visible focus and reduced-motion behavior.
- [x] Run `pnpm --dir frontend build`. Verify the desktop layout, keyboard use of filters/sort controls, UI states, units, and historical note. The production build and browser states passed at 1280x720.
- [x] Verify a rendered 375px viewport. The page and body remain 375px wide; the 1040px results table scrolls inside its own region.

### Task 4: Record definitions and Sprint 2 evidence

**Files:** `docs/scouting-profile-design.md`, `docs/data.md`, `docs/sprint-plan.md`

- [x] Mark the design approved and record only implementation clarifications that preserve its metric and filter contract.
- [x] Add the project-defined measures to `docs/data.md`, including progression threshold, StatsBomb completion convention, per-90 denominator, role IDs, role-share approximation, null handling, source revision, and historical scope.
- [x] Record Sprint 2 implementation, tests, and browser/accessibility evidence, including the outstanding 375px viewport check, without recording candidate names, IDs, or result snapshots.
- [x] Run `git diff --check` and review the diff for raw data, secrets, unsupported claims, score fields, and unrelated changes.

## Final Verification

- [x] Run `backend/.venv/bin/python -m unittest discover -s backend/tests -v`; confirm unit and opt-in PostgreSQL tests report clearly whether they ran or skipped.
- [x] Run the existing ingestion suite using its documented command and ensure Sprint 1 behavior remains intact.
- [x] Run `pnpm --dir frontend build`.
- [x] Run all five PostgreSQL scenarios twice and compare ordered results in memory; confirm eligibility and sorting without writing real player outputs to Git or logs.
- [x] Exercise API/UI at desktop and mobile widths, including invalid filters, empty results, PostgreSQL unavailable, and keyboard-only sorting. Desktop and rendered 375px browser checks passed; the page has no horizontal overflow and the wide table uses its own horizontal scroller.
- [x] Confirm no AI/provider calls, model downloads, dataset files, or database exports were introduced.
