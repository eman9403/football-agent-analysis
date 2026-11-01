import os

import psycopg
from fastapi import FastAPI, Response, status


app = FastAPI(title="Football Scouting API")


@app.get("/api/health")
def health(response: Response) -> dict[str, str]:
    try:
        with psycopg.connect(
            os.getenv("DATABASE_URL", "dbname=football_scouting"),
            connect_timeout=2,
        ) as connection:
            connection.execute("SELECT 1")
    except psycopg.OperationalError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"api": "ok", "database": "unavailable"}

    return {"api": "ok", "database": "ok"}
