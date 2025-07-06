# backend/app/core/logging.py

import sys
from pathlib import Path

from loguru import logger

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)  # create logs directory

# default logging settings
logger.remove()  # remove default handler (disable FastAPI default logger)
logger.add(
    sys.stdout,
    level="INFO",
    enqueue=True,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "{message}",
)

# file logging (INFO and above)
logger.add(
    LOG_DIR / "app.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)
