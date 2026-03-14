from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest

DEFAULT_TEST_NOW = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(slots=True)
class FakeClock:
    current: datetime = field(default_factory=lambda: DEFAULT_TEST_NOW)

    def now(self) -> datetime:
        return self.current

    def advance(
        self,
        *,
        seconds: int = 0,
        minutes: int = 0,
    ) -> None:
        self.current += timedelta(seconds=seconds, minutes=minutes)


@dataclass(slots=True)
class FakeIdGenerator:
    prefix: str = "id"
    counter: int = 0

    def next(self, prefix: str | None = None) -> str:
        effective_prefix = prefix or self.prefix
        self.counter += 1
        return f"{effective_prefix}_{self.counter:04d}"


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def fake_id_generator() -> FakeIdGenerator:
    return FakeIdGenerator()
