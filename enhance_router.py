"""Image enhancement router."""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from backend.schemas.result_schema import EnhancementRequest, EnhancementResponse, JobStatusResponse
from backend.api.auth_router import get_current_user
from backend.services.enhancement_service import enqueue_enhancement
from backend.database.connection import get_database
from backend.utils.logging_utils import get_logger

logger = get_logger("enhance")

router = APIRouter(prefix="/enhance", tags=["enhancement"])


@router.post("", response_model=EnhancementResponse)
async def enhance_image(
    request: EnhancementRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Request image enhancement.
    
    Methods:
    - unet: U-Net based enhancement
    - watergan: WaterGAN synthesis
    - dino: DINO feature stabilization
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
        "job_type": "enhancement",
        "status": "pending",
        "model_used": request.method,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    await db.results.insert_one(result_doc)
    
    # Enqueue job
    await enqueue_enhancement(job_id, request.file_id, request.method)
    
    logger.info(f"Enhancement job created: {job_id} for file {request.file_id}")
    
    return EnhancementResponse(
        job_id=job_id,
        status="pending",
        message="Enhancement job queued"
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_enhancement_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get enhancement job status."""
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
        response_data["result"] = {
            "enhanced_file_path": result.get("enhanced_file_path"),
            "metrics": result.get("metrics")
        }
    
    return JobStatusResponse(**response_data)

