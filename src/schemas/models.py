"""Pydantic models for data validation."""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

class FileType(str, Enum):
    """Enumeration of allowed file types."""
    ASSY = "Assy"
    FABCUT = "Fabcut"
    LP = "LP"
    SEWDC = "SEW-DC"
    SEWFB = "SEW-FB"

    @property
    def db_value(self) -> str:
        """Get the database storage value for the file type.

        Returns:
            String value to be stored in database

        Example:
            >>> FileType.SEWDC.db_value
            'DC-Sew'
        """
        if self == FileType.SEWDC:
            return "DC-Sew"
        return self.value

class ProcessingStatus(str, Enum):
    """Enumeration of processing statuses."""
    SUCCESS = "success"
    ERROR = "error"
    DUPLICATE = "duplicate"
    SKIPPED = "skipped"

class DispatchDataBase(BaseModel):
    """Base model for dispatch data."""
    file_type: FileType
    work_cell: str
    job_number: str
    part_number: str
    comments: Optional[str] = None
    job_qty: float
    bal_qty: float
    code: str
    prod_date: date
    est_compl_date: Optional[date] = None
    and_on: Optional[str] = None
    m_pc: Optional[float] = None
    prod_hr: Optional[float] = None
    report_start_date: date
    report_end_date: date
    report_department: str
    report_creation_datetime: datetime

    @validator('job_qty', 'bal_qty', 'm_pc', 'prod_hr')
    def validate_numeric_fields(cls, v):
        """Validate numeric fields are not negative."""
        if v is not None and v < 0:
            raise ValueError("Numeric values cannot be negative")
        return v

class DispatchDataCreate(DispatchDataBase):
    """Model for creating dispatch data records."""
    file_name: str
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.SUCCESS)
    upload_date: datetime = Field(default_factory=datetime.now)

class DispatchDataInDB(DispatchDataBase):
    """Model for dispatch data records in database."""
    id: int
    file_name: str
    processing_status: ProcessingStatus
    upload_date: datetime

    class Config:
        """Pydantic configuration."""
        from_attributes = True

class FileProcessingSummary(BaseModel):
    """Summary of file processing results."""
    file_name: str
    file_type: FileType
    total_rows: int = 0
    successful_rows: int = 0
    duplicate_rows: int = 0
    error_rows: int = 0
    skipped_rows: int = 0
    upload_date: datetime

class ProcessingResponse(BaseModel):
    """Response model for file processing."""
    file_name: str
    status: str
    message: str
    summary: Optional[FileProcessingSummary] = None
