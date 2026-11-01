# Football scouting agent

A local-first football scouting workbench for exploring players in open event data. The intended result is a React interface where a scout can ask a question, inspect the filters and player metrics behind the answer, and read a report grounded in those metrics.

This repository is at the **planning and skeleton** stage. There is no runnable application yet. [The sprint plan](docs/sprint-plan.md) starts with a thin end-to-end slice and adds the AI workflow only after the data and deterministic search work.

## Working stack

- **Frontend:** React and TypeScript.
- **API:** FastAPI and Python; it owns validation and database access.
- **Database:** local PostgreSQL for normalized football data and derived metrics.
- **Local AI:** Ollama, called through LangChain for question interpretation and report drafting. LangGraph is reserved for a workflow that actually needs branching or retries.
- **Data:** [StatsBomb Open Data, hosted by Hudl](https://github.com/hudl/open-data), as the first source to assess. Its usable fields and publication terms must be checked before ingestion.

The product should run on an Apple M1 Pro with 16 GB memory without an OpenAI API key or per-call model bill. Model choice, speed, and report quality will be measured on that machine before one is adopted.

## Repository map

| Path | Purpose |
| --- | --- |
| [`frontend/`](frontend/README.md) | React scouting interface |
| [`backend/`](backend/README.md) | FastAPI service and local AI integration |
| [`data/`](data/README.md) | Ingestion code and local data workspace |
| [`evals/`](evals/README.md) | Repeatable AI and data-quality checks |
| [`infra/`](infra/README.md) | Local runtime setup |
| [`docs/`](docs/README.md) | Architecture, data rules, skill use, and sprints |

Start with [Sprint 0](docs/sprint-plan.md). Repository guidance for Codex is in [AGENTS.md](AGENTS.md).
