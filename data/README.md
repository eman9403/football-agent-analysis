# Data workspace

The Sprint 1 importer is [`import_statsbomb.py`](import_statsbomb.py). The source snapshot is pinned in [`statsbomb-selection.json`](statsbomb-selection.json), and the PostgreSQL tables and metrics view are defined in [`schema.sql`](schema.sql).

StatsBomb's GitHub files are publicly downloadable without authentication. Its [user agreement](https://github.com/hudl/open-data/blob/master/LICENSE.pdf) governs use, including research/analysis limits and restrictions on commercial use and redistribution. StatsBomb asks users to register at the [Resource Centre](https://statsbomb.com/resource-centre/); published analysis should credit StatsBomb and use its logo.

Start Postgres.app, then run this command from the repository root:

```bash
backend/.venv/bin/python data/import_statsbomb.py
```

The command downloads only the selected Premier League 2015/16 files and loads them into the local `football_scouting` database. It does not clone the full StatsBomb repository. Raw JSON and the generated manifest are saved under `data/raw/`; the directory is ignored by Git. Do not commit or externally expose those files. The import can be rerun from the manifest and pinned commit. See [`docs/data.md`](../docs/data.md) for table, metric, provenance, and validation details.
