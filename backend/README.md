# Backend

This folder will hold the FastAPI service, PostgreSQL access, and local-model adapter. FastAPI validates typed filters and builds deterministic queries; LangChain talks to Ollama for question interpretation and report drafting. Keep model prompts and parsing separate from metric calculations.

Sprint 0 adds a health endpoint. Later sprints add ingestion-facing data access, search, and evaluation-backed AI routes. Keep tests beside the related Python modules.
