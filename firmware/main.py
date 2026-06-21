# =============================================================================
# main.py — Plantchi ESP32 Plant Sensor  |  Entry point
#
# Execution flow (runs on every deep-sleep wake-up):
#
#   1.  Initialise I2C bus and ADC pins
#   2.  Connect to WiFi  (timeout → machine.reset())
#   3.  NTP time sync    (handled inside wifi.connect)
#   4.  Read all sensors
#   5.  POST reading to backend
#   6.  Enter deep sleep for POLL_INTERVAL_S seconds
#
# Deep sleep RESETS all GPIO and RAM state — everything must be re-initialised
# from scratch inside main() on every wake.  Do NOT rely on module-level
# globals persisting between sleeps.
#
# ⚠️  ADC2 reminder: WiFi disables ADC2.  All analog sensors use ADC1 pins
#     (GPIO 32–39) only.  See config.py.
# =============================================================================

import machine
import time
import sys

import config
import sensors
import wifi
import publisher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _init_adc(pin: int) -> machine.ADC:
    """
    Configure an ADC1 pin with 12-bit resolution and full 0–3.3 V range.

    :param pin: GPIO number (must be an ADC1 pin: 32–39).
    :returns:   Configured ``machine.ADC`` object.
    """
    adc = machine.ADC(machine.Pin(pin))
    adc.atten(machine.ADC.ATTN_11DB)    # 0–3.3 V range
    adc.width(machine.ADC.WIDTH_12BIT)  # 12-bit → 0–4095
    return adc


def _init_i2c() -> machine.I2C:
    """
    Initialise the shared I2C bus for BH1750 + SHT31.

    :returns: Ready ``machine.I2C`` object.
    """
    return machine.I2C(
        0,
        sda=machine.Pin(config.I2C_SDA_PIN),
        scl=machine.Pin(config.I2C_SCL_PIN),
        freq=config.I2C_FREQ,
    )


def _deep_sleep_ms(duration_ms: int):
    """Enter deep sleep for *duration_ms* milliseconds."""
    print("[main] entering deep sleep for", duration_ms // 1000, "s")
    machine.deepsleep(duration_ms)
    # Unreachable: deepsleep() never returns — the device resets on wake.


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 48)
    print(" Plantchi v1.0  |  device:", config.DEVICE_ID)
    print("=" * 48)

    # ------------------------------------------------------------------
    # 1. Hardware initialisation
    #    Deep sleep resets GPIO state, so every pin must be re-configured
    #    on each boot.  Do this BEFORE WiFi so ADC reads are ready.
    # ------------------------------------------------------------------
    try:
        i2c      = _init_i2c()
        soil_adc = _init_adc(config.SOIL_ADC_PIN)
        tds_adc  = _init_adc(config.TDS_ADC_PIN)
        print("[main] hardware initialised")
    except Exception as exc:
        print("[main] hardware init failed:", exc)
        # No point continuing without sensors; sleep and retry
        _deep_sleep_ms(config.POLL_INTERVAL_S * 1000)

    # ------------------------------------------------------------------
    # 2 + 3. WiFi connect + NTP sync
    #         wifi.connect() calls machine.reset() if it times out, so
    #         this function only returns on success.
    # ------------------------------------------------------------------
    try:
        ip = wifi.connect(
            ssid=config.WIFI_SSID,
            password=config.WIFI_PASSWORD,
            timeout_s=config.WIFI_TIMEOUT_S,
        )
        print("[main] network ready, IP:", ip)
    except Exception as exc:
        # Unexpected exception (not a timeout — that does machine.reset()).
        print("[main] wifi error:", exc)
        _deep_sleep_ms(config.POLL_INTERVAL_S * 1000)

    # ------------------------------------------------------------------
    # 4. Read all sensors
    #    Individual sensor failures are caught inside sensors.read_all()
    #    and logged; failed channels are returned as None rather than
    #    crashing the whole cycle.
    # ------------------------------------------------------------------
    readings = sensors.read_all(i2c, soil_adc, tds_adc)
    print("[main] readings:", readings)

    # ------------------------------------------------------------------
    # 5. POST to backend
    #    A failure here is non-fatal — we log and proceed to sleep.
    #    Data is lost (no local queue), but the device keeps running.
    # ------------------------------------------------------------------
    try:
        ok = publisher.post_reading(
            backend_url=config.BACKEND_URL,
            device_id=config.DEVICE_ID,
            readings=readings,
        )
        if ok:
            print("[main] reading posted successfully")
        else:
            print("[main] POST returned error (will retry next cycle)")
    except Exception as exc:
        print("[main] publisher exception (non-fatal):", exc)

    # ------------------------------------------------------------------
    # 6. Deep sleep until next poll
    #    deepsleep() resets the chip — execution resumes at main.py again
    #    on the next scheduled wake.
    # ------------------------------------------------------------------
    _deep_sleep_ms(config.POLL_INTERVAL_S * 1000)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

# MicroPython runs main.py directly; the if-guard is kept for clarity and to
# allow importing this module in tests without triggering execution.
if __name__ == "__main__":
    main()
