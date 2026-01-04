# app/core/logging_config.py - RECOMMENDED COLORLOG SETUP
import logging.config
import sys
from pathlib import Path

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)


def setup_logging():
    """
    Configure logging with beautiful colored console output
    """
    
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        
        "formatters": {
            # Beautiful colored console
            "colored": {
                "()": "colorlog.ColoredFormatter",
                "format": (
                    "%(log_color)s%(asctime)s%(reset)s | "
                    "%(blue)s%(name)-25s%(reset)s | "
                    "%(log_color)s%(levelname)-8s%(reset)s | "
                    "%(message)s"
                ),
                "datefmt": "%H:%M:%S",  # Just time for console
                "log_colors": {
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
            },
            # Detailed for files
            "file": {
                "format": (
                    "%(asctime)s | %(name)-25s | %(levelname)-8s | "
                    "[%(filename)s:%(lineno)d] | %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "colored",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "file",
                "filename": str(LOGS_DIR / "app.log"),
                "maxBytes": 10_485_760,
                "backupCount": 5,
                "encoding": "utf8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "file",
                "filename": str(LOGS_DIR / "error.log"),
                "maxBytes": 10_485_760,
                "backupCount": 5,
                "encoding": "utf8",
            },
        },
        
        "loggers": {
            "app": {
                "level": "DEBUG",
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        
        "root": {
            "level": "INFO",
            "handlers": ["console", "file"],
        }
    }
    
    logging.config.dictConfig(LOGGING_CONFIG)
    
    logger = logging.getLogger(__name__)
    logger.info("Colorlog enabled - logs are now beautiful!")
    logger.debug("Debug mode active")
    logger.warning("This is a warning")
    logger.error("This is an error")