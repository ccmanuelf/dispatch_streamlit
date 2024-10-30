"""Streamlit application entry point."""
import subprocess
import sys
from pathlib import Path

def main():
    """Run the Streamlit application."""
    # Get the path to the Home.py file
    streamlit_path = Path(__file__).parent / "web" / "Home.py"
    
    # Run streamlit
    subprocess.run([
        "streamlit",
        "run",
        str(streamlit_path),
        "--server.port=8501",
        "--browser.serverAddress=localhost"
    ])

if __name__ == "__main__":
    main()