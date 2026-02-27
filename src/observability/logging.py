"""Structured logging (structlog): JSON, timestamp, level, message, request_id."""

import logging
import sys
from typing import Any

import structlog


def configure_logging() -> None:
    """Configure structlog with JSON output and standard fields."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(*args: Any, **kwargs: Any) -> structlog.stdlib.BoundLogger:
    """Return a bound logger. Pass request_id via bind(request_id=...)."""
    return structlog.get_logger(*args, **kwargs)
