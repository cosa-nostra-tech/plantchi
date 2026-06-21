"""
plantbook.py — Open Plantbook API integration + MiFloraDB fallback.

Open Plantbook is a public read API (no auth for read endpoints).
  Search:  GET https://open.plantbook.io/api/v1/plant/search/?alias={query}&limit=10
  Detail:  GET https://open.plantbook.io/api/v1/plant/detail/{pid}/

MiFloraDB fallback covers 10 common species inline.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

PLANTBOOK_BASE = "https://open.plantbook.io/api/v1"
TIMEOUT = 8.0  # seconds

# ---------------------------------------------------------------------------
# Embedded MiFloraDB fallback data — 10 common species
# Keys match our threshold dict schema.
# ---------------------------------------------------------------------------

MIFLORADB: dict[str, dict] = {
    "monstera deliciosa": {
        "display_pid": "Monstera deliciosa",
        "alias": "monstera",
        "min_soil_moist": 20,
        "max_soil_moist": 60,
        "min_light_lux": 1000,
        "max_light_lux": 10000,
        "min_temp": 15,
        "max_temp": 32,
        "min_conductivity": 350,
        "max_conductivity": 2000,
    },
    "epipremnum aureum": {
        "display_pid": "Epipremnum aureum",
        "alias": "pothos",
        "min_soil_moist": 15,
        "max_soil_moist": 50,
        "min_light_lux": 500,
        "max_light_lux": 5000,
        "min_temp": 15,
        "max_temp": 32,
        "min_conductivity": 350,
        "max_conductivity": 2000,
    },
    "spathiphyllum wallisii": {
        "display_pid": "Spathiphyllum wallisii",
        "alias": "peace lily",
        "min_soil_moist": 25,
        "max_soil_moist": 65,
        "min_light_lux": 200,
        "max_light_lux": 3000,
        "min_temp": 18,
        "max_temp": 30,
        "min_conductivity": 350,
        "max_conductivity": 2000,
    },
    "dracaena trifasciata": {
        "display_pid": "Dracaena trifasciata",
        "alias": "snake plant",
        "min_soil_moist": 10,
        "max_soil_moist": 40,
        "min_light_lux": 300,
        "max_light_lux": 5000,
        "min_temp": 15,
        "max_temp": 35,
        "min_conductivity": 350,
        "max_conductivity": 2000,
    },
    "ficus lyrata": {
        "display_pid": "Ficus lyrata",
        "alias": "fiddle leaf fig",
        "min_soil_moist": 25,
        "max_soil_moist": 60,
        "min_light_lux": 2000,
        "max_light_lux": 10000,
        "min_temp": 18,
        "max_temp": 30,
        "min_conductivity": 350,
        "max_conductivity": 2000,
    },
    "echeveria": {
        "display_pid": "Echeveria",
        "alias": "succulent",
        "min_soil_moist": 5,
        "max_soil_moist": 25,
        "min_light_lux": 5000,
        "max_light_lux": 30000,
        "min_temp": 10,
        "max_temp": 35,
        "min_conductivity": 350,
        "max_conductivity": 2000,
    },
    "chlorophytum comosum": {
        "display_pid": "Chlorophytum comosum",
        "alias": "spider plant",
        "min_soil_moist": 20,
        "max_soil_moist": 60,
        "min_light_lux": 500,
        "max_light_lux": 5000,
        "min_temp": 15,
        "max_temp": 30,
        "min_conductivity": 350,
        "max_conductivity": 2000,
    },
    "aloe vera": {
        "display_pid": "Aloe vera",
        "alias": "aloe",
        "min_soil_moist": 5,
        "max_soil_moist": 25,
        "min_light_lux": 3000,
        "max_light_lux": 20000,
        "min_temp": 13,
        "max_temp": 35,
        "min_conductivity": 350,
        "max_conductivity": 2000,
    },
    "phalaenopsis": {
        "display_pid": "Phalaenopsis",
        "alias": "orchid",
        "min_soil_moist": 15,
        "max_soil_moist": 40,
        "min_light_lux": 1000,
        "max_light_lux": 5000,
        "min_temp": 18,
        "max_temp": 28,
        "min_conductivity": 350,
        "max_conductivity": 2000,
    },
    "nephrolepis exaltata": {
        "display_pid": "Nephrolepis exaltata",
        "alias": "fern",
        "min_soil_moist": 30,
        "max_soil_moist": 70,
        "min_light_lux": 500,
        "max_light_lux": 3000,
        "min_temp": 15,
        "max_temp": 25,
        "min_conductivity": 350,
        "max_conductivity": 2000,
    },
}

# Aliases for easy lookup
_ALIAS_INDEX: dict[str, str] = {}
for _pid, _data in MIFLORADB.items():
    _ALIAS_INDEX[_pid.lower()] = _pid
    _ALIAS_INDEX[_data.get("alias", "").lower()] = _pid


def _map_plantbook_to_thresholds(detail: dict) -> dict:
    """Map Open Plantbook detail response to our threshold schema."""
    return {
        "min_soil_moist": detail.get("min_soil_moist", 25),
        "max_soil_moist": detail.get("max_soil_moist", 65),
        "min_light_lux": detail.get("min_light_mmol", 500),  # approximation
        "max_light_lux": detail.get("max_light_mmol", 8000),
        "min_temp": detail.get("min_temp", 16),
        "max_temp": detail.get("max_temp", 32),
        "min_conductivity": detail.get("min_conductivity", 100),
        "max_conductivity": detail.get("max_conductivity", 2500),
    }


def _mifloradb_search(query: str) -> list[dict]:
    query_low = query.lower()
    results = []
    for pid, data in MIFLORADB.items():
        alias = data.get("alias", "")
        if query_low in pid.lower() or query_low in alias.lower():
            results.append({"pid": pid, **data})
    return results


def search_species(query: str) -> list[dict]:
    """
    Search for plant species.

    Tries Open Plantbook first; falls back to MiFloraDB on any error.
    """
    try:
        url = f"{PLANTBOOK_BASE}/plant/search/"
        params = {"alias": query, "limit": 10}
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", data if isinstance(data, list) else [])
            if results:
                return results
    except Exception as exc:
        logger.warning("Open Plantbook search failed, using MiFloraDB fallback: %s", exc)

    return _mifloradb_search(query)


def get_thresholds(species_key: str) -> Optional[dict]:
    """
    Fetch thresholds for a given species key.

    Tries Open Plantbook first; falls back to MiFloraDB on error or 404.
    Returns None if the species is not found anywhere.
    """
    # Try Open Plantbook
    try:
        url = f"{PLANTBOOK_BASE}/plant/detail/{species_key}/"
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return _map_plantbook_to_thresholds(resp.json())
    except Exception as exc:
        logger.warning("Open Plantbook detail failed, using MiFloraDB fallback: %s", exc)

    # MiFloraDB fallback
    key = species_key.lower().strip()
    canonical = _ALIAS_INDEX.get(key)
    if canonical:
        data = MIFLORADB[canonical]
        return {
            "min_soil_moist": data["min_soil_moist"],
            "max_soil_moist": data["max_soil_moist"],
            "min_light_lux": data["min_light_lux"],
            "max_light_lux": data["max_light_lux"],
            "min_temp": data["min_temp"],
            "max_temp": data["max_temp"],
            "min_conductivity": data["min_conductivity"],
            "max_conductivity": data["max_conductivity"],
        }

    return None
