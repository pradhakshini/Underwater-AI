"""Main FastAPI application."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import uvicorn

from backend.utils.config import settings
from backend.utils.logging_utils import setup_logging, get_logger
from backend.database.connection import connect_to_mongo, close_mongo_connection, get_database
from backend.api import auth_router, upload_router, enhance_router, detect_router, stream_router

# Setup logging
setup_logging(log_level="INFO")
logger = get_logger("main")

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-Based Underwater Image Enhancement & Threat Detection System",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(upload_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(enhance_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(detect_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(stream_router.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Underwater Security System API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db = get_database()
        if db is not None:
            await db.command("ping")
            return {"status": "healthy", "database": "connected"}
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "error": "Database not connected"}
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


# Mount static files for frontend (must be after API routes)
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    # Serve frontend static files (CSS, JS, images)
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Mount uploads and outputs directories for serving images
uploads_dir = Path(settings.UPLOAD_DIR)
outputs_dir = Path(settings.OUTPUT_DIR)
if uploads_dir.exists():
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
if outputs_dir.exists():
    app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")
    
    # Serve frontend HTML files at root (catch-all, must be last)
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_frontend(path: str):
        """Serve frontend HTML files."""
        # Skip API routes and static files
        if path.startswith("api/") or path.startswith("docs") or path.startswith("redoc") or path.startswith("openapi.json") or path in ["health", ""]:
            raise HTTPException(status_code=404, detail="Not found")
        
        if path == "/":
            path = "index.html"
        file_path = frontend_dir / path
        if file_path.exists() and file_path.suffix == ".html":
            return FileResponse(file_path)
        raise HTTPException(status_code=404, detail="Not found")


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("Starting up...")
    await connect_to_mongo()
    logger.info("Application started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down...")
    await close_mongo_connection()
    logger.info("Application stopped")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

