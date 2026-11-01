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

**Implemented on 2026-11-01:** Added one deterministic ball-progressing central-midfielder profile for the historical sample. The API uses bounded typed filters, explainable project-defined event metrics, stable per-metric sorting, and a pinned season/source scope. Five saved input scenarios were run twice against local PostgreSQL and their ordered results were compared in memory with filter and sort checks; candidate names, IDs, and result snapshots were not saved. Backend unit/integration tests, the Sprint 1 importer suite, invalid/empty/unavailable API checks, and the React production build passed. Browser checks covered the populated shortlist, metric sorting, an empty filter result, the PostgreSQL-unavailable message and retry path, and accessible labels/status semantics. Responsive styles were reviewed, but a rendered 375px viewport remains unverified because the available embedded-browser controls could not set that viewport. No AI/provider call or model download was added.

## Sprint 3 — Local AI assistance

**Outcome:** Natural-language questions become inspectable filters and evidence-backed summaries.

- [ ] Benchmark candidate Ollama models on the M1 Pro for memory, latency, and filter accuracy.
- [ ] Use LangChain to produce typed filters; reject or repair invalid outputs in the API.
- [ ] Draft short reports from retrieved rows with metric units and source context.
- [ ] Create a fixed evaluation set covering valid questions, unsupported attributes, ambiguous requests, and factual report claims.

**Exit check:** Compare the selected model against the deterministic scenarios, record quality and latency, and show a report whose factual claims trace to returned data. Search still works when Ollama is unavailable.

## Sprint 4 — Production habits

**Outcome:** The local app is repeatable, observable, and safe to extend.

- [ ] Add structured logs, request IDs, model/prompt versions, and failure visibility.
- [ ] Add appropriate caching and timeouts after measuring slow paths.
- [ ] Run unit, integration, and evaluation checks in CI where local-model requirements permit.
- [ ] Write a short local runbook covering startup, data refresh, model download/removal, backup, and recovery.
- [ ] Decide from observed workflow complexity whether LangGraph adds value.

**Exit check:** Another developer can start the app, load the sample, run checks, inspect a failed request, and reproduce a scouting answer using the documented versioned inputs.
