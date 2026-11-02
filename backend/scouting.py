from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict, Field, model_validator
from psycopg.rows import dict_row


COMPETITION_ID = 2
SEASON_ID = 27
COMPETITION_NAME = "Premier League"
SEASON_NAME = "2015/16"
SOURCE_COMMIT = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"
CENTRAL_MIDFIELD_POSITION_IDS = frozenset({9, 10, 11, 13, 14, 15})
CHANCE_CREATOR_POSITION_IDS = frozenset({17, 19, 20, 21})
FORWARD_POSITION_IDS = frozenset({22, 23, 24})
PROGRESSIVE_X_THRESHOLD = 10
DEFAULT_MIN_MINUTES = 450
DEFAULT_MIN_ROLE_SHARE_PCT = 50.0
MAX_RESULT_LIMIT = 100
POSITIVE_OUTCOMES = ("Won", "Success In Play", "Success Out")


class ScoutingMetricDefinition(BaseModel):
    key: str
    label: str
    unit: str
    definition: str


class ScoutingProfileSummary(BaseModel):
    profile_key: str
    profile_name: str
    profile_description: str
    role_group: str
    role_label: str
    position_ids: list[int]
    default_sort: str
    metric_definitions: list[ScoutingMetricDefinition]


class ScoutingScope(BaseModel):
    competition_id: int = COMPETITION_ID
    competition_name: str = COMPETITION_NAME
    season_id: int = SEASON_ID
    season_name: str = SEASON_NAME
    source_commit: str = SOURCE_COMMIT
    historical_note: str = "Historical open-data sample; not a current-player recommendation."


@dataclass(frozen=True)
class ProfileSpec:
    key: str
    name: str
    description: str
    role_group: str
    role_label: str
    position_ids: frozenset[int]
    default_sort: str
    metric_definitions: tuple[ScoutingMetricDefinition, ...]


PROFILE_SPECS = {
    "ball_progressing_midfielder": ProfileSpec(
        key="ball_progressing_midfielder",
        name="Ball-progressing central midfielder",
        description=(
            "Compare progressive passing and carrying among players used mainly "
            "in central midfield in the historical sample."
        ),
        role_group="central_midfield",
        role_label="Central-midfield",
        position_ids=CENTRAL_MIDFIELD_POSITION_IDS,
        default_sort="progressive_passes_completed_per90",
        metric_definitions=(
            ScoutingMetricDefinition(
                key="progressive_passes_attempted_per90",
                label="Progressive passes attempted / 90",
                unit="passes per 90 minutes",
                definition="Passes ending at least 10 x units farther toward goal, divided by season minutes and multiplied by 90.",
            ),
            ScoutingMetricDefinition(
                key="progressive_passes_completed_per90",
                label="Progressive passes completed / 90",
                unit="completed passes per 90 minutes",
                definition="Progressive passes with no StatsBomb pass outcome, divided by season minutes and multiplied by 90.",
            ),
            ScoutingMetricDefinition(
                key="progressive_pass_completion_pct",
                label="Progressive pass completion",
                unit="percent",
                definition="Completed progressive passes divided by progressive pass attempts; unavailable when there are no attempts.",
            ),
            ScoutingMetricDefinition(
                key="progressive_carries_per90",
                label="Progressive carries / 90",
                unit="carries per 90 minutes",
                definition="Carries ending at least 10 x units farther toward goal, divided by season minutes and multiplied by 90.",
            ),
            ScoutingMetricDefinition(
                key="overall_pass_completion_pct",
                label="Overall pass completion",
                unit="percent",
                definition="Completed passes divided by pass attempts; unavailable when there are no attempts.",
            ),
        ),
    ),
    "chance_creating_attacker": ProfileSpec(
        key="chance_creating_attacker",
        name="Chance-creating wide or attacking player",
        description=(
            "Compare shot creation, goal assists, box passing, and progressive "
            "carrying among wide and attacking midfield roles."
        ),
        role_group="chance_creator",
        role_label="Wide/attacking",
        position_ids=CHANCE_CREATOR_POSITION_IDS,
        default_sort="shot_assists_per90",
        metric_definitions=(
            ScoutingMetricDefinition(
                key="shot_assists_per90",
                label="Shot assists / 90",
                unit="shot assists per 90 minutes",
                definition="Passes flagged by StatsBomb as shot assists, divided by season minutes and multiplied by 90; this is not xA.",
            ),
            ScoutingMetricDefinition(
                key="goal_assists_per90",
                label="Goal assists / 90",
                unit="goal assists per 90 minutes",
                definition="Passes flagged by StatsBomb as goal assists, divided by season minutes and multiplied by 90.",
            ),
            ScoutingMetricDefinition(
                key="completed_box_passes_per90",
                label="Completed passes ending in the box / 90",
                unit="passes per 90 minutes",
                definition="Completed passes ending at x >= 102 and 18 <= y <= 62, divided by season minutes and multiplied by 90.",
            ),
            ScoutingMetricDefinition(
                key="progressive_carries_per90",
                label="Progressive carries / 90",
                unit="carries per 90 minutes",
                definition="Carries ending at least 10 x units farther toward goal, divided by season minutes and multiplied by 90.",
            ),
        ),
    ),
    "forward_finisher": ProfileSpec(
        key="forward_finisher",
        name="Forward finisher",
        description=(
            "Compare shot volume, source xG, and recorded goals among center-forward roles."
        ),
        role_group="forward",
        role_label="Center-forward",
        position_ids=FORWARD_POSITION_IDS,
        default_sort="expected_goals_per90",
        metric_definitions=(
            ScoutingMetricDefinition(
                key="shots_per90",
                label="Shots / 90",
                unit="shots per 90 minutes",
                definition="Recorded shots, divided by season minutes and multiplied by 90.",
            ),
            ScoutingMetricDefinition(
                key="expected_goals_per90",
                label="Expected goals / 90",
                unit="xG per 90 minutes",
                definition="Sum of StatsBomb's source xG for the player's shots, divided by season minutes and multiplied by 90.",
            ),
            ScoutingMetricDefinition(
                key="goals_per90",
                label="Goals / 90",
                unit="goals per 90 minutes",
                definition="Recorded goals, divided by season minutes and multiplied by 90.",
            ),
            ScoutingMetricDefinition(
                key="expected_goals_per_shot",
                label="Expected goals per shot",
                unit="xG per shot",
                definition="Sum of source xG divided by shot count; includes the source's shot mix and is unavailable without shots.",
            ),
        ),
    ),
    "ball_winning_midfielder": ProfileSpec(
        key="ball_winning_midfielder",
        name="Ball-winning central midfielder",
        description=(
            "Compare recorded pressure, recovery, interception, and tackle activity "
            "among central midfield roles."
        ),
        role_group="central_midfield",
        role_label="Central-midfield",
        position_ids=CENTRAL_MIDFIELD_POSITION_IDS,
        default_sort="interceptions_per90",
        metric_definitions=(
            ScoutingMetricDefinition(
                key="pressures_per90",
                label="Pressures / 90",
                unit="pressures per 90 minutes",
                definition="Recorded pressure events, divided by season minutes and multiplied by 90; volume is not pressure success.",
            ),
            ScoutingMetricDefinition(
                key="ball_recoveries_per90",
                label="Ball recoveries / 90",
                unit="recoveries per 90 minutes",
                definition="Recorded Ball Recovery events, divided by season minutes and multiplied by 90; not a success rate.",
            ),
            ScoutingMetricDefinition(
                key="interceptions_per90",
                label="Interceptions / 90",
                unit="interceptions per 90 minutes",
                definition="Recorded Interception events, divided by season minutes and multiplied by 90.",
            ),
            ScoutingMetricDefinition(
                key="interception_positive_outcome_pct",
                label="Interceptions with positive coded outcome",
                unit="percent",
                definition="Interceptions with outcome Won, Success In Play, or Success Out divided by all recorded interceptions.",
            ),
            ScoutingMetricDefinition(
                key="tackle_duels_per90",
                label="Tackle duels / 90",
                unit="tackle duels per 90 minutes",
                definition="Duel events with subtype Tackle, divided by season minutes and multiplied by 90.",
            ),
            ScoutingMetricDefinition(
                key="tackle_positive_outcome_pct",
                label="Tackle duels with positive coded outcome",
                unit="percent",
                definition="Tackle duels with outcome Won, Success In Play, or Success Out divided by all tackle duels.",
            ),
        ),
    ),
}


PROFILE_ORDER = (
    "ball_progressing_midfielder",
    "chance_creating_attacker",
    "forward_finisher",
    "ball_winning_midfielder",
)


class ScoutingFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str = "ball_progressing_midfielder"
    min_minutes: int = Field(default=DEFAULT_MIN_MINUTES, ge=0, le=25000)
    min_role_share_pct: float = Field(default=DEFAULT_MIN_ROLE_SHARE_PCT, ge=0, le=100)
    sort_by: str | None = None
    sort_direction: str = Field(default="desc", pattern="^(asc|desc)$")
    limit: int = Field(default=25, ge=1, le=MAX_RESULT_LIMIT)

    @model_validator(mode="after")
    def validate_profile_metric(self):
        profile = PROFILE_SPECS.get(self.profile)
        if profile is None:
            raise ValueError(f"Unknown scouting profile: {self.profile}")
        if self.sort_by is None:
            self.sort_by = profile.default_sort
        elif self.sort_by not in {metric.key for metric in profile.metric_definitions}:
            raise ValueError(
                f"Sort metric {self.sort_by!r} is not available for profile {self.profile!r}"
            )
        return self


@dataclass(frozen=True)
class PlayerSeasonAggregate:
    player_id: int
    player_name: str
    country_name: str | None
    appearances: int
    minutes_played: float
    team_names: tuple[str, ...]
    role_minutes: dict[str, float]
    metric_counts: dict[str, float]


class ScoutingPlayer(BaseModel):
    player_id: int
    player_name: str
    country_name: str | None
    team_names: list[str]
    appearances: int
    minutes_played: float
    role_minutes: float
    role_share_pct: float | None
    metrics: dict[str, float | None]


class ScoutingResponse(BaseModel):
    profile_key: str
    profile_name: str
    profile_description: str
    role_label: str
    scope: ScoutingScope
    filters: ScoutingFilters
    metric_definitions: list[ScoutingMetricDefinition]
    result_count: int
    results: list[ScoutingPlayer]


METRIC_COUNT_KEYS = (
    "passes_attempted",
    "passes_completed",
    "progressive_passes_attempted",
    "progressive_passes_completed",
    "progressive_carries",
    "shot_assists",
    "goal_assists",
    "completed_box_passes",
    "shots",
    "goals",
    "expected_goals",
    "pressures",
    "ball_recoveries",
    "interceptions",
    "positive_interceptions",
    "tackle_duels",
    "positive_tackle_duels",
)


SCOUTING_QUERY = """
WITH appearance_totals AS (
    SELECT
        p.player_id,
        p.player_name,
        p.country_name,
        count(DISTINCT a.match_id)::integer AS appearances,
        coalesce(sum(a.minutes_played), 0)::double precision AS minutes_played,
        coalesce(sum(a.minutes_played) FILTER (
            WHERE a.position_id = ANY(%s)
        ), 0)::double precision AS central_midfield_minutes,
        coalesce(sum(a.minutes_played) FILTER (
            WHERE a.position_id = ANY(%s)
        ), 0)::double precision AS chance_creator_minutes,
        coalesce(sum(a.minutes_played) FILTER (
            WHERE a.position_id = ANY(%s)
        ), 0)::double precision AS forward_minutes,
        coalesce(
            array_agg(DISTINCT t.team_name ORDER BY t.team_name),
            ARRAY[]::text[]
        ) AS team_names
    FROM statsbomb_appearances AS a
    JOIN statsbomb_matches AS m ON m.match_id = a.match_id
    JOIN statsbomb_players AS p ON p.player_id = a.player_id
    JOIN statsbomb_teams AS t ON t.team_id = a.team_id
    WHERE m.competition_id = %s AND m.season_id = %s
    GROUP BY p.player_id, p.player_name, p.country_name
), event_coordinates AS (
    SELECT
        e.event_id,
        e.player_id,
        e.event_type,
        e.location_x,
        e.pass_completed,
        e.shot_outcome,
        e.source_payload,
        CASE
            WHEN jsonb_typeof(e.source_payload #> '{pass,end_location,0}') = 'number'
            THEN (e.source_payload #>> '{pass,end_location,0}')::numeric
        END AS pass_end_x,
        CASE
            WHEN jsonb_typeof(e.source_payload #> '{pass,end_location,1}') = 'number'
            THEN (e.source_payload #>> '{pass,end_location,1}')::numeric
        END AS pass_end_y,
        CASE
            WHEN jsonb_typeof(e.source_payload #> '{carry,end_location,0}') = 'number'
            THEN (e.source_payload #>> '{carry,end_location,0}')::numeric
        END AS carry_end_x
    FROM statsbomb_events AS e
    JOIN statsbomb_matches AS m ON m.match_id = e.match_id
    WHERE m.competition_id = %s AND m.season_id = %s AND e.player_id IS NOT NULL
), event_totals AS (
    SELECT
        player_id,
        count(event_id) FILTER (WHERE event_type = 'Pass')::integer AS passes_attempted,
        count(event_id) FILTER (
            WHERE event_type = 'Pass' AND pass_completed IS TRUE
        )::integer AS passes_completed,
        count(event_id) FILTER (
            WHERE event_type = 'Pass'
              AND location_x IS NOT NULL AND pass_end_x IS NOT NULL
              AND pass_end_x - location_x >= %s
        )::integer AS progressive_passes_attempted,
        count(event_id) FILTER (
            WHERE event_type = 'Pass' AND pass_completed IS TRUE
              AND location_x IS NOT NULL AND pass_end_x IS NOT NULL
              AND pass_end_x - location_x >= %s
        )::integer AS progressive_passes_completed,
        count(event_id) FILTER (
            WHERE event_type = 'Carry'
              AND location_x IS NOT NULL AND carry_end_x IS NOT NULL
              AND carry_end_x - location_x >= %s
        )::integer AS progressive_carries,
        count(event_id) FILTER (
            WHERE event_type = 'Pass'
              AND source_payload #>> '{pass,shot_assist}' = 'true'
        )::integer AS shot_assists,
        count(event_id) FILTER (
            WHERE event_type = 'Pass'
              AND source_payload #>> '{pass,goal_assist}' = 'true'
        )::integer AS goal_assists,
        count(event_id) FILTER (
            WHERE event_type = 'Pass' AND pass_completed IS TRUE
              AND pass_end_x >= 102 AND pass_end_y BETWEEN 18 AND 62
        )::integer AS completed_box_passes,
        count(event_id) FILTER (WHERE event_type = 'Shot')::integer AS shots,
        count(event_id) FILTER (
            WHERE event_type = 'Shot' AND shot_outcome = 'Goal'
        )::integer AS goals,
        coalesce(sum(
            CASE
                WHEN event_type = 'Shot'
                  AND jsonb_typeof(source_payload #> '{shot,statsbomb_xg}') = 'number'
                THEN (source_payload #>> '{shot,statsbomb_xg}')::double precision
                ELSE 0
            END
        ), 0)::double precision AS expected_goals,
        count(event_id) FILTER (WHERE event_type = 'Pressure')::integer AS pressures,
        count(event_id) FILTER (WHERE event_type = 'Ball Recovery')::integer AS ball_recoveries,
        count(event_id) FILTER (WHERE event_type = 'Interception')::integer AS interceptions,
        count(event_id) FILTER (
            WHERE event_type = 'Interception'
              AND source_payload #>> '{interception,outcome,name}' = ANY(%s)
        )::integer AS positive_interceptions,
        count(event_id) FILTER (
            WHERE event_type = 'Duel'
              AND source_payload #>> '{duel,type,name}' = 'Tackle'
        )::integer AS tackle_duels,
        count(event_id) FILTER (
            WHERE event_type = 'Duel'
              AND source_payload #>> '{duel,type,name}' = 'Tackle'
              AND source_payload #>> '{duel,outcome,name}' = ANY(%s)
        )::integer AS positive_tackle_duels
    FROM event_coordinates
    GROUP BY player_id
)
SELECT
    a.player_id,
    a.player_name,
    a.country_name,
    a.appearances,
    a.minutes_played,
    a.central_midfield_minutes,
    a.chance_creator_minutes,
    a.forward_minutes,
    a.team_names,
    coalesce(e.passes_attempted, 0)::integer AS passes_attempted,
    coalesce(e.passes_completed, 0)::integer AS passes_completed,
    coalesce(e.progressive_passes_attempted, 0)::integer AS progressive_passes_attempted,
    coalesce(e.progressive_passes_completed, 0)::integer AS progressive_passes_completed,
    coalesce(e.progressive_carries, 0)::integer AS progressive_carries,
    coalesce(e.shot_assists, 0)::integer AS shot_assists,
    coalesce(e.goal_assists, 0)::integer AS goal_assists,
    coalesce(e.completed_box_passes, 0)::integer AS completed_box_passes,
    coalesce(e.shots, 0)::integer AS shots,
    coalesce(e.goals, 0)::integer AS goals,
    coalesce(e.expected_goals, 0)::double precision AS expected_goals,
    coalesce(e.pressures, 0)::integer AS pressures,
    coalesce(e.ball_recoveries, 0)::integer AS ball_recoveries,
    coalesce(e.interceptions, 0)::integer AS interceptions,
    coalesce(e.positive_interceptions, 0)::integer AS positive_interceptions,
    coalesce(e.tackle_duels, 0)::integer AS tackle_duels,
    coalesce(e.positive_tackle_duels, 0)::integer AS positive_tackle_duels
FROM appearance_totals AS a
LEFT JOIN event_totals AS e ON e.player_id = a.player_id
ORDER BY a.player_name, a.player_id
"""


def list_scouting_profiles() -> list[ScoutingProfileSummary]:
    return [
        ScoutingProfileSummary(
            profile_key=spec.key,
            profile_name=spec.name,
            profile_description=spec.description,
            role_group=spec.role_group,
            role_label=spec.role_label,
            position_ids=sorted(spec.position_ids),
            default_sort=spec.default_sort,
            metric_definitions=list(spec.metric_definitions),
        )
        for spec in (PROFILE_SPECS[key] for key in PROFILE_ORDER)
    ]


def is_progressive(start_x: float | None, end_x: float | None) -> bool:
    """Return whether a known end point advances at least ten x units."""
    return (
        start_x is not None
        and end_x is not None
        and float(end_x) - float(start_x) >= PROGRESSIVE_X_THRESHOLD
    )


def fetch_player_aggregates(connection) -> list[PlayerSeasonAggregate]:
    parameters = (
        list(CENTRAL_MIDFIELD_POSITION_IDS),
        list(CHANCE_CREATOR_POSITION_IDS),
        list(FORWARD_POSITION_IDS),
        COMPETITION_ID,
        SEASON_ID,
        COMPETITION_ID,
        SEASON_ID,
        PROGRESSIVE_X_THRESHOLD,
        PROGRESSIVE_X_THRESHOLD,
        PROGRESSIVE_X_THRESHOLD,
        list(POSITIVE_OUTCOMES),
        list(POSITIVE_OUTCOMES),
    )
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(SCOUTING_QUERY, parameters)
        rows = cursor.fetchall()
    return [
        PlayerSeasonAggregate(
            player_id=row["player_id"],
            player_name=row["player_name"],
            country_name=row["country_name"],
            appearances=row["appearances"],
            minutes_played=row["minutes_played"],
            team_names=tuple(row["team_names"] or ()),
            role_minutes={
                "central_midfield": row["central_midfield_minutes"],
                "chance_creator": row["chance_creator_minutes"],
                "forward": row["forward_minutes"],
            },
            metric_counts={key: row[key] for key in METRIC_COUNT_KEYS},
        )
        for row in rows
    ]


def _per90(count: float, minutes: float) -> float | None:
    if minutes <= 0:
        return None
    return round(count * 90.0 / minutes, 4)


def _percentage(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator * 100.0 / denominator, 4)


def _ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _metric_values(aggregate: PlayerSeasonAggregate) -> dict[str, float | None]:
    counts = aggregate.metric_counts
    minutes = aggregate.minutes_played
    return {
        "progressive_passes_attempted_per90": _per90(
            counts["progressive_passes_attempted"], minutes
        ),
        "progressive_passes_completed_per90": _per90(
            counts["progressive_passes_completed"], minutes
        ),
        "progressive_pass_completion_pct": _percentage(
            counts["progressive_passes_completed"], counts["progressive_passes_attempted"]
        ),
        "progressive_carries_per90": _per90(counts["progressive_carries"], minutes),
        "overall_pass_completion_pct": _percentage(
            counts["passes_completed"], counts["passes_attempted"]
        ),
        "shot_assists_per90": _per90(counts["shot_assists"], minutes),
        "goal_assists_per90": _per90(counts["goal_assists"], minutes),
        "completed_box_passes_per90": _per90(counts["completed_box_passes"], minutes),
        "shots_per90": _per90(counts["shots"], minutes),
        "expected_goals_per90": _per90(counts["expected_goals"], minutes),
        "goals_per90": _per90(counts["goals"], minutes),
        "expected_goals_per_shot": _ratio(counts["expected_goals"], counts["shots"]),
        "pressures_per90": _per90(counts["pressures"], minutes),
        "ball_recoveries_per90": _per90(counts["ball_recoveries"], minutes),
        "interceptions_per90": _per90(counts["interceptions"], minutes),
        "interception_positive_outcome_pct": _percentage(
            counts["positive_interceptions"], counts["interceptions"]
        ),
        "tackle_duels_per90": _per90(counts["tackle_duels"], minutes),
        "tackle_positive_outcome_pct": _percentage(
            counts["positive_tackle_duels"], counts["tackle_duels"]
        ),
    }


def _build_scouting_player(
    aggregate: PlayerSeasonAggregate,
    profile: ProfileSpec,
) -> ScoutingPlayer:
    role_minutes = aggregate.role_minutes.get(profile.role_group, 0.0)
    metric_values = _metric_values(aggregate)
    return ScoutingPlayer(
        player_id=aggregate.player_id,
        player_name=aggregate.player_name,
        country_name=aggregate.country_name,
        team_names=list(aggregate.team_names),
        appearances=aggregate.appearances,
        minutes_played=round(aggregate.minutes_played, 2),
        role_minutes=round(role_minutes, 2),
        role_share_pct=_percentage(role_minutes, aggregate.minutes_played),
        metrics={metric.key: metric_values[metric.key] for metric in profile.metric_definitions},
    )


def sort_players(
    players: list[ScoutingPlayer], filters: ScoutingFilters
) -> list[ScoutingPlayer]:
    metric_key = filters.sort_by
    named_players = sorted(
        players,
        key=lambda player: (player.player_name.casefold(), player.player_id),
    )
    valued = [player for player in named_players if player.metrics[metric_key] is not None]
    missing = [player for player in named_players if player.metrics[metric_key] is None]
    valued.sort(
        key=lambda player: player.metrics[metric_key],
        reverse=filters.sort_direction == "desc",
    )
    return valued + missing


def build_eligible_player_pool(
    aggregates: list[PlayerSeasonAggregate],
    filters: ScoutingFilters,
) -> list[ScoutingPlayer]:
    profile = PROFILE_SPECS[filters.profile]
    candidates: list[ScoutingPlayer] = []
    for aggregate in aggregates:
        if aggregate.minutes_played < filters.min_minutes or aggregate.minutes_played <= 0:
            continue
        role_minutes = aggregate.role_minutes.get(profile.role_group, 0.0)
        role_share_pct = role_minutes * 100.0 / aggregate.minutes_played
        if role_share_pct < filters.min_role_share_pct:
            continue
        candidates.append(_build_scouting_player(aggregate, profile))
    return candidates


def build_player_results(
    aggregates: list[PlayerSeasonAggregate],
    filters: ScoutingFilters,
) -> list[ScoutingPlayer]:
    return sort_players(build_eligible_player_pool(aggregates, filters), filters)[: filters.limit]


def build_scouting_response(
    aggregates: list[PlayerSeasonAggregate],
    filters: ScoutingFilters,
) -> ScoutingResponse:
    profile = PROFILE_SPECS[filters.profile]
    results = build_player_results(aggregates, filters)
    return ScoutingResponse(
        profile_key=profile.key,
        profile_name=profile.name,
        profile_description=profile.description,
        role_label=profile.role_label,
        scope=ScoutingScope(),
        filters=filters,
        metric_definitions=list(profile.metric_definitions),
        result_count=len(results),
        results=results,
    )
