"""
LangChain-powered chat endpoint for the Growbox project.
Each request pulls *live* sensor readings and feeds them to GPT
via the system prompt, so the assistant can answer with real-time context.
"""

from __future__ import annotations

import os
import csv
import logging
from typing import List, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ──────────────────────── Project Imports ────────────────────────
from data import get_sensor_readings

# ──────────────────────── Environment Setup ────────────────────────
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY is missing in .env")

MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.0

llm = ChatOpenAI(
    model_name=MODEL_NAME,
    temperature=TEMPERATURE,
    streaming=False
)

# ──────────────────────── Pydantic Models ────────────────────────
class ChatReq(BaseModel):
    message: str
    history: List[Dict[str, str]] | None = None  # [{role, content}, …]

class ChatResp(BaseModel):
    reply: str
    history: List[Dict[str, str]]

# ──────────────────────── FastAPI Router ────────────────────────
router = APIRouter(tags=["chat"])

# ──────────────────────── YOLO Detection Setup ────────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
YOLO_DIR = os.path.join(current_dir, "yolo")
DETECTION_CSV = os.path.join(current_dir, "static", "detected_photo", "detected_classes.csv")

# ──────────────────────── Helper Functions ────────────────────────
def _sensor_context() -> str:
    """Return a formatted line of current sensor values."""
    s = get_sensor_readings()
    return (
        f"- Temperature: {s['temperature_c']} °C\n"
        f"- Air Quality (MQ-135): {s['mq135_pct']} %\n"
        f"- Soil Moisture (raw ADC): {s['soil_raw']}\n"
    )

def get_detected_classes() -> List[str]:
    """Read detected classes from the YOLO CSV output."""
    detected_classes = []
    try:
        if os.path.exists(DETECTION_CSV):
            with open(DETECTION_CSV, 'r') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if row and row[0].strip():
                        detected_classes.append(row[0].strip())
    except Exception as e:
        logging.error(f"Error reading detected classes from CSV: {e}")
    return detected_classes

# ──────────────────────── Main Chat Endpoint ────────────────────────
@router.post("/chat", response_model=ChatResp)
async def chat(req: ChatReq) -> ChatResp:
    """
    Generate a GPT response based on the user message, history,
    real-time sensor data, and YOLO detection results.
    """
    try:
        # Get current YOLO detection and sensor data
        detected_classes = get_detected_classes()
        sensor_context = _sensor_context()

        # Compose system message
        system_msg = SystemMessage(
            content=(
                "# Strawberry Plant Growth & Health Assistant\n\n"
                "## Role:\n"
                "You are an AI assistant designed to provide insights about the growth stages and health status of strawberry plants "
                "based on object detection results. Your role is to communicate findings clearly and offer care suggestions where appropriate. "
                "You operate alongside an automated growbox system that manages environmental variables like light, humidity, and irrigation.\n\n"

                "## Input Classes You May Receive:\n"
                "- Healthy Leaf\n"
                "- Flower\n"
                "- Unripe Strawberry\n"
                "- Ripe Strawberry\n"
                "- Powdery Mildew Fruit\n"
                "- Gray Mold\n\n"

                "## Growth Stage Logic:\n"
                "**Stage 1 – Vegetative Phase**: Only leaves detected.\n"
                "**Stage 2 – Flowering Phase**: Flowers detected (with/without fruit).\n"
                "**Stage 3 – Fruit Development Phase**: Unripe strawberries detected.\n"
                "**Stage 4 – Fruit Maturity or Stress Phase**: Ripe/diseased fruits present.\n\n"

                "⚠️ Presence of ripe/diseased fruit alone means Stage 4.\n\n"

                "## Responsibilities:\n"
                "- Identify growth stage\n"
                "- Explain detected classes\n"
                "- Give care suggestions (excluding auto-controlled parameters)\n\n"

                "## Knowledge Base:\n"
                "- Powdery Mildew: white spots in humid areas\n"
                "- Gray Mold: fuzzy mold on ripe fruit\n"
                "- Stages follow natural development: leaf → flower → fruit → ripe\n"
                "- Sanitation reduces disease risk\n"
                "- Presence of fruit = past flowering\n\n"

                "## Communication Style:\n"
                "- Informative and accessible\n"
                "- Always grounded in detections\n"
                "- No speculation unless prompted\n\n"

                "## Current Sensor Readings:\n"
                f"{sensor_context}\n\n"

                "## Latest Detections:\n"
                f"{', '.join(detected_classes) if detected_classes else 'No features detected'}\n"
            )
        )

        # Limit history to last 20 turns
        history = (req.history or [])[-20:]
        lc_history = [
            HumanMessage(content=m["content"]) if m["role"] == "user"
            else AIMessage(content=m["content"])
            for m in history
        ]
        lc_history.append(HumanMessage(content=req.message))

        # Run model
        ai_msg: AIMessage = await llm.ainvoke([system_msg, *lc_history])
        assistant_reply = ai_msg.content.strip()

        # Return with updated history
        new_history = [
            *history,
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": assistant_reply},
        ]

        return ChatResp(reply=assistant_reply, history=new_history)

    except Exception as exc:
        logging.exception("LangChain / OpenAI call failed")
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}")
