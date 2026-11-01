# StatsBomb Open Data: Premier League 2015/16

Research snapshot: 1 November 2026. Sources below are first-party StatsBomb/Hudl material and the live official open-data repository.

## Recommended import sample

Use the men's English Premier League 2015/16 season as the first scouting dataset. In StatsBomb's official [`competitions.json`](https://raw.githubusercontent.com/hudl/open-data/master/data/competitions.json), it is `competition_id: 2`, `season_id: 27`. The official [`matches/2/27.json`](https://raw.githubusercontent.com/hudl/open-data/master/data/matches/2/27.json) contains 380 unique match records, all with `match_status: "available"`, dated 8 August 2015 to 17 May 2016. These IDs and counts were checked directly against those files for this note.

This gives a full league season for player and team comparisons. The season's `match_available_360` value is null in `competitions.json`, so the open-data repository does not advertise 360 data for this sample. Do not make 360-based features a Sprint 1 requirement.

## Official file layout and access

StatsBomb publishes JSON exports in a hierarchy: one competition/season catalogue, a match list at `matches/{competition_id}/{season_id}.json`, and per-match event and lineup files under `events/{match_id}.json` and `lineups/{match_id}.json`. 360 files exist only for selected matches. The repository also includes data-format documentation in `doc/`. See the [official repository README](https://github.com/hudl/open-data#statsbomb-open-data).

For this sample, fetch the catalogue and `matches/2/27.json`, then fetch the `events/{match_id}.json` and `lineups/{match_id}.json` files for those 380 IDs from the official [raw-data host](https://raw.githubusercontent.com/hudl/open-data/master/). Selective file downloads are sufficient; cloning the full repository is unnecessary. Because `master` can change, an importer should record the resolved repository commit, retrieval time, and hashes of downloaded files in its local manifest so a rerun can identify its source snapshot.

## Terms and attribution

The repository README describes the data as freely available for research projects and genuine interest in football analytics. The repository's [StatsBomb Public Data User Agreement](https://github.com/hudl/open-data/blob/master/LICENSE.pdf) governs use. Its relevant provisions state:

- Use is for analysis and research. The agreement says the data must not be edited, distorted, distributed, reproduced, sold, or provided to an external/third party, and bars commercial exploitation of the data or analysis derived from it (clause 1.2).
- Public analysis or conclusions may be shared, but any publication of analysis formed from StatsBomb data must be credited with the StatsBomb brand logo (agreement introduction and clause 1.4; the [README](https://github.com/hudl/open-data#terms--conditions) repeats the source and logo requirement). Use the logo from StatsBomb's [Media Pack](https://statsbomb.com/resource-centre/).
- StatsBomb asks users to register their interest at the [Resource Centre](https://statsbomb.com/resource-centre/) before using the service (agreement introduction and clause 2.2). Access to the public GitHub files itself does not prompt for authentication; this does not replace the agreement or registration request.
- The data is provided as-is, and StatsBomb disclaims warranties about accuracy, reliability, and completeness (clauses 3.2–3.4). StatsBomb also reserves the right to withhold GitHub access (clause 2.1).

For this project, keep the raw StatsBomb files in ignored local storage and do not commit or expose them through a public endpoint. Keep the project non-commercial. If the scouting analysis is published or shared publicly, include StatsBomb attribution and its logo; do not publish or redistribute the underlying event/lineup data. StatsBomb requests Resource Centre registration; downloading the public GitHub files does not itself require authentication. This note records the source terms; it does not register the user or accept terms on their behalf.

## Import implications

- First import scope: competition 2, season 27, match list plus each match's events and lineups; omit 360.
- Preserve StatsBomb match, team, and player IDs with the imported records, and retain the source snapshot details locally.
- Validate that the import sees 380 unique matches and that each match file can be retrieved. Treat availability flags and nullable fields as source data, not as guarantees that every possible metric is present.
- The official source states that the data may be incomplete or inaccurate. Derived scouting metrics should be documented as calculations over this released sample, not official StatsBomb IQ metrics.

## Sources

- [StatsBomb Open Data README](https://github.com/hudl/open-data) — stated research purpose, attribution/logo, file layout, and docs location.
- [StatsBomb Public Data User Agreement PDF](https://github.com/hudl/open-data/blob/master/LICENSE.pdf) — use, redistribution, commercial-use, registration, warranty, and availability terms.
- [Official competition catalogue](https://raw.githubusercontent.com/hudl/open-data/master/data/competitions.json) — competition/season IDs and 360 availability metadata.
- [Official Premier League 2015/16 match list](https://raw.githubusercontent.com/hudl/open-data/master/data/matches/2/27.json) — 380 match records, match status, IDs, and dates.
- [StatsBomb Resource Centre](https://statsbomb.com/resource-centre/) — registration and media-pack access.
