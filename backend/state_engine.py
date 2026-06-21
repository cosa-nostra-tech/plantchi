"""
state_engine.py — Emotional state computation for Plantchi.

Priority order (highest → lowest):
  1. SLEEPING   — nighttime hours (22:00–06:59)
  2. DROWNING   — soil oversaturated for >24 h
  3. THIRSTY    — soil below minimum
  4. HOT        — temperature above maximum
  5. COLD       — temperature below minimum
  6. SCORCHED   — light too high, sustained >2 h
  7. DIM        — light too low during daytime
  8. HUNGRY     — conductivity below minimum
  9. THRIVING   — all optimal, sustained >48 h
 10. HAPPY      — all within thresholds
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS: dict = {
    "min_soil_moist": 25,
    "max_soil_moist": 65,
    "min_light_lux": 500,
    "max_light_lux": 8000,
    "min_temp": 16,
    "max_temp": 32,
    "min_conductivity": 100,
    "max_conductivity": 2500,
}

# State → severity mapping
SEVERITY: dict[str, str] = {
    "SLEEPING": "ok",
    "DROWNING": "critical",
    "THIRSTY": "warn",
    "HOT": "critical",
    "COLD": "critical",
    "SCORCHED": "critical",
    "DIM": "warn",
    "HUNGRY": "warn",
    "THRIVING": "ok",
    "HAPPY": "ok",
}

# How long history entries are valid for sustained-condition checks (seconds)
_24H = 24 * 3600
_48H = 48 * 3600
_2H = 2 * 3600


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts_to_epoch(ts: str | float | int | None) -> Optional[float]:
    """Convert ISO-8601 string or numeric epoch to float epoch seconds."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    # Try ISO-8601
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(ts, fmt)
            return dt.replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def _now_epoch() -> float:
    return datetime.now(timezone.utc).timestamp()


def _sustained_above(
    field: str,
    threshold: float,
    history: list[dict],
    current_value: float,
    current_ts: float,
    window_seconds: float,
) -> bool:
    """
    Return True if *every* history point within the window has field > threshold,
    AND the window actually spans the required duration.
    Requires at least one history point older than window_seconds ago to confirm
    sustained exceedance.
    """
    cutoff = current_ts - window_seconds
    # Collect readings within the window (including current)
    relevant = [r for r in history if (_ts_to_epoch(r.get("timestamp")) or 0) >= cutoff]

    # Need at least one reading that is old enough to anchor the window
    oldest_available = min(
        (_ts_to_epoch(r.get("timestamp")) or current_ts for r in history),
        default=current_ts,
    )
    if current_ts - oldest_available < window_seconds:
        # We don't have enough history to confirm sustained condition
        return False

    # All readings in window must exceed threshold
    for r in relevant:
        val = r.get(field)
        if val is None:
            return False
        if val <= threshold:
            return False

    return current_value > threshold


def _sustained_in_optimal(
    reading: dict,
    thresholds: dict,
    history: list[dict],
    current_ts: float,
    window_seconds: float,
) -> bool:
    """
    Return True if all sensors have been within their optimal ranges for
    the entire window.  "Upper-optimal" for soil/light means in the band
    [40-60% of range above min], temp within 2°C of midpoint, lux within
    optimal range.
    """
    th = thresholds

    def soil_optimal(v):
        r = th["max_soil_moist"] - th["min_soil_moist"]
        low = th["min_soil_moist"] + 0.4 * r
        high = th["min_soil_moist"] + 0.6 * r
        return low <= v <= high

    def temp_optimal(v):
        mid = (th["min_temp"] + th["max_temp"]) / 2
        return abs(v - mid) <= 2

    def lux_optimal(v):
        return th["min_light_lux"] <= v <= th["max_light_lux"]

    # Check current reading
    if reading.get("soil_pct") is None or not soil_optimal(reading["soil_pct"]):
        return False
    if reading.get("temp_c") is None or not temp_optimal(reading["temp_c"]):
        return False
    if reading.get("light_lux") is None or not lux_optimal(reading["light_lux"]):
        return False

    cutoff = current_ts - window_seconds
    relevant = [r for r in history if (_ts_to_epoch(r.get("timestamp")) or 0) >= cutoff]

    oldest = min(
        (_ts_to_epoch(r.get("timestamp")) or current_ts for r in history),
        default=current_ts,
    )
    if current_ts - oldest < window_seconds:
        return False

    for r in relevant:
        if r.get("soil_pct") is None or not soil_optimal(r["soil_pct"]):
            return False
        if r.get("temp_c") is None or not temp_optimal(r["temp_c"]):
            return False
        if r.get("light_lux") is None or not lux_optimal(r["light_lux"]):
            return False

    return True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_state(
    reading: dict,
    thresholds: dict,
    current_hour: int,
    history: list[dict],
) -> tuple[str, str]:
    """
    Compute the plant's emotional state.

    Parameters
    ----------
    reading      : dict with keys soil_pct, light_lux, temp_c, humidity_pct,
                   conductivity_ppm (optional), and optionally 'timestamp'
    thresholds   : dict — uses DEFAULT_THRESHOLDS for any missing keys
    current_hour : int 0-23 (local hour at the plant location)
    history      : list of dicts, same schema as reading, ordered oldest→newest

    Returns
    -------
    (state_name, severity) tuple
    """
    th = {**DEFAULT_THRESHOLDS, **thresholds}

    soil = reading.get("soil_pct")
    lux = reading.get("light_lux")
    temp = reading.get("temp_c")
    conductivity = reading.get("conductivity_ppm")

    # Determine current timestamp (epoch)
    current_ts = _ts_to_epoch(reading.get("timestamp")) or _now_epoch()

    # ------------------------------------------------------------------
    # 1. SLEEPING — night hours 22:00 – 06:59
    # ------------------------------------------------------------------
    if current_hour >= 22 or current_hour < 7:
        return "SLEEPING", SEVERITY["SLEEPING"]

    # ------------------------------------------------------------------
    # 2. DROWNING — oversaturated soil for > 24 h
    # ------------------------------------------------------------------
    if soil is not None and soil > th["max_soil_moist"]:
        if _sustained_above(
            "soil_pct", th["max_soil_moist"], history, soil, current_ts, _24H
        ):
            return "DROWNING", SEVERITY["DROWNING"]

    # ------------------------------------------------------------------
    # 3. THIRSTY — soil below minimum
    # ------------------------------------------------------------------
    if soil is not None and soil < th["min_soil_moist"]:
        return "THIRSTY", SEVERITY["THIRSTY"]

    # ------------------------------------------------------------------
    # 4. HOT — temperature above maximum
    # ------------------------------------------------------------------
    if temp is not None and temp > th["max_temp"]:
        return "HOT", SEVERITY["HOT"]

    # ------------------------------------------------------------------
    # 5. COLD — temperature below minimum
    # ------------------------------------------------------------------
    if temp is not None and temp < th["min_temp"]:
        return "COLD", SEVERITY["COLD"]

    # ------------------------------------------------------------------
    # 6. SCORCHED — light too high, sustained > 2 h
    # ------------------------------------------------------------------
    if lux is not None and lux > th["max_light_lux"]:
        if _sustained_above(
            "light_lux", th["max_light_lux"], history, lux, current_ts, _2H
        ):
            return "SCORCHED", SEVERITY["SCORCHED"]

    # ------------------------------------------------------------------
    # 7. DIM — light too low during daytime (07:00–21:59)
    # ------------------------------------------------------------------
    if 7 <= current_hour < 22:
        if lux is not None and lux < th["min_light_lux"]:
            return "DIM", SEVERITY["DIM"]

    # ------------------------------------------------------------------
    # 8. HUNGRY — conductivity below minimum (only if sensor present)
    # ------------------------------------------------------------------
    if conductivity is not None and conductivity < th["min_conductivity"]:
        return "HUNGRY", SEVERITY["HUNGRY"]

    # ------------------------------------------------------------------
    # 9. THRIVING — all in upper-optimal range for > 48 h
    # ------------------------------------------------------------------
    if _sustained_in_optimal(reading, th, history, current_ts, _48H):
        return "THRIVING", SEVERITY["THRIVING"]

    # ------------------------------------------------------------------
    # 10. HAPPY — all within thresholds, no issues
    # ------------------------------------------------------------------
    return "HAPPY", SEVERITY["HAPPY"]
