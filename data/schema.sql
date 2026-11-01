CREATE TABLE IF NOT EXISTS statsbomb_competitions (
    competition_id integer NOT NULL,
    season_id integer NOT NULL,
    competition_name text NOT NULL,
    season_name text NOT NULL,
    source_repository text NOT NULL,
    source_commit text NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (competition_id, season_id)
);

CREATE TABLE IF NOT EXISTS statsbomb_teams (
    team_id integer PRIMARY KEY,
    team_name text NOT NULL
);

CREATE TABLE IF NOT EXISTS statsbomb_players (
    player_id integer PRIMARY KEY,
    player_name text NOT NULL,
    player_nickname text,
    country_name text
);

CREATE TABLE IF NOT EXISTS statsbomb_matches (
    match_id bigint PRIMARY KEY,
    competition_id integer NOT NULL,
    season_id integer NOT NULL,
    match_date date NOT NULL,
    match_week integer,
    home_team_id integer NOT NULL REFERENCES statsbomb_teams(team_id),
    away_team_id integer NOT NULL REFERENCES statsbomb_teams(team_id),
    home_score integer,
    away_score integer,
    source_commit text NOT NULL,
    FOREIGN KEY (competition_id, season_id)
        REFERENCES statsbomb_competitions(competition_id, season_id),
    CHECK (home_team_id <> away_team_id)
);

CREATE TABLE IF NOT EXISTS statsbomb_appearances (
    match_id bigint NOT NULL REFERENCES statsbomb_matches(match_id) ON DELETE CASCADE,
    player_id integer NOT NULL REFERENCES statsbomb_players(player_id),
    team_id integer NOT NULL REFERENCES statsbomb_teams(team_id),
    started boolean NOT NULL,
    position_id integer,
    position_name text,
    minutes_played numeric(8, 2) NOT NULL CHECK (minutes_played >= 0),
    PRIMARY KEY (match_id, player_id)
);

CREATE TABLE IF NOT EXISTS statsbomb_events (
    match_id bigint NOT NULL REFERENCES statsbomb_matches(match_id) ON DELETE CASCADE,
    event_id uuid NOT NULL,
    event_index integer NOT NULL,
    period smallint NOT NULL,
    minute integer NOT NULL,
    second smallint NOT NULL,
    event_type text NOT NULL,
    possession integer,
    team_id integer REFERENCES statsbomb_teams(team_id),
    player_id integer REFERENCES statsbomb_players(player_id),
    location_x numeric(6, 2),
    location_y numeric(6, 2),
    pass_outcome text,
    pass_completed boolean,
    shot_outcome text,
    source_payload jsonb NOT NULL,
    PRIMARY KEY (match_id, event_id),
    UNIQUE (match_id, event_index)
);

CREATE INDEX IF NOT EXISTS statsbomb_events_player_type_idx
    ON statsbomb_events (player_id, event_type, match_id);

CREATE TABLE IF NOT EXISTS statsbomb_import_files (
    source_commit text NOT NULL,
    source_path text NOT NULL,
    source_url text NOT NULL,
    sha256 char(64) NOT NULL,
    byte_size bigint NOT NULL CHECK (byte_size >= 0),
    retrieved_at timestamptz NOT NULL,
    PRIMARY KEY (source_commit, source_path)
);

CREATE OR REPLACE VIEW statsbomb_player_season_metrics AS
WITH appearance_totals AS (
    SELECT
        m.competition_id,
        m.season_id,
        p.player_id,
        p.player_name,
        p.player_nickname,
        p.country_name,
        count(DISTINCT a.match_id)::integer AS appearances,
        coalesce(sum(a.minutes_played), 0)::numeric(10, 2) AS minutes_played
    FROM statsbomb_appearances AS a
    JOIN statsbomb_matches AS m ON m.match_id = a.match_id
    JOIN statsbomb_players AS p ON p.player_id = a.player_id
    GROUP BY
        m.competition_id,
        m.season_id,
        p.player_id,
        p.player_name,
        p.player_nickname,
        p.country_name
), event_totals AS (
    SELECT
        m.competition_id,
        m.season_id,
        e.player_id,
        count(e.event_id) FILTER (WHERE e.event_type = 'Pass')::integer AS passes_attempted,
        count(e.event_id) FILTER (
            WHERE e.event_type = 'Pass' AND e.pass_completed IS TRUE
        )::integer AS passes_completed,
        count(e.event_id) FILTER (WHERE e.event_type = 'Shot')::integer AS shots,
        count(e.event_id) FILTER (
            WHERE e.event_type = 'Shot' AND e.shot_outcome = 'Goal'
        )::integer AS goals
    FROM statsbomb_events AS e
    JOIN statsbomb_matches AS m ON m.match_id = e.match_id
    WHERE e.player_id IS NOT NULL
    GROUP BY
        m.competition_id,
        m.season_id,
        e.player_id
)
SELECT
    a.competition_id,
    a.season_id,
    a.player_id,
    a.player_name,
    a.player_nickname,
    a.country_name,
    a.appearances,
    a.minutes_played,
    coalesce(e.passes_attempted, 0) AS passes_attempted,
    coalesce(e.passes_completed, 0) AS passes_completed,
    coalesce(e.shots, 0) AS shots,
    coalesce(e.goals, 0) AS goals,
    round(coalesce(e.passes_completed, 0) * 90.0 / nullif(a.minutes_played, 0), 2)
        AS passes_completed_per90,
    round(coalesce(e.shots, 0) * 90.0 / nullif(a.minutes_played, 0), 2) AS shots_per90,
    round(coalesce(e.goals, 0) * 90.0 / nullif(a.minutes_played, 0), 2) AS goals_per90
FROM appearance_totals AS a
LEFT JOIN event_totals AS e
    ON e.competition_id = a.competition_id
    AND e.season_id = a.season_id
    AND e.player_id = a.player_id;
