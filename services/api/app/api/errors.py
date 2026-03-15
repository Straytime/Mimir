from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    detail: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
