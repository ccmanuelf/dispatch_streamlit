"""Data retrieval router."""
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlite3 import Connection
import logging

from src.api.deps import get_db, verify_file_type
from src.schemas.models import (
    FileType,
    DispatchDataInDB,
    FileProcessingSummary
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["data"])

@router.get(
    "/files",
    response_model=List[FileProcessingSummary],
    status_code=status.HTTP_200_OK,
    description="Get list of processed files"
)
async def get_processed_files(
    file_type: Optional[FileType] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Connection = Depends(get_db)
) -> List[FileProcessingSummary]:
    """Get list of processed files with optional filtering.
    
    Args:
        file_type: Optional file type filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        db: Database connection
        
    Returns:
        List of file processing summaries
    """
    try:
        query = """
        SELECT 
            file_name,
            file_type,
            COUNT(*) as total_rows,
            SUM(CASE WHEN processing_status = 'success' THEN 1 ELSE 0 END) as successful_rows,
            SUM(CASE WHEN processing_status = 'duplicate' THEN 1 ELSE 0 END) as duplicate_rows,
            SUM(CASE WHEN processing_status = 'error' THEN 1 ELSE 0 END) as error_rows,
            MAX(upload_date) as upload_date
        FROM dispatch_data
        WHERE 1=1
        """
        params = []
        
        if file_type:
            query += " AND file_type = ?"
            params.append(file_type.value)
            
        if start_date:
            query += " AND DATE(upload_date) >= ?"
            params.append(start_date.isoformat())
            
        if end_date:
            query += " AND DATE(upload_date) <= ?"
            params.append(end_date.isoformat())
            
        query += " GROUP BY file_name, file_type ORDER BY upload_date DESC"
        
        cursor = db.execute(query, params)
        return [FileProcessingSummary(**dict(row)) for row in cursor.fetchall()]
        
    except Exception as e:
        logger.error(f"Error retrieving file list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving file list: {str(e)}"
        )

@router.get(
    "/records",
    response_model=List[DispatchDataInDB],
    status_code=status.HTTP_200_OK,
    description="Get dispatch records with filtering"
)
async def get_dispatch_records(
    file_type: Optional[FileType] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    work_cell: Optional[str] = None,
    job_number: Optional[str] = None,
    part_number: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Connection = Depends(get_db)
) -> List[DispatchDataInDB]:
    """Get dispatch records with optional filtering.
    
    Args:
        file_type: Optional file type filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        work_cell: Optional work cell filter
        job_number: Optional job number filter
        part_number: Optional part number filter
        limit: Maximum number of records to return (default: 100, max: 1000)
        offset: Number of records to skip (default: 0)
        db: Database connection
        
    Returns:
        List of dispatch records
    """
    try:
        query = "SELECT * FROM dispatch_data WHERE 1=1"
        params = []
        
        if file_type:
            query += " AND file_type = ?"
            params.append(file_type.value)
            
        if start_date:
            query += " AND DATE(prod_date) >= ?"
            params.append(start_date.isoformat())
            
        if end_date:
            query += " AND DATE(prod_date) <= ?"
            params.append(end_date.isoformat())
            
        if work_cell:
            query += " AND work_cell = ?"
            params.append(work_cell)
            
        if job_number:
            query += " AND job_number = ?"
            params.append(job_number)
            
        if part_number:
            query += " AND part_number = ?"
            params.append(part_number)
            
        query += " ORDER BY prod_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = db.execute(query, params)
        return [DispatchDataInDB(**dict(row)) for row in cursor.fetchall()]
        
    except Exception as e:
        logger.error(f"Error retrieving dispatch records: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving dispatch records: {str(e)}"
        )