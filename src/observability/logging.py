"""Structured logging (structlog): JSON, timestamp, level, message, request_id.

Log level is taken from config (LOG_LEVEL / .env) or from the optional level
argument; when the run entrypoint is used with --log-level, CLI overrides config.
Output goes to stdout by default."""

import logging
import sys
from typing import Any

import structlog

from src.api.config import get_settings

# Map level names (case-insensitive) to logging constants; invalid values fall back to INFO.
_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def configure_logging(level: str | None = None) -> None:
    """Configure structlog with JSON output to stdout and standard fields.

    If level is provided (e.g. from CLI), it is used; otherwise the level is
    read from config (get_settings().log_level). Command line takes precedence
    when the run entrypoint passes --log-level."""
    effective = (level or get_settings().log_level).strip().upper()
    log_level_int = _LEVEL_MAP.get(effective, logging.INFO)
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
        wrapper_class=structlog.make_filtering_bound_logger(log_level_int),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(*args: Any, **kwargs: Any) -> structlog.stdlib.BoundLogger:
    """Return a bound logger. Pass request_id via bind(request_id=...)."""
    return structlog.get_logger(*args, **kwargs)
