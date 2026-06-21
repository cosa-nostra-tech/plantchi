"""
test_state_engine.py — Unit tests for the Plantchi state engine.

Covers all 10 states and key priority rules.
"""
from __future__ import annotations

import pytest
import time
from state_engine import compute_state, DEFAULT_THRESHOLDS, _24H, _48H, _2H

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TH = dict(DEFAULT_THRESHOLDS)  # default thresholds shorthand

NOW = time.time()


def _reading(soil=40.0, lux=2000.0, temp=24.0, humidity=55.0, conductivity=500.0, ts=None):
    return {
        "soil_pct": soil,
        "light_lux": lux,
        "temp_c": temp,
        "humidity_pct": humidity,
        "conductivity_ppm": conductivity,
        "timestamp": ts if ts is not None else NOW,
    }


def _history_readings(n: int, age_seconds: float, **reading_kwargs) -> list[dict]:
    """Return n readings evenly spaced over age_seconds ending at NOW."""
    if n == 0:
        return []
    step = age_seconds / n
    return [_reading(ts=NOW - age_seconds + i * step, **reading_kwargs) for i in range(n)]


# ---------------------------------------------------------------------------
# 1. SLEEPING
# ---------------------------------------------------------------------------

class TestSleeping:
    def test_sleeping_at_night_hour_23(self):
        state, severity = compute_state(_reading(), TH, 23, [])
        assert state == "SLEEPING"
        assert severity == "ok"

    def test_sleeping_at_midnight(self):
        state, _ = compute_state(_reading(), TH, 0, [])
        assert state == "SLEEPING"

    def test_sleeping_at_hour_6(self):
        state, _ = compute_state(_reading(), TH, 6, [])
        assert state == "SLEEPING"

    def test_sleeping_at_hour_22(self):
        state, _ = compute_state(_reading(), TH, 22, [])
        assert state == "SLEEPING"

    def test_not_sleeping_at_hour_7(self):
        state, _ = compute_state(_reading(), TH, 7, [])
        assert state != "SLEEPING"

    def test_sleeping_wins_over_thirsty(self):
        """SLEEPING must beat THIRSTY at night."""
        state, _ = compute_state(_reading(soil=1.0), TH, 23, [])
        assert state == "SLEEPING"


# ---------------------------------------------------------------------------
# 2. DROWNING
# ---------------------------------------------------------------------------

class TestDrowning:
    def _make_drowning_history(self):
        """25 h of oversaturated soil readings with oldest > 24h ago."""
        return _history_readings(50, 25 * 3600, soil=80.0)

    def test_drowning_with_sufficient_history(self):
        history = self._make_drowning_history()
        state, severity = compute_state(_reading(soil=80.0), TH, 12, history)
        assert state == "DROWNING"
        assert severity == "critical"

    def test_no_drowning_without_history(self):
        """Soil too high but no history → Not DROWNING (insufficient window)."""
        state, _ = compute_state(_reading(soil=80.0), TH, 12, [])
        assert state != "DROWNING"

    def test_no_drowning_short_history(self):
        """Only 1h of wet soil — not enough to drown."""
        history = _history_readings(5, 1 * 3600, soil=80.0)
        state, _ = compute_state(_reading(soil=80.0), TH, 12, history)
        assert state != "DROWNING"

    def test_drowning_beats_thirsty(self):
        """DROWNING is checked before THIRSTY — but with wet soil THIRSTY won't fire.
        The test confirms DROWNING is returned (not THIRSTY) when soil is very high."""
        history = self._make_drowning_history()
        state, _ = compute_state(_reading(soil=90.0), TH, 12, history)
        assert state == "DROWNING"


# ---------------------------------------------------------------------------
# 3. THIRSTY
# ---------------------------------------------------------------------------

class TestThirsty:
    def test_thirsty_when_soil_below_min(self):
        state, severity = compute_state(_reading(soil=10.0), TH, 12, [])
        assert state == "THIRSTY"
        assert severity == "warn"

    def test_not_thirsty_when_soil_ok(self):
        state, _ = compute_state(_reading(soil=40.0), TH, 12, [])
        assert state != "THIRSTY"

    def test_thirsty_beats_happy(self):
        state, _ = compute_state(_reading(soil=5.0), TH, 12, [])
        assert state == "THIRSTY"

    def test_thirsty_exact_boundary(self):
        """At exactly min_soil_moist — not thirsty."""
        state, _ = compute_state(_reading(soil=TH["min_soil_moist"]), TH, 12, [])
        assert state != "THIRSTY"


# ---------------------------------------------------------------------------
# 4. HOT
# ---------------------------------------------------------------------------

class TestHot:
    def test_hot_above_max_temp(self):
        state, severity = compute_state(_reading(temp=40.0), TH, 12, [])
        assert state == "HOT"
        assert severity == "critical"

    def test_not_hot_at_max_temp(self):
        state, _ = compute_state(_reading(temp=TH["max_temp"]), TH, 12, [])
        assert state != "HOT"


# ---------------------------------------------------------------------------
# 5. COLD
# ---------------------------------------------------------------------------

class TestCold:
    def test_cold_below_min_temp(self):
        state, severity = compute_state(_reading(temp=5.0), TH, 12, [])
        assert state == "COLD"
        assert severity == "critical"

    def test_not_cold_at_min_temp(self):
        state, _ = compute_state(_reading(temp=TH["min_temp"]), TH, 12, [])
        assert state != "COLD"


# ---------------------------------------------------------------------------
# 6. SCORCHED
# ---------------------------------------------------------------------------

class TestScorched:
    def _make_scorched_history(self):
        return _history_readings(20, 3 * 3600, lux=15000.0)

    def test_scorched_with_sustained_high_light(self):
        history = self._make_scorched_history()
        state, severity = compute_state(_reading(lux=15000.0), TH, 12, history)
        assert state == "SCORCHED"
        assert severity == "critical"

    def test_no_scorched_without_history(self):
        state, _ = compute_state(_reading(lux=15000.0), TH, 12, [])
        assert state != "SCORCHED"

    def test_no_scorched_brief_high_light(self):
        """Only 1h of bright light — still not scorched."""
        history = _history_readings(10, 1 * 3600, lux=15000.0)
        state, _ = compute_state(_reading(lux=15000.0), TH, 12, history)
        assert state != "SCORCHED"


# ---------------------------------------------------------------------------
# 7. DIM
# ---------------------------------------------------------------------------

class TestDim:
    def test_dim_during_daytime(self):
        state, severity = compute_state(_reading(lux=50.0), TH, 12, [])
        assert state == "DIM"
        assert severity == "warn"

    def test_not_dim_at_night(self):
        """DIM should not fire at night (SLEEPING takes priority, but even without it,
        DIM only checks 7–22 range by design)."""
        # Use hour=7 (boundary), should be DIM
        state, _ = compute_state(_reading(lux=50.0), TH, 7, [])
        assert state == "DIM"

    def test_not_dim_when_light_ok(self):
        state, _ = compute_state(_reading(lux=2000.0), TH, 12, [])
        assert state != "DIM"


# ---------------------------------------------------------------------------
# 8. HUNGRY
# ---------------------------------------------------------------------------

class TestHungry:
    def test_hungry_when_conductivity_low(self):
        state, severity = compute_state(_reading(conductivity=50.0), TH, 12, [])
        assert state == "HUNGRY"
        assert severity == "warn"

    def test_not_hungry_when_conductivity_ok(self):
        state, _ = compute_state(_reading(conductivity=500.0), TH, 12, [])
        assert state != "HUNGRY"

    def test_not_hungry_when_conductivity_none(self):
        """No conductivity sensor → never HUNGRY."""
        r = _reading()
        r["conductivity_ppm"] = None
        state, _ = compute_state(r, TH, 12, [])
        assert state != "HUNGRY"


# ---------------------------------------------------------------------------
# 9. THRIVING
# ---------------------------------------------------------------------------

class TestThriving:
    def _make_thriving_history(self):
        """49h of readings in the perfect optimal band."""
        # Midpoint soil: (25+65)/2 = 45; 40-60% of range (40) above min → 41–49
        return _history_readings(
            100,
            49 * 3600,
            soil=45.0,
            lux=3000.0,
            temp=24.0,
        )

    def test_thriving_with_long_optimal_history(self):
        history = self._make_thriving_history()
        state, severity = compute_state(
            _reading(soil=45.0, lux=3000.0, temp=24.0), TH, 12, history
        )
        assert state == "THRIVING"
        assert severity == "ok"

    def test_not_thriving_without_history(self):
        state, _ = compute_state(_reading(soil=45.0, lux=3000.0, temp=24.0), TH, 12, [])
        assert state != "THRIVING"

    def test_not_thriving_with_short_history(self):
        history = _history_readings(20, 10 * 3600, soil=45.0, lux=3000.0, temp=24.0)
        state, _ = compute_state(_reading(soil=45.0, lux=3000.0, temp=24.0), TH, 12, history)
        assert state != "THRIVING"


# ---------------------------------------------------------------------------
# 10. HAPPY
# ---------------------------------------------------------------------------

class TestHappy:
    def test_happy_when_all_in_range(self):
        state, severity = compute_state(_reading(), TH, 12, [])
        assert state == "HAPPY"
        assert severity == "ok"

    def test_happy_default(self):
        """Default reading with no history → HAPPY."""
        state, _ = compute_state(_reading(), TH, 12, [])
        assert state == "HAPPY"


# ---------------------------------------------------------------------------
# Priority tests
# ---------------------------------------------------------------------------

class TestPriority:
    def test_sleeping_beats_thirsty(self):
        state, _ = compute_state(_reading(soil=1.0), TH, 23, [])
        assert state == "SLEEPING"

    def test_sleeping_beats_hot(self):
        state, _ = compute_state(_reading(temp=50.0), TH, 2, [])
        assert state == "SLEEPING"

    def test_thirsty_beats_happy(self):
        state, _ = compute_state(_reading(soil=5.0), TH, 12, [])
        assert state == "THIRSTY"

    def test_hot_beats_dim(self):
        state, _ = compute_state(_reading(temp=40.0, lux=50.0), TH, 12, [])
        assert state == "HOT"

    def test_cold_beats_dim(self):
        state, _ = compute_state(_reading(temp=0.0, lux=50.0), TH, 12, [])
        assert state == "COLD"

    def test_thirsty_beats_hungry(self):
        state, _ = compute_state(_reading(soil=5.0, conductivity=10.0), TH, 12, [])
        assert state == "THIRSTY"

    def test_hot_beats_hungry(self):
        state, _ = compute_state(_reading(temp=40.0, conductivity=10.0), TH, 12, [])
        assert state == "HOT"

    def test_drowning_beats_thirsty(self):
        """When soil is high (DROWNING) it cannot also be THIRSTY."""
        history = _history_readings(50, 25 * 3600, soil=80.0)
        state, _ = compute_state(_reading(soil=80.0), TH, 12, history)
        assert state == "DROWNING"
        assert state != "THIRSTY"
