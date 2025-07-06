# backend/app/core/logging.py

import sys

from app.core.config import settings
from loguru import logger

LOG_DIR = settings.LOG_DIR
LOG_DIR.mkdir(parents=True, exist_ok=True)  # create logs directory

# default logging settings
logger.remove()  # remove default handler (disable FastAPI default logger)
logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
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
    rotation=settings.LOG_ROTATION,
    retention=settings.LOG_RETENTION,
    level=settings.LOG_LEVEL,
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)
