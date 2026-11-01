from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from psycopg.rows import dict_row


PROFILE_KEY = "ball_progressing_midfielder"
PROFILE_NAME = "Ball-progressing central midfielder"
PROFILE_DESCRIPTION = (
    "Players with a substantial central-midfield role, compared by their "
    "progressive passing and carrying in the imported historical sample."
)
COMPETITION_ID = 2
SEASON_ID = 27
COMPETITION_NAME = "Premier League"
SEASON_NAME = "2015/16"
SOURCE_COMMIT = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"
CENTRAL_MIDFIELD_POSITION_IDS = frozenset({9, 10, 11, 13, 14, 15})
PROGRESSIVE_X_THRESHOLD = 10
DEFAULT_MIN_MINUTES = 450
DEFAULT_MIN_CENTRAL_SHARE_PCT = 50.0
DEFAULT_SORT = "progressive_passes_completed_per90"
MAX_RESULT_LIMIT = 100

SortMetric = Literal[
    "progressive_passes_attempted_per90",
    "progressive_passes_completed_per90",
    "progressive_pass_completion_pct",
    "progressive_carries_per90",
    "overall_pass_completion_pct",
]
SortDirection = Literal["asc", "desc"]


class ScoutingFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: Literal["ball_progressing_midfielder"] = PROFILE_KEY
    min_minutes: int = Field(default=DEFAULT_MIN_MINUTES, ge=0, le=25000)
    min_central_share_pct: float = Field(default=DEFAULT_MIN_CENTRAL_SHARE_PCT, ge=0, le=100)
    sort_by: SortMetric = DEFAULT_SORT
    sort_direction: SortDirection = "desc"
    limit: int = Field(default=25, ge=1, le=MAX_RESULT_LIMIT)


@dataclass(frozen=True)
class PlayerSeasonAggregate:
    player_id: int
    player_name: str
    country_name: str | None
    appearances: int
    minutes_played: float
    central_midfield_minutes: float
    team_names: tuple[str, ...]
    passes_attempted: int
    passes_completed: int
    progressive_passes_attempted: int
    progressive_passes_completed: int
    progressive_carries: int


class ScoutingMetricDefinition(BaseModel):
    key: str
    label: str
    unit: str
    definition: str


class ScoutingScope(BaseModel):
    competition_id: int = COMPETITION_ID
    competition_name: str = COMPETITION_NAME
    season_id: int = SEASON_ID
    season_name: str = SEASON_NAME
    source_commit: str = SOURCE_COMMIT
    historical_note: str = "Historical open-data sample; not a current-player recommendation."


class ScoutingPlayer(BaseModel):
    player_id: int
    player_name: str
    country_name: str | None
    team_names: list[str]
    appearances: int
    minutes_played: float
    central_midfield_minutes: float
    central_midfield_share_pct: float | None
    passes_attempted: int
    passes_completed: int
    overall_pass_completion_pct: float | None
    progressive_passes_attempted: int
    progressive_passes_attempted_per90: float | None
    progressive_passes_completed: int
    progressive_passes_completed_per90: float | None
    progressive_pass_completion_pct: float | None
    progressive_carries: int
    progressive_carries_per90: float | None


class ScoutingResponse(BaseModel):
    profile_key: str
    profile_name: str
    profile_description: str
    scope: ScoutingScope
    filters: ScoutingFilters
    metric_definitions: list[ScoutingMetricDefinition]
    result_count: int
    results: list[ScoutingPlayer]


METRIC_DEFINITIONS = [
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
]


SCOUTING_QUERY = """
WITH appearance_totals AS (
    SELECT
        m.competition_id,
        m.season_id,
        p.player_id,
        p.player_name,
        p.country_name,
        count(DISTINCT a.match_id)::integer AS appearances,
        coalesce(sum(a.minutes_played), 0)::double precision AS minutes_played,
        coalesce(
            sum(a.minutes_played) FILTER (WHERE a.position_id = ANY(%s)),
            0
        )::double precision AS central_midfield_minutes,
        coalesce(
            array_agg(DISTINCT t.team_name ORDER BY t.team_name),
            ARRAY[]::text[]
        ) AS team_names
    FROM statsbomb_appearances AS a
    JOIN statsbomb_matches AS m ON m.match_id = a.match_id
    JOIN statsbomb_players AS p ON p.player_id = a.player_id
    JOIN statsbomb_teams AS t ON t.team_id = a.team_id
    WHERE m.competition_id = %s AND m.season_id = %s
    GROUP BY m.competition_id, m.season_id, p.player_id, p.player_name, p.country_name
), event_coordinates AS (
    SELECT
        m.competition_id,
        m.season_id,
        e.event_id,
        e.player_id,
        e.event_type,
        e.location_x,
        e.pass_completed,
        CASE e.event_type
            WHEN 'Pass' THEN e.source_payload #>> '{pass,end_location,0}'
            WHEN 'Carry' THEN e.source_payload #>> '{carry,end_location,0}'
            ELSE NULL
        END AS end_location_x
    FROM statsbomb_events AS e
    JOIN statsbomb_matches AS m ON m.match_id = e.match_id
    WHERE m.competition_id = %s AND m.season_id = %s AND e.player_id IS NOT NULL
), event_totals AS (
    SELECT
        competition_id,
        season_id,
        player_id,
        count(event_id) FILTER (WHERE event_type = 'Pass')::integer AS passes_attempted,
        count(event_id) FILTER (
            WHERE event_type = 'Pass' AND pass_completed IS TRUE
        )::integer AS passes_completed,
        count(event_id) FILTER (
            WHERE event_type = 'Pass'
              AND location_x IS NOT NULL
              AND end_location_x IS NOT NULL
              AND end_location_x::numeric - location_x >= %s
        )::integer AS progressive_passes_attempted,
        count(event_id) FILTER (
            WHERE event_type = 'Pass'
              AND pass_completed IS TRUE
              AND location_x IS NOT NULL
              AND end_location_x IS NOT NULL
              AND end_location_x::numeric - location_x >= %s
        )::integer AS progressive_passes_completed,
        count(event_id) FILTER (
            WHERE event_type = 'Carry'
              AND location_x IS NOT NULL
              AND end_location_x IS NOT NULL
              AND end_location_x::numeric - location_x >= %s
        )::integer AS progressive_carries
    FROM event_coordinates
    GROUP BY competition_id, season_id, player_id
)
SELECT
    a.player_id,
    a.player_name,
    a.country_name,
    a.appearances,
    a.minutes_played,
    a.central_midfield_minutes,
    a.team_names,
    coalesce(e.passes_attempted, 0)::integer AS passes_attempted,
    coalesce(e.passes_completed, 0)::integer AS passes_completed,
    coalesce(e.progressive_passes_attempted, 0)::integer AS progressive_passes_attempted,
    coalesce(e.progressive_passes_completed, 0)::integer AS progressive_passes_completed,
    coalesce(e.progressive_carries, 0)::integer AS progressive_carries
FROM appearance_totals AS a
LEFT JOIN event_totals AS e
    ON e.competition_id = a.competition_id
    AND e.season_id = a.season_id
    AND e.player_id = a.player_id
ORDER BY a.player_name, a.player_id
"""


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
        COMPETITION_ID,
        SEASON_ID,
        COMPETITION_ID,
        SEASON_ID,
        PROGRESSIVE_X_THRESHOLD,
        PROGRESSIVE_X_THRESHOLD,
        PROGRESSIVE_X_THRESHOLD,
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
            central_midfield_minutes=row["central_midfield_minutes"],
            team_names=tuple(row["team_names"] or ()),
            passes_attempted=row["passes_attempted"],
            passes_completed=row["passes_completed"],
            progressive_passes_attempted=row["progressive_passes_attempted"],
            progressive_passes_completed=row["progressive_passes_completed"],
            progressive_carries=row["progressive_carries"],
        )
        for row in rows
    ]


def _per90(count: int, minutes: float) -> float | None:
    if minutes <= 0:
        return None
    return round(count * 90.0 / minutes, 4)


def _percentage(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator * 100.0 / denominator, 4)


def build_scouting_player(aggregate: PlayerSeasonAggregate) -> ScoutingPlayer:
    return ScoutingPlayer(
        player_id=aggregate.player_id,
        player_name=aggregate.player_name,
        country_name=aggregate.country_name,
        team_names=list(aggregate.team_names),
        appearances=aggregate.appearances,
        minutes_played=round(aggregate.minutes_played, 2),
        central_midfield_minutes=round(aggregate.central_midfield_minutes, 2),
        central_midfield_share_pct=_percentage(
            aggregate.central_midfield_minutes, aggregate.minutes_played
        ),
        passes_attempted=aggregate.passes_attempted,
        passes_completed=aggregate.passes_completed,
        overall_pass_completion_pct=_percentage(aggregate.passes_completed, aggregate.passes_attempted),
        progressive_passes_attempted=aggregate.progressive_passes_attempted,
        progressive_passes_attempted_per90=_per90(
            aggregate.progressive_passes_attempted, aggregate.minutes_played
        ),
        progressive_passes_completed=aggregate.progressive_passes_completed,
        progressive_passes_completed_per90=_per90(
            aggregate.progressive_passes_completed, aggregate.minutes_played
        ),
        progressive_pass_completion_pct=_percentage(
            aggregate.progressive_passes_completed, aggregate.progressive_passes_attempted
        ),
        progressive_carries=aggregate.progressive_carries,
        progressive_carries_per90=_per90(aggregate.progressive_carries, aggregate.minutes_played),
    )


def sort_players(players: list[ScoutingPlayer], filters: ScoutingFilters) -> list[ScoutingPlayer]:
    metric_key = filters.sort_by
    named_players = sorted(players, key=lambda player: (player.player_name.casefold(), player.player_id))
    valued = [player for player in named_players if getattr(player, metric_key) is not None]
    missing = [player for player in named_players if getattr(player, metric_key) is None]
    valued.sort(
        key=lambda player: getattr(player, metric_key),
        reverse=filters.sort_direction == "desc",
    )
    return valued + missing


def build_player_results(
    aggregates: list[PlayerSeasonAggregate], filters: ScoutingFilters
) -> list[ScoutingPlayer]:
    candidates: list[ScoutingPlayer] = []
    for aggregate in aggregates:
        if aggregate.minutes_played < filters.min_minutes or aggregate.minutes_played <= 0:
            continue
        central_share_pct = (
            aggregate.central_midfield_minutes * 100.0 / aggregate.minutes_played
        )
        if central_share_pct < filters.min_central_share_pct:
            continue
        player = build_scouting_player(aggregate)
        candidates.append(player)
    return sort_players(candidates, filters)[: filters.limit]


def build_scouting_response(
    aggregates: list[PlayerSeasonAggregate], filters: ScoutingFilters
) -> ScoutingResponse:
    results = build_player_results(aggregates, filters)
    return ScoutingResponse(
        profile_key=PROFILE_KEY,
        profile_name=PROFILE_NAME,
        profile_description=PROFILE_DESCRIPTION,
        scope=ScoutingScope(),
        filters=filters,
        metric_definitions=METRIC_DEFINITIONS,
        result_count=len(results),
        results=results,
    )
