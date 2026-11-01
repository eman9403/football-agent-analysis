# Frontend

This folder will hold the React + TypeScript scouting interface. Sprint 0 creates the smallest page that calls FastAPI; Sprint 2 adds player filters, candidate results, and visible metric provenance. Keep UI tests beside the components they cover.

Sprint 0's page shows distinct checking, ready, database-down, and API-down states. Vite proxies `/api` requests to FastAPI on port 8000, so the browser uses a same-origin request during development. Start the full stack with `./infra/dev.sh` from the repository root; `pnpm run build` checks TypeScript and creates a production bundle.

The API owns filter validation and rankings. The interface should show the interpreted filters before a natural-language search is accepted so a scout can spot a mistaken interpretation.
