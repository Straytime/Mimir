from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class RetryDecision:
    should_retry: bool
    retry_number: int | None
    delay: timedelta | None


class RetryPolicy:
    def __init__(
        self,
        *,
        max_retries: int = 3,
        wait_seconds: int = 3,
    ) -> None:
        if max_retries < 1:
            raise ValueError("max_retries must be at least 1")
        if wait_seconds < 0:
            raise ValueError("wait_seconds must be non-negative")

        self.max_retries = max_retries
        self.wait_seconds = wait_seconds

    def after_failure(self, *, failures: int) -> RetryDecision:
        if failures < 1:
            raise ValueError("failures must be at least 1")

        if failures <= self.max_retries:
            return RetryDecision(
                should_retry=True,
                retry_number=failures,
                delay=timedelta(seconds=self.wait_seconds),
            )

        return RetryDecision(
            should_retry=False,
            retry_number=None,
            delay=None,
        )

    def is_exhausted(self, *, failures: int) -> bool:
        if failures < 1:
            raise ValueError("failures must be at least 1")

        return failures > self.max_retries
