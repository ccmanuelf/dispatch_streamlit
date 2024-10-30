"""Script to run both FastAPI and Streamlit applications."""
import subprocess
import sys
from pathlib import Path
import time
import webbrowser
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run both FastAPI and Streamlit applications."""
    try:
        # Start FastAPI
        logger.info("Starting FastAPI server...")
        fastapi_process = subprocess.Popen(
            [sys.executable, "src/main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for FastAPI to start
        time.sleep(2)
        
        # Start Streamlit
        logger.info("Starting Streamlit application...")
        streamlit_process = subprocess.Popen(
            [sys.executable, "src/run_streamlit.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for Streamlit to start
        time.sleep(2)
        
        # Open browser
        webbrowser.open("http://localhost:8501")
        
        logger.info("""
        Applications started successfully!
        
        FastAPI server running at: http://localhost:8000
        Streamlit app running at:  http://localhost:8501
        
        Press Ctrl+C to stop both applications.
        """)
        
        # Keep the script running
        fastapi_process.wait()
        streamlit_process.wait()
        
    except KeyboardInterrupt:
        logger.info("\nStopping applications...")
        fastapi_process.terminate()
        streamlit_process.terminate()
        logger.info("Applications stopped.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if 'fastapi_process' in locals():
            fastapi_process.terminate()
        if 'streamlit_process' in locals():
            streamlit_process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()