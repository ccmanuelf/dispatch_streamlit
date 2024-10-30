"""File upload and processing router."""
from typing import List
from pathlib import Path
import shutil
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlite3 import Connection
import logging

from src.api.deps import get_db, verify_file_type
from src.config.settings import get_settings
from src.schemas.models import FileType, ProcessingResponse
from src.processors import (
    create_assy_processor,
    create_fabcut_processor,
    create_lp_processor,
    create_sewdc_processor,
    create_sewfb_processor
)

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

# Mapping of file types to their processor creation functions
PROCESSOR_MAP = {
    FileType.ASSY: create_assy_processor,
    FileType.FABCUT: create_fabcut_processor,
    FileType.LP: create_lp_processor,
    FileType.SEWDC: create_sewdc_processor,
    FileType.SEWFB: create_sewfb_processor
}

async def save_upload_file(upload_file: UploadFile) -> Path:
    """Save uploaded file to temporary location.

    Args:
        upload_file: Uploaded file object

    Returns:
        Path to saved file

    Raises:
        HTTPException: If file saving fails
    """
    try:
        # Create upload directory if it doesn't exist
        settings.ensure_upload_folder()

        # Create file path
        file_path = settings.UPLOAD_FOLDER / upload_file.filename

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        return file_path

    except Exception as e:
        logger.error(f"Error saving file {upload_file.filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}"
        )
    finally:
        upload_file.file.close()

async def process_file(
    file_path: Path,
    file_type: FileType,
    db: Connection
) -> ProcessingResponse:
    """Process a single file.

    Args:
        file_path: Path to file to process
        file_type: Type of file
        db: Database connection

    Returns:
        Processing response with results

    Raises:
        HTTPException: If processing fails
    """
    try:
        # Get appropriate processor
        processor_creator = PROCESSOR_MAP[file_type]
        processor = processor_creator(file_path, db)

        # Process file
        summary = processor.process_file()

        return ProcessingResponse(
            file_name=file_path.name,
            status="success",
            message="File processed successfully",
            summary=summary
        )

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )
    finally:
        # Clean up temporary file
        try:
            file_path.unlink()
        except Exception as e:
            logger.warning(f"Error deleting temporary file {file_path}: {str(e)}")

@router.post(
    "/upload/{file_type}",
    response_model=ProcessingResponse,
    status_code=status.HTTP_200_OK,
    description="Upload and process a single file"
)
async def upload_file(
    file_type: FileType = Depends(verify_file_type),
    file: UploadFile = File(...),
    db: Connection = Depends(get_db),
    test_rows: Optional[int] = None
) -> ProcessingResponse:
    """Upload and process a single file.

    Args:
        file_type: Type of file being uploaded
        file: Uploaded file
        db: Database connection

    Returns:
        Processing results

    Raises:
        HTTPException: If file processing fails
    """
    # Verify file size
    if file.size and file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE} bytes"
        )

    # Save and process file
    file_path = await save_upload_file(file)
    return await process_file(file_path, file_type, db)

@router.post(
    "/upload-multiple/{file_type}",
    response_model=List[ProcessingResponse],
    status_code=status.HTTP_200_OK,
    description="Upload and process multiple files"
)
async def upload_multiple_files(
    file_type: FileType = Depends(verify_file_type),
    files: List[UploadFile] = File(...),
    db: Connection = Depends(get_db)
) -> List[ProcessingResponse]:
    """Upload and process multiple files.

    Args:
        file_type: Type of files being uploaded
        files: List of uploaded files
        db: Database connection

    Returns:
        List of processing results

    Raises:
        HTTPException: If file processing fails
    """
    results = []

    for file in files:
        # Verify file size
        if file.size and file.size > settings.MAX_UPLOAD_SIZE:
            logger.warning(f"Skipping file {file.filename}: exceeds size limit")
            results.append(
                ProcessingResponse(
                    file_name=file.filename,
                    status="error",
                    message=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE} bytes"
                )
            )
            continue

        try:
            # Save and process file
            file_path = await save_upload_file(file)
            result = await process_file(file_path, file_type, db)
            results.append(result)

        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")
            results.append(
                ProcessingResponse(
                    file_name=file.filename,
                    status="error",
                    message=str(e)
                )
            )

    return results
