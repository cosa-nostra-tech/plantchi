"""
main.py — Plantchi FastAPI application entry point.
"""
from __future__ import annotations

import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from database import db_conn, init_db
from models import (
    PlantCreate,
    PlantState,
    PlantSummary,
    ReadingIn,
    ReadingResponse,
    HistoryPoint,
    Thresholds,
)
from plantbook import get_thresholds, search_species
from state_engine import DEFAULT_THRESHOLDS, compute_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialised.")
    yield


app = FastAPI(
    title="Plantchi API",
    description="Backend for the Plantchi plant-sensor tamagotchi",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _epoch_to_iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _load_thresholds(raw_json: str) -> dict:
    try:
        return json.loads(raw_json)
    except Exception:
        return dict(DEFAULT_THRESHOLDS)


def _get_latest_reading(conn, plant_id: str) -> Optional[dict]:
    row = conn.execute(
        """
        SELECT * FROM readings
        WHERE plant_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (plant_id,),
    ).fetchone()
    return dict(row) if row else None


def _get_history(conn, plant_id: str, since_iso: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT * FROM readings
        WHERE plant_id = ? AND timestamp >= ?
        ORDER BY timestamp ASC
        """,
        (plant_id, since_iso),
    ).fetchall()
    return [dict(r) for r in rows]


def _get_last_state(conn, plant_id: str) -> Optional[str]:
    row = conn.execute(
        """
        SELECT state FROM state_log
        WHERE plant_id = ?
        ORDER BY changed_at DESC
        LIMIT 1
        """,
        (plant_id,),
    ).fetchone()
    return row["state"] if row else None


def _compute_plant_state(conn, plant_id: str) -> tuple[str, str]:
    """Fetch latest reading + history and compute state. Returns (state, severity)."""
    plant_row = conn.execute(
        "SELECT thresholds FROM plants WHERE id = ?", (plant_id,)
    ).fetchone()
    if not plant_row:
        return "HAPPY", "ok"

    thresholds = _load_thresholds(plant_row["thresholds"])
    latest = _get_latest_reading(conn, plant_id)
    if not latest:
        return "HAPPY", "ok"

    # Get 48h of history for sustained checks
    since = (datetime.now(timezone.utc) - timedelta(hours=49)).isoformat()
    history = _get_history(conn, plant_id, since)
    # Exclude the very latest reading from history (it's passed as `reading`)
    history = [r for r in history if r["id"] != latest["id"]]

    current_hour = datetime.now(timezone.utc).hour  # Use UTC hour; adjust if needed
    return compute_state(latest, thresholds, current_hour, history)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ------------------------------------------------------------------
# Plants
# ------------------------------------------------------------------

@app.post("/plants", status_code=201)
def create_plant(body: PlantCreate):
    plant_id = str(uuid.uuid4())
    now = _now_iso()

    # Resolve thresholds: manual override > species lookup > defaults
    if body.thresholds:
        thresholds = body.thresholds.model_dump()
    elif body.species_key:
        thresholds = get_thresholds(body.species_key) or dict(DEFAULT_THRESHOLDS)
    else:
        thresholds = dict(DEFAULT_THRESHOLDS)

    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO plants (id, name, species_key, created_at, thresholds)
            VALUES (?, ?, ?, ?, ?)
            """,
            (plant_id, body.name, body.species_key, now, json.dumps(thresholds)),
        )

    return {"plant_id": plant_id, "name": body.name, "thresholds": thresholds}


@app.get("/plants", response_model=list[PlantSummary])
def list_plants():
    with db_conn() as conn:
        rows = conn.execute("SELECT * FROM plants ORDER BY created_at DESC").fetchall()
        result = []
        for row in rows:
            plant_id = row["id"]
            state, severity = _compute_plant_state(conn, plant_id)
            latest = _get_latest_reading(conn, plant_id)
            last_updated = latest["timestamp"] if latest else None
            result.append(
                PlantSummary(
                    plant_id=plant_id,
                    name=row["name"],
                    state=state,
                    severity=severity,
                    last_updated=last_updated,
                )
            )
    return result


@app.get("/plants/{plant_id}", response_model=PlantState)
def get_plant(plant_id: str):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM plants WHERE id = ?", (plant_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Plant not found")

        thresholds = _load_thresholds(row["thresholds"])
        state, severity = _compute_plant_state(conn, plant_id)
        latest = _get_latest_reading(conn, plant_id)
        last_updated = latest["timestamp"] if latest else None

        # Clean up reading for response (remove internal fields)
        readings_out = None
        if latest:
            readings_out = {
                k: latest[k]
                for k in (
                    "soil_pct",
                    "light_lux",
                    "temp_c",
                    "humidity_pct",
                    "conductivity_ppm",
                )
                if k in latest
            }

    return PlantState(
        plant_id=plant_id,
        name=row["name"],
        state=state,
        severity=severity,
        readings=readings_out,
        thresholds=thresholds,
        last_updated=last_updated,
    )


@app.get("/plants/{plant_id}/history", response_model=list[HistoryPoint])
def get_history(plant_id: str, hours: int = Query(default=24, ge=1, le=8760)):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id FROM plants WHERE id = ?", (plant_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Plant not found")

        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        readings = _get_history(conn, plant_id, since)

    return [
        HistoryPoint(
            timestamp=r["timestamp"],
            soil_pct=r.get("soil_pct"),
            light_lux=r.get("light_lux"),
            temp_c=r.get("temp_c"),
            humidity_pct=r.get("humidity_pct"),
        )
        for r in readings
    ]


# ------------------------------------------------------------------
# Readings
# ------------------------------------------------------------------

@app.post("/readings", response_model=ReadingResponse)
def post_reading(body: ReadingIn):
    plant_id = body.device_id
    reading_id = str(uuid.uuid4())
    ts_iso = _epoch_to_iso(body.timestamp)
    r = body.readings

    with db_conn() as conn:
        # Auto-create plant if it doesn't exist yet
        plant_row = conn.execute(
            "SELECT * FROM plants WHERE id = ?", (plant_id,)
        ).fetchone()
        if not plant_row:
            conn.execute(
                """
                INSERT INTO plants (id, name, species_key, created_at, thresholds)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    plant_id,
                    f"Plant {plant_id[:8]}",
                    None,
                    _now_iso(),
                    json.dumps(DEFAULT_THRESHOLDS),
                ),
            )

        # Store reading
        conn.execute(
            """
            INSERT INTO readings
              (id, plant_id, timestamp, soil_pct, light_lux, temp_c,
               humidity_pct, conductivity_ppm)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reading_id,
                plant_id,
                ts_iso,
                r.soil_pct,
                r.light_lux,
                r.temp_c,
                r.humidity_pct,
                r.conductivity_ppm,
            ),
        )

        # Compute new state
        thresholds = _load_thresholds(
            conn.execute(
                "SELECT thresholds FROM plants WHERE id = ?", (plant_id,)
            ).fetchone()["thresholds"]
        )

        # History for sustained checks
        since = (datetime.now(timezone.utc) - timedelta(hours=49)).isoformat()
        history = _get_history(conn, plant_id, since)
        history = [row for row in history if row["id"] != reading_id]

        current_hour = datetime.now(timezone.utc).hour
        reading_dict = {
            "soil_pct": r.soil_pct,
            "light_lux": r.light_lux,
            "temp_c": r.temp_c,
            "humidity_pct": r.humidity_pct,
            "conductivity_ppm": r.conductivity_ppm,
            "timestamp": ts_iso,
        }
        new_state, severity = compute_state(
            reading_dict, thresholds, current_hour, history
        )

        # Check if state changed
        prev_state = _get_last_state(conn, plant_id)
        changed = prev_state != new_state

        if changed:
            conn.execute(
                """
                INSERT INTO state_log (id, plant_id, state, changed_at)
                VALUES (?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), plant_id, new_state, _now_iso()),
            )

    return ReadingResponse(
        plant_id=plant_id,
        state=new_state,
        severity=severity,
        changed=changed,
    )


# ------------------------------------------------------------------
# Species search
# ------------------------------------------------------------------

@app.get("/species/search")
def species_search(q: str = Query(..., min_length=1)):
    results = search_species(q)
    return {"results": results, "count": len(results)}


# ---------------------------------------------------------------------------
# Dev runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
