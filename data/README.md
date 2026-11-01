# Data workspace

Ingestion code and small committed fixtures will live here. The source assessment and metric contract are in [docs/data.md](../docs/data.md).

When Sprint 1 starts, use `raw/` for unchanged downloaded source files and `processed/` for regenerable local outputs. Both directories are ignored by Git; document the exact source selection and transformations so a fresh checkout can reproduce the database.
