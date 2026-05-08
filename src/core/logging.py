"""Logging configuration using loguru."""

import sys

from loguru import logger

from src.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    """Configure global application logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level.upper(),
        backtrace=False,
        diagnose=False,
        enqueue=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}:{function}:{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )
