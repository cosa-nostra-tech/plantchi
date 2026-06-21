"""
database.py — SQLite initialization and connection management for Plantchi.
"""
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.environ.get("PLANTCHI_DB", "plantchi.db")


def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_conn():
    """Context manager that yields a connection and commits/rolls back automatically."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str | None = None) -> None:
    """Create all tables if they don't already exist."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS plants (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            species_key TEXT,
            created_at  TEXT NOT NULL,
            thresholds  TEXT NOT NULL   -- JSON blob
        );

        CREATE TABLE IF NOT EXISTS readings (
            id               TEXT PRIMARY KEY,
            plant_id         TEXT NOT NULL REFERENCES plants(id),
            timestamp        TEXT NOT NULL,
            soil_pct         REAL,
            light_lux        REAL,
            temp_c           REAL,
            humidity_pct     REAL,
            conductivity_ppm REAL
        );

        CREATE INDEX IF NOT EXISTS idx_readings_plant_ts
            ON readings(plant_id, timestamp);

        CREATE TABLE IF NOT EXISTS state_log (
            id         TEXT PRIMARY KEY,
            plant_id   TEXT NOT NULL REFERENCES plants(id),
            state      TEXT NOT NULL,
            changed_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_state_log_plant
            ON state_log(plant_id, changed_at);
        """
    )
    conn.commit()
    conn.close()
