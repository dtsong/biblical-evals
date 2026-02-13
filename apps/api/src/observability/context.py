"""Request-scoped logging context.

Cloud Run and Cloud Logging can correlate logs by request/trace identifiers.
We store those identifiers in context variables so they are available across
async call stacks without passing them through every function.
"""

from __future__ import annotations

from contextvars import ContextVar, Token

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
evaluation_id_var: ContextVar[str | None] = ContextVar("evaluation_id", default=None)


def set_request_id(value: str | None) -> Token[str | None]:
    return request_id_var.set(value)


def set_trace_id(value: str | None) -> Token[str | None]:
    return trace_id_var.set(value)


def set_evaluation_id(value: str | None) -> Token[str | None]:
    return evaluation_id_var.set(value)


def reset_request_id(token: Token[str | None]) -> None:
    request_id_var.reset(token)


def reset_trace_id(token: Token[str | None]) -> None:
    trace_id_var.reset(token)


def reset_evaluation_id(token: Token[str | None]) -> None:
    evaluation_id_var.reset(token)


def get_request_id() -> str | None:
    return request_id_var.get()


def get_trace_id() -> str | None:
    return trace_id_var.get()


def get_evaluation_id() -> str | None:
    return evaluation_id_var.get()
