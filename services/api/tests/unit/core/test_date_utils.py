from datetime import UTC, datetime, timezone

from app.core.date_utils import format_date_cn


def test_utc_evening_converts_to_next_day_in_utc8() -> None:
    """UTC 20:00 = UTC+8 04:00 next day."""
    dt = datetime(2026, 4, 3, 20, 0, 0, tzinfo=UTC)
    assert format_date_cn(dt) == "2026-04-04"


def test_utc_morning_stays_same_day_in_utc8() -> None:
    """UTC 10:00 = UTC+8 18:00 same day."""
    dt = datetime(2026, 4, 3, 10, 0, 0, tzinfo=UTC)
    assert format_date_cn(dt) == "2026-04-03"


def test_utc_midnight_converts_to_morning_utc8() -> None:
    """UTC 00:00 = UTC+8 08:00 same day."""
    dt = datetime(2026, 1, 15, 0, 0, 0, tzinfo=UTC)
    assert format_date_cn(dt) == "2026-01-15"


def test_utc_1559_stays_same_day_in_utc8() -> None:
    """UTC 15:59 = UTC+8 23:59, still same day."""
    dt = datetime(2026, 12, 31, 15, 59, 0, tzinfo=UTC)
    assert format_date_cn(dt) == "2026-12-31"


def test_utc_1600_crosses_to_next_day_in_utc8() -> None:
    """UTC 16:00 = UTC+8 00:00 next day."""
    dt = datetime(2026, 12, 31, 16, 0, 0, tzinfo=UTC)
    assert format_date_cn(dt) == "2027-01-01"


def test_format_is_exactly_10_chars() -> None:
    dt = datetime(2026, 4, 3, 12, 0, 0, tzinfo=UTC)
    result = format_date_cn(dt)
    assert len(result) == 10
    assert "T" not in result
    assert "+" not in result
