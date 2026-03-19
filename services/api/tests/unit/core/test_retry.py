from datetime import timedelta

import pytest

from app.core.retry import RetryPolicy


def test_retry_policy_uses_exponential_backoff_by_default() -> None:
    policy = RetryPolicy()

    first_retry = policy.after_failure(failures=1)
    second_retry = policy.after_failure(failures=2)
    third_retry = policy.after_failure(failures=3)
    exhausted = policy.after_failure(failures=4)

    assert first_retry.should_retry is True
    assert first_retry.retry_number == 1
    assert first_retry.delay == timedelta(seconds=3)

    assert second_retry.should_retry is True
    assert second_retry.retry_number == 2
    assert second_retry.delay == timedelta(seconds=6)

    assert third_retry.should_retry is True
    assert third_retry.retry_number == 3
    assert third_retry.delay == timedelta(seconds=12)

    assert exhausted.should_retry is False
    assert exhausted.retry_number is None
    assert exhausted.delay is None
    assert policy.is_exhausted(failures=4) is True


def test_retry_policy_backoff_multiplier_one_gives_fixed_interval() -> None:
    policy = RetryPolicy(max_retries=3, wait_seconds=5, backoff_multiplier=1.0)

    delays = [
        policy.after_failure(failures=i).delay
        for i in range(1, 4)
    ]

    assert delays == [timedelta(seconds=5)] * 3


def test_retry_policy_max_wait_seconds_caps_delay() -> None:
    policy = RetryPolicy(
        max_retries=3,
        wait_seconds=10,
        backoff_multiplier=3.0,
        max_wait_seconds=20.0,
    )

    # failures=1 → 10s, failures=2 → 30s capped to 20s, failures=3 → 90s capped to 20s
    assert policy.after_failure(failures=1).delay == timedelta(seconds=10)
    assert policy.after_failure(failures=2).delay == timedelta(seconds=20)
    assert policy.after_failure(failures=3).delay == timedelta(seconds=20)


def test_retry_policy_supports_custom_configuration_without_adapter_dependencies() -> None:
    policy = RetryPolicy(max_retries=2, wait_seconds=5)

    decision = policy.after_failure(failures=2)

    assert decision.should_retry is True
    assert decision.delay == timedelta(seconds=10)  # 5 * 2^(2-1) = 10

    with pytest.raises(ValueError):
        policy.after_failure(failures=0)


def test_retry_policy_rejects_invalid_backoff_multiplier() -> None:
    with pytest.raises(ValueError, match="backoff_multiplier"):
        RetryPolicy(backoff_multiplier=0.5)


def test_retry_policy_rejects_invalid_max_wait_seconds() -> None:
    with pytest.raises(ValueError, match="max_wait_seconds"):
        RetryPolicy(max_wait_seconds=0)

    with pytest.raises(ValueError, match="max_wait_seconds"):
        RetryPolicy(max_wait_seconds=-1)
