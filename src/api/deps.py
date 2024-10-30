"""FastAPI dependencies module."""
from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlite3 import Connection

from src.database.connection import DatabaseConnection
from src.config.settings import get_settings

settings = get_settings()

async def get_db() -> Generator[Connection, None, None]:
    """Database dependency.
    
    Yields:
        SQLite connection from connection pool
    
    Raises:
        HTTPException: If database connection fails
    """
    try:
        db: DatabaseConnection = DatabaseConnection(
            db_path=settings.get_database_path()
        )
        with db.get_connection() as conn:
            yield conn
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection failed: {str(e)}"
        )

async def verify_file_type(file_type: str) -> str:
    """Verify that the file type is allowed.
    
    Args:
        file_type: Type of file being processed
    
    Returns:
        Verified file type
    
    Raises:
        HTTPException: If file type is not allowed
    """
    if file_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file_type}' not allowed. Must be one of: {settings.ALLOWED_FILE_TYPES}"
        )
    return file_type