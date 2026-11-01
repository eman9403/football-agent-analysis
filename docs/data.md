# Data and provenance

## Candidate source

Start by assessing [StatsBomb Open Data](https://github.com/hudl/open-data). Its repository provides competition/season, match, event, and lineup JSON, with 360 files for selected matches. Before importing a subset, confirm the current terms, attribution requirements, available fields, and the competitions and seasons chosen for the MVP. Follow the source's attribution and logo instructions when publishing analysis.

## Ingestion contract

- Preserve the original source URL, retrieval date or revision, competition, season, match ID, and source player/team IDs.
- Keep raw files unchanged in `data/raw/` locally. Record transformations in versioned ingestion code; put regenerable outputs in `data/processed/` locally.
- Define each derived metric with its event rule, denominator, unit, and calculation version. Use explicit nulls for unavailable values and check minutes before any per-90 calculation.
- Validate identity joins and duplicate records before exposing player-level rankings.
- A query or report may use only fields and metrics actually supported by the imported sample. Show coverage and missingness rather than filling gaps with model guesses.

The normalized PostgreSQL tables and exact metric definitions are Sprint 1 deliverables. Tiny synthetic test fixtures may be committed with the code; full source exports and generated tables stay local.
