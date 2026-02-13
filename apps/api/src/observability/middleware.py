"""Middleware for request context propagation."""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.observability.context import (
    reset_request_id,
    reset_trace_id,
    set_request_id,
    set_trace_id,
)

logger = logging.getLogger(__name__)


def _parse_cloud_trace_context(value: str) -> str | None:
    """Extract trace ID from X-Cloud-Trace-Context header.

    Header format: TRACE_ID/SPAN_ID;o=TRACE_TRUE
    """

    if not value:
        return None
    trace_part = value.split("/", 1)[0].strip()
    return trace_part or None


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        start = time.perf_counter()

        trace_id = _parse_cloud_trace_context(
            request.headers.get("X-Cloud-Trace-Context", "")
        )
        request_id = request.headers.get("X-Request-Id") or trace_id or str(uuid4())

        tok_req = set_request_id(request_id)
        tok_trace = set_trace_id(trace_id)
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            # Structured access log.
            logger.info(
                "request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": getattr(response, "status_code", None),
                    "duration_ms": duration_ms,
                },
            )
            # Reset context to avoid leaking between requests.
            reset_request_id(tok_req)
            reset_trace_id(tok_trace)

            if response is not None:
                # Help clients correlate.
                response.headers.setdefault("X-Request-Id", request_id)
                if trace_id:
                    response.headers.setdefault("X-Trace-Id", trace_id)
