import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.core.retry import RetryPolicy


class RetryableLLMError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class TextGeneration:
    deltas: tuple[str, ...]
    full_text: str
    provider_finish_reason: str | None = None
    provider_usage: dict[str, Any] | None = None


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
