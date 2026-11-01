# Scouting profile design: ball-progressing central midfielder

**Status:** Approved and implemented in Sprint 2
**Product slice:** Sprint 2 — deterministic scouting search

## Goal

Let a scout build an explainable shortlist of players who mainly played central midfield in the imported Premier League 2015/16 sample and compare how often they advanced the ball. The shortlist describes that historical sample; it is not a recommendation about current players.

The first profile is one entry in a profile library. The data/query shape should allow later profiles for chance-creating wingers and forwards without introducing a composite score shared by every role.

## Candidate pool

- Treat StatsBomb position IDs `9`, `10`, `11`, `13`, `14`, and `15` as defensive and central midfield roles. This is based on the position names in the StatsBomb specification and the imported lineups.
- Include a player when at least 50% of their season minutes were assigned to those roles, and they played at least 450 minutes. Both thresholds are adjustable in the UI.
- The current importer keeps one primary position per appearance, rather than exact minutes for every position interval. The role-share measure therefore approximates a player's season role; show it in the results and document that limitation.

## Metrics shown separately

Use the player’s season minutes as the per-90 denominator. Do not calculate an overall scouting score.

- **Progressive passes attempted / 90:** pass events whose end x-coordinate is at least 10 units farther toward the attacking goal than their start x-coordinate.
- **Progressive passes completed / 90:** the same action threshold, limited to passes with no StatsBomb pass outcome.
- **Progressive pass completion:** completed progressive passes divided by progressive passes attempted.
- **Progressive carries / 90:** carry events whose end x-coordinate is at least 10 units farther toward the attacking goal than their start x-coordinate.
- **Overall pass completion:** completed passes divided by all pass attempts.
- **Context:** minutes played, central-midfield role share, team(s), appearances, competition, and season.

The role-share control uses the same primary-position approximation as the candidate pool: minutes in appearances whose recorded position is one of the selected midfield roles divided by all season minutes. The importer does not retain exact time in every position interval, so this is a useful filter rather than a precise tactical-role measurement. The interface displays the share and this caveat beside the results.

These are project-defined metrics calculated from source events, not official StatsBomb ratings. StatsBomb's [open-data specification](https://github.com/hudl/open-data/blob/master/doc/StatsBomb%20Open%20Data%20Specification%20v1.1.pdf) defines pass and carry end locations and the relevant position IDs. Hudl's [event-data filter guide](https://support.hudl.com/s/article/filter-event-data-statsbomb?language=en_US) uses x values above 102 for the attacking penalty area, so increasing x is treated as movement toward goal. Coordinates or missing event details that cannot be evaluated are excluded from the numerator, never guessed.

The default order is progressive passes completed per 90. Users can sort by any displayed performance measure, so the ordering rule remains visible and there is no hidden weighting.

## Interface and API behavior

- Return one allowlisted profile (`ball_progressing_midfielder`) with its definition and available metrics.
- Accept a profile key, minimum minutes, minimum central-midfield share, result limit, and an allowlisted sort metric.
- Reject unknown profiles, unsupported sort metrics, and out-of-range filter values with a clear validation error.
- Return a stable result shape with metric values, units, data scope, and definitions so the UI and later report generation use the same evidence.
- Show the historical season prominently. Keep this slice deterministic; no model call or generated ranking is involved.

The React shortlist should show profile and filters, a loading/error/empty state, and a responsive results table with separate metric columns. Every column heading should explain its unit and sort action accessibly.

## Acceptance checks

- At least five fixed scouting scenarios return repeatable ordered results.
- Unit tests verify progress thresholds, completed-pass handling, per-90 calculations, minimum-role-share and minimum-minute filters, validation, and empty results.
- Results include the metric definitions and the 2015/16 scope; no weighted score or claim about present-day players appears.
- The UI build passes; responsive styles stack the search layout and filters, and the wide table remains horizontally scrollable. Keyboard sorting is verified. At a rendered 375px viewport, the page and body remain 375px wide and the table scrolls inside its own results region.

## Delivered implementation

- Deterministic allowlisted FastAPI query and response model; invalid profile, metric, or filter values receive validation errors.
- Focused backend unit and local PostgreSQL integration tests for the metric rules, filters, stable ordering, and empty results.
- React controls and keyboard-operable, separately sortable metric columns with loading, error, and empty states.
- Five saved filter scenarios verified against the imported local database. No generated shortlist or player output is persisted in Git.
