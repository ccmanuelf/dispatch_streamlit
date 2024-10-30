"""Fabcut file processor implementation."""
from typing import List, Optional, Tuple
import csv
from pathlib import Path
from sqlite3 import Connection

from src.processors.base import FileProcessor
from src.schemas.models import FileType, DispatchDataCreate, ProcessingStatus
from src.utils.date_parser import parse_date, parse_datetime

class FabcutFileProcessor(FileProcessor):
    """Processor for Fabcut files."""

    @property
    def file_type(self) -> FileType:
        """Get file type."""
        return FileType.FABCUT

    def _extract_metadata(self, reader: csv.reader) -> Tuple[str, str]:
        """Extract report start date and department from file.
        
        Args:
            reader: CSV reader object
            
        Returns:
            Tuple of (report_start_date, report_department)
            
        Raises:
            ValueError: If required metadata cannot be extracted
        """
        try:
            # First row contains report start date in second column
            report_start_date = parse_date(next(reader)[1])
            if not report_start_date:
                raise ValueError("Invalid report start date")
            
            # Second row contains department in third column
            report_department = next(reader)[2]
            if not report_department:
                raise ValueError("Missing department information")
            
            return report_start_date, report_department
            
        except (StopIteration, IndexError) as e:
            raise ValueError(f"Failed to extract metadata: {str(e)}")

    def _get_prod_date(self, row: List[str]) -> Optional[str]:
        """Extract production date from row.
        
        Args:
            row: CSV row data
            
        Returns:
            Production date string in YYYY-MM-DD format or None
        """
        try:
            return parse_date(row[22])  # prod_date is in column 23 (index 22)
        except IndexError:
            return None

    def _get_report_creation_datetime(self, row: List[str]) -> Optional[str]:
        """Extract report creation datetime from row.
        
        Args:
            row: CSV row data
            
        Returns:
            Report creation datetime string in YYYY-MM-DD HH:MM:SS format or None
        """
        try:
            return parse_datetime(row[25])  # report_creation_datetime is in column 26 (index 25)
        except IndexError:
            return None

    def _convert_to_float(self, value: str) -> Optional[float]:
        """Convert string to float, handling accounting notation.
        
        Args:
            value: String value to convert
            
        Returns:
            Float value or None if conversion fails
            
        Example:
            >>> _convert_to_float("123")
            123.0
            >>> _convert_to_float("(123)")
            -123.0
        """
        if not value or not isinstance(value, str):
            return None
            
        value = value.strip()
        if not value:
            return None
            
        try:
            # Try direct conversion first
            return float(value)
        except ValueError:
            # Check for accounting notation
            if value.startswith('(') and value.endswith(')'):
                try:
                    return -float(value[1:-1])
                except ValueError:
                    return None
            return None

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
        # Check if row is empty (columns 17-25 are blank)
        if all(not cell.strip() for cell in row[17:25]):
            return None
            
        try:
            # Extract required dates
            prod_date = parse_date(row[22])
            if not prod_date:
                return None
            
            # Create data object
            data = DispatchDataCreate(
                file_type=self.file_type.db_value,
                work_cell=row[16],        # Different column mapping for Fabcut files
                job_number=row[17],
                part_number=row[18],
                comments=None,            # Fabcut files don't have comments
                job_qty=self._convert_to_float(row[19]),
                bal_qty=self._convert_to_float(row[20]),
                code=row[21],
                prod_date=prod_date,
                est_compl_date=None,      # Fabcut files don't have estimated completion date
                and_on=None,              # Fabcut files don't have and_on field
                m_pc=self._convert_to_float(row[23]) if row[23] else None,
                prod_hr=self._convert_to_float(row[24]) if row[24] else None,
                report_start_date=report_start_date,
                report_end_date=report_end_date,
                report_department=report_department,
                report_creation_datetime=report_creation_datetime,
                file_name=self.file_path.name,
                processing_status=ProcessingStatus.SUCCESS
            )
            
            return data
            
        except Exception as e:
            raise ValueError(f"Error mapping row data: {str(e)}")


def create_fabcut_processor(file_path: Path, db_conn: Connection) -> FabcutFileProcessor:
    """Factory function to create Fabcut file processor.
    
    Args:
        file_path: Path to the Fabcut file
        db_conn: Database connection
        
    Returns:
        Configured FabcutFileProcessor instance
    """
    return FabcutFileProcessor(file_path, db_conn)