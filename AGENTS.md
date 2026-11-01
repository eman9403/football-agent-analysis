# Repository guidance

Build a local-first football scouting workbench. The current plan is in `docs/sprint-plan.md`; Sprint 0 provides a running React, FastAPI, and PostgreSQL foundation.

- Use `docs/architecture.md` when changing service boundaries or the AI workflow.
- Use `docs/data.md` when selecting a source, changing ingestion, defining metrics, or publishing an analysis.
- Use `evals/README.md` when changing prompts, models, structured outputs, or report generation.
- Use `docs/skills.md` when choosing a reusable workflow for a sprint task.

Keep database queries and metric calculations deterministic. Let the local model propose typed scouting filters and draft text from retrieved evidence; validate filters in FastAPI and attach source context to reported numbers. Build only against fields verified in the selected dataset. Keep raw datasets, model weights, secrets, and generated evaluation results out of Git.

Use the smallest working slice for each sprint. Put tests beside the code they exercise and record observed checks in the sprint plan when a deliverable is completed. A paid model API is outside the current plan unless the user requests it.
