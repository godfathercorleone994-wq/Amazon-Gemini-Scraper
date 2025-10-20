"""
Logging configuration using Loguru
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import settings
import json
from datetime import datetime

def serialize_record(record):
    """Serialize log record for JSON output"""
    subset = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"]
    }
    
    # Add extra fields if present
    if record["extra"]:
        subset.update(record["extra"])
    
    return json.dumps(subset)

def setup_logger():
    """Configure Loguru logger"""
    # Remove default handler
    logger.remove()
    
    # Console handler with color
    if settings.debug:
        logger.add(
            sys.stdout,
            level="DEBUG",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )
    else:
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            colorize=False
        )
    
    # File handler for all logs
    log_dir = Path(settings.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        settings.log_file,
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        backtrace=True,
        diagnose=True,
        enqueue=True
    )
    
    # JSON file handler for production
    if settings.is_production:
        logger.add(
            f"{log_dir}/app.json",
            rotation="50 MB",
            retention="90 days",
            level="INFO",
            serialize=True,
            enqueue=True
        )
    
    # Error file handler
    logger.add(
        f"{log_dir}/errors.log",
        rotation="10 MB",
        retention="60 days",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        backtrace=True,
        diagnose=True,
        enqueue=True
    )
    
    # Sentry integration if configured
    if settings.sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.loguru import LoguruIntegration
        
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            integrations=[LoguruIntegration()],
            traces_sample_rate=0.1 if settings.is_production else 1.0
        )
        
        logger.info("Sentry integration enabled")
    
    logger.info(f"Logger configured for {settings.environment} environment")
    return logger

# Setup logger on import
logger = setup_logger()

# Convenience functions
def log_error(message: str, **kwargs):
    """Log error with extra context"""
    logger.error(message, **kwargs)

def log_warning(message: str, **kwargs):
    """Log warning with extra context"""
    logger.warning(message, **kwargs)

def log_info(message: str, **kwargs):
    """Log info with extra context"""
    logger.info(message, **kwargs)

def log_debug(message: str, **kwargs):
    """Log debug with extra context"""
    logger.debug(message, **kwargs)

def log_scraping_event(asin: str, status: str, **kwargs):
    """Log scraping specific events"""
    logger.info(
        f"Scraping {status}",
        asin=asin,
        event_type="scraping",
        **kwargs
    )

def log_ai_request(provider: str, model: str, tokens: int = 0, **kwargs):
    """Log AI API requests"""
    logger.info(
        f"AI request to {provider}",
        provider=provider,
        model=model,
        tokens=tokens,
        event_type="ai_request",
        **kwargs
    )

def log_notification(type: str, channel: str, recipient: str, **kwargs):
    """Log notification events"""
    logger.info(
        f"Notification sent",
        notification_type=type,
        channel=channel,
        recipient=recipient,
        event_type="notification",
        **kwargs
  )
