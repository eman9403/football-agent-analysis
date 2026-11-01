# Football scouting agent

A local-first football scouting workbench for exploring players in open event data. The intended result is a React interface where a scout can ask a question, inspect the filters and player metrics behind the answer, and read a report grounded in those metrics.

The app has a running React, FastAPI, and PostgreSQL foundation, a local StatsBomb sample, and four deterministic, explainable role-specific scouting profiles. Local AI is planned as a separate next sprint. See the [sprint plan](docs/sprint-plan.md), [profile data audit](docs/profile-data-audit.md), and [profile definitions](docs/scouting-profile-design.md).

## Run the local foundation

On a Mac, install [Node.js](https://nodejs.org/en/download) 20.19+ or 22.12+, [pnpm](https://pnpm.io/installation), and Python 3.12+. Install [Postgres.app](https://postgresapp.com/documentation/install.html), open it, and click **Initialize** once. The startup script finds Postgres.app's command-line tools in its standard Applications location. It can also use PostgreSQL already on your `PATH`.

From the repository root, run:

```bash
./infra/dev.sh
```

The first run creates the `football_scouting` database if needed, installs the Python and JavaScript dependencies locally, and starts both servers. Open [http://127.0.0.1:5173](http://127.0.0.1:5173) to see the API and database status. The API response is also available at [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health). Press Ctrl+C in the terminal to stop the development servers.

If the default ports are already in use, choose free local ports and the script configures the browser proxy to match: `API_PORT=8001 UI_PORT=5175 ./infra/dev.sh`.

No OpenAI API key, Ollama model, or football dataset is needed for Sprint 0. If you use a different Python or PostgreSQL installation, set `PYTHON_BIN` or `POSTGRES_BIN_DIR` before running the script.

## Working stack

- **Frontend:** React and TypeScript.
- **API:** FastAPI and Python; it owns validation and database access.
- **Database:** local PostgreSQL for normalized football data and derived metrics.
- **Local AI:** Ollama, called through LangChain for question interpretation and report drafting. LangGraph is reserved for a workflow that actually needs branching or retries.
- **Data:** [StatsBomb Open Data, hosted by Hudl](https://github.com/hudl/open-data), pinned to the Premier League 2015/16 season for Sprint 1. The sample, local import command, metric definitions, and usage terms are documented in [docs/data.md](docs/data.md).

The product should run on an Apple M1 Pro with 16 GB memory without an OpenAI API key or per-call model bill. Model choice, speed, and report quality will be measured on that machine before one is adopted.

## Repository map

| Path | Purpose |
| --- | --- |
| [`frontend/`](frontend/README.md) | React scouting interface |
| [`backend/`](backend/README.md) | FastAPI service and local AI integration |
| [`data/`](data/README.md) | Ingestion code and local data workspace |
| [`evals/`](evals/README.md) | Repeatable AI and data-quality checks |
| [`infra/`](infra/README.md) | Local runtime setup |
| [`docs/`](docs/README.md) | Architecture, data rules, profile audit, skill use, and sprints |

Start with [Sprint 0](docs/sprint-plan.md). Repository guidance for Codex is in [AGENTS.md](AGENTS.md).
