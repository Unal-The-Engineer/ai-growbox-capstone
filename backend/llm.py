"""
Growbox automation core logic.
Uses LangChain + GPT to decide actuator states (fan, light, pump)
based on live sensor data.
"""

import os
import time
import json
import logging
import datetime
import threading
from typing import Dict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from tasmota import cmd as tas_cmd
from shared_state import manual_lock, last_decision
from data import get_sensor_readings
from pump import blink_led

# ───────────────────────────── 1) Environment & LLM ─────────────────────────────
load_dotenv()
if "OPENAI_API_KEY" not in os.environ:
    raise RuntimeError("OPENAI_API_KEY is missing in .env!")

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    model_kwargs={"response_format": {"type": "json_object"}},
)

# ───────────────────────────── 2) System Prompt ─────────────────────────────
SYSTEM_PROMPT = """
ROLE
You control an indoor strawberry growbox.
From one sensor snapshot you must decide whether each actuator is **on** or **off**.

SENSORS (JSON keys you will receive)
- temperature_c : float   # degrees Celsius
- mq135_pct     : float   # gas concentration, 0-100 %
- soil_raw      : int     # soil-moisture raw value, 0-1023
- current_time  : string  # local 24-h clock, “HH:MM”

RULES
1. pump  -> “on” if soil_raw < 400            # soil is too dry
2. fan   -> “on” if temperature_c > 30 OR mq135_pct > 60
3. light -> “on” if 06:00 ≤ current_time < 22:00 AND temperature_c ≤ 35

OUTPUT
Return **one** JSON object only, lowercase keys, e.g.

{
  "fan":   "on",
  "light": "off",
  "pump":  "on"
}

No extra keys, no units, no comments.
Plant safety is your top priority.
"""

# ───────────────────────────── 3) Prompt Template ─────────────────────────────
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Readings:\n{readings_json}")
])

# ───────────────────────────── 4) Pump Trigger Thread ─────────────────────────────
PUMP_DURATION = 2  # seconds

def _run_pump(duration: int = PUMP_DURATION) -> None:
    """Trigger the pump (via GPIO17) and update shared state."""
    last_decision["pump"] = "on"
    blink_led(duration=duration)
    last_decision["pump"] = "off"

# ───────────────────────────── 5) Core Logic ─────────────────────────────
def decide_actuators(readings: Dict) -> Dict[str, str]:
    """
    Send sensor readings to the LLM and get ON/OFF decisions.
    Applies manual locks and executes hardware actions.
    """
    # Add current time to readings
    now_dt = datetime.datetime.now(datetime.timezone.utc).astimezone()
    readings["current_time"] = now_dt.strftime("%H:%M")

    # Compose and send prompt
    messages = prompt.format_messages(
        readings_json=json.dumps(readings, ensure_ascii=False)
    )
    response = llm.invoke(messages)

    try:
        decision = json.loads(response.content)
    except json.JSONDecodeError:
        logging.warning("LLM JSON parse error: %s", response.content)
        return last_decision

    if not all(k in decision for k in ("fan", "light", "pump")):
        logging.warning("Missing keys in decision: %s", decision)
        return last_decision

    final_decision = decision.copy()
    now = time.time()

    # ─── Fan & Light: Controlled via Tasmota ─────
    for dev in ("fan", "light"):
        locked_state, expiry = manual_lock.get(dev, (None, 0))
        if locked_state and now < expiry:
            final_decision[dev] = locked_state  # Respect manual override
            continue

        tas_cmd(dev, "On" if decision[dev] == "on" else "Off")

        if dev in manual_lock and now >= expiry:
            manual_lock.pop(dev, None)

    # ─── Pump: GPIO control ─────
    if decision["pump"] == "on" and last_decision.get("pump") != "on":
        threading.Thread(target=_run_pump, daemon=True).start()
        final_decision["pump"] = "on"
    elif decision["pump"] == "off":
        final_decision["pump"] = "off"

    # Save and return
    last_decision.update(final_decision)
    return final_decision

# ───────────────────────────── 6) Continuous Loop ─────────────────────────────
def run_control_loop(interval: int = 60):
    """
    Repeats forever:
    • read sensors
    • send to LLM
    • act based on returned decisions
    """
    logging.info("Growbox control loop started (interval = %ss)", interval)
    while True:
        readings = get_sensor_readings()
        decision = decide_actuators(readings)
        logging.info("Decision: %s | Readings: %s", decision, readings)
        time.sleep(interval)
