"""Result model for storing processing results."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId
from backend.models.user_model import PyObjectId


class Detection(BaseModel):
    """Detection result."""
    label: str
    confidence: float
    bbox: List[float] = Field(..., description="Bounding box [x, y, w, h]")
    class_id: Optional[int] = None


class ProcessingResult(BaseModel):
    """Processing result model."""
    id: Optional[PyObjectId] = None
    file_id: str
    user_id: Optional[str] = None
    job_type: str = Field(..., description="Type: 'enhancement' or 'detection'")
    status: str = Field(default="pending", description="pending, processing, completed, failed")
    
    # Enhancement results
    enhanced_file_path: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    
    # Detection results
    detections: Optional[List[Detection]] = None
    annotated_file_path: Optional[str] = None
    
    # Metadata
    processing_time: Optional[float] = None
    model_used: Optional[str] = None
    error_message: Optional[str] = None
    
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }
