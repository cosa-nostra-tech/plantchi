"""
models.py — Pydantic request/response models for Plantchi.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Inbound
# ---------------------------------------------------------------------------

class SensorReadings(BaseModel):
    soil_pct: float
    light_lux: float
    temp_c: float
    humidity_pct: float
    conductivity_ppm: Optional[float] = None


class ReadingIn(BaseModel):
    device_id: str = Field(..., description="Maps directly to plant_id")
    timestamp: float = Field(..., description="Unix epoch seconds (float)")
    readings: SensorReadings


class Thresholds(BaseModel):
    min_soil_moist: float = 25.0
    max_soil_moist: float = 65.0
    min_light_lux: float = 500.0
    max_light_lux: float = 8000.0
    min_temp: float = 16.0
    max_temp: float = 32.0
    min_conductivity: float = 100.0
    max_conductivity: float = 2500.0


class PlantCreate(BaseModel):
    name: str
    species_key: Optional[str] = None
    thresholds: Optional[Thresholds] = None


# ---------------------------------------------------------------------------
# Outbound
# ---------------------------------------------------------------------------

class HistoryPoint(BaseModel):
    timestamp: str
    soil_pct: Optional[float]
    light_lux: Optional[float]
    temp_c: Optional[float]
    humidity_pct: Optional[float]


class PlantState(BaseModel):
    plant_id: str
    name: str
    state: str
    severity: str                       # ok | warn | critical
    readings: Optional[dict]            # latest sensor reading
    thresholds: dict
    last_updated: Optional[str]


class ReadingResponse(BaseModel):
    plant_id: str
    state: str
    severity: str
    changed: bool


class PlantSummary(BaseModel):
    plant_id: str
    name: str
    state: str
    severity: str
    last_updated: Optional[str]
