# =============================================================================
# publisher.py — HTTP POST sensor readings to the Plantchi backend
#
# Uses urequests (bundled with MicroPython) — NOT the CPython `requests` lib.
# Key differences to be aware of:
#   • No session object
#   • No connection pooling
#   • MUST call response.close() after every request to free socket
#   • No automatic JSON decode — use ujson manually if needed
# =============================================================================

import ujson
import time

try:
    import urequests as requests
except ImportError:
    # Some MicroPython builds expose it as 'requests'
    import requests  # type: ignore


def post_reading(backend_url: str, device_id: str, readings: dict) -> bool:
    """
    POST one sensor reading snapshot to ``POST /readings``.

    :param backend_url: Root URL of the backend, e.g. ``"http://plantchi.local:8000"``.
                        No trailing slash.
    :param device_id:   Unique identifier for this sensor node.
    :param readings:    Dict produced by ``sensors.read_all()``.
    :returns:           ``True`` if the server returned HTTP 2xx, ``False`` otherwise.
    """
    url = backend_url.rstrip("/") + "/readings"

    # Build payload --------------------------------------------------------
    # Include a Unix timestamp so the server can record when the reading was
    # taken even if it arrives late.  time.time() returns 0 on cold boot if
    # NTP hasn't synced yet — the server should treat 0 as "unknown".
    payload = {
        "device_id":          device_id,
        "timestamp":          time.time(),
        "soil_pct":           readings.get("soil_pct"),
        "light_lux":          readings.get("light_lux"),
        "temp_c":             readings.get("temp_c"),
        "humidity_pct":       readings.get("humidity_pct"),
        "conductivity_ppm":   readings.get("conductivity_ppm"),
    }

    # Serialise to JSON — None values become JSON null which is valid.
    body = ujson.dumps(payload)
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
    }

    print("[publisher] POST", url)
    print("[publisher] payload:", body)

    response = None
    try:
        response = requests.post(url, data=body, headers=headers)
        status = response.status_code
        print("[publisher] response:", status)

        if 200 <= status < 300:
            return True

        # Log non-2xx but don't crash — we'll go to sleep anyway
        print("[publisher] unexpected status", status)
        return False

    except Exception as exc:
        print("[publisher] POST failed:", exc)
        return False

    finally:
        # CRITICAL: always close the response to release the socket.
        # Failing to do this on MicroPython leaks the connection and will
        # exhaust available sockets after a few cycles.
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
