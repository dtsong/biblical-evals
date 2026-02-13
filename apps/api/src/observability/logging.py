"""Structured logging configuration.

In production (Cloud Run), logs are emitted as JSON for Cloud Logging.
In development/test, logs default to a readable text format unless
`LOG_FORMAT=json` is set.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any

from src.observability.context import get_evaluation_id, get_request_id, get_trace_id


class ContextFilter(logging.Filter):
    """Inject request/trace/evaluation context into all log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        if not hasattr(record, "trace_id"):
            record.trace_id = get_trace_id()
        if not hasattr(record, "evaluation_id"):
            record.evaluation_id = get_evaluation_id()
        return True


class JsonFormatter(logging.Formatter):
    """JSON formatter aligned with Cloud Logging conventions."""

    _reserved = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
            "request_id": getattr(record, "request_id", None),
            "evaluation_id": getattr(record, "evaluation_id", None),
        }

        # Include arbitrary structured fields from logger extras.
        for k, v in record.__dict__.items():
            if k in self._reserved or k.startswith("_"):
                continue
            if k in payload:
                continue
            if v is None:
                continue
            payload[k] = v

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _want_json(settings: Any) -> bool:
    forced = os.getenv("LOG_FORMAT", "").strip().lower()
    if forced in {"json", "structured"}:
        return True
    if forced in {"text", "plain"}:
        return False
    # Default by environment.
    return bool(getattr(settings, "is_production", False))


def configure_logging(settings: Any) -> None:
    """Configure root logger handlers.

    Safe to call multiple times; the previous handlers are replaced.
    """

    root = logging.getLogger()
    level = logging.DEBUG if getattr(settings, "debug", False) else logging.INFO
    root.setLevel(level)

    # Replace handlers to avoid duplicates in tests/reloads.
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.addFilter(ContextFilter())

    if _want_json(settings):
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )

    root.addHandler(handler)

    # Reduce noise from HTTP client internals.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
