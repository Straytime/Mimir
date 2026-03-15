import pytest

from app.domain.enums import TaskPhase, TaskStatus
from app.domain.exceptions import (
    InvalidStatusPhaseCombinationError,
    InvalidTaskTransitionError,
)
from app.domain.state_machine import TaskLifecycleState, TaskStateMachine


def test_task_state_machine_allows_documented_happy_path_transitions() -> None:
    state = TaskLifecycleState(status=TaskStatus.RUNNING, phase=TaskPhase.CLARIFYING)

    state = TaskStateMachine.transition(
        current=state,
        target=TaskLifecycleState(
            status=TaskStatus.AWAITING_USER_INPUT,
            phase=TaskPhase.CLARIFYING,
        ),
    )
    state = TaskStateMachine.transition(
        current=state,
        target=TaskLifecycleState(
            status=TaskStatus.RUNNING,
            phase=TaskPhase.ANALYZING_REQUIREMENT,
        ),
    )
    state = TaskStateMachine.transition(
        current=state,
        target=TaskLifecycleState(
            status=TaskStatus.RUNNING,
            phase=TaskPhase.PLANNING_COLLECTION,
        ),
    )
    state = TaskStateMachine.transition(
        current=state,
        target=TaskLifecycleState(
            status=TaskStatus.RUNNING,
            phase=TaskPhase.COLLECTING,
        ),
    )
    state = TaskStateMachine.transition(
        current=state,
        target=TaskLifecycleState(
            status=TaskStatus.RUNNING,
            phase=TaskPhase.SUMMARIZING_COLLECTION,
        ),
    )
    state = TaskStateMachine.transition(
        current=state,
        target=TaskLifecycleState(
            status=TaskStatus.RUNNING,
            phase=TaskPhase.PLANNING_COLLECTION,
        ),
    )
    state = TaskStateMachine.transition(
        current=state,
        target=TaskLifecycleState(
            status=TaskStatus.RUNNING,
            phase=TaskPhase.MERGING_SOURCES,
        ),
    )
    state = TaskStateMachine.transition(
        current=state,
        target=TaskLifecycleState(
            status=TaskStatus.RUNNING,
            phase=TaskPhase.PREPARING_OUTLINE,
        ),
    )
    state = TaskStateMachine.transition(
        current=state,
        target=TaskLifecycleState(
            status=TaskStatus.RUNNING,
            phase=TaskPhase.WRITING_REPORT,
        ),
    )
    state = TaskStateMachine.transition(
        current=state,
        target=TaskLifecycleState(
            status=TaskStatus.AWAITING_FEEDBACK,
            phase=TaskPhase.DELIVERED,
        ),
    )
    state = TaskStateMachine.transition(
        current=state,
        target=TaskLifecycleState(
            status=TaskStatus.RUNNING,
            phase=TaskPhase.PROCESSING_FEEDBACK,
        ),
    )
    state = TaskStateMachine.transition(
        current=state,
        target=TaskLifecycleState(
            status=TaskStatus.RUNNING,
            phase=TaskPhase.PLANNING_COLLECTION,
        ),
    )

    assert state == TaskLifecycleState(
        status=TaskStatus.RUNNING,
        phase=TaskPhase.PLANNING_COLLECTION,
    )


def test_task_state_machine_allows_terminal_transitions_from_active_and_delivered_states() -> None:
    terminated = TaskStateMachine.transition(
        current=TaskLifecycleState(
            status=TaskStatus.RUNNING,
            phase=TaskPhase.COLLECTING,
        ),
        target=TaskLifecycleState(
            status=TaskStatus.TERMINATED,
            phase=TaskPhase.COLLECTING,
        ),
    )
    failed = TaskStateMachine.transition(
        current=TaskLifecycleState(
            status=TaskStatus.AWAITING_FEEDBACK,
            phase=TaskPhase.DELIVERED,
        ),
        target=TaskLifecycleState(
            status=TaskStatus.FAILED,
            phase=TaskPhase.DELIVERED,
        ),
    )
    expired = TaskStateMachine.transition(
        current=TaskLifecycleState(
            status=TaskStatus.AWAITING_FEEDBACK,
            phase=TaskPhase.DELIVERED,
        ),
        target=TaskLifecycleState(
            status=TaskStatus.EXPIRED,
            phase=TaskPhase.DELIVERED,
        ),
    )

    assert terminated.status is TaskStatus.TERMINATED
    assert failed.status is TaskStatus.FAILED
    assert expired.status is TaskStatus.EXPIRED


def test_task_state_machine_rejects_illegal_transitions() -> None:
    with pytest.raises(InvalidTaskTransitionError):
        TaskStateMachine.transition(
            current=TaskLifecycleState(
                status=TaskStatus.AWAITING_USER_INPUT,
                phase=TaskPhase.CLARIFYING,
            ),
            target=TaskLifecycleState(
                status=TaskStatus.AWAITING_FEEDBACK,
                phase=TaskPhase.DELIVERED,
            ),
        )

    with pytest.raises(InvalidTaskTransitionError):
        TaskStateMachine.transition(
            current=TaskLifecycleState(
                status=TaskStatus.RUNNING,
                phase=TaskPhase.WRITING_REPORT,
            ),
            target=TaskLifecycleState(
                status=TaskStatus.RUNNING,
                phase=TaskPhase.COLLECTING,
            ),
        )


def test_status_phase_matrix_matches_documented_public_combinations() -> None:
    valid_pairs = [
        (TaskStatus.AWAITING_USER_INPUT, TaskPhase.CLARIFYING),
        (TaskStatus.RUNNING, TaskPhase.CLARIFYING),
        (TaskStatus.RUNNING, TaskPhase.ANALYZING_REQUIREMENT),
        (TaskStatus.RUNNING, TaskPhase.PLANNING_COLLECTION),
        (TaskStatus.RUNNING, TaskPhase.COLLECTING),
        (TaskStatus.RUNNING, TaskPhase.SUMMARIZING_COLLECTION),
        (TaskStatus.RUNNING, TaskPhase.MERGING_SOURCES),
        (TaskStatus.RUNNING, TaskPhase.PREPARING_OUTLINE),
        (TaskStatus.RUNNING, TaskPhase.WRITING_REPORT),
        (TaskStatus.RUNNING, TaskPhase.PROCESSING_FEEDBACK),
        (TaskStatus.AWAITING_FEEDBACK, TaskPhase.DELIVERED),
        (TaskStatus.EXPIRED, TaskPhase.DELIVERED),
        (TaskStatus.TERMINATED, TaskPhase.COLLECTING),
        (TaskStatus.FAILED, TaskPhase.DELIVERED),
    ]

    for status, phase in valid_pairs:
        assert TaskStateMachine.is_valid_public_state(status=status, phase=phase)

    invalid_pairs = [
        (TaskStatus.AWAITING_USER_INPUT, TaskPhase.COLLECTING),
        (TaskStatus.AWAITING_FEEDBACK, TaskPhase.CLARIFYING),
        (TaskStatus.EXPIRED, TaskPhase.WRITING_REPORT),
        (TaskStatus.RUNNING, TaskPhase.DELIVERED),
    ]

    for status, phase in invalid_pairs:
        assert not TaskStateMachine.is_valid_public_state(status=status, phase=phase)

    with pytest.raises(InvalidStatusPhaseCombinationError):
        TaskStateMachine.ensure_public_state(
            status=TaskStatus.AWAITING_FEEDBACK,
            phase=TaskPhase.COLLECTING,
        )
