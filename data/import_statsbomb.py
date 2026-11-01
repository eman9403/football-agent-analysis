"""Selective, repeatable local import of a pinned StatsBomb Open Data sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import psycopg
from psycopg.types.json import Jsonb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SELECTION_PATH = Path(__file__).with_name("statsbomb-selection.json")
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_RAW_ROOT = PROJECT_ROOT / "data" / "raw"
USER_AGENT = "football-scouting-local-research/1.0"


@dataclass(frozen=True)
class ImportSummary:
    matches: int
    appearances: int
    events: int
    players: int
    source_files: int


def load_selection(path: Path = SELECTION_PATH) -> dict[str, Any]:
    selection = json.loads(path.read_text())
    required = {
        "source_repository",
        "source_commit",
        "competition_id",
        "season_id",
        "competition_name",
        "season_name",
        "expected_match_count",
        "importer_version",
    }
    missing = required - selection.keys()
    if missing:
        raise ValueError(f"Selection is missing required fields: {', '.join(sorted(missing))}")
    if not re.fullmatch(r"[0-9a-f]{40}", selection["source_commit"]):
        raise ValueError("source_commit must be a 40-character lowercase Git commit SHA")
    return selection


def parse_game_clock(value: str) -> int:
    """Convert StatsBomb's elapsed match clock (MM:SS) into seconds."""
    pieces = value.split(":")
    if len(pieces) != 2 or not all(piece.isdigit() for piece in pieces):
        raise ValueError(f"Invalid StatsBomb game clock: {value!r}")
    minutes, seconds = map(int, pieces)
    if seconds >= 60:
        raise ValueError(f"Invalid StatsBomb game clock: {value!r}")
    return minutes * 60 + seconds


def match_end_seconds(events: list[dict[str, Any]]) -> int:
    if not events:
        raise ValueError("A match must have events to determine its final elapsed time")
    return max(int(event["minute"]) * 60 + int(event.get("second") or 0) for event in events)


def normalize_appearances(
    lineups: list[dict[str, Any]], match_end_seconds: int
) -> list[dict[str, Any]]:
    """Normalize players who took the pitch, using lineup position intervals."""
    appearances = []
    seen_players: set[int] = set()

    for team in lineups:
        team_id = team.get("team_id")
        if team_id is None or not team.get("team_name"):
            raise ValueError("Every lineup team must include its StatsBomb ID and name")

        for player in team.get("lineup", []):
            player_id = player.get("player_id")
            player_name = player.get("player_name")
            if player_id is None or not player_name:
                raise ValueError("Every lineup player must include its StatsBomb ID and name")
            positions = player.get("positions") or []
            if not positions:
                continue
            if player_id in seen_players:
                raise ValueError(f"Player {player_id} appears for more than one team in a match")
            seen_players.add(player_id)

            intervals = []
            for order, position in enumerate(positions):
                start = parse_game_clock(position["from"])
                end = (
                    parse_game_clock(position["to"])
                    if position.get("to") is not None
                    else match_end_seconds
                )
                if end < start:
                    raise ValueError(f"Position interval ends before it starts for player {player_id}")
                intervals.append(
                    {
                        "start": start,
                        "end": end,
                        "order": order,
                        "position_id": position.get("position_id"),
                        "position_name": position.get("position"),
                    }
                )

            boundaries = sorted(
                {point for interval in intervals for point in (interval["start"], interval["end"])}
            )
            role_seconds: dict[tuple[int | None, str | None], int] = {}
            role_order: dict[tuple[int | None, str | None], int] = {}
            total_seconds = 0
            for left, right in zip(boundaries, boundaries[1:]):
                active = [
                    interval
                    for interval in intervals
                    if interval["start"] <= left and interval["end"] >= right
                ]
                if not active or right == left:
                    continue
                # If the source intervals overlap, the latest position change wins.
                selected = max(active, key=lambda interval: (interval["start"], -interval["order"]))
                role = (selected["position_id"], selected["position_name"])
                duration = right - left
                total_seconds += duration
                role_seconds[role] = role_seconds.get(role, 0) + duration
                role_order.setdefault(role, selected["order"])

            # Keep a zero-length stint as an appearance and retain its listed
            # position when no interval contributes any played seconds.
            primary_role = (
                max(
                    role_seconds,
                    key=lambda role: (role_seconds[role], -role_order[role]),
                )
                if role_seconds
                else (positions[0].get("position_id"), positions[0].get("position"))
            )
            country = player.get("country") or {}
            appearances.append(
                {
                    "player_id": player_id,
                    "player_name": player_name,
                    "player_nickname": player.get("player_nickname"),
                    "country_name": country.get("name"),
                    "team_id": team_id,
                    "team_name": team["team_name"],
                    "started": positions[0].get("start_reason") == "Starting XI",
                    "position_id": primary_role[0],
                    "position_name": primary_role[1],
                    "minutes_played": round(total_seconds / 60, 2),
                }
            )

    return appearances


def normalize_event(event: dict[str, Any], match_id: int) -> dict[str, Any]:
    event_type = (event.get("type") or {}).get("name")
    if not event.get("id") or event.get("index") is None or not event_type:
        raise ValueError("Every StatsBomb event must include an ID, index, and type")
    player = event.get("player") or {}
    team = event.get("team") or {}
    location = event.get("location") or []
    pass_data = event.get("pass")
    shot_data = event.get("shot") or {}
    pass_outcome = ((pass_data or {}).get("outcome") or {}).get("name")
    shot_outcome = (shot_data.get("outcome") or {}).get("name")

    return {
        "match_id": match_id,
        "event_id": event["id"],
        "event_index": int(event["index"]),
        "period": int(event["period"]),
        "minute": int(event["minute"]),
        "second": int(event.get("second") or 0),
        "event_type": event_type,
        "possession": event.get("possession"),
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "player_id": player.get("id"),
        "player_name": player.get("name"),
        "location_x": location[0] if len(location) > 0 else None,
        "location_y": location[1] if len(location) > 1 else None,
        "pass_outcome": pass_outcome,
        "pass_completed": None if event_type != "Pass" or not isinstance(pass_data, dict) else pass_outcome is None,
        "shot_outcome": shot_outcome,
        "source_payload": event,
    }


def _repository_raw_url(selection: dict[str, Any]) -> str:
    repository_path = urlparse(selection["source_repository"]).path.strip("/").removesuffix(".git")
    parts = repository_path.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("source_repository must be a GitHub owner/repository URL")
    return f"https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/{selection['source_commit']}"


def _read_json(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text())
    if not isinstance(value, list):
        raise ValueError(f"Expected a JSON array in {path}")
    return value


def _file_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def download_selection(
    selection: dict[str, Any],
    raw_root: Path = DEFAULT_RAW_ROOT,
    *,
    raw_base_url: str | None = None,
    workers: int = 6,
) -> Path:
    """Download only the selected season and its event/lineup JSON files."""
    source_root = raw_root / "statsbomb" / selection["source_commit"]
    manifest_path = source_root / "manifest.json"
    source_root.mkdir(parents=True, exist_ok=True)
    base_url = (raw_base_url or _repository_raw_url(selection)).rstrip("/")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("source_commit") != selection["source_commit"]:
            raise ValueError("Existing manifest does not match the selected source commit")
    else:
        manifest = {
            "source_repository": selection["source_repository"],
            "source_commit": selection["source_commit"],
            "competition_id": selection["competition_id"],
            "season_id": selection["season_id"],
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "files": {},
        }

    manifest_lock = threading.Lock()

    def fetch(relative_path: str) -> dict[str, Any]:
        destination = source_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        url = f"{base_url}/{relative_path}"
        with manifest_lock:
            previous = manifest["files"].get(relative_path)
        if destination.is_file() and previous:
            digest, size = _file_digest(destination)
            try:
                _read_json(destination)
            except (ValueError, json.JSONDecodeError):
                pass
            else:
                if digest == previous.get("sha256") and size == previous.get("byte_size"):
                    return previous

        temporary = destination.with_name(destination.name + ".part")
        digest = hashlib.sha256()
        size = 0
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            _read_json(temporary)
            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

        record = {
            "source_url": url,
            "sha256": digest.hexdigest(),
            "byte_size": size,
        }
        with manifest_lock:
            manifest["files"][relative_path] = record
            _write_manifest(manifest_path, manifest)
        return record

    catalogue_path = "data/competitions.json"
    fetch(catalogue_path)
    catalogue = _read_json(source_root / catalogue_path)
    has_selection = any(
        row.get("competition_id") == selection["competition_id"]
        and row.get("season_id") == selection["season_id"]
        for row in catalogue
    )
    if not has_selection:
        raise ValueError("The pinned competition catalogue does not contain the selected season")

    matches_relative = f"data/matches/{selection['competition_id']}/{selection['season_id']}.json"
    fetch(matches_relative)
    matches = _read_json(source_root / matches_relative)
    match_ids = [match.get("match_id") for match in matches]
    if any(match_id is None for match_id in match_ids) or len(set(match_ids)) != len(match_ids):
        raise ValueError("The selected match file contains a missing or duplicate match ID")
    if len(matches) != selection["expected_match_count"]:
        raise ValueError(
            f"Expected {selection['expected_match_count']} matches, found {len(matches)}"
        )
    unavailable = [
        match["match_id"]
        for match in matches
        if match.get("match_status") != "available"
    ]
    if unavailable:
        raise ValueError(f"Selected match list includes unavailable matches: {unavailable[:5]}")

    jobs = [
        relative_path
        for match_id in match_ids
        for relative_path in (f"data/events/{match_id}.json", f"data/lineups/{match_id}.json")
    ]
    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch, relative_path): relative_path for relative_path in jobs}
        for future in as_completed(futures):
            future.result()
            completed += 1
            if completed % 50 == 0 or completed == len(jobs):
                print(f"Verified {completed}/{len(jobs)} match event and lineup files", file=sys.stderr)

    for match_id in match_ids:
        events = _read_json(source_root / f"data/events/{match_id}.json")
        lineups = _read_json(source_root / f"data/lineups/{match_id}.json")
        event_ids = [event.get("id") for event in events]
        if any(event_id is None for event_id in event_ids) or len(set(event_ids)) != len(event_ids):
            raise ValueError(f"Match {match_id} contains a missing or duplicate event ID")
        if not isinstance(lineups, list) or not lineups:
            raise ValueError(f"Match {match_id} has no lineup records")

    return manifest_path


def create_schema(connection: psycopg.Connection) -> None:
    connection.execute(SCHEMA_PATH.read_text())


def _upsert_team(connection: psycopg.Connection, team_id: int | None, team_name: str | None) -> None:
    if team_id is None or not team_name:
        return
    connection.execute(
        """INSERT INTO statsbomb_teams (team_id, team_name) VALUES (%s, %s)
           ON CONFLICT (team_id) DO UPDATE SET team_name = EXCLUDED.team_name""",
        (team_id, team_name),
    )


def _upsert_player(
    connection: psycopg.Connection,
    player_id: int | None,
    player_name: str | None,
    player_nickname: str | None = None,
    country_name: str | None = None,
) -> None:
    if player_id is None or not player_name:
        return
    connection.execute(
        """INSERT INTO statsbomb_players
               (player_id, player_name, player_nickname, country_name)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (player_id) DO UPDATE SET
               player_name = EXCLUDED.player_name,
               player_nickname = COALESCE(EXCLUDED.player_nickname, statsbomb_players.player_nickname),
               country_name = COALESCE(EXCLUDED.country_name, statsbomb_players.country_name)""",
        (player_id, player_name, player_nickname, country_name),
    )


def _ensure_competition(connection: psycopg.Connection, selection: dict[str, Any]) -> None:
    existing = connection.execute(
        """SELECT source_commit FROM statsbomb_competitions
           WHERE competition_id = %s AND season_id = %s FOR UPDATE""",
        (selection["competition_id"], selection["season_id"]),
    ).fetchone()
    if existing and existing[0] != selection["source_commit"]:
        raise ValueError(
            "This competition-season is already loaded from a different source commit; "
            "clear its local rows before importing a different snapshot"
        )
    connection.execute(
        """INSERT INTO statsbomb_competitions
               (competition_id, season_id, competition_name, season_name,
                source_repository, source_commit)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (competition_id, season_id) DO UPDATE SET
               imported_at = now()""",
        (
            selection["competition_id"],
            selection["season_id"],
            selection["competition_name"],
            selection["season_name"],
            selection["source_repository"],
            selection["source_commit"],
        ),
    )


def import_match(
    connection: psycopg.Connection,
    selection: dict[str, Any],
    match: dict[str, Any],
    lineups: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> tuple[int, int, int]:
    """Upsert one match, its full squad, active appearances, and source events."""
    normalized_appearances = normalize_appearances(lineups, match_end_seconds(events))
    match_id = int(match["match_id"])

    with connection.transaction():
        _ensure_competition(connection, selection)
        home = match.get("home_team") or {}
        away = match.get("away_team") or {}
        home_id = home.get("home_team_id")
        home_name = home.get("home_team_name")
        away_id = away.get("away_team_id")
        away_name = away.get("away_team_name")
        if None in (home_id, away_id) or not home_name or not away_name:
            raise ValueError(f"Match {match_id} is missing home or away team identity")
        _upsert_team(connection, home_id, home_name)
        _upsert_team(connection, away_id, away_name)
        for team in lineups:
            _upsert_team(connection, team.get("team_id"), team.get("team_name"))
            for player in team.get("lineup", []):
                country = player.get("country") or {}
                if player.get("player_id") is None or not player.get("player_name"):
                    raise ValueError(f"Match {match_id} has a lineup player without source identity")
                _upsert_player(
                    connection,
                    player["player_id"],
                    player["player_name"],
                    player.get("player_nickname"),
                    country.get("name"),
                )

        normalized_events = [normalize_event(event, match_id) for event in events]
        for event in normalized_events:
            _upsert_team(connection, event["team_id"], event["team_name"])
            _upsert_player(connection, event["player_id"], event["player_name"])

        connection.execute(
            """INSERT INTO statsbomb_matches
                   (match_id, competition_id, season_id, match_date, match_week,
                    home_team_id, away_team_id, home_score, away_score, source_commit)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (match_id) DO UPDATE SET
                   competition_id = EXCLUDED.competition_id,
                   season_id = EXCLUDED.season_id,
                   match_date = EXCLUDED.match_date,
                   match_week = EXCLUDED.match_week,
                   home_team_id = EXCLUDED.home_team_id,
                   away_team_id = EXCLUDED.away_team_id,
                   home_score = EXCLUDED.home_score,
                   away_score = EXCLUDED.away_score,
                   source_commit = EXCLUDED.source_commit""",
            (
                match_id,
                selection["competition_id"],
                selection["season_id"],
                match["match_date"],
                match.get("match_week"),
                home_id,
                away_id,
                match.get("home_score"),
                match.get("away_score"),
                selection["source_commit"],
            ),
        )

        with connection.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO statsbomb_appearances
                   (match_id, player_id, team_id, started, position_id, position_name, minutes_played)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (match_id, player_id) DO UPDATE SET
                   team_id = EXCLUDED.team_id,
                   started = EXCLUDED.started,
                   position_id = EXCLUDED.position_id,
                   position_name = EXCLUDED.position_name,
                   minutes_played = EXCLUDED.minutes_played""",
                [
                    (
                        match_id,
                        appearance["player_id"],
                        appearance["team_id"],
                        appearance["started"],
                        appearance["position_id"],
                        appearance["position_name"],
                        appearance["minutes_played"],
                    )
                    for appearance in normalized_appearances
                ],
            )
            cursor.executemany(
                """INSERT INTO statsbomb_events
                   (match_id, event_id, event_index, period, minute, second, event_type,
                    possession, team_id, player_id, location_x, location_y, pass_outcome,
                    pass_completed, shot_outcome, source_payload)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (match_id, event_id) DO UPDATE SET
                   event_index = EXCLUDED.event_index,
                   period = EXCLUDED.period,
                   minute = EXCLUDED.minute,
                   second = EXCLUDED.second,
                   event_type = EXCLUDED.event_type,
                   possession = EXCLUDED.possession,
                   team_id = EXCLUDED.team_id,
                   player_id = EXCLUDED.player_id,
                   location_x = EXCLUDED.location_x,
                   location_y = EXCLUDED.location_y,
                   pass_outcome = EXCLUDED.pass_outcome,
                   pass_completed = EXCLUDED.pass_completed,
                   shot_outcome = EXCLUDED.shot_outcome,
                   source_payload = EXCLUDED.source_payload""",
                [
                    (
                        match_id,
                        event["event_id"],
                        event["event_index"],
                        event["period"],
                        event["minute"],
                        event["second"],
                        event["event_type"],
                        event["possession"],
                        event["team_id"],
                        event["player_id"],
                        event["location_x"],
                        event["location_y"],
                        event["pass_outcome"],
                        event["pass_completed"],
                        event["shot_outcome"],
                        Jsonb(event["source_payload"]),
                    )
                    for event in normalized_events
                ],
            )

    return len(normalized_appearances), len(normalized_events), sum(
        len(team.get("lineup", [])) for team in lineups
    )


def import_season(
    connection: psycopg.Connection,
    selection: dict[str, Any],
    raw_root: Path = DEFAULT_RAW_ROOT,
) -> ImportSummary:
    source_root = raw_root / "statsbomb" / selection["source_commit"]
    matches_path = source_root / "data" / "matches" / str(selection["competition_id"]) / f"{selection['season_id']}.json"
    matches = _read_json(matches_path)
    if len(matches) != selection["expected_match_count"]:
        raise ValueError(f"Expected {selection['expected_match_count']} matches, found {len(matches)}")

    create_schema(connection)
    appearance_count = 0
    event_count = 0
    player_ids: set[int] = set()
    for index, match in enumerate(matches, start=1):
        match_id = int(match["match_id"])
        lineups = _read_json(source_root / "data" / "lineups" / f"{match_id}.json")
        events = _read_json(source_root / "data" / "events" / f"{match_id}.json")
        appearances, events_imported, roster_size = import_match(
            connection, selection, match, lineups, events
        )
        appearance_count += appearances
        event_count += events_imported
        player_ids.update(
            player["player_id"]
            for team in lineups
            for player in team.get("lineup", [])
        )
        if index % 25 == 0 or index == len(matches):
            print(
                f"Imported {index}/{len(matches)} matches "
                f"({appearance_count} appearances, {event_count:,} events)",
                file=sys.stderr,
            )

    manifest = json.loads((source_root / "manifest.json").read_text())
    retrieved_at = manifest["retrieved_at"]
    with connection.transaction():
        for source_path, record in manifest["files"].items():
            connection.execute(
                """INSERT INTO statsbomb_import_files
                       (source_commit, source_path, source_url, sha256, byte_size, retrieved_at)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (source_commit, source_path) DO UPDATE SET
                       source_url = EXCLUDED.source_url,
                       sha256 = EXCLUDED.sha256,
                       byte_size = EXCLUDED.byte_size,
                       retrieved_at = EXCLUDED.retrieved_at""",
                (
                    selection["source_commit"],
                    source_path,
                    record["source_url"],
                    record["sha256"],
                    record["byte_size"],
                    retrieved_at,
                ),
            )

    return ImportSummary(
        matches=len(matches),
        appearances=appearance_count,
        events=event_count,
        players=len(player_ids),
        source_files=len(manifest["files"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", "dbname=football_scouting"),
    )
    args = parser.parse_args()
    selection = load_selection()
    print(
        f"Preparing {selection['competition_name']} {selection['season_name']} "
        f"({selection['expected_match_count']} matches) from {selection['source_commit']}"
    )
    manifest = download_selection(selection, args.raw_root)
    print(f"Local source manifest: {manifest}")
    with psycopg.connect(args.database_url, autocommit=True) as connection:
        summary = import_season(connection, selection, args.raw_root)
    print(
        "Import complete: "
        f"{summary.matches} matches, {summary.appearances} appearances, "
        f"{summary.events:,} events, {summary.players} rostered players, "
        f"{summary.source_files} source files."
    )


if __name__ == "__main__":
    main()
