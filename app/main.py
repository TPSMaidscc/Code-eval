"""
Main FastAPI application for Bot Repetitions Analysis
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging.config
import os
from pathlib import Path

# Load environment variables from .env file in development
try:
    from dotenv import load_dotenv
    if os.getenv("ENVIRONMENT", "development") == "development":
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass

from app.config import (
    API_TITLE, API_DESCRIPTION, API_VERSION,
    LOGGING_CONFIG, REQUIRED_DIRECTORIES
)
from app.api.routes import router

# Create required directories
for directory in REQUIRED_DIRECTORIES:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Configure logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/health")
def health_check():
    print("✅ /health was called")
    return {"status": "ok"}


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": str(exc) if os.getenv("DEBUG") else "Internal server error"
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(f"Starting {API_TITLE} v{API_VERSION}")
    logger.info("Application startup completed")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Application shutdown completed")

if __name__ == "__main__":
    import uvicorn
    from app.config import API_HOST, API_PORT
    
    uvicorn.run(
        "app.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )
