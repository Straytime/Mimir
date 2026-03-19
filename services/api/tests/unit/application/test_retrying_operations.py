import pytest

from app.application.services.invocation import (
    RetryableOperationError,
    RetryingOperationInvoker,
)
from app.core.retry import RetryPolicy


@pytest.mark.asyncio
async def test_retrying_operation_invoker_retries_transient_failures_before_success() -> None:
    failures = 0
    delays: list[float] = []

    async def operation() -> str:
        nonlocal failures
        failures += 1
        if failures < 3:
            raise RetryableOperationError("temporary")
        return "ok"

    async def sleeper(seconds: float) -> None:
        delays.append(seconds)

    invoker = RetryingOperationInvoker[str](
        retry_policy=RetryPolicy(max_retries=3, wait_seconds=2),
        sleeper=sleeper,
    )

    result = await invoker.invoke(operation)

    assert result == "ok"
    assert failures == 3
    assert delays == [2.0, 4.0]  # exponential backoff: 2*2^0=2, 2*2^1=4


@pytest.mark.asyncio
async def test_retrying_operation_invoker_raises_after_policy_is_exhausted() -> None:
    async def operation() -> str:
        raise RetryableOperationError("still failing")

    invoker = RetryingOperationInvoker[str](
        retry_policy=RetryPolicy(max_retries=2, wait_seconds=1),
    )

    with pytest.raises(RetryableOperationError):
        await invoker.invoke(operation)
