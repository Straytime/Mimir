from datetime import timedelta

import pytest

from app.core.retry import RetryPolicy


def test_retry_policy_uses_documented_wait_and_retry_budget() -> None:
    policy = RetryPolicy()

    first_retry = policy.after_failure(failures=1)
    third_retry = policy.after_failure(failures=3)
    exhausted = policy.after_failure(failures=4)

    assert first_retry.should_retry is True
    assert first_retry.retry_number == 1
    assert first_retry.delay == timedelta(seconds=3)

    assert third_retry.should_retry is True
    assert third_retry.retry_number == 3
    assert third_retry.delay == timedelta(seconds=3)

    assert exhausted.should_retry is False
    assert exhausted.retry_number is None
    assert exhausted.delay is None
    assert policy.is_exhausted(failures=4) is True


def test_retry_policy_supports_custom_configuration_without_adapter_dependencies() -> None:
    policy = RetryPolicy(max_retries=2, wait_seconds=5)

    decision = policy.after_failure(failures=2)

    assert decision.should_retry is True
    assert decision.delay == timedelta(seconds=5)

    with pytest.raises(ValueError):
        policy.after_failure(failures=0)
