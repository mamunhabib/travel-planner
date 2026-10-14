"""
Travel Planner - Logging Configuration
Configures structured dual logging to both daily files (logs/log_YYYY-MM-DD.log) and stdout.
"""
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Resolve project base directory to ensure logs/ is always in project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Generate daily log filename: logs/log_YYYY-MM-DD.log
LOG_FILE = LOGS_DIR / f"log_{datetime.now().strftime('%Y-%m-%d')}.log"

# Define standard log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Create root formatter
formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

# 1. File Handler (writes to daily log file for Filebeat / archival)
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# 2. Console Handler (writes to stdout for Docker / Kubernetes container logs)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

def get_logger(name: str = "travel_planner") -> logging.Logger:
    """
    Returns a configured logger instance with both file and console handlers.
    Avoids duplicate handlers on repeated calls (e.g., Streamlit script reruns).
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent attaching duplicate handlers if get_logger is called repeatedly
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        # Prevent propagation to avoid double logging if root logger also handles it
        logger.propagate = False

    return logger

# Default logger instance for direct import
logger = get_logger("travel_planner")
