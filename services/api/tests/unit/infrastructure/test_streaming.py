from datetime import UTC, datetime

from app.domain.enums import TaskPhase
from app.domain.schemas import EventEnvelope
from app.infrastructure.streaming.broker import serialize_sse_event


def test_serialize_sse_event_formats_standard_sse_frame() -> None:
    event = EventEnvelope(
        seq=7,
        event="task.created",
        task_id="tsk_123",
        revision_id="rev_123",
        phase=TaskPhase.CLARIFYING,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        payload={"snapshot": {"task_id": "tsk_123"}},
    )

    frame = serialize_sse_event(event).decode("utf-8")

    assert frame.startswith("id: 7\n")
    assert "event: task.created\n" in frame
    assert '"seq":7' in frame
    assert frame.endswith("\n\n")
