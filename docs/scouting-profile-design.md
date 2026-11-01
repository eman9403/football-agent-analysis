# Multi-profile scouting design

**Status:** Sprint 3 discovery complete; additional profiles are specified but not implemented.

**Scope:** The pinned StatsBomb Premier League 2015/16 sample only. See the [data audit](profile-data-audit.md) for observed coverage.

## Product goal

Give a scout several role-specific shortlists, each with its own candidate pool and visible evidence. A profile is a lens for a particular job on the pitch, not a universal ranking of players. The existing ball-progressing midfielder remains the first implemented profile.

All profiles are descriptive views of this released historical sample. They are not current-player recommendations, predictions, or official StatsBomb ratings. Do not calculate one weighted score across roles.

## Shared candidate rules

- Default minimum playing time: 450 season minutes.
- Default role share: at least 50% of season minutes in the profile's selected primary-position appearances.
- Show minutes and role share in every result. Keep both thresholds adjustable and validate them in FastAPI.
- The importer calculates minutes from position intervals but stores the dominant position for each appearance. Role share is therefore an approximation and can hide role changes within an appearance.
- Use season minutes for per-90 denominators. Keep null values when a denominator is zero; never fill missing evidence with a model guess.
- Put the competition, season, source revision, metric units, and caveats in every API response.

## Profile contracts

The profile keys and role pools below are proposals for Sprint 3 implementation. Position names are the labels observed in the imported lineups. Pool sizes are estimates at the shared thresholds, not player recommendations.

### Ball-progressing central midfielder

**Role pool:** IDs 9, 10, 11, 13, 14, and 15: defensive and central midfield positions.

**Estimated pool:** 81 players.

**Status:** Implemented in Sprint 2.

- Progressive passes attempted and completed per 90. A pass is progressive when its known end x is at least 10 coordinate units beyond its start x.
- Progressive pass completion: completed progressive passes divided by progressive attempts.
- Progressive carries per 90, using the same known-coordinate and 10-unit threshold.
- Overall pass completion as context.

Passes are completed when the source pass has no outcome. End coordinates come from the event payload. Do not infer missing locations or role labels.

### Chance-creating wide or attacking player

**Key:** `chance_creating_attacker`

**Role pool:** IDs 17 (Right Wing), 19 (Center Attacking Midfield), 20 (Left Attacking Midfield), and 21 (Left Wing).

**Estimated pool:** 68 players.

- Passes flagged as shot assists per 90.
- Passes flagged as goal assists per 90.
- Completed passes ending in the project-defined attacking box per 90: end x at least 102 and end y between 18 and 62.
- Progressive carries per 90 as a separate ball-carrying measure.

There is no xA field in this sample. Do not call shot assists expected assists or treat a goal-assist count as a complete creativity measure. Keep shot assists and goal assists separate, and show their event definitions.

### Forward finisher

**Key:** `forward_finisher`

**Role pool:** IDs 22 (Right Center Forward), 23 (Center Forward), and 24 (Left Center Forward).

**Estimated pool:** 50 players.

- Shots per 90.
- Source-provided xG per 90, summing the numeric StatsBomb xG attached to a player's shots.
- Goals per 90.
- xG per shot, unavailable when the player has no shots.

All 9,908 shots in the audited sample have numeric source xG. The initial profile includes the source's shot mix; it must not label the metric non-penalty xG unless a penalty exclusion field is separately verified. Goals and xG are outcomes in this season, not a projection of future finishing.

### Ball-winning central midfielder

**Key:** `ball_winning_midfielder`

**Role pool:** IDs 9, 10, 11, 13, 14, and 15: the same broad central-midfield pool as the progressor profile.

**Estimated pool:** 81 players.

- Pressure events per 90.
- Ball Recovery events per 90; label these as recorded recoveries, not successful recoveries.
- Interceptions per 90, plus the share whose recorded outcome is `Won`, `Success In Play`, or `Success Out`.
- Tackle duels per 90, where a Duel event has subtype Tackle, plus the share with those same positive coded outcomes.

Keep raw event volume and coded outcomes distinct. Pressure volume alone is not a measure of pressure success. The source's recovery-failure flag is present on only some recovery events, so do not treat a missing flag as verified success.

## API and interface behavior for Sprint 3

- Return an allowlisted profile library with a distinct name, description, role pool, filters, metrics, units, definitions, and historical scope for each profile.
- Reject unknown profiles, unsupported metrics, and invalid filter ranges.
- Let a scout switch profiles without carrying incompatible sort fields or filters across them.
- Keep each metric independently sortable; use a visible profile-specific default metric. There is no cross-profile or shared composite score.
- Include the source season and evidence notes beside results. Show a clear empty state and keep the deterministic shortlist usable when any later local model is unavailable.

## Acceptance checks

- The four profile contracts above are implemented with typed, allowlisted filters and deterministic Postgres queries.
- Each metric has unit tests for numerator, denominator, missing evidence, and outcomes; integration tests compare aggregates with source JSON for representative event types.
- Saved deterministic scenarios cover all profiles, role/minute thresholds, sorting, empty results, and repeatability.
- The UI exposes profile-specific metric labels and definitions, makes the historical scope visible, and never shows one aggregate score across roles.
- No current-day, causal, off-ball, or predictive claim is made from this sample.
