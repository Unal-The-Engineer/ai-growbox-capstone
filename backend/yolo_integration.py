"""
YOLO integration API router for Growbox.
Provides endpoints for image capture, latest image retrieval, and class detection info.
"""

import os
import sys
import shutil
import schedule
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

# ─────────────────────── YOLO & Static Path Setup ───────────────────────
current_dir = os.path.dirname(os.path.abspath(__file__))
yolo_dir = os.path.join(current_dir, "yolo")  # YOLO is inside backend now
sys.path.append(yolo_dir)

STATIC_DIR = os.path.join(current_dir, "static")
YOLO_OUTPUT_DIR = os.path.join(STATIC_DIR, "detected_photo")
DETECTION_IMAGE = os.path.join(YOLO_OUTPUT_DIR, "detection_result.jpg")
DETECTION_CSV = os.path.join(YOLO_OUTPUT_DIR, "detected_classes.csv")

os.makedirs(YOLO_OUTPUT_DIR, exist_ok=True)

# ───────────────────────────── FastAPI Router ─────────────────────────────
router = APIRouter(prefix="/yolo", tags=["yolo"])

@router.get("/capture-image")
async def capture_image():
    """
    Manually trigger the YOLO detection pipeline and refresh the scheduler.
    """
    try:
        schedule.clear()  # clear existing job

        # Run pipeline manually
        os.chdir(yolo_dir)
        from yolo.model_pipeline import run_pipeline, CHECK_INTERVAL
        run_pipeline()
        os.chdir(current_dir)

        # Reschedule future executions
        schedule.every(CHECK_INTERVAL).minutes.do(run_pipeline)

        if os.path.exists(DETECTION_IMAGE):
            return {"status": "success", "message": "Image captured and analyzed successfully."}
        else:
            raise HTTPException(status_code=404, detail="Image not created by pipeline.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Capture error: {str(e)}")

@router.get("/latest-image")
async def get_latest_image():
    """
    Return the latest YOLO-annotated image file.
    """
    if os.path.exists(DETECTION_IMAGE):
        return FileResponse(DETECTION_IMAGE)
    else:
        raise HTTPException(status_code=404, detail="No image available.")

@router.get("/detected-classes")
async def get_detected_classes():
    """
    Read the last detected class list from the CSV file.
    """
    if os.path.exists(DETECTION_CSV):
        with open(DETECTION_CSV, "r") as f:
            classes = [line.strip() for line in f if line.strip()]
        return {"classes": classes}
    else:
        raise HTTPException(status_code=404, detail="No class data found.")
