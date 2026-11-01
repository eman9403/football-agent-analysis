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

## Sprint 2 scouting profile: ball-progressing central midfielder

The deterministic profile uses only the pinned Premier League 2015/16 sample (competition `2`, season `27`, source commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`). These are project-defined descriptive measures, not official StatsBomb ratings or current-player recommendations.

- A progressive pass or carry must have known start and end x-coordinates and advance at least 10 x-units (`end_x - start_x >= 10`). Events without sufficient coordinates do not count toward the progressive-action numerator.
- A pass is completed when the imported StatsBomb pass event has no `pass.outcome`; the normalized `pass_completed` field records that convention. Progressive pass completion is completed progressive passes divided by progressive attempts. Overall pass completion uses completed passes divided by all pass attempts.
- Per-90 rates divide action counts by all season minutes played, then multiply by 90. A rate or completion percentage is `NULL` if its denominator is zero. The UI displays unavailable values as an em dash. Filter thresholds use unrounded aggregate values; displayed rates are rounded for readability.
- The profile treats position IDs `9`, `10`, `11`, `13`, `14`, and `15` as central-midfield roles. Central-midfield share is the sum of appearance minutes whose recorded primary position is in that set divided by the player's total season minutes. Because the importer stores one primary position per appearance rather than exact minutes across position intervals, role share approximates tactical role and must be interpreted cautiously.
- The API accepts only the named profile, bounded minute/share/limit filters, and five displayed sort metrics. Sorting is stable by player name and source player ID after the selected metric; unavailable metric values sort last. There is no composite score.

The web interface keeps the sample season visible and repeats the role-share and historical-scope caveats beside results. The local API and database are the only data path; this sprint makes no model/provider call.

Sprint 3's read-only event-coverage audit and role-specific metric contracts are documented in the [profile data audit](profile-data-audit.md) and [scouting profile design](scouting-profile-design.md). The audit SQL prints aggregates only. The API implements four deterministic profiles: ball-progressing midfielder, chance-creating attacker, forward finisher, and ball-winning midfielder. The profile catalog and player responses include metric definitions, selected role pool, historical scope, and filter values; no model or paid provider call is involved.

## Validation and source limits

The import verifies the pinned catalogue and 380 unique available match IDs, requires one event and lineup file per match, checks event identity uniqueness, and records file checksums. Database keys enforce unique match, appearance, and event identities. Re-importing the same revision updates existing rows without duplicating them. Unit and PostgreSQL integration tests use synthetic records and do not include StatsBomb data.

The agreement provides data as-is and disclaims completeness and accuracy guarantees. Preserve nulls and source IDs. Do not infer missing identity, position, or metrics. Do not use the dataset or derived analysis commercially or redistribute the source data. Add StatsBomb's source credit and logo if analysis is published.
