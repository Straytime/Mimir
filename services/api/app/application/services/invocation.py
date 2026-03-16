import asyncio
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

from app.core.retry import RetryPolicy


T = TypeVar("T")


class RetryableOperationError(Exception):
    pass


class RiskControlTriggered(Exception):
    pass


class RetryingOperationInvoker(Generic[T]):
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
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        failures = 0
        while True:
            try:
                return await operation()
            except RetryableOperationError:
                failures += 1
                decision = self._retry_policy.after_failure(failures=failures)
                if not decision.should_retry or decision.delay is None:
                    raise
                await self._sleeper(decision.delay.total_seconds())
