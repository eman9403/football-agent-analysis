# Data source and import

## Selected source

The first dataset is [StatsBomb Open Data](https://github.com/hudl/open-data), provided by StatsBomb and hosted on GitHub. The project pins the men's English Premier League 2015/16 sample: competition `2`, season `27`, and 380 matches. The selection is recorded in [`data/statsbomb-selection.json`](../data/statsbomb-selection.json) and pins source commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb` so future changes to the repository do not silently alter the sample.

StatsBomb describes this dataset as free for research and analysis. The GitHub files are publicly downloadable without authentication, but the [user agreement](https://github.com/hudl/open-data/blob/master/LICENSE.pdf) governs their use: it prohibits commercial exploitation and redistribution or external provision of the data. StatsBomb asks users to register at its [Resource Centre](https://statsbomb.com/resource-centre/); if analysis is published, its README asks for StatsBomb source credit and logo. This project keeps the source files and database local; it does not publish or commit the data. See the [research note](research/statsbomb-open-data.md) for the source clauses and links.

The official repository layout provides a competition catalogue, a match list for each competition and season, then per-match event and lineup JSON. The chosen season has no advertised 360 files, so 360-derived features are outside Sprint 1.

## Reproducing the local import

Start Postgres.app and run from the repository root. The GitHub download itself does not require a login; StatsBomb still asks users to register and the agreement governs use of the data:

```bash
backend/.venv/bin/python data/import_statsbomb.py
```

The importer selectively fetches the pinned catalogue, match list, and the event and lineup files for those 380 matches. It does not clone the full StatsBomb repository. Files are stored unchanged under the ignored `data/raw/statsbomb/` directory. A local manifest records each file's source URL, immutable commit, retrieval time, byte count, and SHA-256. Downloads are atomic and can be resumed from a verified manifest. The importer processes one match at a time and upserts rows into the local `football_scouting` PostgreSQL database. It can be rerun safely against the same source revision.

Set `DATABASE_URL` if PostgreSQL is not using the default local connection. The raw source files, manifest, and all generated database rows stay outside Git. Do not add raw or processed data to a commit or make it available through an external endpoint.

## Observed import

The local import completed on 2026-11-01 from the pinned commit: 380 matches, 10,469 appearances, 1,313,773 events, 644 rostered players, and 762 source files (about 1.1 GiB). A full second run verified the same totals without duplicating rows. The metrics view contains 550 player-season rows; this sample has no zero-minute appearance rows and no per-90 values with a zero-minute denominator. The 8 importer tests pass, including PostgreSQL integration. These figures describe the local sample, not a promise that upstream data will remain available.

## PostgreSQL model and metric definitions

`data/schema.sql` defines source competitions/seasons, teams, players, matches, appearances, events, and imported-file provenance. Original source IDs are retained. Each normalized event row also keeps the source event JSON for traceability; the unchanged files remain the local source of record.

The initial `statsbomb_player_season_metrics` view derives these deterministic metrics:

| Metric | Definition | Unit |
| --- | --- | --- |
| Appearances | One lineup record with at least one active position interval for a player in a match; unused substitutes are excluded. | matches |
| Minutes played | Union of active position intervals in the lineup's elapsed `MM:SS` match clock. Where source position intervals overlap, the latest starting position interval takes precedence so minutes are never double-counted. | minutes |
| Passes attempted | Events whose type is `Pass` and which have a player ID. | count |
| Passes completed | `Pass` events with a `pass` object and no `pass.outcome`, following the StatsBomb event convention. | count |
| Shots | Events whose type is `Shot` and which have a player ID. | count |
| Goals | `Shot` events whose `shot.outcome.name` is `Goal`. | count |
| Per-90 rates | Each count above divided by the player's summed lineup minutes and multiplied by 90. | count per 90 minutes |

Per-90 values are `NULL` when total minutes are zero. They describe calculations over this released sample, not official StatsBomb IQ metrics. A query or report may use only imported fields, and must show sample scope and data coverage rather than filling gaps with model guesses.

## Validation and source limits

The import verifies the pinned catalogue and 380 unique available match IDs, requires one event and lineup file per match, checks event identity uniqueness, and records file checksums. Database keys enforce unique match, appearance, and event identities. Re-importing the same revision updates existing rows without duplicating them. Unit and PostgreSQL integration tests use synthetic records and do not include StatsBomb data.

The agreement provides data as-is and disclaims completeness and accuracy guarantees. Preserve nulls and source IDs. Do not infer missing identity, position, or metrics. Do not use the dataset or derived analysis commercially or redistribute the source data. Add StatsBomb's source credit and logo if analysis is published.
