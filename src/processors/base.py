"""Base class for file processors."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
import csv
import logging
from datetime import datetime

from src.schemas.models import (
    FileType,
    ProcessingStatus,
    DispatchDataCreate,
    FileProcessingSummary
)
from src.utils.date_parser import parse_date, parse_datetime
from sqlite3 import Connection

logger = logging.getLogger(__name__)

class FileProcessor(ABC):
    """Abstract base class for file processors."""

    def __init__(self, file_path: Path, db_conn: Connection):
        """Initialize file processor.
        
        Args:
            file_path: Path to the file to process
            db_conn: Database connection
        """
        self.file_path = Path(file_path)
        self.db_conn = db_conn
        self.summary = FileProcessingSummary(
            file_name=self.file_path.name,
            file_type=self.file_type,
            upload_date=datetime.now()
        )

    @property
    @abstractmethod
    def file_type(self) -> FileType:
        """Get file type enum."""
        pass

    @abstractmethod
    def _extract_metadata(self, reader: csv.reader) -> tuple[str, str]:
        """Extract report start date and department from file.
        
        Args:
            reader: CSV reader object
            
        Returns:
            Tuple of (report_start_date, report_department)
        """
        pass

    @abstractmethod
    def _map_row_to_data(
        self, 
        row: List[str], 
        report_start_date: str,
        report_end_date: str,
        report_department: str,
        report_creation_datetime: str
    ) -> Optional[DispatchDataCreate]:
        """Map CSV row to data model.
        
        Args:
            row: CSV row data
            report_start_date: Report start date
            report_end_date: Report end date
            report_department: Report department
            report_creation_datetime: Report creation datetime
            
        Returns:
            DispatchDataCreate object or None if row should be skipped
        """
        pass

    def row_exists(self, data: Dict[str, Any]) -> bool:
        """Check if row already exists in database.
        
        Args:
            data: Row data to check
            
        Returns:
            True if row exists, False otherwise
        """
        sql = """SELECT COUNT(*) FROM dispatch_data WHERE
                 file_type = ? AND work_cell = ? AND job_number = ? AND
                 part_number = ? AND job_qty = ? AND bal_qty = ? AND
                 code = ? AND prod_date = ? AND est_compl_date = ? AND
                 and_on = ? AND m_pc = ? AND prod_hr = ?"""
                 
        cur = self.db_conn.cursor()
        cur.execute(sql, (
            data["file_type"],
            data["work_cell"],
            data["job_number"],
            data["part_number"],
            data["job_qty"],
            data["bal_qty"],
            data["code"],
            data["prod_date"],
            data["est_compl_date"],
            data["and_on"],
            data["m_pc"],
            data["prod_hr"]
        ))
        return cur.fetchone()[0] > 0

    def process_file(self) -> FileProcessingSummary:
        """Process the file and return summary.
        
        Returns:
            FileProcessingSummary object with processing results
            
        Raises:
            Exception: If file processing fails
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                
                # Extract metadata
                report_start_date, report_department = self._extract_metadata(reader)
                
                # First pass to determine max prod_date
                file.seek(0)
                next(reader)  # Skip first row
                next(reader)  # Skip second row
                
                max_prod_date = None
                for row in reader:
                    try:
                        prod_date = self._get_prod_date(row)
                        if prod_date and (max_prod_date is None or prod_date > max_prod_date):
                            max_prod_date = prod_date
                    except Exception as e:
                        logger.warning(f"Error parsing prod_date: {e}")
                
                report_end_date = max_prod_date or report_start_date
                
                # Reset for second pass
                file.seek(0)
                reader = csv.reader(file)
                next(reader)  # Skip first row
                next(reader)  # Skip second row
                
                for row_num, row in enumerate(reader, start=1):
                    self.summary.total_rows += 1
                    
                    try:
                        # Process row
                        data = self._map_row_to_data(
                            row,
                            report_start_date,
                            report_end_date,
                            report_department,
                            self._get_report_creation_datetime(row)
                        )
                        
                        if data is None:
                            self.summary.skipped_rows += 1
                            continue
                            
                        if self.row_exists(data.model_dump()):
                            self.summary.duplicate_rows += 1
                            continue
                            
                        self._insert_data(data)
                        self.summary.successful_rows += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing row {row_num}: {e}")
                        self.summary.error_rows += 1
                
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            raise
            
        return self.summary

    def _insert_data(self, data: DispatchDataCreate) -> None:
        """Insert data into database.
        
        Args:
            data: Data to insert
        """
        sql = """INSERT INTO dispatch_data (
                    file_type, work_cell, job_number, part_number, comments,
                    job_qty, bal_qty, code, prod_date, est_compl_date, and_on,
                    m_pc, prod_hr, report_start_date, report_end_date,
                    report_department, report_creation_datetime, upload_date,
                    file_name, processing_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                
        try:
            cur = self.db_conn.cursor()
            cur.execute(sql, tuple(data.model_dump().values()))
            self.db_conn.commit()
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Error inserting data: {e}")
            raise

    @abstractmethod
    def _get_prod_date(self, row: List[str]) -> Optional[str]:
        """Extract production date from row.
        
        Args:
            row: CSV row data
            
        Returns:
            Production date string in YYYY-MM-DD format or None
        """
        pass

    @abstractmethod
    def _get_report_creation_datetime(self, row: List[str]) -> Optional[str]:
        """Extract report creation datetime from row.
        
        Args:
            row: CSV row data
            
        Returns:
            Report creation datetime string in YYYY-MM-DD HH:MM:SS format or None
        """
        pass