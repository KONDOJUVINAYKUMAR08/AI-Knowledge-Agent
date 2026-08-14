"""
Structured logging for the Knowledge Agent.
"""

import logging
import re
import sys
from typing import Any

import structlog

from src.core.config import get_settings

_SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
)
_SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?:Bearer\s+\S+|AIza[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,})",
    re.IGNORECASE,
)


def _redact(value: Any, key: str = "") -> Any:
    if any(fragment in key.casefold() for fragment in _SENSITIVE_KEY_FRAGMENTS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {item_key: _redact(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    if isinstance(value, str) and _SENSITIVE_VALUE_PATTERN.search(value):
        return "[REDACTED]"
    return value


def redact_sensitive_values(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Redact secret-bearing fields before rendering any log event."""

    return _redact(event_dict)


def configure_logging() -> None:
    """Configure structlog."""
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        redact_sensitive_values,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.log_format == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=log_level,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
