from app.domain.enums import TaskPhase, TaskStatus


class DomainError(Exception):
    """Base error type for pure domain failures."""


class InvalidStatusPhaseCombinationError(DomainError):
    def __init__(self, *, status: TaskStatus, phase: TaskPhase) -> None:
        super().__init__(f"Invalid status/phase combination: {status}/{phase}")
        self.status = status
        self.phase = phase


class InvalidTaskTransitionError(DomainError):
    def __init__(
        self,
        *,
        current_status: TaskStatus,
        current_phase: TaskPhase,
        target_status: TaskStatus,
        target_phase: TaskPhase,
    ) -> None:
        super().__init__(
            "Invalid task transition: "
            f"{current_status}/{current_phase} -> {target_status}/{target_phase}"
        )
        self.current_status = current_status
        self.current_phase = current_phase
        self.target_status = target_status
        self.target_phase = target_phase
