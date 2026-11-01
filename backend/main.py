import os
from typing import Annotated

import psycopg
from fastapi import FastAPI, HTTPException, Query, Response, status

from backend.scouting import (
    ScoutingFilters,
    ScoutingResponse,
    build_scouting_response,
    fetch_player_aggregates,
)


app = FastAPI(title="Football Scouting API")


def _connect_database():
    return psycopg.connect(
        os.getenv("DATABASE_URL", "dbname=football_scouting"),
        connect_timeout=2,
    )


@app.get("/api/health")
def health(response: Response) -> dict[str, str]:
    try:
        with _connect_database() as connection:
            connection.execute("SELECT 1")
    except psycopg.OperationalError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"api": "ok", "database": "unavailable"}

    return {"api": "ok", "database": "ok"}


@app.get("/api/scouting/players", response_model=ScoutingResponse)
def get_scouting_players(filters: Annotated[ScoutingFilters, Query()]) -> ScoutingResponse:
    try:
        with _connect_database() as connection:
            aggregates = fetch_player_aggregates(connection)
    except psycopg.OperationalError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local PostgreSQL is unavailable. Start PostgreSQL and try again.",
        ) from error

    return build_scouting_response(aggregates, filters)
