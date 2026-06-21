# =============================================================================
# sensors.py — Plantchi sensor-read functions
#
# Reads:
#   • Soil moisture  (capacitive ADC, GPIO 34)
#   • Ambient light  (BH1750 I2C, addr 0x23)
#   • Temperature    (SHT31-D I2C, addr 0x44)
#   • Humidity       (SHT31-D I2C, addr 0x44)
#   • Conductivity   (Gravity TDS ADC, GPIO 35)
# =============================================================================

from lib.bh1750 import BH1750
from lib.sht31  import SHT31


# ---------------------------------------------------------------------------
# Individual conversion helpers (also useful for unit tests on a PC)
# ---------------------------------------------------------------------------

def soil_pct(adc_raw: int, dry: int, wet: int) -> float:
    """
    Map a raw ADC reading to a soil-moisture percentage.

    Capacitive sensors output *higher* voltage (higher raw ADC count) when dry
    and *lower* voltage when wet — the opposite of resistive sensors.

        dry   (e.g. 3000 raw) → 0 %
        wet   (e.g. 1300 raw) → 100 %

    Values outside the calibrated range are clamped to [0, 100].

    :param adc_raw: Raw ADC reading (0–4095 for 12-bit ESP32 ADC).
    :param dry:     Raw ADC value in dry air (SOIL_DRY in config).
    :param wet:     Raw ADC value fully submerged (SOIL_WET in config).
    :returns:       Moisture percentage, float in [0.0, 100.0].
    """
    if dry == wet:
        return 0.0  # guard against division-by-zero during uncalibrated use
    pct = (dry - adc_raw) / (dry - wet) * 100.0
    return max(0.0, min(100.0, pct))


def tds_ppm(adc_raw: int, vref: float = 3.3, adc_bits: int = 12) -> float:
    """
    Convert a raw TDS ADC reading to a rough PPM (parts-per-million) estimate.

    Formula is derived from the DFRobot Gravity TDS sensor reference design:
        voltage  = adc_raw / (2^adc_bits - 1) * vref
        tds_ppm ≈ (133.42 * V³ − 255.86 * V² + 857.39 * V) * 0.5

    The 0.5 factor converts EC (µS/cm) to TDS (ppm) using the NaCl
    conversion approximation.  For accurate nutrient measurements, use a
    proper EC meter and known-solution calibration.

    :param adc_raw:   Raw ADC reading (0–4095 for 12-bit).
    :param vref:      ADC reference voltage (default 3.3 V).
    :param adc_bits:  ADC resolution in bits (default 12).
    :returns:         Estimated TDS in ppm, float ≥ 0.
    """
    max_adc = (1 << adc_bits) - 1          # 4095 for 12-bit
    voltage  = adc_raw / max_adc * vref
    # DFRobot polynomial (temperature-compensated formula at 25 °C baseline)
    ppm = (133.42 * voltage**3 - 255.86 * voltage**2 + 857.39 * voltage) * 0.5
    return max(0.0, ppm)


# ---------------------------------------------------------------------------
# Main aggregator
# ---------------------------------------------------------------------------

def read_all(i2c, soil_adc, tds_adc) -> dict:
    """
    Read every sensor and return a unified dict.

    :param i2c:      Initialised ``machine.I2C`` object.
    :param soil_adc: Initialised ``machine.ADC`` object for the soil pin.
    :param tds_adc:  Initialised ``machine.ADC`` object for the TDS pin.
    :returns:        Dict with keys:
                       soil_pct        (float, 0–100 %)
                       light_lux       (float, lux)
                       temp_c          (float, °C)
                       humidity_pct    (float, 0–100 %)
                       conductivity_ppm (float, ppm)
    """
    import config  # import here so this module can also be tested offline

    readings = {
        "soil_pct":          None,
        "light_lux":         None,
        "temp_c":            None,
        "humidity_pct":      None,
        "conductivity_ppm":  None,
    }

    # --- Soil moisture (ADC) -------------------------------------------
    try:
        raw_soil        = soil_adc.read()
        readings["soil_pct"] = soil_pct(raw_soil, config.SOIL_DRY, config.SOIL_WET)
    except Exception as exc:
        print("[sensors] soil read failed:", exc)

    # --- Conductivity / TDS (ADC) --------------------------------------
    try:
        raw_tds = tds_adc.read()
        readings["conductivity_ppm"] = tds_ppm(raw_tds)
    except Exception as exc:
        print("[sensors] TDS read failed:", exc)

    # --- Light (BH1750 I2C) --------------------------------------------
    try:
        light = BH1750(i2c)
        readings["light_lux"] = light.read_lux()
    except Exception as exc:
        print("[sensors] BH1750 read failed:", exc)

    # --- Temperature & Humidity (SHT31-D I2C) --------------------------
    try:
        sht = SHT31(i2c)
        temp_c, hum_pct = sht.read_both()
        readings["temp_c"]       = temp_c
        readings["humidity_pct"] = hum_pct
    except Exception as exc:
        print("[sensors] SHT31 read failed:", exc)

    return readings
