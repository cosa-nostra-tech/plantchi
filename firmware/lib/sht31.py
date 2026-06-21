# =============================================================================
# lib/sht31.py — Minimal MicroPython I2C driver for the SHT31-D
#
# Datasheet: Sensirion SHT3x-DIS
# Default I2C address: 0x44 (ADDR pin LOW) or 0x45 (ADDR pin HIGH)
# =============================================================================

import time


class SHT31:
    """
    SHT31-D temperature & relative-humidity sensor driver.

    Usage::

        from machine import I2C, Pin
        from lib.sht31 import SHT31

        i2c    = I2C(0, sda=Pin(21), scl=Pin(22), freq=400_000)
        sht    = SHT31(i2c)
        temp_c, hum_pct = sht.read_both()
    """

    # Single-shot measurement commands (MSB, LSB)
    # 0x2C = clock-stretching enabled; 0x06 = high repeatability
    _CMD_MEAS_CLOCKSTR_HIGH = (0x2C, 0x06)

    # Soft-reset command
    _CMD_SOFT_RESET = (0x30, 0xA2)

    # CRC-8 parameters (Sensirion proprietary)
    _CRC_POLY = 0x31
    _CRC_INIT = 0xFF

    def __init__(self, i2c, addr: int = 0x44):
        self._i2c  = i2c
        self._addr = addr

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _write_cmd(self, cmd: tuple):
        self._i2c.writeto(self._addr, bytes(cmd))

    def _crc8(self, data: bytes) -> int:
        """
        Compute Sensirion CRC-8 over *data*.
        Polynomial: 0x31 (x^8 + x^5 + x^4 + 1), init: 0xFF, no reflect.
        """
        crc = self._CRC_INIT
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ self._CRC_POLY) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return crc

    def _measure(self) -> tuple:
        """
        Trigger a single-shot high-repeatability measurement and return
        (raw_temp: int, raw_hum: int).

        Raises ValueError if CRC validation fails.
        """
        self._write_cmd(self._CMD_MEAS_CLOCKSTR_HIGH)
        # Clock-stretching holds SCL low until data is ready (~15 ms max
        # for high repeatability).  Give the sensor a generous margin.
        time.sleep_ms(20)

        data = self._i2c.readfrom(self._addr, 6)
        # Byte layout: [TH, TL, T_CRC, HH, HL, H_CRC]
        raw_temp = (data[0] << 8) | data[1]
        raw_hum  = (data[3] << 8) | data[4]

        # CRC validation
        if self._crc8(data[0:2]) != data[2]:
            raise ValueError("SHT31: temperature CRC mismatch")
        if self._crc8(data[3:5]) != data[5]:
            raise ValueError("SHT31: humidity CRC mismatch")

        return raw_temp, raw_hum

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_both(self) -> tuple:
        """
        Return ``(temp_c: float, humidity_pct: float)`` in a single I2C
        transaction.
        """
        raw_temp, raw_hum = self._measure()
        temp_c       = -45.0 + 175.0 * raw_temp / 65535.0
        humidity_pct = 100.0 * raw_hum  / 65535.0
        # Clamp humidity to physical range
        humidity_pct = max(0.0, min(100.0, humidity_pct))
        return temp_c, humidity_pct

    def read_temp(self) -> float:
        """Return temperature in degrees Celsius."""
        temp_c, _ = self.read_both()
        return temp_c

    def read_humidity(self) -> float:
        """Return relative humidity in percent (0–100)."""
        _, humidity_pct = self.read_both()
        return humidity_pct

    def reset(self):
        """Issue a soft reset (takes ~2 ms)."""
        self._write_cmd(self._CMD_SOFT_RESET)
        time.sleep_ms(2)
