from datetime import UTC, datetime, timedelta

from app.application.policies.activity_lock import ActivityLockPolicy
from app.application.policies.ip_quota import IPQuotaPolicy


def test_activity_lock_policy_blocks_when_global_lock_is_held() -> None:
    decision = ActivityLockPolicy().evaluate(active_task_id="tsk_01JLOCK")

    assert decision.allowed is False
    assert decision.lock_name == "global_active_task"


def test_ip_quota_policy_returns_retry_budget_when_limit_is_exhausted() -> None:
    now = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    policy = IPQuotaPolicy(limit=3, window=timedelta(hours=24))

    decision = policy.evaluate(
        created_at_values=[
            now - timedelta(hours=23, minutes=30),
            now - timedelta(hours=2),
            now - timedelta(minutes=5),
        ],
        now=now,
    )

    assert decision.allowed is False
    assert decision.quota_limit == 3
    assert decision.quota_used == 3
    assert decision.retry_after_seconds == 1800
    assert decision.next_available_at == datetime(2026, 3, 15, 12, 30, tzinfo=UTC)
