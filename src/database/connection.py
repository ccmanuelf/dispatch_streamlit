"""Database connection management module."""
from typing import Optional
import sqlite3
from pathlib import Path
from dataclasses import dataclass
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration class."""
    db_path: Path
    create_if_missing: bool = True

    def __post_init__(self):
        """Convert string path to Path object if necessary."""
        if isinstance(self.db_path, str):
            self.db_path = Path(self.db_path)

class DatabaseConnection:
    """Database connection manager."""
    
    def __init__(self, config: DatabaseConfig):
        """Initialize database connection manager.
        
        Args:
            config: DatabaseConfig object containing connection settings
        """
        self.config = config
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Initialize database if it doesn't exist."""
        if not self.config.db_path.exists() and self.config.create_if_missing:
            logger.info(f"Creating new database at {self.config.db_path}")
            self.config.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self.get_connection() as conn:
                self._create_tables(conn)
    
    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create database tables.
        
        Args:
            conn: SQLite connection object
        """
        sql = """CREATE TABLE IF NOT EXISTS dispatch_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_type TEXT NOT NULL,
                    work_cell TEXT NOT NULL,
                    job_number TEXT NOT NULL,
                    part_number TEXT NOT NULL,
                    comments TEXT,
                    job_qty REAL NOT NULL,
                    bal_qty REAL NOT NULL,
                    code TEXT NOT NULL,
                    prod_date DATE NOT NULL,
                    est_compl_date DATE,
                    and_on TEXT,
                    m_pc REAL,
                    prod_hr REAL,
                    report_start_date DATE NOT NULL,
                    report_end_date DATE NOT NULL,
                    report_department TEXT NOT NULL,
                    report_creation_datetime DATETIME NOT NULL,
                    upload_date DATETIME NOT NULL,
                    file_name TEXT NOT NULL,
                    processing_status TEXT NOT NULL
                )"""
        try:
            conn.execute(sql)
            conn.commit()
            logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    @contextmanager
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection using context manager.
        
        Yields:
            SQLite connection object
        
        Raises:
            sqlite3.Error: If connection fails
        """
        conn = None
        try:
            conn = sqlite3.connect(self.config.db_path)
            conn.row_factory = sqlite3.Row  # Enable row factory for named columns
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

def get_processed_files(db_config: DatabaseConfig) -> list[dict]:
    """Get list of processed files and their statistics.
    
    Args:
        db_config: Database configuration object
    
    Returns:
        List of dictionaries containing file processing statistics
    """
    db = DatabaseConnection(db_config)
    query = """
    SELECT 
        file_name,
        file_type,
        COUNT(*) as total_rows,
        SUM(CASE WHEN processing_status = 'success' THEN 1 ELSE 0 END) as successful_rows,
        SUM(CASE WHEN processing_status = 'duplicate' THEN 1 ELSE 0 END) as duplicate_rows,
        SUM(CASE WHEN processing_status = 'error' THEN 1 ELSE 0 END) as error_rows,
        MAX(upload_date) as last_upload
    FROM dispatch_data
    GROUP BY file_name, file_type
    ORDER BY last_upload DESC
    """
    
    with db.get_connection() as conn:
        cursor = conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]