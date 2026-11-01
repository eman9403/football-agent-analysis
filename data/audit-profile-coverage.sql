-- Read-only aggregate audit for the pinned EPL 2015/16 scouting sample.
-- Prints counts and coverage only; it does not return player-level or raw event rows.
BEGIN TRANSACTION READ ONLY;

WITH sample_events AS (
    SELECT e.*
    FROM statsbomb_events AS e
    JOIN statsbomb_matches AS m ON m.match_id = e.match_id
    WHERE m.competition_id = 2 AND m.season_id = 27
)
SELECT
    'event_coverage' AS section,
    count(*) AS events,
    count(DISTINCT match_id) AS matches,
    count(*) FILTER (WHERE player_id IS NOT NULL) AS with_player,
    count(*) FILTER (WHERE team_id IS NOT NULL) AS with_team,
    count(*) FILTER (WHERE possession IS NOT NULL) AS with_possession,
    count(*) FILTER (WHERE location_x IS NOT NULL AND location_y IS NOT NULL) AS with_start_location
FROM sample_events;

WITH sample_events AS (
    SELECT e.*
    FROM statsbomb_events AS e
    JOIN statsbomb_matches AS m ON m.match_id = e.match_id
    WHERE m.competition_id = 2 AND m.season_id = 27
)
SELECT event_type, count(*) AS events,
       count(*) FILTER (WHERE player_id IS NOT NULL) AS with_player
FROM sample_events
GROUP BY event_type
ORDER BY events DESC;

WITH sample_events AS (
    SELECT e.*
    FROM statsbomb_events AS e
    JOIN statsbomb_matches AS m ON m.match_id = e.match_id
    WHERE m.competition_id = 2 AND m.season_id = 27
)
SELECT
    'payload_fields' AS section,
    count(*) FILTER (WHERE event_type = 'Shot') AS shots,
    count(*) FILTER (
        WHERE event_type = 'Shot'
          AND jsonb_typeof(source_payload #> '{shot,statsbomb_xg}') = 'number'
    ) AS shots_with_numeric_xg,
    min((source_payload #>> '{shot,statsbomb_xg}')::numeric)
        FILTER (WHERE event_type = 'Shot') AS min_xg,
    max((source_payload #>> '{shot,statsbomb_xg}')::numeric)
        FILTER (WHERE event_type = 'Shot') AS max_xg,
    count(*) FILTER (
        WHERE event_type = 'Pass' AND source_payload #>> '{pass,shot_assist}' = 'true'
    ) AS shot_assist_passes,
    count(*) FILTER (
        WHERE event_type = 'Pass' AND source_payload #>> '{pass,goal_assist}' = 'true'
    ) AS goal_assist_passes,
    count(*) FILTER (
        WHERE event_type = 'Pass'
          AND source_payload #> '{pass,end_location}' IS NOT NULL
    ) AS passes_with_end_location,
    count(*) FILTER (
        WHERE event_type = 'Carry'
          AND source_payload #> '{carry,end_location}' IS NOT NULL
    ) AS carries_with_end_location
FROM sample_events;

WITH sample_events AS (
    SELECT e.*
    FROM statsbomb_events AS e
    JOIN statsbomb_matches AS m ON m.match_id = e.match_id
    WHERE m.competition_id = 2 AND m.season_id = 27
)
SELECT
    'attacking_box_endpoints' AS section,
    count(*) FILTER (
        WHERE event_type = 'Pass'
          AND NULLIF(source_payload #>> '{pass,end_location,0}', '')::numeric >= 102
          AND NULLIF(source_payload #>> '{pass,end_location,1}', '')::numeric BETWEEN 18 AND 62
    ) AS passes_ending_in_box,
    count(*) FILTER (
        WHERE event_type = 'Pass' AND pass_completed IS TRUE
          AND NULLIF(source_payload #>> '{pass,end_location,0}', '')::numeric >= 102
          AND NULLIF(source_payload #>> '{pass,end_location,1}', '')::numeric BETWEEN 18 AND 62
    ) AS completed_passes_ending_in_box,
    count(*) FILTER (
        WHERE event_type = 'Carry'
          AND NULLIF(source_payload #>> '{carry,end_location,0}', '')::numeric >= 102
          AND NULLIF(source_payload #>> '{carry,end_location,1}', '')::numeric BETWEEN 18 AND 62
    ) AS carries_ending_in_box
FROM sample_events;

WITH sample_events AS (
    SELECT e.*
    FROM statsbomb_events AS e
    JOIN statsbomb_matches AS m ON m.match_id = e.match_id
    WHERE m.competition_id = 2 AND m.season_id = 27
)
SELECT event_type,
       count(*) AS events,
       count(*) FILTER (WHERE source_payload #>> '{interception,outcome,name}' IS NOT NULL)
           AS interception_with_outcome,
       count(*) FILTER (WHERE source_payload #>> '{ball_recovery,recovery_failure}' IS NOT NULL)
           AS recovery_with_failure_flag,
       count(*) FILTER (
           WHERE source_payload #>> '{duel,type,name}' = 'Tackle'
       ) AS tackle_duels,
       count(*) FILTER (
           WHERE source_payload #>> '{duel,type,name}' = 'Tackle'
             AND source_payload #>> '{duel,outcome,name}' IS NOT NULL
       ) AS tackle_duels_with_outcome
FROM sample_events
WHERE event_type IN ('Interception', 'Ball Recovery', 'Duel', 'Pressure')
GROUP BY event_type
ORDER BY event_type;

WITH player_role_minutes AS (
    SELECT
        a.player_id,
        sum(a.minutes_played) AS season_minutes,
        coalesce(sum(a.minutes_played) FILTER (
            WHERE a.position_id = ANY(ARRAY[9, 10, 11, 13, 14, 15])
        ), 0) AS central_midfield_minutes,
        coalesce(sum(a.minutes_played) FILTER (
            WHERE a.position_id = ANY(ARRAY[17, 19, 20, 21])
        ), 0) AS chance_creator_minutes,
        coalesce(sum(a.minutes_played) FILTER (
            WHERE a.position_id = ANY(ARRAY[22, 23, 24])
        ), 0) AS forward_minutes
    FROM statsbomb_appearances AS a
    JOIN statsbomb_matches AS m ON m.match_id = a.match_id
    WHERE m.competition_id = 2 AND m.season_id = 27
    GROUP BY a.player_id
)
SELECT
    'estimated_candidate_pools' AS section,
    count(*) FILTER (
        WHERE season_minutes >= 450
          AND central_midfield_minutes / season_minutes >= 0.5
    ) AS central_midfielders,
    count(*) FILTER (
        WHERE season_minutes >= 450
          AND chance_creator_minutes / season_minutes >= 0.5
    ) AS chance_creators,
    count(*) FILTER (
        WHERE season_minutes >= 450
          AND forward_minutes / season_minutes >= 0.5
    ) AS forwards
FROM player_role_minutes;

WITH possession_groups AS (
    SELECT
        e.match_id,
        e.possession,
        count(DISTINCT NULLIF(e.source_payload #>> '{possession_team,id}', ''))
            AS possession_team_count,
        count(DISTINCT e.team_id) AS event_team_count
    FROM statsbomb_events AS e
    JOIN statsbomb_matches AS m ON m.match_id = e.match_id
    WHERE m.competition_id = 2 AND m.season_id = 27
      AND e.possession IS NOT NULL
    GROUP BY e.match_id, e.possession
)
SELECT
    'possession_integrity' AS section,
    count(*) AS match_possessions,
    count(*) FILTER (WHERE possession_team_count = 1) AS with_one_possession_team,
    count(*) FILTER (WHERE possession_team_count <> 1) AS with_unusual_possession_team_count,
    count(*) FILTER (WHERE event_team_count > 1) AS with_multiple_event_teams
FROM possession_groups;

ROLLBACK;
