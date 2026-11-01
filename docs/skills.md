# Skills for this project

Codex skills are installed globally and loaded when their workflow fits the task; this repository points to them instead of copying their files. Use the routes below for work that touches the project. A skill guides the process; project data contracts, tests, and evaluation results decide whether the result is correct.

## Project workflow

| Work | Skills | Project use |
| --- | --- | --- |
| Clarify scouting language and decisions | `grill-with-docs`, `domain-modeling` | Resolve ambiguous roles, metrics, or decisions; record settled vocabulary and architecture decisions in the project docs. |
| Check external facts | `research` | Verify football data terms, source licenses, and current framework or model integration details against primary sources. |
| Track work as issues | `setup-matt-pocock-skills`, `to-spec`, `to-tickets`, `triage` | Configure an issue tracker before using issue-based workflows. The project currently tracks work in `docs/sprint-plan.md`; tracker-specific setup is not recorded yet. |
| Plan a substantial change | `superpowers:brainstorming`, `superpowers:writing-plans` | Explore the design when the behavior is new, then record ordered work and completion checks before implementation. |
| Shape service and module boundaries | `codebase-design` | Design ingestion, metrics, API, database, and model adapter interfaces before they spread across the codebase. |
| Prototype an uncertain flow | `prototype` | Try a scouting interaction or state model before committing to production structure. |
| Implement a spec or planned slice | `implement-spec`, `implement`, `superpowers:executing-plans` | Follow agreed requirements and work through an implementation plan. Use only the route that matches the artifact we actually have. |
| Build and verify behavior | `tdd`, `superpowers:test-driven-development`, `superpowers:verification-before-completion` | Define observable behavior, add meaningful tests, and run the relevant checks before calling a slice complete. |
| Keep code focused and maintainable | `karpathy-guidelines`, `ponytail:ponytail` | Keep each change small, avoid speculative abstractions, and review whether every changed line serves the feature. |
| Diagnose failures or performance problems | `diagnosing-bugs` | Trace a reproducible failure through ingestion, SQL, API validation, Ollama, or the UI before changing code. |
| Review a completed slice | `code-review`, `superpowers:requesting-code-review` | Check the diff against project conventions and the sprint’s acceptance criteria. |
| Improve the next sprint | `retro` | Record specific workflow improvements after a sprint or meaningful release. |
| Add commit-time checks | `setup-pre-commit` | Configure formatting, type checks, and tests once the repository has stable commands for them. |
| Update guidance for future Codex work | `writing-for-agents` | Change `AGENTS.md` or this guide when an instruction should apply to later tasks. |

## Project checks that skills do not replace

There is no installed skill specialized in football scouting metrics, StatsBomb data interpretation, or LangChain/Ollama evaluation. We cover those areas with project evidence and checks:

- Confirm source terms and available fields in [data guidance](data.md); preserve provenance and define metric units and coverage before ranking players.
- Keep SQL and metric calculations deterministic, as required by [architecture guidance](architecture.md).
- Use the [evaluation workspace](../evals/README.md) for fixed cases covering valid, ambiguous, and unsupported questions, filter accuracy, report factuality, and local latency or memory.
- Research changing framework and model behavior from official documentation; pin versions and record the tested model and configuration.
- Keep local secrets, downloaded data, model weights, and generated evaluation results out of Git. Add deployment security, access control, and recovery checks before exposing the service beyond the development machine.

The project has broad engineering workflows, but no skill can guarantee an impeccable result. The acceptance checks in each sprint, verified data, repeatable tests, and AI evaluations provide the evidence for each deliverable. Add a project-specific `SKILL.md` only after a repeated football-data or evaluation task has a stable recipe that deserves to be reused.
