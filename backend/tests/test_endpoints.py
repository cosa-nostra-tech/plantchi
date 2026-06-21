"""
test_endpoints.py — Integration tests for the Plantchi FastAPI endpoints.

Uses TestClient (synchronous) with a temp SQLite database.
"""
from __future__ import annotations

import os
import time
import tempfile
import pytest

# Point the DB at a temp file before importing app modules
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["PLANTCHI_DB"] = _tmp_db.name

# Now import database + app (so they pick up the env var)
import database  # noqa: E402
database.DB_PATH = _tmp_db.name

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402
from main import app  # noqa: E402

# Patch main's db path too (it calls init_db on startup using database.DB_PATH)
main.DB_PATH = _tmp_db.name  # type: ignore[attr-defined]

# Initialise a fresh schema
database.init_db(_tmp_db.name)

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plant(name="Testicus plantus", species_key=None):
    payload = {"name": name}
    if species_key:
        payload["species_key"] = species_key
    resp = client.post("/plants", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["plant_id"]


def _post_reading(plant_id: str, soil=40.0, lux=2000.0, temp=24.0, humidity=55.0, conductivity=500.0):
    payload = {
        "device_id": plant_id,
        "timestamp": time.time(),
        "readings": {
            "soil_pct": soil,
            "light_lux": lux,
            "temp_c": temp,
            "humidity_pct": humidity,
            "conductivity_ppm": conductivity,
        },
    }
    resp = client.post("/readings", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /plants
# ---------------------------------------------------------------------------

class TestCreatePlant:
    def test_create_plant_returns_201(self):
        resp = client.post("/plants", json={"name": "My Fern"})
        assert resp.status_code == 201

    def test_create_plant_returns_plant_id(self):
        resp = client.post("/plants", json={"name": "Money Tree"})
        data = resp.json()
        assert "plant_id" in data
        assert isinstance(data["plant_id"], str)
        assert len(data["plant_id"]) > 0

    def test_create_plant_with_thresholds(self):
        resp = client.post(
            "/plants",
            json={
                "name": "Custom Plant",
                "thresholds": {
                    "min_soil_moist": 10,
                    "max_soil_moist": 80,
                    "min_light_lux": 200,
                    "max_light_lux": 20000,
                    "min_temp": 10,
                    "max_temp": 40,
                    "min_conductivity": 50,
                    "max_conductivity": 3000,
                },
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["thresholds"]["min_soil_moist"] == 10

    def test_create_plant_returns_thresholds(self):
        resp = client.post("/plants", json={"name": "Threshold Tester"})
        data = resp.json()
        assert "thresholds" in data


# ---------------------------------------------------------------------------
# POST /readings
# ---------------------------------------------------------------------------

class TestPostReadings:
    def test_reading_returns_200(self):
        plant_id = _make_plant("Reading Plant")
        resp_data = _post_reading(plant_id)
        assert "state" in resp_data

    def test_reading_returns_plant_id(self):
        plant_id = _make_plant("PID Plant")
        resp_data = _post_reading(plant_id)
        assert resp_data["plant_id"] == plant_id

    def test_reading_returns_state(self):
        plant_id = _make_plant("State Plant")
        resp_data = _post_reading(plant_id)
        assert resp_data["state"] in {
            "SLEEPING", "DROWNING", "THIRSTY", "HOT", "COLD",
            "SCORCHED", "DIM", "HUNGRY", "THRIVING", "HAPPY",
        }

    def test_reading_returns_severity(self):
        plant_id = _make_plant("Severity Plant")
        resp_data = _post_reading(plant_id)
        assert resp_data["severity"] in {"ok", "warn", "critical"}

    def test_reading_changed_flag_first_post(self):
        plant_id = _make_plant("Changed Plant")
        resp_data = _post_reading(plant_id)
        # First reading: changed must be True (no prior state)
        assert resp_data["changed"] is True

    def test_reading_changed_flag_same_state(self):
        plant_id = _make_plant("Same State Plant")
        _post_reading(plant_id)            # sets initial state
        resp_data = _post_reading(plant_id)  # same params → same state
        assert resp_data["changed"] is False

    def test_reading_auto_creates_plant(self):
        """Posting a reading for an unknown device_id auto-creates the plant."""
        fake_id = "auto-device-001"
        resp = client.post(
            "/readings",
            json={
                "device_id": fake_id,
                "timestamp": time.time(),
                "readings": {
                    "soil_pct": 40.0,
                    "light_lux": 2000.0,
                    "temp_c": 24.0,
                    "humidity_pct": 55.0,
                },
            },
        )
        assert resp.status_code == 200
        assert resp.json()["plant_id"] == fake_id

    def test_reading_without_conductivity(self):
        plant_id = _make_plant("No Cond Plant")
        resp = client.post(
            "/readings",
            json={
                "device_id": plant_id,
                "timestamp": time.time(),
                "readings": {
                    "soil_pct": 40.0,
                    "light_lux": 2000.0,
                    "temp_c": 24.0,
                    "humidity_pct": 55.0,
                },
            },
        )
        assert resp.status_code == 200

    def test_thirsty_state_returned(self):
        """A very dry soil reading produces THIRSTY or SLEEPING (depending on hour)."""
        plant_id = _make_plant("Dry Plant")
        resp_data = _post_reading(plant_id, soil=1.0)
        assert resp_data["state"] in ("THIRSTY", "SLEEPING")

    def test_hot_state_returned(self):
        plant_id = _make_plant("Hot Plant")
        resp_data = _post_reading(plant_id, temp=50.0)
        assert resp_data["state"] in ("HOT", "SLEEPING")


# ---------------------------------------------------------------------------
# GET /plants/{plant_id}
# ---------------------------------------------------------------------------

class TestGetPlant:
    def test_get_plant_returns_200(self):
        plant_id = _make_plant("Get Plant")
        resp = client.get(f"/plants/{plant_id}")
        assert resp.status_code == 200

    def test_get_plant_has_state_field(self):
        plant_id = _make_plant("Get State Plant")
        resp = client.get(f"/plants/{plant_id}")
        data = resp.json()
        assert "state" in data

    def test_get_plant_has_thresholds(self):
        plant_id = _make_plant("Threshold Plant")
        resp = client.get(f"/plants/{plant_id}")
        data = resp.json()
        assert "thresholds" in data
        assert isinstance(data["thresholds"], dict)

    def test_get_plant_has_plant_id(self):
        plant_id = _make_plant("ID Plant")
        resp = client.get(f"/plants/{plant_id}")
        data = resp.json()
        assert data["plant_id"] == plant_id

    def test_get_plant_readings_populated_after_post(self):
        plant_id = _make_plant("Reading Populated Plant")
        _post_reading(plant_id)
        resp = client.get(f"/plants/{plant_id}")
        data = resp.json()
        assert data["readings"] is not None
        assert "soil_pct" in data["readings"]

    def test_get_plant_404_unknown_id(self):
        resp = client.get("/plants/does-not-exist-xyz")
        assert resp.status_code == 404

    def test_get_plant_severity_field(self):
        plant_id = _make_plant("Sev Plant")
        resp = client.get(f"/plants/{plant_id}")
        data = resp.json()
        assert data["severity"] in {"ok", "warn", "critical"}


# ---------------------------------------------------------------------------
# GET /plants/{plant_id}/history
# ---------------------------------------------------------------------------

class TestGetHistory:
    def test_history_returns_200(self):
        plant_id = _make_plant("History Plant")
        resp = client.get(f"/plants/{plant_id}/history")
        assert resp.status_code == 200

    def test_history_returns_list(self):
        plant_id = _make_plant("History List Plant")
        resp = client.get(f"/plants/{plant_id}/history")
        assert isinstance(resp.json(), list)

    def test_history_contains_readings(self):
        plant_id = _make_plant("History Readings Plant")
        _post_reading(plant_id)
        _post_reading(plant_id)
        resp = client.get(f"/plants/{plant_id}/history")
        data = resp.json()
        assert len(data) == 2

    def test_history_point_has_timestamp(self):
        plant_id = _make_plant("History TS Plant")
        _post_reading(plant_id)
        resp = client.get(f"/plants/{plant_id}/history")
        point = resp.json()[0]
        assert "timestamp" in point

    def test_history_point_has_sensor_fields(self):
        plant_id = _make_plant("History Fields Plant")
        _post_reading(plant_id)
        resp = client.get(f"/plants/{plant_id}/history")
        point = resp.json()[0]
        for field in ("soil_pct", "light_lux", "temp_c", "humidity_pct"):
            assert field in point

    def test_history_hours_param(self):
        plant_id = _make_plant("History Hours Plant")
        _post_reading(plant_id)
        resp = client.get(f"/plants/{plant_id}/history?hours=1")
        assert resp.status_code == 200

    def test_history_404_unknown_plant(self):
        resp = client.get("/plants/no-such-plant-abc/history")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /plants
# ---------------------------------------------------------------------------

class TestListPlants:
    def test_list_plants_returns_200(self):
        resp = client.get("/plants")
        assert resp.status_code == 200

    def test_list_plants_returns_list(self):
        resp = client.get("/plants")
        assert isinstance(resp.json(), list)

    def test_list_plants_includes_created(self):
        plant_id = _make_plant("Listed Plant")
        resp = client.get("/plants")
        ids = [p["plant_id"] for p in resp.json()]
        assert plant_id in ids

    def test_list_plants_has_state_field(self):
        _make_plant("State Listed Plant")
        resp = client.get("/plants")
        plants = resp.json()
        assert len(plants) > 0
        assert "state" in plants[0]


# ---------------------------------------------------------------------------
# Species search
# ---------------------------------------------------------------------------

class TestSpeciesSearch:
    def test_species_search_returns_200(self):
        # Will fall back to MiFloraDB (network may not be available in CI)
        resp = client.get("/species/search?q=monstera")
        assert resp.status_code == 200

    def test_species_search_returns_results_key(self):
        resp = client.get("/species/search?q=fern")
        data = resp.json()
        assert "results" in data
        assert "count" in data

    def test_species_search_mifloradb_fallback(self):
        """MiFloraDB should return results for known species."""
        resp = client.get("/species/search?q=aloe")
        data = resp.json()
        assert data["count"] >= 1
