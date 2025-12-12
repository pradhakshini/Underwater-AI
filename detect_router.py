"""Threat detection router."""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from backend.schemas.result_schema import DetectionRequest, DetectionResponse, JobStatusResponse
from backend.api.auth_router import get_current_user
from backend.services.detection_service import enqueue_detection
from backend.database.connection import get_database
from backend.utils.logging_utils import get_logger

logger = get_logger("detect")

router = APIRouter(prefix="/detect", tags=["detection"])


@router.post("", response_model=DetectionResponse)
async def detect_threats(
    request: DetectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Request threat detection on image/video.
    
    Models:
    - yolov8: YOLOv8 object detection
    - clip: CLIP-ViT label refinement
    """
    db = get_database()
    
    # Verify file exists
    file_doc = await db.files.find_one({"file_id": request.file_id})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Create job
    job_id = str(uuid.uuid4())
    result_doc = {
        "job_id": job_id,
        "file_id": request.file_id,
        "user_id": str(current_user["_id"]),
        "job_type": "detection",
        "status": "pending",
        "model_used": request.model,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    await db.results.insert_one(result_doc)
    
    # Enqueue job
    await enqueue_detection(job_id, request.file_id, request.model)
    
    logger.info(f"Detection job created: {job_id} for file {request.file_id}")
    
    return DetectionResponse(
        job_id=job_id,
        status="pending",
        message="Detection job queued"
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_detection_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detection job status."""
    db = get_database()
    result = await db.results.find_one({"job_id": job_id})
    
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if str(result.get("user_id")) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    response_data = {
        "job_id": job_id,
        "status": result.get("status", "unknown"),
        "result": None,
        "error": result.get("error_message")
    }
    
    if result.get("status") == "completed":
        detections = result.get("detections", [])
        response_data["result"] = {
            "detections": detections,
            "annotated_file_path": result.get("annotated_file_path")
        }
    
    return JobStatusResponse(**response_data)

