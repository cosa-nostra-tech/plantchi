# =============================================================================
# wifi.py — WiFi connection with timeout and NTP sync
#
# ⚠️  ADC2 WARNING: The ESP32 WiFi radio shares ADC2.
#     All analog reads MUST use ADC1 pins (GPIO 32–39).
#     This module enables WiFi — after this runs, ADC2 is unavailable.
# =============================================================================

import time
import network
import ntptime
import machine

import config  # WIFI_SSID, WIFI_PASSWORD, WIFI_TIMEOUT_S, NTP_HOST


def connect(ssid: str = None, password: str = None, timeout_s: int = None) -> str:
    """
    Connect to WiFi.

    Blocks until connected or *timeout_s* seconds elapse.  On timeout the
    function calls ``machine.reset()`` so the watchdog never has to — the
    device simply reboots and tries again on the next wake.

    :param ssid:      WiFi network name.  Defaults to ``config.WIFI_SSID``.
    :param password:  WiFi password.     Defaults to ``config.WIFI_PASSWORD``.
    :param timeout_s: Seconds to wait.   Defaults to ``config.WIFI_TIMEOUT_S``.
    :returns:         Assigned IP address string on success.
    :raises RuntimeError: (never actually raised — the device resets instead)
    """
    ssid      = ssid      or config.WIFI_SSID
    password  = password  or config.WIFI_PASSWORD
    timeout_s = timeout_s if timeout_s is not None else config.WIFI_TIMEOUT_S

    sta = network.WLAN(network.STA_IF)

    # Power up the interface
    if not sta.active():
        sta.active(True)
        time.sleep_ms(100)

    # If somehow already connected, return early
    if sta.isconnected():
        ip = sta.ifconfig()[0]
        print("[wifi] already connected, IP:", ip)
        _sync_ntp()
        return ip

    print("[wifi] connecting to", ssid, "…")
    sta.connect(ssid, password)

    deadline = time.time() + timeout_s
    while not sta.isconnected():
        if time.time() > deadline:
            print("[wifi] timeout after", timeout_s, "s — resetting device")
            sta.active(False)
            time.sleep_ms(200)
            machine.reset()
            # Unreachable — machine.reset() never returns
        time.sleep_ms(500)
        print("[wifi] status:", sta.status())

    ip = sta.ifconfig()[0]
    print("[wifi] connected, IP:", ip)

    _sync_ntp()
    return ip


def disconnect():
    """Politely disconnect from WiFi (optional — deep sleep drops it anyway)."""
    sta = network.WLAN(network.STA_IF)
    if sta.isconnected():
        sta.disconnect()
    sta.active(False)
    print("[wifi] disconnected")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sync_ntp():
    """
    Synchronise the ESP32 RTC to NTP time.

    Failure here is non-fatal — the device keeps running with whatever time
    it has (epoch 0 after cold boot).  Web API timestamps will be wrong but
    readings will still be stored.
    """
    try:
        ntptime.host = config.NTP_HOST
        # ntptime.settime() can block for several seconds; retry once
        for attempt in range(2):
            try:
                ntptime.settime()
                print("[wifi] NTP sync OK")
                return
            except OSError as exc:
                print("[wifi] NTP attempt", attempt + 1, "failed:", exc)
                time.sleep_ms(1000)
    except Exception as exc:
        print("[wifi] NTP sync error (non-fatal):", exc)
