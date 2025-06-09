"""
Tasmota HTTP API controller for smart actuators (fan, light).
Sends power commands via HTTP to preconfigured Tasmota devices.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# IP addresses for Tasmota-controlled devices
IP = {
    "fan": os.getenv("FAN_IP"),
    "light": os.getenv("LIGHT_IP")
}

def cmd(dev: str, power_cmd: str) -> dict:
    """
    Send a power command to the specified Tasmota device.

    Parameters:
    - dev: "fan" or "light"
    - power_cmd: one of "On", "Off", "Toggle", or ""

    Returns:
    - JSON response from device if available
    - Fallback plain-text wrapped in {"RAW": ...} if not JSON
    - {"error": ...} if connection fails or device/IP is undefined
    """
    if dev not in IP or not IP[dev]:
        raise ValueError(f"Tasmota IP not defined for device: {dev}")

    sep = '%20' if power_cmd else ''  # Avoid trailing %20 if command is empty
    url = f"http://{IP[dev]}/cm?cmnd=Power{sep}{power_cmd}"

    try:
        r = requests.get(url, timeout=4)
    except requests.RequestException as exc:
        return {"error": str(exc)}

    if "application/json" in r.headers.get("content-type", ""):
        return r.json()
    else:
        return {"RAW": r.text}
