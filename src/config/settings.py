"""Application configuration settings."""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings.

    Attributes:
        APP_NAME: Name of the application
        API_V1_STR: API version string
        DATABASE_URL: SQLite database URL (can be updated at runtime)
        UPLOAD_FOLDER: Path to store temporary uploaded files
        ALLOWED_FILE_TYPES: List of allowed file types
        MAX_UPLOAD_SIZE: Maximum file size in bytes (default: 100MB)
        TEST_MODE: Whether to run in test mode
        TEST_ROWS: Number of rows to process in test mode
    """
    APP_NAME: str = "Production Data Manager"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./production_data.db"
    UPLOAD_FOLDER: Path = Path("./uploads")
    ALLOWED_FILE_TYPES: list[str] = ["Assy", "Fabcut", "LP", "SEW-DC", "SEW-FB"]
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    TEST_MODE: bool = False
    TEST_ROWS: Optional[int] = None

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = True

    def get_database_path(self) -> Path:
        """Get database path from DATABASE_URL."""
        return Path(self.DATABASE_URL.replace("sqlite:///", ""))

    def set_database_path(self, path: Path) -> None:
        """Update database path.

        Args:
            path: New database path
        """
        self.DATABASE_URL = f"sqlite:///{path}"

    def ensure_upload_folder(self) -> None:
        """Create upload folder if it doesn't exist."""
        self.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    @classmethod
    def detect_file_type(cls, filename: str) -> Optional[str]:
        """Detect file type from filename.

        Args:
            filename: Name of the file

        Returns:
            Detected file type or None if not found
        """
        for file_type in cls.ALLOWED_FILE_TYPES:
            if file_type in filename:
                return file_type
        return None

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
