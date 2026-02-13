"""Shared pytest fixtures for API tests.

These fixtures intentionally avoid real database or network calls.
They provide lightweight fakes that cover the subset of the async SQLAlchemy
session interface used by handlers and domain logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest


class FakeScalarResult:
    def __init__(self, rows: list[Any]):
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class FakeExecuteResult:
    def __init__(
        self, one: Any | None = None, many: list[Any] | None = None, scalar: Any = None
    ):
        self._one = one
        self._many = list(many or [])
        self._scalar = scalar

    def scalar_one_or_none(self) -> Any | None:
        return self._one

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._many)

    def scalar(self) -> Any:
        return self._scalar


class FakeAsyncSession:
    """Minimal async session fake used by unit tests."""

    def __init__(
        self,
        execute_results: list[Any] | None = None,
        get_by_id: dict[Any, Any] | None = None,
        commit_error: Exception | None = None,
    ):
        self.execute_results = list(execute_results or [])
        self.get_by_id = dict(get_by_id or {})
        self.commit_error = commit_error

        self.added: list[Any] = []
        self.commits = 0
        self.rollbacks = 0
        self.refreshed: list[Any] = []

    async def execute(self, _query: Any) -> FakeExecuteResult:
        if not self.execute_results:
            return FakeExecuteResult()

        result = self.execute_results.pop(0)
        if isinstance(result, Exception):
            raise result
        if isinstance(result, FakeExecuteResult):
            return result
        if isinstance(result, dict):
            return FakeExecuteResult(**result)
        if isinstance(result, list):
            return FakeExecuteResult(many=result)
        return result

    async def get(self, _model: Any, _id: Any) -> Any | None:
        return self.get_by_id.get(_id)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1
        if self.commit_error is not None and self.commits == 1:
            raise self.commit_error

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, obj: Any) -> None:
        self.refreshed.append(obj)


@dataclass
class FakeLiteLLMUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass
class FakeLiteLLMMessage:
    content: str | None


@dataclass
class FakeLiteLLMChoice:
    message: FakeLiteLLMMessage


@dataclass
class FakeLiteLLMResponse:
    choices: list[FakeLiteLLMChoice]
    usage: FakeLiteLLMUsage | None = None
    _hidden_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class LiteLLMStub:
    """Configurable stub for litellm.acompletion."""

    calls: list[dict[str, Any]] = field(default_factory=list)
    responses_by_model: dict[str, Any] = field(default_factory=dict)
    default_response: Any | None = None
    failures_before_success: dict[str, int] = field(default_factory=dict)
    failure_exc_by_model: dict[str, Exception] = field(default_factory=dict)

    def set_response(self, model: str, response: Any) -> None:
        self.responses_by_model[model] = response

    def set_default_response(self, response: Any) -> None:
        self.default_response = response

    def set_failing(
        self, model: str, exc: Exception, failures_before_success: int
    ) -> None:
        self.failure_exc_by_model[model] = exc
        self.failures_before_success[model] = failures_before_success

    async def acompletion(self, **kwargs: Any) -> Any:
        self.calls.append(dict(kwargs))
        model = kwargs.get("model")

        if isinstance(model, str) and model in self.failures_before_success:
            remaining = self.failures_before_success[model]
            if remaining > 0:
                self.failures_before_success[model] = remaining - 1
                raise self.failure_exc_by_model.get(model, RuntimeError("boom"))

        if isinstance(model, str) and model in self.responses_by_model:
            resp = self.responses_by_model[model]
        else:
            resp = self.default_response

        if isinstance(resp, Exception):
            raise resp
        if resp is None:
            raise RuntimeError("No response configured")
        return resp


@pytest.fixture
def fake_db() -> FakeAsyncSession:
    return FakeAsyncSession()


@pytest.fixture
def current_user() -> Any:
    return SimpleNamespace(id=uuid4(), role="reviewer", access_status="approved")


@pytest.fixture
def model_config() -> Any:
    return SimpleNamespace(
        name="gpt-4o",
        provider="openai",
        litellm_model="openai/gpt-4o",
        api_key_env="OPENAI_API_KEY",
    )


@pytest.fixture
def prompt_template() -> Any:
    return SimpleNamespace(template="Q: {question}")


@pytest.fixture
def mock_litellm_acompletion(monkeypatch: pytest.MonkeyPatch) -> LiteLLMStub:
    """Monkeypatch litellm.acompletion with a configurable stub."""

    import litellm

    stub = LiteLLMStub()
    monkeypatch.setattr(litellm, "acompletion", stub.acompletion)
    return stub


@pytest.fixture
def mock_litellm_failing(mock_litellm_acompletion: LiteLLMStub) -> LiteLLMStub:
    """Alias fixture used for retry/failure-focused tests."""

    return mock_litellm_acompletion
