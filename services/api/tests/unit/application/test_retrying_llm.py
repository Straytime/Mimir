from collections.abc import Awaitable, Callable

import pytest

from app.application.services.llm import (
    RetryingLLMInvoker,
    RetryableLLMError,
    TextGeneration,
)
from app.core.retry import RetryPolicy


@pytest.mark.asyncio
async def test_retrying_llm_invoker_retries_transient_failures_before_success() -> None:
    failures = 0
    recorded_delays: list[float] = []

    async def operation() -> TextGeneration:
        nonlocal failures
        failures += 1
        if failures < 3:
            raise RetryableLLMError("temporary")
        return TextGeneration(
            deltas=("ok",),
            full_text="ok",
        )

    async def sleeper(seconds: float) -> None:
        recorded_delays.append(seconds)

    invoker = RetryingLLMInvoker(
        retry_policy=RetryPolicy(max_retries=3, wait_seconds=2),
        sleeper=sleeper,
    )

    result = await invoker.invoke(operation)

    assert result.full_text == "ok"
    assert failures == 3
    assert recorded_delays == [2.0, 4.0]  # exponential backoff: 2*2^0=2, 2*2^1=4


@pytest.mark.asyncio
async def test_retrying_llm_invoker_raises_after_policy_is_exhausted() -> None:
    async def operation() -> TextGeneration:
        raise RetryableLLMError("still failing")

    invoker = RetryingLLMInvoker(
        retry_policy=RetryPolicy(max_retries=2, wait_seconds=1),
    )

    with pytest.raises(RetryableLLMError):
        await invoker.invoke(operation)
