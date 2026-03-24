import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.application.dto.invocation import LLMInvocation
from app.core.retry import RetryPolicy


class RetryableLLMError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class TextGeneration:
    deltas: tuple[str, ...]
    full_text: str
    request_id: str | None = None
    reasoning_text: str = ""
    tool_calls: tuple[dict[str, Any], ...] = ()
    provider_finish_reason: str | None = None
    provider_usage: dict[str, Any] | None = None
    request_payload: dict[str, Any] | None = None
    response_payload: dict[str, Any] | None = None


def build_trace_request_payload(
    *,
    invocation: LLMInvocation,
    explicit_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return dict(explicit_payload or invocation.to_provider_payload())


def build_trace_response_payload(
    *,
    explicit_payload: dict[str, Any] | None = None,
    parsed_text: str,
    reasoning_text: str = "",
    tool_calls: tuple[dict[str, Any], ...] = (),
    provider_finish_reason: str | None = None,
    provider_usage: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    if explicit_payload is not None:
        return dict(explicit_payload)
    return {
        "request_id": request_id,
        "parsed_text": parsed_text,
        "reasoning_text": reasoning_text,
        "tool_calls": list(tool_calls),
        "provider_finish_reason": provider_finish_reason,
        "provider_usage": provider_usage,
    }


class RetryingLLMInvoker:
    def __init__(
        self,
        *,
        retry_policy: RetryPolicy,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._retry_policy = retry_policy
        self._sleeper = sleeper

    async def invoke(
        self,
        operation: Callable[[], Awaitable[TextGeneration]],
    ) -> TextGeneration:
        failures = 0
        while True:
            try:
                return await operation()
            except RetryableLLMError:
                failures += 1
                decision = self._retry_policy.after_failure(failures=failures)
                if not decision.should_retry or decision.delay is None:
                    raise
                await self._sleeper(decision.delay.total_seconds())
