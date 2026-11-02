# Evaluations

`sprint-4-local-ai.json` holds versioned scouting questions, expected structured filters, and the report evidence contract. It covers supported requests across profile lenses, ambiguous wording, unsupported fields, and report claim traceability. Keep player-level outputs and generated runs out of Git; runs belong in `results/`, which is ignored.

Run the fixed filter suite on the local Ollama model after downloading it:

```bash
backend/.venv/bin/python -m backend.run_local_ai_evals
```

The result records model name, exact filter accuracy, median/p95 latency, sampled Ollama process RSS, and loaded model sizes. The API separately tests that every report statement comes from a metric key, a known metric definition, and the deterministic role-filtered peer cohort. Add LangGraph evaluation only if that workflow is adopted.
