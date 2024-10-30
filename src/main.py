"""Main FastAPI application entry point."""
import uvicorn
from src.api.main import app
from src.config.settings import get_settings

settings = get_settings()

def main():
    """Run the FastAPI application."""
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    main()