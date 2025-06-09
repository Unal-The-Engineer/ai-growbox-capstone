"""
Sensor reading utilities for Growbox project.
Reads analog values from MCP3008 via SPI for:
- Temperature (LM35)
- Air Quality (MQ-135)
- Soil Moisture
"""

import spidev
import time

# ─────────────────────────── SPI Setup ───────────────────────────
spi = spidev.SpiDev()
spi.open(0, 0)  # Bus 0, CE0
spi.max_speed_hz = 1_350_000

# ──────────────────────── Low-Level Read Utils ────────────────────────
def _read_channel(channel: int) -> int:
    """Read raw ADC value (0–1023) from given MCP3008 channel."""
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    return ((adc[1] & 3) << 8) + adc[2]

def _lm35_celsius(raw: int) -> float:
    """Convert raw LM35 value to degrees Celsius."""
    voltage = (raw * 3.3) / 1023
    return voltage * 100.0  # 10 mV/°C for LM35

# ──────────────────────── Public Interface ────────────────────────
def get_sensor_readings() -> dict:
    """
    Read all sensor channels and return values in a structured dictionary.
    """
    lm35_raw  = _read_channel(0)
    mq135_raw = _read_channel(1)
    soil_raw  = _read_channel(2)

    temperature_c = _lm35_celsius(lm35_raw)
    mq135_pct     = round(mq135_raw / 1023 * 100, 1)

    # Uncomment below lines for debug output
    # print("-" * 40)
    # print(f"LM35 Temperature : {temperature_c:6.2f} °C")
    # print(f"MQ-135 Gas       : {mq135_pct:5.1f}%  ({mq135_raw}/1023)")
    # print(f"Soil Moisture    : {soil_raw}/1023")
    # print("-" * 40)

    return {
        "temperature_c": round(temperature_c, 2),
        "mq135_raw": mq135_raw,
        "mq135_pct": mq135_pct,
        "soil_raw": soil_raw,
        "timestamp": int(time.time())
    }

# ──────────────────────── CLI Test Hook ────────────────────────
if __name__ == "__main__":
    try:
        get_sensor_readings()
    finally:
        spi.close()
