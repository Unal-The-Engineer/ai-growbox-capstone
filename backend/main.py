"""
Main FastAPI application for the Growbox project.
Manages system lifespan, actuator endpoints, YOLO & LLM background loops, and WebSocket updates.
"""

import asyncio
import logging
import os
import sys
import threading
import time
from contextlib import asynccontextmanager

from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shared_state import last_decision, manual_lock
from tasmota import cmd as tas_cmd
from data import get_sensor_readings
from llm import run_control_loop
from chat import router as chat_router
from yolo_integration import router as yolo_router
from pump import blink_led  # GPIO water-pump helper

# ─────────────────────── YOLO Path Setup ───────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
yolo_dir = os.path.join(current_dir, "yolo")
sys.path.append(yolo_dir)

# ─────────────────────── Application Lifespan ───────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure logging and start background workers for LLM and YOLO."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # LLM decision control loop
    def _llm_worker():
        run_control_loop(interval=10)

    threading.Thread(target=_llm_worker, daemon=True).start()
    logging.info("LLM control loop thread started.")

    # YOLO detection pipeline loop
    def _yolo_worker():
        try:
            logging.info("Starting YOLO pipeline...")
            os.chdir(yolo_dir)
            from yolo.model_pipeline import run_pipeline, CHECK_INTERVAL
            import schedule

            run_pipeline()  # initial detection
            schedule.every(CHECK_INTERVAL).minutes.do(run_pipeline)
            logging.info(f"YOLO scheduled every {CHECK_INTERVAL} minutes.")

            while True:
                schedule.run_pending()
                time.sleep(1)

        except Exception as e:
            logging.error(f"YOLO pipeline error: {e}")
        finally:
            os.chdir(current_dir)

    threading.Thread(target=_yolo_worker, daemon=True).start()
    logging.info("YOLO pipeline thread started.")

    yield  # Lifespan context end

# ─────────────────────── FastAPI App Setup ───────────────────────
app = FastAPI(title="Growbox API", lifespan=lifespan)
app.include_router(chat_router)
app.include_router(yolo_router)

# ─────────────────────── Static File Mount ───────────────────────
static_dir = os.path.join(current_dir, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ─────────────────────── Helper: Auto Release ───────────────────────
def _auto_release(dev: str, desired: str, minutes: int):
    """Automatically release a manual lock after specified duration."""
    time.sleep(minutes * 60)
    tas_cmd(dev, desired.capitalize())
    manual_lock.pop(dev, None)
    last_decision[dev] = desired

# ─────────────────────── Fan / Light Control ───────────────────────
@app.post("/actuators/{dev}/{action}")
async def toggle_device(
    dev: str,
    action: str,
    payload: dict | None = Body(None)  # Optional {"duration": <minutes>}
):
    """
    Manually control fan or light.
    action  : on | off | toggle
    duration: how long to keep state (0 = indefinitely)
    """
    action = action.lower()
    if action not in ("on", "off", "toggle"):
        return {"error": "action must be on/off/toggle"}

    power_cmd = action.capitalize()
    duration = int(payload.get("duration", 0)) if payload else 0

    result = tas_cmd(dev, power_cmd)

    if dev in ("fan", "light"):
        state = "on" if power_cmd == "On" else "off"
        last_decision[dev] = state

        expiry = float("inf") if duration == 0 else time.time() + duration * 60
        manual_lock[dev] = (state, expiry)

        if duration > 0:
            threading.Thread(
                target=_auto_release,
                args=(dev, "off" if state == "on" else "on", duration),
                daemon=True
            ).start()

    return result

# ─────────────────────── Water Pump Control ───────────────────────
@app.post("/actuators/pump/on")
async def water_pump(payload: dict | None = Body(None)):
    """
    Start the water pump for a specified duration in seconds.
    """
    seconds = int(payload.get("duration", 5)) if payload else 2

    def _run():
        try:
            last_decision["pump"] = "on"
            blink_led(duration=seconds)
        except Exception as e:
            logging.exception("Pump failure: %s", e)
        finally:
            last_decision["pump"] = "off"

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "watering", "duration": seconds}

# ─────────────────────── CORS Configuration ───────────────────────
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ─────────────────────── REST API Endpoints ───────────────────────
@app.get("/actuators")
async def read_actuators():
    """Return the last known actuator states."""
    return last_decision

@app.get("/sensor")
async def read_sensor():
    """Return current LM35, MQ-135, and soil-moisture readings."""
    return get_sensor_readings()

# ─────────────────────── WebSocket Stream ───────────────────────
@app.websocket("/ws/actuators")
async def ws_actuators(websocket: WebSocket):
    """Stream actuator state changes to the frontend."""
    await websocket.accept()
    last_sent = None
    try:
        while True:
            state = last_decision.copy()
            if state != last_sent:
                await websocket.send_json(state)
                last_sent = state
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass

# ─────────────────────── CLI Entrypoint ───────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
