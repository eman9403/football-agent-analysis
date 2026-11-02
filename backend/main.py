import os
from typing import Annotated

import psycopg
from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from backend.local_ai import (
    InvalidModelOutput,
    InterpretationResult,
    LocalModelUnavailable,
    OllamaStatus,
    interpret_question,
)
from backend.reporting import (
    PlayerReport,
    PlayerReportEvidence,
    ReportRequest,
    build_report_evidence,
    draft_player_report,
)
from backend.scouting import (
    ScoutingFilters,
    ScoutingProfileSummary,
    ScoutingResponse,
    build_scouting_response,
    fetch_player_aggregates,
    list_scouting_profiles,
)


app = FastAPI(title="Football Scouting API")


class InterpretQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=1000)
    active_filters: ScoutingFilters = Field(default_factory=ScoutingFilters)


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


@app.get("/api/scouting/profiles", response_model=list[ScoutingProfileSummary])
def get_scouting_profiles() -> list[ScoutingProfileSummary]:
    return list_scouting_profiles()


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


@app.get("/api/ai/status", response_model=OllamaStatus)
def get_local_ai_status() -> OllamaStatus:
    return OllamaStatus.inspect()


@app.post("/api/ai/interpret", response_model=InterpretationResult)
def interpret_scouting_question(request: InterpretQuestionRequest):
    local_status = OllamaStatus.inspect()
    if not local_status.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=local_status.detail,
        )
    try:
        return interpret_question(request.question, request.active_filters)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except InvalidModelOutput as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except LocalModelUnavailable as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@app.post("/api/reports/player", response_model=PlayerReport)
def get_player_report(request: ReportRequest) -> PlayerReport:
    try:
        with _connect_database() as connection:
            aggregates = fetch_player_aggregates(connection)
    except psycopg.OperationalError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local PostgreSQL is unavailable. Start PostgreSQL and try again.",
        ) from error

    try:
        evidence: PlayerReportEvidence = build_report_evidence(
            aggregates,
            request.filters,
            request.player_id,
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return draft_player_report(evidence)
