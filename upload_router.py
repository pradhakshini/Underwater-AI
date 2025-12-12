"""File upload router."""
import os
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from backend.schemas.upload_schema import UploadResponse
from backend.api.auth_router import get_current_user
from backend.utils.config import settings
from backend.database.connection import get_database
from backend.utils.logging_utils import get_logger

logger = get_logger("upload")

router = APIRouter(prefix="/upload", tags=["upload"])

# Ensure upload directory exists
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload an image or video file.
    
    Supported formats: jpg, jpeg, png, mp4, avi
    Max file size: 50MB
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "video/mp4", "video/avi"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not supported. Allowed: {allowed_types}"
        )
    
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    filename = f"{file_id}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    # Read and save file
    try:
        contents = await file.read()
        if len(contents) > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Store file metadata in database
        db = get_database()
        file_doc = {
            "file_id": file_id,
            "filename": file.filename,
            "file_path": file_path,
            "file_size": len(contents),
            "content_type": file.content_type,
            "user_id": str(current_user["_id"]),
            "created_at": datetime.utcnow()
        }
        await db.files.insert_one(file_doc)
        
        logger.info(f"File uploaded: {file_id} by user {current_user['username']}")
        
        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_size=len(contents),
            content_type=file.content_type
        )
    except Exception as e:
        logger.error(f"Upload error: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/files/{file_id}")
async def get_file_info(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get file information."""
    db = get_database()
    file_doc = await db.files.find_one({"file_id": file_id})
    
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    if str(file_doc.get("user_id")) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "file_id": file_doc["file_id"],
        "filename": file_doc["filename"],
        "file_path": file_doc["file_path"],
        "file_size": file_doc["file_size"],
        "content_type": file_doc["content_type"]
    }
