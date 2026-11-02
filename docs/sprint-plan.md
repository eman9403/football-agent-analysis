# Sprint plan

Use one-week iterations as a planning cadence; adjust the calendar to available time. Each sprint finishes with a demonstrable slice and observed checks. Sprint 0 is complete.

## Sprint 0 — Local foundation

**Outcome:** A browser page, API, and database can run together on the development Mac.

- [x] Create the repository skeleton and document the working architecture, data rules, skills, and plan.
- [x] Bootstrap React + TypeScript and FastAPI with a health endpoint.
- [x] Add local PostgreSQL setup and a documented start command.
- [x] Make one React request to the API and show a clear success or failure state.

**Exit check:** A new checkout can follow the README, start the stack, and see the API status in the browser. No model or full dataset is required.

**Observed on 2026-11-01:** `./infra/dev.sh` created `football_scouting` in Postgres.app and started both servers. The browser showed FastAPI and PostgreSQL as connected. Stopping PostgreSQL returned HTTP 503 with `database: unavailable`; the browser showed the database failure, then recovered after PostgreSQL restarted. With only Vite running, the browser showed the API failure. The TypeScript/Vite production build passed.

## Sprint 1 — Trustworthy football data

**Outcome:** A small, reproducible player dataset is queryable in PostgreSQL.

- [x] Review the StatsBomb source terms and choose Premier League 2015/16 (competition 2, season 27; 380 matches). StatsBomb requests Resource Centre registration; GitHub downloads are unauthenticated.
- [x] Selectively import the pinned competition, match, lineup, and event files with source IDs and provenance into local PostgreSQL.
- [x] Define a small set of player metrics and coverage rules from the fields actually present.
- [x] Add ingestion tests for joins, duplicates, missing values, and metric units.

**Completed on 2026-11-01:** Imported the pinned StatsBomb revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`: 380 matches, 10,469 appearances, 1,313,773 events, 644 rostered players, and 762 source files (1.1 GiB on disk). The 8 importer tests pass, including PostgreSQL integration; the local metrics view has 550 player-season rows, no zero-minute rows in this sample, and no invalid per-90 values. A second full import produced the same row counts. Source JSON and its checksum manifest are ignored by Git.

**Exit check:** Re-running the importer from the same sample produces the same player rows and documented metrics; a query shows source competition and season.

## Sprint 2 — Deterministic scouting search

**Outcome:** A scout can filter and compare players without AI.

- [x] Define typed, allowlisted filters and a stable response shape in FastAPI.
- [x] Build the query/ranking path over the Sprint 1 sample.
- [x] Add React filter controls, candidate results, and metric/source details.
- [x] Cover invalid filters, empty results, low-minute players, and missing metrics.

**Exit check:** At least five saved scouting scenarios return expected candidates and explain which data produced them.

**Implemented on 2026-11-01:** Added one deterministic ball-progressing central-midfielder profile for the historical sample. The API uses bounded typed filters, explainable project-defined event metrics, stable per-metric sorting, and a pinned season/source scope. Five saved input scenarios were run twice against local PostgreSQL and their ordered results were compared in memory with filter and sort checks; candidate names, IDs, and result snapshots were not saved. Backend unit/integration tests, the Sprint 1 importer suite, invalid/empty/unavailable API checks, and the React production build passed. Browser checks covered the populated shortlist, metric sorting, an empty filter result, the PostgreSQL-unavailable message and retry path, accessible labels/status semantics, and a rendered 375px viewport; at 375px the page stays within the viewport and the wide table scrolls within its results region. No AI/provider call or model download was added.

## Sprint 3 — Explainable multi-profile scouting

**Outcome:** A scout can compare role-specific shortlists using evidence and metrics that fit each role.

- [x] Audit the imported event, location, outcome, possession, xG, assist, and position coverage; save repeatable aggregate SQL and findings in docs/profile-data-audit.md.
- [x] Define candidate role pools and separate metric contracts for a progressor, chance creator, finisher, and ball-winner in docs/scouting-profile-design.md.
- [x] Implement the three additional allowlisted FastAPI profiles with profile-specific query metrics and stable response definitions.
- [x] Add profile selection and profile-specific controls, metric columns, sorting, and caveats to the React interface.
- [x] Add source-payload integration checks and deterministic scenarios for each profile.

**Discovery completed on 2026-11-01:** The read-only audit of the pinned 2015/16 sample found 9,908 shots with numeric xG, 6,506 shot-assist flags, 669 goal-assist flags, and strong coverage for pressures, recoveries, interceptions, and tackle outcomes. At the shared 450-minute and 50% role-share thresholds, estimated role pools are 81 central midfielders, 68 wide/attacking creators, and 50 forwards. These are pool-size estimates; role share uses each appearance's primary position. The audit SQL is data/audit-profile-coverage.sql. No player-level result was written to Git. Search remains deterministic; no model or paid API was used.

**Implemented on 2026-11-01:** The API now exposes four allowlisted role profiles, with each profile's position pool, role-share filter, independent metrics, definitions, units, and default sort. The React shortlist fetches the profile catalog and renders the selected profile's metrics and sorting controls. PostgreSQL integration checks compare aggregate pass, carry, shot, assist, box-pass, pressure, recovery, interception, and tackle counts with source JSON payloads; eight saved scenarios cover all profiles and repeatability without storing player-level outputs. Backend unit tests, PostgreSQL integration tests, frontend helper tests, and the production TypeScript/Vite build passed. No model or paid API was used.

**Exit check:** All four profiles produce deterministic, role-appropriate results with visible metric definitions and data caveats. No shared composite score or present-day claim is displayed. Sprint 3 is complete.

## Sprint 4 — Local AI assistance

**Outcome:** Natural-language questions become inspectable filters and evidence-backed summaries.

- [ ] Benchmark candidate Ollama models on the M1 Pro for memory, latency, and filter accuracy with the fixed harness.
- [x] Use LangChain to produce typed filters; reject or repair invalid outputs in the API.
- [x] Draft evidence-first dossiers from role-filtered metrics with units and source context.
- [x] Create a fixed evaluation set covering supported requests, unsupported attributes, ambiguous requests, and report evidence.

**Implemented on 2026-11-02:** Added optional local Ollama status, LangChain structured filter interpretation, a manual review/apply gate, and evidence dossiers whose metric statements and peer comparisons are computed and validated in FastAPI. If Ollama is absent, manual search and deterministic evidence-only dossiers continue to work. Added 13 fixed question cases and a repeatable benchmark harness for exact filter accuracy, median/p95 latency, Ollama process RSS, and loaded-model size. The LangChain integration and schema construct successfully; unit/API tests and the frontend production build pass. Ollama is not installed and no model was downloaded, so the real M1 Pro benchmark and model-quality measurement remain outstanding; see docs/local-ai.md.

**Exit check:** Compare the selected model against deterministic scenarios, record quality and latency, and show a report whose factual claims trace to returned data. Search still works when Ollama is unavailable.

## Sprint 5 — Production habits

**Outcome:** The local app is repeatable, observable, and safe to extend.

- [ ] Add structured logs, request IDs, model/prompt versions, and failure visibility.
- [ ] Add appropriate caching and timeouts after measuring slow paths.
- [ ] Run unit, integration, and evaluation checks in CI where local-model requirements permit.
- [ ] Write a short local runbook covering startup, data refresh, model download/removal, backup, and recovery.
- [ ] Decide from observed workflow complexity whether LangGraph adds value.

**Exit check:** Another developer can start the app, load the sample, run checks, inspect a failed request, and reproduce a scouting answer using the documented versioned inputs.
