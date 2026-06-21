# =============================================================================
# lib/bh1750.py — Minimal MicroPython I2C driver for the BH1750 light sensor
#
# Datasheet: ROHM BH1750FVI
# Default I2C address: 0x23 (ADDR pin LOW) or 0x5C (ADDR pin HIGH)
# =============================================================================

import time


class BH1750:
    """
    BH1750 ambient light sensor driver.

    Usage::

        from machine import I2C, Pin
        from lib.bh1750 import BH1750

        i2c   = I2C(0, sda=Pin(21), scl=Pin(22), freq=400_000)
        light = BH1750(i2c)
        lux   = light.read_lux()
    """

    # Opcodes
    _CMD_POWER_ON           = 0x01
    _CMD_RESET              = 0x07
    _CMD_CONT_HRES_MODE1    = 0x10   # continuous, 1 lux resolution, ~120 ms
    _CMD_CONT_HRES_MODE2    = 0x11   # continuous, 0.5 lux resolution, ~120 ms
    _CMD_ONE_SHOT_HRES_MODE = 0x20   # single shot, then powers down

    # Measurement conversion factor (from datasheet §2.4)
    _SENSITIVITY = 1.2  # lux per count

    def __init__(self, i2c, addr: int = 0x23):
        self._i2c  = i2c
        self._addr = addr
        self._init()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _init(self):
        """Power on and set continuous high-resolution mode 1."""
        self._write(BH1750._CMD_POWER_ON)       # wake from power-down
        time.sleep_ms(10)
        self._write(BH1750._CMD_CONT_HRES_MODE1)
        time.sleep_ms(180)                       # wait for first measurement

    def _write(self, cmd: int):
        self._i2c.writeto(self._addr, bytes([cmd]))

    def _read_raw(self) -> int:
        """Read 2 bytes, combine big-endian → raw count."""
        data = self._i2c.readfrom(self._addr, 2)
        return (data[0] << 8) | data[1]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_lux(self) -> float:
        """
        Return the current ambient light level in lux.

        The sensor is in continuous mode, so no trigger is needed.
        A fresh measurement completes every ~120 ms; calling faster than
        that returns the previous result.
        """
        raw = self._read_raw()
        return raw / self._SENSITIVITY
