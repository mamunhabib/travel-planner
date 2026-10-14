"""
Travel Planner - Entry Point Launcher
Launches the Streamlit web frontend on port 8501.
"""
import sys
import os
from pathlib import Path
from core.config import Config
from utils.logger import logger

def main():
    # 1. Pre-flight check: Validate environment secrets
    try:
        Config.validate()
        logger.info("Environment configuration validated successfully.")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        print(f"❌ Configuration Error: {e}")
        sys.exit(1)

    # 2. Resolve path to app/ui.py
    app_path = Path(__file__).resolve().parent / "app" / "ui.py"
    port = os.getenv("PORT", "8501")

    print(f"🚀 Starting AI Travel Planner on http://localhost:{port}")
    logger.info(f"Launching Streamlit application on port {port}")

    # 3. Launch Streamlit CLI programmatically
    from streamlit.web import cli as stcli
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        f"--server.port={port}",
        "--server.address=0.0.0.0",
        "--server.headless=false",
        "--browser.serverAddress=localhost"
    ]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
