"""Date parsing utilities."""
from datetime import datetime
from typing import Optional
import logging
import re

logger = logging.getLogger(__name__)

class DateParsingError(Exception):
    """Custom exception for date parsing errors."""
    pass

def parse_date(date_str: str) -> Optional[str]:
    """Parse date string into standardized format.
    
    Args:
        date_str: Date string to parse
        
    Returns:
        Standardized date string in YYYY-MM-DD format or None if parsing fails
        
    Example:
        >>> parse_date("30-Sep-24")
        "2024-09-30"
        >>> parse_date("9/27/2024")
        "2024-09-27"
    """
    if not date_str or not isinstance(date_str, str):
        return None
        
    date_str = date_str.strip()
    if not date_str:
        return None

    date_formats = [
        '%d-%b-%y',    # For "30-Sep-24"
        '%d-%b-%Y',    # For "27-Sep-2024"
        '%m/%d/%Y',    # For "9/27/2024"
        '%d-%b-%y',    # For "11-Oct-24"
        '%d/%b/%y'     # For "11/Sep/24"
    ]

    for date_format in date_formats:
        try:
            return datetime.strptime(date_str, date_format).strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    logger.warning(f"Could not parse date: {date_str}")
    return None

def parse_datetime(datetime_str: str) -> Optional[str]:
    """Parse datetime string into standardized format.
    
    Args:
        datetime_str: Datetime string to parse
        
    Returns:
        Standardized datetime string in YYYY-MM-DD HH:MM:SS format or None if parsing fails
        
    Example:
        >>> parse_datetime("Printed on 9/27/2024 /  3:59:22PM")
        "2024-09-27 15:59:22"
    """
    if not datetime_str or not isinstance(datetime_str, str):
        return None

    datetime_str = datetime_str.strip()
    if not datetime_str:
        return None

    # For "Printed on 9/27/2024 /  3:59:22PM" format
    pattern = r'Printed on (\d{1,2}/\d{1,2}/\d{4}) / *(\d{1,2}:\d{2}:\d{2})(AM|PM)'
    match = re.search(pattern, datetime_str)

    if match:
        date_str, time_str, ampm = match.groups()
        dt_str = f"{date_str} {time_str} {ampm}"
        try:
            dt = datetime.strptime(dt_str, '%m/%d/%Y %I:%M:%S %p')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass

    # For "2024-09-27 16:12:15" format
    try:
        return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass

    # For "2024-10-14T20:04:43.342962" format
    try:
        return datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%f').strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass

    logger.warning(f"Could not parse datetime: {datetime_str}")
    return None