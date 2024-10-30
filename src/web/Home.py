"""Main page of the Streamlit application."""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
from typing import Optional
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

def fetch_processed_files(
    file_type: Optional[str] = None,
    days: Optional[int] = None
) -> Optional[pd.DataFrame]:
    """Fetch processed files from API.
    
    Args:
        file_type: Optional file type filter
        days: Optional number of days to look back
        
    Returns:
        DataFrame with processed files data or None if error
    """
    try:
        params = {}
        if file_type:
            params['file_type'] = file_type
        if days:
            params['start_date'] = (datetime.now() - timedelta(days=days)).date().isoformat()
            
        response = requests.get(
            f"{st.session_state.api_url}/data/files",
            params=params
        )
        response.raise_for_status()
        
        data = response.json()
        if not data:
            return None
            
        df = pd.DataFrame(data)
        # Convert upload_date to datetime
        df['upload_date'] = pd.to_datetime(df['upload_date'])
        return df
        
    except Exception as e:
        logger.error(f"Error fetching processed files: {e}")
        st.error(f"Error fetching data: {str(e)}")
        return None

def main():
    """Main function for the home page."""
    st.set_page_config(
        page_title=f"{settings.APP_NAME} - Home",
        page_icon="🏭",
        layout="wide"
    )
    
    init_session_state()
    
    # Header
    st.title("Production Data Manager")
    st.markdown("---")
    
    # Quick Stats Section
    st.subheader("📊 Quick Statistics")
    
    # Create three columns for stats
    col1, col2, col3 = st.columns(3)
    
    # Fetch recent data (last 30 days)
    df = fetch_processed_files(days=30)
    
    if df is not None:
        with col1:
            st.metric(
                label="Files Processed (30 days)",
                value=len(df)
            )
            
        with col2:
            total_rows = df['total_rows'].sum()
            successful_rows = df['successful_rows'].sum()
            success_rate = (successful_rows / total_rows * 100) if total_rows > 0 else 0
            st.metric(
                label="Success Rate",
                value=f"{success_rate:.1f}%"
            )
            
        with col3:
            latest_upload = df['upload_date'].max()
            if pd.notna(latest_upload):
                time_diff = datetime.now() - latest_upload.to_pydatetime()
                hours_ago = time_diff.total_seconds() / 3600
                if hours_ago < 1:
                    time_str = "< 1 hour ago"
                else:
                    time_str = f"{int(hours_ago)} hours ago"
                    
                st.metric(
                    label="Last Upload",
                    value=time_str
                )
            else:
                st.metric(
                    label="Last Upload",
                    value="No data"
                )
    
    # Recent Activity Section
    st.markdown("---")
    st.subheader("📋 Recent Activity")
    
    # File type filter
    file_type = st.selectbox(
        "Filter by file type",
        options=["All"] + [ft.value for ft in FileType],
        index=0
    )
    
    # Time range filter
    time_range = st.selectbox(
        "Time range",
        options=["Last 24 hours", "Last 7 days", "Last 30 days"],
        index=1
    )
    
    # Convert time range to days
    days_map = {
        "Last 24 hours": 1,
        "Last 7 days": 7,
        "Last 30 days": 30
    }
    days = days_map[time_range]
    
    # Fetch filtered data
    df = fetch_processed_files(
        file_type=None if file_type == "All" else file_type,
        days=days
    )
    
    if df is not None and not df.empty:
        # Add custom columns for display
        df['Success Rate'] = (df['successful_rows'] / df['total_rows'] * 100).round(1)
        df['Upload Time'] = df['upload_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Reorder and select columns for display
        display_df = df[[
            'file_name',
            'file_type',
            'total_rows',
            'successful_rows',
            'duplicate_rows',
            'error_rows',
            'Success Rate',
            'Upload Time'
        ]].sort_values('upload_date', ascending=False)
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No data available for the selected filters.")
    
    # Navigation Help
    st.markdown("---")
    st.subheader("🧭 Quick Navigation")
    
    # Create two columns for navigation cards
    nav_col1, nav_col2 = st.columns(2)
    
    with nav_col1:
        st.info(
            """
            ### 📤 Upload Files
            Go to the Upload page to process new files.
            
            *Navigate using the sidebar menu: Upload*
            """
        )
        
    with nav_col2:
        st.info(
            """
            ### 🔍 Browse Data
            View and analyze processed data in detail.
            
            *Navigate using the sidebar menu: Data Browser*
            """
        )

if __name__ == "__main__":
    main()