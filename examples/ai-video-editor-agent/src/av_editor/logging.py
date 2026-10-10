"""Structured logging via structlog.

Every log line carries run_id / asset_id / agent_name / stage context when
available. Secrets are masked before emission (LAW 5 / §6.10).
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

_SECRET_KEY_RE = re.compile(r"(api[_-]?key|token|secret|password|authorization)", re.IGNORECASE)
_SECRET_VALUE_RE = re.compile(r"(sk-[A-Za-z0-9\-_]{8,}|ghp_[A-Za-z0-9]{20,}|Bearer\s+\S+)")

_configured = False


def _mask_secret_values(_, __, method_calls: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover - processor
    """Mask obvious secret-looking values in event strings and kwargs."""
    for key in list(method_calls.keys()):
        if _SECRET_KEY_RE.search(key):
            method_calls[key] = "***masked***"
        elif isinstance(method_calls[key], str):
            method_calls[key] = _SECRET_VALUE_RE.sub("***masked***", method_calls[key])
    return method_calls


def configure_logging(*, json_output: bool = False, level: str = "INFO") -> None:
    """Idempotently configure structlog + stdlib logging."""
    global _configured
    if _configured:
        return
    logging.basicConfig(stream=sys.stderr, level=getattr(logging, level.upper(), logging.INFO),
                        format="%(message)s")
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        _mask_secret_values,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer: Any = (structlog.processors.JSONRenderer() if json_output
                     else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()))
    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str, **initial_context: Any) -> structlog.stdlib.BoundLogger:
    """Return a bound structured logger; binds initial context keys."""
    configure_logging()
    return structlog.get_logger(name).bind(**initial_context)


def bind_run(run_id: str, **extra: Any) -> None:
    """Bind run-scoped context to all subsequently created loggers."""
    structlog.contextvars.bind_contextvars(run_id=run_id, **extra)


def clear_run() -> None:
    structlog.contextvars.clear_contextvars()
