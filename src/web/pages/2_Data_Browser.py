"""Data browser page of the Streamlit application."""
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

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
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'records_per_page' not in st.session_state:
        st.session_state.records_per_page = 50
    if 'total_records' not in st.session_state:
        st.session_state.total_records = 0

def fetch_unique_values(field: str) -> List[str]:
    """Fetch unique values for a field from the API.
    
    Args:
        field: Field name to get unique values for
        
    Returns:
        List of unique values
    """
    try:
        response = requests.get(
            f"{st.session_state.api_url}/data/unique-values/{field}"
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching unique values for {field}: {e}")
        return []

def fetch_data(filters: Dict, page: int, per_page: int) -> Tuple[Optional[pd.DataFrame], int]:
    """Fetch filtered data from API.
    
    Args:
        filters: Dictionary of filter parameters
        page: Page number
        per_page: Records per page
        
    Returns:
        Tuple of (DataFrame with data or None if error, total record count)
    """
    try:
        # Add pagination to filters
        params = {
            **filters,
            "offset": (page - 1) * per_page,
            "limit": per_page
        }
        
        response = requests.get(
            f"{st.session_state.api_url}/data/records",
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        
        if not data["records"]:
            return None, 0
            
        df = pd.DataFrame(data["records"])
        
        # Convert date columns
        date_columns = ['prod_date', 'est_compl_date', 'report_start_date', 
                       'report_end_date', 'report_creation_datetime', 'upload_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
        
        return df, data["total"]
        
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        st.error(f"Error fetching data: {str(e)}")
        return None, 0

def render_filters() -> Dict:
    """Render filter controls and return filter values.
    
    Returns:
        Dictionary of filter parameters
    """
    filters = {}
    
    # Create three columns for filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # File Type filter
        file_type = st.selectbox(
            "File Type",
            options=["All"] + [ft.value for ft in FileType]
        )
        if file_type != "All":
            filters["file_type"] = file_type
        
        # Job Number filter
        job_number = st.text_input("Job Number")
        if job_number:
            filters["job_number"] = job_number
    
    with col2:
        # Work Cell filter
        work_cell = st.text_input("Work Cell")
        if work_cell:
            filters["work_cell"] = work_cell
            
        # Part Number filter
        part_number = st.text_input("Part Number")
        if part_number:
            filters["part_number"] = part_number
    
    with col3:
        # Date range filter
        date_option = st.selectbox(
            "Date Filter",
            options=["All Time", "Last 7 Days", "Last 30 Days", "Custom Range"]
        )
        
        if date_option == "Custom Range":
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            if start_date and end_date:
                filters["start_date"] = start_date.isoformat()
                filters["end_date"] = end_date.isoformat()
        elif date_option != "All Time":
            days = 7 if date_option == "Last 7 Days" else 30
            filters["start_date"] = (datetime.now() - timedelta(days=days)).date().isoformat()
            filters["end_date"] = datetime.now().date().isoformat()
    
    return filters

def display_data(df: pd.DataFrame):
    """Display data with formatting.
    
    Args:
        df: DataFrame to display
    """
    # Format date columns
    date_columns = ['prod_date', 'est_compl_date', 'report_start_date', 
                   'report_end_date', 'report_creation_datetime', 'upload_date']
    
    display_df = df.copy()
    for col in date_columns:
        if col in display_df.columns:
            display_df[col] = display_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Calculate derived columns
    if 'job_qty' in display_df.columns and 'bal_qty' in display_df.columns:
        display_df['completion_rate'] = ((display_df['job_qty'] - display_df['bal_qty']) / 
                                       display_df['job_qty'] * 100).round(1)
        display_df['completion_rate'] = display_df['completion_rate'].astype(str) + '%'
    
    # Reorder columns for better presentation
    preferred_order = [
        'file_type', 'work_cell', 'job_number', 'part_number', 'completion_rate',
        'job_qty', 'bal_qty', 'code', 'prod_date', 'est_compl_date'
    ]
    
    # Get available columns in preferred order
    display_columns = [col for col in preferred_order if col in display_df.columns]
    # Add any remaining columns
    remaining_columns = [col for col in display_df.columns if col not in display_columns]
    display_columns.extend(remaining_columns)
    
    st.dataframe(
        display_df[display_columns],
        use_container_width=True,
        hide_index=True
    )

def render_pagination(total_records: int):
    """Render pagination controls.
    
    Args:
        total_records: Total number of records
    """
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.session_state.records_per_page = st.selectbox(
            "Records per page",
            options=[10, 25, 50, 100],
            index=2
        )
    
    total_pages = (total_records - 1) // st.session_state.records_per_page + 1
    
    with col2:
        page_numbers = [i for i in range(max(1, st.session_state.current_page - 2),
                                       min(total_pages + 1, st.session_state.current_page + 3))]
        
        st.write("Page:")
        cols = st.columns(len(page_numbers) + 2)
        
        # Previous button
        if cols[0].button("◀"):
            st.session_state.current_page = max(1, st.session_state.current_page - 1)
            st.experimental_rerun()
        
        # Page numbers
        for i, page in enumerate(page_numbers, 1):
            if cols[i].button(
                str(page),
                type="primary" if page == st.session_state.current_page else "secondary"
            ):
                st.session_state.current_page = page
                st.experimental_rerun()
        
        # Next button
        if cols[-1].button("▶"):
            st.session_state.current_page = min(total_pages, st.session_state.current_page + 1)
            st.experimental_rerun()
    
    with col3:
        st.write(f"Total records: {total_records}")

def main():
    """Main function for the data browser page."""
    st.set_page_config(
        page_title=f"{settings.APP_NAME} - Data Browser",
        page_icon="🔍",
        layout="wide"
    )
    
    init_session_state()
    
    st.title("Data Browser")
    st.markdown("Browse and filter production data records.")
    
    # Filters section
    with st.expander("Filters", expanded=True):
        filters = render_filters()
    
    # Fetch and display data
    df, total_records = fetch_data(
        filters,
        st.session_state.current_page,
        st.session_state.records_per_page
    )
    
    if df is not None and not df.empty:
        # Update total records in session state
        st.session_state.total_records = total_records
        
        # Display data
        display_data(df)
        
        # Pagination
        st.markdown("---")
        render_pagination(total_records)
        
        # Export section
        st.markdown("---")
        st.subheader("Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Export to CSV"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"production_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("Export to Excel"):
                excel_buffer = pd.ExcelWriter('data.xlsx', engine='xlsxwriter')
                df.to_excel(excel_buffer, index=False)
                excel_buffer.close()
                
                with open('data.xlsx', 'rb') as f:
                    st.download_button(
                        label="Download Excel",
                        data=f,
                        file_name=f"production_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
    else:
        st.info("No data found matching the current filters.")
    
    # Help section in sidebar
    with st.sidebar:
        st.markdown("### Help")
        st.markdown("""
        **Using Filters:**
        - Select multiple filters to narrow down results
        - Leave filters empty to see all records
        - Use date filters to focus on specific time periods
        
        **Data Display:**
        - Click column headers to sort
        - Use the search box to find specific values
        - Adjust records per page as needed
        
        **Export Options:**
        - Export to CSV for basic data
        - Export to Excel for formatted data
        """)

if __name__ == "__main__":
    main()