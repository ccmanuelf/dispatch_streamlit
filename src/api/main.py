"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import get_settings
from src.database.connection import DatabaseConnection, DatabaseConfig

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    # Ensure upload directory exists
    settings.ensure_upload_folder()
    
    # Initialize database
    db_config = DatabaseConfig(db_path=settings.get_database_path())
    db = DatabaseConnection(db_config)
    
    # Store database connection in app state
    app.state.db = db

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    # Add cleanup code here if needed
    pass

@app.get("/")
async def root():
    """Root endpoint for health check.
    
    Returns:
        dict: Basic application information
    """
    return {
        "app_name": settings.APP_NAME,
        "status": "healthy",
        "api_version": settings.API_V1_STR
    }