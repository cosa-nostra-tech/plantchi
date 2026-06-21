# =============================================================================
# config.py — Plantchi ESP32 Plant Sensor
# All user-configurable constants. Edit this file before flashing.
# =============================================================================

# ----------------------------------------------------------------------------
# WiFi
# ----------------------------------------------------------------------------
WIFI_SSID     = "YourSSID"
WIFI_PASSWORD = "YourPassword"
WIFI_TIMEOUT_S = 30          # seconds before giving up and calling machine.reset()

# ----------------------------------------------------------------------------
# Backend
# ----------------------------------------------------------------------------
BACKEND_URL = "http://plantchi.local:8000"  # mDNS hostname, or set Railway URL
DEVICE_ID   = "plant-01"                    # unique identifier for this unit

# ----------------------------------------------------------------------------
# Sensor pin assignments
# NOTE: ADC2 pins (GPIO 0,2,4,12,13,14,15,25,26,27) are DISABLED when WiFi
#       is active. Always use ADC1 pins (GPIO 32-39) for analog reads.
# ----------------------------------------------------------------------------
SOIL_ADC_PIN = 34   # ADC1_CH6 — capacitive soil moisture sensor
TDS_ADC_PIN  = 35   # ADC1_CH7 — Gravity TDS conductivity sensor

I2C_SDA_PIN  = 21   # BH1750 + SHT31 shared SDA
I2C_SCL_PIN  = 22   # BH1750 + SHT31 shared SCL
I2C_FREQ     = 400_000  # 400 kHz fast-mode

# ----------------------------------------------------------------------------
# Calibration  — run a calibration sketch once per unit and update these.
# SOIL_DRY : raw ADC reading with sensor in open air
# SOIL_WET : raw ADC reading with sensor fully submerged in water
# ----------------------------------------------------------------------------
SOIL_DRY = 3000   # higher raw value  → driest (capacitive sensors invert)
SOIL_WET = 1300   # lower  raw value  → wettest

# ----------------------------------------------------------------------------
# Polling / deep-sleep
# ----------------------------------------------------------------------------
POLL_INTERVAL_S = 900   # 15 minutes between readings (deep sleep)

# ----------------------------------------------------------------------------
# NTP
# ----------------------------------------------------------------------------
NTP_HOST = "pool.ntp.org"
