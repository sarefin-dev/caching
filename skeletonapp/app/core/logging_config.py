# app/core/logging_config.py - SIMPLIFIED
import logging.config
import sys
from pathlib import Path

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(filename)s:%(lineno)d - %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        # ✅ Removed JSON formatter - we're not using it
    },
    
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": sys.stdout,  # ✅ Changed from "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": "logs/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
        },
    },
    
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
    
    "loggers": {
        "app": {
            "level": "INFO",
            "handlers": ["console", "file", "error_file"],
            "propagate": False,
        },
        # SQLAlchemy logger (optional - shows SQL queries)
        "sqlalchemy.engine": {
            "level": "WARNING",  # Change to INFO to see all SQL
            "handlers": ["console"],
            "propagate": False,
        },
        # Uvicorn loggers
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    }
}


def setup_logging():
    """Configure application logging"""
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")