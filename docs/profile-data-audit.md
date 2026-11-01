# Multi-profile data audit

**Audited:** 2026-11-01

**Scope:** StatsBomb Open Data, men's Premier League 2015/16; competition 2, season 27; pinned source commit `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`.

This audit checks whether the imported sample can support more than the Sprint 2 central-midfielder profile. It uses read-only aggregate queries and stores no player-level output. The repeatable SQL is [`data/audit-profile-coverage.sql`](../data/audit-profile-coverage.sql). Run it from the repository root with `psql -X -v ON_ERROR_STOP=1 -d football_scouting -f data/audit-profile-coverage.sql`.

## Findings

| Coverage check | Observed in this sample |
| --- | ---: |
| Matches / events | 380 / 1,313,773 |
| Events with a player / team / possession | 1,309,036 / 1,313,773 / 1,313,773 |
| Events with a start location | 1,305,696 |
| Passes with a source end location | 368,619 |
| Carries with a source end location | 276,949 |
| Shots with numeric StatsBomb xG | 9,908 / 9,908 |
| Passes flagged as shot assists / goal assists | 6,506 / 669 |
| Passes ending in the project-defined attacking box / completed passes ending there | 28,711 / 9,748 |
| Carries ending in that box | 9,547 |
| Pressures / ball recoveries / interceptions | 115,402 / 40,943 / 8,920 |
| Duel events with subtype Tackle and an outcome | 15,445 |
| Match-possession groups with one recorded possession team | 71,884 / 71,884 |

The attacking-box proxy uses StatsBomb's 120-by-80 pitch coordinates: end x at least 102 and end y from 18 through 62. It is a project-defined location filter. A pass endpoint alone does not mean the pass was completed; the completed count applies the imported no-pass-outcome convention.

Possession IDs are local to a match, so queries must use both match ID and possession ID. Every audited match-possession group had exactly one recorded possession team. However, 60,601 groups include events whose acting team differs across the group. A defensive pressure or tackle can occur while the opponent has the ball. Future possession analysis must retain both the acting team and the source possession team instead of treating all actions in a possession as actions by the possessing side.

Position candidate counts below use the existing 450-minute minimum and 50% role-share threshold. They are pool-size estimates, not final player recommendations. The importer computes actual appearance minutes from position intervals but stores only the dominant position for that appearance. Role share therefore uses minutes from appearances assigned to a selected primary position; it cannot precisely apportion minutes between role changes within one appearance.

## Profile readiness

| Proposed profile | Role IDs in this sample | Estimated candidate pool | Data readiness |
| --- | --- | ---: | --- |
| Ball-progressing central midfielder | 9, 10, 11, 13, 14, 15 | 81 | Implemented in Sprint 2; progressive pass and carry evidence is available. |
| Chance-creating wide/attacking player | 17, 19, 20, 21 | 68 | Supported by shot-assist and goal-assist flags, pass endpoints, and carries; xA is not present. |
| Forward finisher | 22, 23, 24 | 50 | Supported by shots, outcomes, and numeric xG on every shot. The initial contract will not claim a non-penalty split. |
| Ball-winning central midfielder | 9, 10, 11, 13, 14, 15 | 81 | Supported by pressures, recoveries, interceptions, and tackle duels with outcomes. Event counts describe recorded activity, not defensive quality by themselves. |

The final two columns in each future profile should remain role-specific. Do not collapse different roles into a shared scouting score. Use per-90 rates for event volume and show the denominator, role share, historical season, and event definition beside the result.

## Limits

- This is one historical season. It cannot tell a scout how a player performs today or predict a transfer outcome.
- The sample has no 360 or tracking data. It cannot measure off-ball movement, spacing, scanning, or defensive shape from event coordinates alone.
- xG is a source-provided shot estimate. It is not a model trained by this project, and the audit has not established a reliable penalty-shot exclusion rule.
- Shot assists and goal assists are source event flags, not expected assists or a complete measure of creative contribution.
- Pressure and recovery counts depend on match context and team tactics. Do not label a high count as quality without further evidence.
- Keep source data and the local database private under the StatsBomb Open Data terms documented in [`docs/data.md`](data.md).
