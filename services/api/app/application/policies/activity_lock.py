from dataclasses import dataclass


GLOBAL_ACTIVE_TASK_LOCK = "global_active_task"


@dataclass(frozen=True, slots=True)
class ActivityLockDecision:
    allowed: bool
    lock_name: str
    active_task_id: str | None


class ActivityLockPolicy:
    def evaluate(self, *, active_task_id: str | None) -> ActivityLockDecision:
        return ActivityLockDecision(
            allowed=active_task_id is None,
            lock_name=GLOBAL_ACTIVE_TASK_LOCK,
            active_task_id=active_task_id,
        )
