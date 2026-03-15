from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class QuotaDecision:
    allowed: bool
    quota_limit: int
    quota_used: int
    retry_after_seconds: int | None
    next_available_at: datetime | None


class IPQuotaPolicy:
    def __init__(self, *, limit: int, window: timedelta) -> None:
        self.limit = limit
        self.window = window

    def evaluate(
        self,
        *,
        created_at_values: list[datetime],
        now: datetime,
    ) -> QuotaDecision:
        window_start = now - self.window
        recent = sorted(
            timestamp for timestamp in created_at_values if timestamp >= window_start
        )
        quota_used = len(recent)

        if quota_used < self.limit:
            return QuotaDecision(
                allowed=True,
                quota_limit=self.limit,
                quota_used=quota_used,
                retry_after_seconds=None,
                next_available_at=None,
            )

        next_available_at = recent[0] + self.window
        retry_after_seconds = max(1, int((next_available_at - now).total_seconds()))
        return QuotaDecision(
            allowed=False,
            quota_limit=self.limit,
            quota_used=quota_used,
            retry_after_seconds=retry_after_seconds,
            next_available_at=next_available_at,
        )
