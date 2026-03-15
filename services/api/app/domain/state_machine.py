from dataclasses import dataclass

from app.domain.enums import TaskPhase, TaskStatus
from app.domain.exceptions import (
    InvalidStatusPhaseCombinationError,
    InvalidTaskTransitionError,
)


@dataclass(frozen=True, slots=True)
class TaskLifecycleState:
    status: TaskStatus
    phase: TaskPhase


class TaskStateMachine:
    _ACTIVE_PHASES = frozenset(
        {
            TaskPhase.CLARIFYING,
            TaskPhase.ANALYZING_REQUIREMENT,
            TaskPhase.PLANNING_COLLECTION,
            TaskPhase.COLLECTING,
            TaskPhase.SUMMARIZING_COLLECTION,
            TaskPhase.MERGING_SOURCES,
            TaskPhase.PREPARING_OUTLINE,
            TaskPhase.WRITING_REPORT,
            TaskPhase.PROCESSING_FEEDBACK,
        }
    )
    _PUBLIC_PHASES_BY_STATUS = {
        TaskStatus.AWAITING_USER_INPUT: frozenset({TaskPhase.CLARIFYING}),
        TaskStatus.RUNNING: _ACTIVE_PHASES,
        TaskStatus.AWAITING_FEEDBACK: frozenset({TaskPhase.DELIVERED}),
        TaskStatus.EXPIRED: frozenset({TaskPhase.DELIVERED}),
        TaskStatus.TERMINATED: _ACTIVE_PHASES | {TaskPhase.DELIVERED},
        TaskStatus.FAILED: _ACTIVE_PHASES | {TaskPhase.DELIVERED},
    }
    _RUNNING_TRANSITIONS = {
        TaskPhase.CLARIFYING: frozenset(
            {
                TaskLifecycleState(
                    status=TaskStatus.AWAITING_USER_INPUT,
                    phase=TaskPhase.CLARIFYING,
                ),
                TaskLifecycleState(
                    status=TaskStatus.RUNNING,
                    phase=TaskPhase.ANALYZING_REQUIREMENT,
                ),
            }
        ),
        TaskPhase.ANALYZING_REQUIREMENT: frozenset(
            {
                TaskLifecycleState(
                    status=TaskStatus.RUNNING,
                    phase=TaskPhase.PLANNING_COLLECTION,
                ),
            }
        ),
        TaskPhase.PLANNING_COLLECTION: frozenset(
            {
                TaskLifecycleState(
                    status=TaskStatus.RUNNING,
                    phase=TaskPhase.COLLECTING,
                ),
                TaskLifecycleState(
                    status=TaskStatus.RUNNING,
                    phase=TaskPhase.MERGING_SOURCES,
                ),
            }
        ),
        TaskPhase.COLLECTING: frozenset(
            {
                TaskLifecycleState(
                    status=TaskStatus.RUNNING,
                    phase=TaskPhase.SUMMARIZING_COLLECTION,
                ),
            }
        ),
        TaskPhase.SUMMARIZING_COLLECTION: frozenset(
            {
                TaskLifecycleState(
                    status=TaskStatus.RUNNING,
                    phase=TaskPhase.PLANNING_COLLECTION,
                ),
            }
        ),
        TaskPhase.MERGING_SOURCES: frozenset(
            {
                TaskLifecycleState(
                    status=TaskStatus.RUNNING,
                    phase=TaskPhase.PREPARING_OUTLINE,
                ),
            }
        ),
        TaskPhase.PREPARING_OUTLINE: frozenset(
            {
                TaskLifecycleState(
                    status=TaskStatus.RUNNING,
                    phase=TaskPhase.WRITING_REPORT,
                ),
            }
        ),
        TaskPhase.WRITING_REPORT: frozenset(
            {
                TaskLifecycleState(
                    status=TaskStatus.AWAITING_FEEDBACK,
                    phase=TaskPhase.DELIVERED,
                ),
            }
        ),
        TaskPhase.PROCESSING_FEEDBACK: frozenset(
            {
                TaskLifecycleState(
                    status=TaskStatus.RUNNING,
                    phase=TaskPhase.PLANNING_COLLECTION,
                ),
            }
        ),
    }

    @classmethod
    def is_valid_public_state(cls, *, status: TaskStatus, phase: TaskPhase) -> bool:
        return phase in cls._PUBLIC_PHASES_BY_STATUS.get(status, frozenset())

    @classmethod
    def is_valid_state(
        cls,
        *,
        status: TaskStatus,
        phase: TaskPhase,
        allow_internal: bool = False,
    ) -> bool:
        if cls.is_valid_public_state(status=status, phase=phase):
            return True

        if allow_internal and status is TaskStatus.PURGED:
            return phase in cls._ACTIVE_PHASES | {TaskPhase.DELIVERED}

        return False

    @classmethod
    def ensure_public_state(cls, *, status: TaskStatus, phase: TaskPhase) -> None:
        if not cls.is_valid_public_state(status=status, phase=phase):
            raise InvalidStatusPhaseCombinationError(status=status, phase=phase)

    @classmethod
    def ensure_state(
        cls,
        *,
        status: TaskStatus,
        phase: TaskPhase,
        allow_internal: bool = False,
    ) -> None:
        if not cls.is_valid_state(
            status=status,
            phase=phase,
            allow_internal=allow_internal,
        ):
            raise InvalidStatusPhaseCombinationError(status=status, phase=phase)

    @classmethod
    def can_transition(
        cls,
        *,
        current: TaskLifecycleState,
        target: TaskLifecycleState,
    ) -> bool:
        cls.ensure_state(
            status=current.status,
            phase=current.phase,
            allow_internal=True,
        )
        cls.ensure_state(
            status=target.status,
            phase=target.phase,
            allow_internal=True,
        )

        if current == target:
            return True

        if target.status in {TaskStatus.TERMINATED, TaskStatus.FAILED}:
            return current.phase == target.phase and current.phase in (
                cls._ACTIVE_PHASES | {TaskPhase.DELIVERED}
            )

        if target.status is TaskStatus.PURGED:
            return (
                current.status in {TaskStatus.TERMINATED, TaskStatus.FAILED, TaskStatus.EXPIRED}
                and current.phase == target.phase
            )

        if current.status in {
            TaskStatus.TERMINATED,
            TaskStatus.FAILED,
            TaskStatus.EXPIRED,
            TaskStatus.PURGED,
        }:
            return False

        if current.status is TaskStatus.AWAITING_USER_INPUT:
            return target == TaskLifecycleState(
                status=TaskStatus.RUNNING,
                phase=TaskPhase.ANALYZING_REQUIREMENT,
            )

        if current.status is TaskStatus.AWAITING_FEEDBACK:
            return target in {
                TaskLifecycleState(
                    status=TaskStatus.RUNNING,
                    phase=TaskPhase.PROCESSING_FEEDBACK,
                ),
                TaskLifecycleState(
                    status=TaskStatus.EXPIRED,
                    phase=TaskPhase.DELIVERED,
                ),
            }

        if current.status is TaskStatus.RUNNING:
            return target in cls._RUNNING_TRANSITIONS.get(current.phase, frozenset())

        return False

    @classmethod
    def transition(
        cls,
        *,
        current: TaskLifecycleState,
        target: TaskLifecycleState,
    ) -> TaskLifecycleState:
        if not cls.can_transition(current=current, target=target):
            raise InvalidTaskTransitionError(
                current_status=current.status,
                current_phase=current.phase,
                target_status=target.status,
                target_phase=target.phase,
            )

        return target
