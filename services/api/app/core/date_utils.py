"""Utility for formatting datetime to UTC+8 date string for LLM prompts."""

from datetime import datetime, timedelta, timezone

_UTC_PLUS_8 = timezone(timedelta(hours=8))


def format_date_cn(dt: datetime) -> str:
    """Convert a datetime to a YYYY-MM-DD string in UTC+8 (China Standard Time).

    The clock injected by services always returns UTC. This function shifts to
    UTC+8 and formats as a date-only string for use in LLM prompts.
    """
    return dt.astimezone(_UTC_PLUS_8).strftime("%Y-%m-%d")
