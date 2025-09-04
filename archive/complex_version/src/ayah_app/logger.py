"""Logging configuration for the Ayah App."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from config.settings import Config


def setup_logging(config: Config, log_name: str = "ayah_app") -> logging.Logger:
    """
    Set up comprehensive logging configuration.
    
    Args:
        config: Application configuration
        log_name: Name for the logger
        
    Returns:
        Configured logger instance
    """
    # Create logs directory
    config.LOGS_DIR.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(log_name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt=config.LOG_FORMAT,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(levelname)s: %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO if not config.DEBUG else logging.DEBUG)
    console_handler.setFormatter(simple_formatter if not config.DEBUG else detailed_formatter)
    logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        filename=config.LOGS_DIR / f"{log_name}.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        filename=config.LOGS_DIR / f"{log_name}_errors.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    # Email handler for critical errors (production only)
    if not config.DEBUG and hasattr(config, 'MAIL_USERNAME') and config.MAIL_USERNAME:
        try:
            email_handler = logging.handlers.SMTPHandler(
                mailhost=(config.MAIL_SERVER, config.MAIL_PORT),
                fromaddr=config.MAIL_DEFAULT_SENDER,
                toaddrs=[config.MAIL_USERNAME],  # Send to admin
                subject=f"Critical Error in {log_name}",
                credentials=(config.MAIL_USERNAME, config.MAIL_PASSWORD),
                secure=() if config.MAIL_USE_TLS else None
            )
            email_handler.setLevel(logging.CRITICAL)
            email_handler.setFormatter(detailed_formatter)
            logger.addHandler(email_handler)
        except Exception as e:
            logger.warning(f"Could not set up email logging: {e}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return logging.getLogger(f"ayah_app.{name}")


class LoggerMixin:
    """Mixin class to add logging capability to other classes."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__.lower())


# Context managers for logging operations
class LogOperation:
    """Context manager for logging operation start/end with timing."""
    
    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.log(self.level, f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.log(self.level, f"Completed {self.operation} in {duration:.2f}s")
        else:
            self.logger.error(f"Failed {self.operation} after {duration:.2f}s: {exc_val}")
            # Re-raise the exception
            return False


def log_exceptions(logger: logging.Logger):
    """Decorator to log exceptions from functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {e}")
                raise
        return wrapper
    return decorator


# Performance logging utilities
def log_performance(logger: logging.Logger, threshold_seconds: float = 1.0):
    """Decorator to log function performance if it exceeds threshold."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                if duration > threshold_seconds:
                    logger.warning(f"{func.__name__} took {duration:.2f}s (threshold: {threshold_seconds}s)")
                return result
            except Exception:
                duration = time.time() - start_time
                logger.error(f"{func.__name__} failed after {duration:.2f}s")
                raise
        return wrapper
    return decorator