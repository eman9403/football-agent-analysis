# StatsBomb Season Import Implementation Plan

> **For agentic workers:** Use the existing Sprint 1 scope in `docs/sprint-plan.md`. This plan is being executed inline because the user authorized the import.

**Goal:** Download the official StatsBomb Open Data Premier League 2015/16 sample at a fixed repository revision, load reproducible player, appearance, match, and event data into local PostgreSQL, and expose deterministic season metrics.

**Architecture:** A checked-in selection file pins the source repository, commit, competition, and season. A small Python importer selectively downloads only that season's match, event, and lineup JSON into ignored `data/raw/`, then normalizes one match at a time into PostgreSQL. Versioned SQL defines the schema and metric view; source JSON remains local and unchanged.

**Tech Stack:** Python 3.12 standard library, psycopg 3, PostgreSQL, `unittest`.

**Spec:** `docs/sprint-plan.md` Sprint 1 and `docs/data.md`.

## Global Constraints

- Keep raw datasets and generated data out of Git.
- Preserve source URLs/revision, retrieval time, competition/season IDs, and source player/team/match/event IDs.
- Keep queries and derived metrics deterministic and only use observed fields.
- Metrics require clear event rules, denominator, units, and version.
- StatsBomb terms permit research/analysis, prohibit commercial use and redistribution of data, and require logo attribution on published analysis.

## Review Focus

- A failed or interrupted download must not leave a partial JSON file treated as valid; test atomic file replacement.
- Re-running an import must not duplicate rows; test unique IDs and conflict-safe writes.
- Missing player, pass outcome, shot outcome, or zero-minute values must not fabricate identity or per-90 values; test null and denominator behavior.
- The source selection must fail clearly if the pinned match file and per-match files do not agree; test missing files and duplicate IDs.
- A source file update must not silently change the imported sample; test the immutable commit URL and manifest provenance.

---

### Task 1: Define the source selection and schema

**Files:**
- Create: `data/statsbomb-selection.json`
- Create: `data/schema.sql`
- Test: `data/tests/test_import_statsbomb.py`

**Interfaces:**
- Selection contains repository URL, full commit SHA, competition ID `2`, season ID `27`, display names, and an importer version.
- Schema creates competition-season, team, player, match, appearance, event, and import-file provenance tables, with stable source IDs and unique constraints.
- A player-season view exposes appearances, minutes, passes attempted/completed, shots, goals, and per-90 rates where minutes are positive.

- [x] Write tests for the fixed selection, uniqueness constraints, and metric semantics using a tiny synthetic match.
- [x] Run the tests and confirm they fail because the schema and importer are not yet implemented.
- [x] Implement the selection and schema, keeping metric units and definitions in the data docs.
- [x] Run the tests and confirm they pass.

### Task 2: Download and validate only the selected source files

**Files:**
- Create: `data/import_statsbomb.py`
- Test: `data/tests/test_import_statsbomb.py`

**Interfaces:**
- `download_selection(selection, raw_root) -> manifest_path` writes immutable-revision JSON under `data/raw/statsbomb/`.
- Downloads are atomic and resumable by skipping already-valid local files; the manifest records source URL, commit, timestamp, byte count, and SHA-256.
- The importer verifies 380 unique matches and requires matching event and lineup files before loading.

- [x] Add tests for atomic download, manifest hashes, resume, and repairing a modified file.
- [x] Run tests to confirm the new behaviors fail before implementation.
- [x] Implement the selective downloader with bounded concurrency and no full-repository clone.
- [x] Run tests and confirm they pass.

### Task 3: Normalize and import matches idempotently

**Files:**
- Modify: `data/import_statsbomb.py`
- Test: `data/tests/test_import_statsbomb.py`

**Interfaces:**
- `import_selection(selection, raw_root, connection) -> ImportSummary` applies schema and processes one match at a time.
- Events preserve source UUID and index, event type/time, source team/player IDs, location, pass/shot outcomes, and the original JSON payload.
- Appearances are derived from lineup position intervals; unused substitutes are excluded, tactical position changes remain one appearance, and primary position is the role with most active seconds.
- SQL upserts ensure the same source revision can be safely imported again.

- [x] Add tests for appearance intervals, unused substitutes, event identity, missing optional fields, and idempotent re-import.
- [x] Run tests and confirm they fail for missing importer behavior.
- [x] Implement transactional per-match upserts and deterministic player-season metrics.
- [x] Run the complete importer `unittest` suite and confirm it passes.

### Task 4: Import the selected season and document observed results

**Files:**
- Modify: `docs/data.md`
- Modify: `data/README.md`
- Modify: `docs/sprint-plan.md`
- Generated locally: `data/raw/statsbomb/` and local PostgreSQL rows (both excluded from Git)

- [x] Run the importer against local PostgreSQL and confirm 380 matches, source player appearances, and event counts are present.
- [x] Query the player-season metrics view and check per-90 denominator behavior.
- [x] Re-run the importer and verify table row counts remain unchanged.
- [x] Record actual counts, dataset size, command, provenance, and checks in the docs and Sprint 1 plan.
- [x] Check Git status to confirm no raw data or generated outputs are tracked.
