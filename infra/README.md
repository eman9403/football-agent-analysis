# Local infrastructure

`dev.sh` is the single startup command for Sprint 0 after Node/pnpm, Python, and PostgreSQL are installed. It checks that PostgreSQL is running, creates the `football_scouting` database if needed, installs missing local dependencies, and starts FastAPI and Vite. See the root README for prerequisites and URLs.

Commit an `.env.example` when settings exist; keep real credentials in ignored local files. Document model downloads and removal in the Sprint 4 runbook.
