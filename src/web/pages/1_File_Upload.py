"""File upload page of the Streamlit application."""
import streamlit as st
import requests
from pathlib import Path
import pandas as pd
from typing import Dict, List, Optional
import time
import logging
from datetime import datetime

from src.config.settings import get_settings
from src.schemas.models import FileType

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

def init_session_state():
    """Initialize session state variables."""
    if 'api_url' not in st.session_state:
        st.session_state.api_url = f"http://localhost:8000{settings.API_V1_STR}"
    if 'upload_history' not in st.session_state:
        st.session_state.upload_history = []
    if 'database_path' not in st.session_state:
        st.session_state.database_path = settings.get_database_path()
    if 'test_mode' not in st.session_state:
        st.session_state.test_mode = False
    if 'test_rows' not in st.session_state:
        st.session_state.test_rows = None

def configure_database():
    """Configure database settings."""
    st.sidebar.subheader("Database Configuration")

    # Database file selection
    db_path = st.sidebar.text_input(
        "Database Path",
        value=str(st.session_state.database_path)
    )

    if st.sidebar.button("Update Database Path"):
        try:
            # Convert to Path and validate
            db_path = Path(db_path)
            # Ensure directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)
            # Update settings
            settings.set_database_path(db_path)
            st.session_state.database_path = db_path
            st.sidebar.success("Database path updated successfully!")
        except Exception as e:
            st.sidebar.error(f"Error updating database path: {str(e)}")

def configure_test_mode():
    """Configure test mode settings."""
    st.sidebar.subheader("Test Mode Configuration")

    # Test mode toggle
    test_mode = st.sidebar.checkbox(
        "Enable Test Mode",
        value=st.session_state.test_mode,
        help="Process only a limited number of rows"
    )

    test_rows = None
    if test_mode:
        test_rows = st.sidebar.number_input(
            "Number of Rows to Process",
            min_value=1,
            value=st.session_state.test_rows or 100,
            help="Maximum number of rows to process per file"
        )

    # Update session state
    st.session_state.test_mode = test_mode
    st.session_state.test_rows = test_rows

def preview_csv(uploaded_file) -> Optional[pd.DataFrame]:
    """Preview first few rows of uploaded CSV.

    Args:
        uploaded_file: StreamlitUploadedFile object

    Returns:
        DataFrame with preview data or None if error
    """
    try:
        # Read first few rows
        preview_df = pd.read_csv(uploaded_file, nrows=5)
        # Reset file pointer for later use
        uploaded_file.seek(0)
        return preview_df
    except Exception as e:
        logger.error(f"Error previewing file: {e}")
        st.error(f"Error reading file: {str(e)}")
        return None

def upload_files(
    files: List[str],
    progress_bar: st.progress,
    status_text: st.empty
) -> List[Dict]:
    """Upload files to API."""
    results = []
    total_files = len(files)

    for idx, file in enumerate(files, 1):
        try:
            # Update progress
            progress = idx / total_files
            progress_bar.progress(progress)
            status_text.text(f"Uploading file {idx}/{total_files}: {file.name}")

            # Detect file type
            file_type = settings.detect_file_type(file.name)
            if not file_type:
                raise ValueError(f"Could not detect file type from filename: {file.name}")

            # Prepare API parameters
            params = {}
            if st.session_state.test_mode and st.session_state.test_rows:
                params['test_rows'] = st.session_state.test_rows

            # Send to API
            files_dict = {"file": file}
            response = requests.post(
                f"{st.session_state.api_url}/files/upload/{file_type}",
                files=files_dict,
                params=params
            )
            response.raise_for_status()

            # Store result
            result = response.json()
            results.append(result)

            # Add to upload history
            st.session_state.upload_history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "file_name": file.name,
                "file_type": file_type,
                "status": result["status"],
                "summary": result["summary"]
            })

        except Exception as e:
            logger.error(f"Error uploading {file.name}: {e}")
            results.append({
                "file_name": file.name,
                "status": "error",
                "message": str(e)
            })

        time.sleep(0.1)

    progress_bar.progress(1.0)
    status_text.text("Upload complete!")
    return results


def display_results(results: List[Dict]):
    """Display upload results in a formatted way.

    Args:
        results: List of upload results
    """
    # Summary metrics
    total = len(results)
    successful = sum(1 for r in results if r["status"] == "success")
    failed = total - successful

    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Files", total)
    with col2:
        st.metric("Successful", successful)
    with col3:
        st.metric("Failed", failed)

    # Detailed results
    st.subheader("Detailed Results")

    for result in results:
        if result["status"] == "success":
            with st.expander(f"✅ {result['file_name']}", expanded=False):
                st.json(result["summary"])
        else:
            with st.expander(f"❌ {result['file_name']}", expanded=True):
                st.error(result["message"])

def display_upload_history():
    """Display upload history in a table format."""
    if st.session_state.upload_history:
        st.subheader("Recent Upload History")

        # Convert history to DataFrame
        history_df = pd.DataFrame(st.session_state.upload_history)

        # Add success rate column
        if not history_df.empty and 'summary' in history_df.columns:
            history_df['success_rate'] = history_df['summary'].apply(
                lambda x: f"{(x['successful_rows'] / x['total_rows'] * 100):.1f}%"
                if x and x['total_rows'] > 0
                else "N/A"
            )

        # Display selected columns
        display_cols = ['timestamp', 'file_name', 'status', 'success_rate']
        st.dataframe(
            history_df[display_cols],
            use_container_width=True,
            hide_index=True
        )

def main():
    """Main function for the upload page."""
    st.set_page_config(
        page_title=f"{settings.APP_NAME} - File Upload",
        page_icon="📤",
        layout="wide"
    )

    init_session_state()

    # Sidebar configurations
    configure_database()
    configure_test_mode()

    st.title("File Upload")
    st.markdown("""
    Upload your production data files for processing.
    File types are automatically detected from filenames.
    Supported types: Assy, Fabcut, LP, SEW-DC, and SEW-FB.
    """)

    # File uploader
    uploaded_files = st.file_uploader(
        "Choose CSV files",
        type="csv",
        accept_multiple_files=True,
        help="You can select multiple files. File types will be detected from filenames."
    )

    if uploaded_files:
        st.subheader("File Preview")

        # Show preview and detected type for first file
        preview_df = preview_csv(uploaded_files[0])
        if preview_df is not None:
            file_type = settings.detect_file_type(uploaded_files[0].name)
            st.info(f"Detected file type: {file_type or 'Unknown'}")
            st.dataframe(preview_df, use_container_width=True)

        # Upload button with test mode indicator
        button_label = "Upload Files"
        if st.session_state.test_mode:
            button_label += f" (Test Mode - {st.session_state.test_rows} rows)"

        if st.button(button_label, type="primary"):
            with st.spinner("Processing files..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                results = upload_files(
                    uploaded_files,
                    progress_bar,
                    status_text
                )

                display_results(results)

    # Show upload history
    st.markdown("---")
    display_upload_history()

if __name__ == "__main__":
    main()
