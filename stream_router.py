"""Real-time streaming router."""
import json
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.streaming_service import process_frame_stream
from backend.utils.logging_utils import get_logger

logger = get_logger("stream")

router = APIRouter(prefix="/stream", tags=["streaming"])


@router.websocket("")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time frame processing.
    
    Expected message format:
    {
        "frame": "base64_encoded_image",
        "frame_id": "optional_frame_id"
    }
    
    Response format:
    {
        "frame_id": "frame_id",
        "enhanced_frame": "base64_encoded_enhanced_image",
        "detections": [
            {
                "label": "submarine",
                "confidence": 0.95,
                "bbox": [x, y, w, h]
            }
        ]
    }
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            # Receive frame data
            data = await websocket.receive_text()
            message = json.loads(data)
            
            frame_base64 = message.get("frame")
            frame_id = message.get("frame_id", "unknown")
            
            if not frame_base64:
                await websocket.send_json({
                    "error": "No frame data provided",
                    "frame_id": frame_id
                })
                continue
            
            try:
                # Process frame
                result = await process_frame_stream(frame_base64)
                
                # Send result
                await websocket.send_json({
                    "frame_id": frame_id,
                    "enhanced_frame": result.get("enhanced_frame"),
                    "detections": result.get("detections", []),
                    "metrics": result.get("metrics")
                })
            except Exception as e:
                logger.error(f"Frame processing error: {e}")
                await websocket.send_json({
                    "error": str(e),
                    "frame_id": frame_id
                })
    
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

