"""Action validator for QBench."""

from qbench.data_models.action import Action
from qbench.data_models.violation import Violation


def find_task_by_id(
    task_id: str, tasks: dict, status_set: set | None = None
) -> tuple[object | None, str | None]:
    """
    Find first task with given original ID (FIFO if duplicates exist).

    Args:
        task_id: Original task ID (what agent sees)
        tasks: Dictionary of tasks keyed by _uid
        status_set: Optional set of UIDs to search in

    Returns:
        (task, uid) if found, (None, None) otherwise
    """
    search_space = status_set if status_set is not None else tasks.keys()

    for uid in search_space:
        task = tasks.get(uid)
        if task and task.id == task_id:
            return task, uid

    return None, None


class ActionValidator:
    """
    Validates agent actions before applying them to the environment.

    Invalid actions result in Violation objects and cause episode failure.
    """

    def validate(
        self,
        action: Action,
        env_state: dict,
        current_time: int
    ) -> tuple[bool, Violation | None]:
        """
        Validate a single action.

        Args:
            action: The action to validate
            env_state: Dictionary containing:
                - tasks: dict[str, Task]
                - pending: set[str]
                - scheduled: set[str]
                - schedule: dict[int, list[str]]
                - capacity_per_step: int
                - horizon: int
            current_time: Current time step

        Returns:
            Tuple of (is_valid, violation)
            - If valid: (True, None)
            - If invalid: (False, Violation)
        """
        if action.type == "noop":
            return True, None

        # Extract required fields
        task_id = action.task_id
        if not task_id:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={"reason": "missing_task_id", "action_type": action.type}
            )

        tasks = env_state["tasks"]
        pending = env_state["pending"]
        scheduled = env_state["scheduled"]
        schedule = env_state["schedule"]
        capacity = env_state["capacity_per_step"]
        horizon = env_state["horizon"]

        # Find task by original ID (FIFO if duplicates)
        task, uid = find_task_by_id(task_id, tasks)

        # Check task exists
        if not task or not uid:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={"reason": "task_not_found", "task_id": task_id}
            )

        # Validate by action type
        if action.type == "schedule":
            return self._validate_schedule(
                action, task, uid, pending, schedule, capacity, horizon, current_time
            )

        elif action.type == "reschedule":
            return self._validate_reschedule(
                action, task, uid, scheduled, schedule, capacity, horizon, current_time
            )

        elif action.type == "reject":
            return self._validate_reject(task, uid, pending, current_time)

        elif action.type == "cancel":
            return self._validate_cancel(task, uid, scheduled, current_time)

        else:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={"reason": "unknown_action_type", "action_type": action.type}
            )

    def _validate_schedule(
        self,
        action: Action,
        task,
        uid: str,
        pending: set,
        schedule: dict,
        capacity: int,
        horizon: int,
        current_time: int
    ) -> tuple[bool, Violation | None]:
        """Validate a schedule action."""
        # Task must be pending
        if uid not in pending:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={
                    "reason": "task_not_pending",
                    "task_id": task.id,
                    "task_status": task.status
                }
            )

        # Must specify step
        if action.step is None:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={"reason": "missing_step", "task_id": task.id}
            )

        step = action.step

        # Step must be in valid range [current_time, horizon-1]
        if step < current_time or step >= horizon:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={
                    "reason": "step_out_of_range",
                    "task_id": task.id,
                    "step": step,
                    "valid_range": f"[{current_time}, {horizon-1}]"
                }
            )

        # Check capacity at that step
        tasks_at_step = schedule.get(step, [])
        if len(tasks_at_step) >= capacity:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={
                    "reason": "step_at_capacity",
                    "task_id": task.id,
                    "step": step,
                    "capacity": capacity,
                    "current_count": len(tasks_at_step)
                }
            )

        return True, None

    def _validate_reschedule(
        self,
        action: Action,
        task,
        uid: str,
        scheduled: set,
        schedule: dict,
        capacity: int,
        horizon: int,
        current_time: int
    ) -> tuple[bool, Violation | None]:
        """Validate a reschedule action."""
        # Task must be scheduled
        if uid not in scheduled:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={
                    "reason": "task_not_scheduled",
                    "task_id": task.id,
                    "task_status": task.status
                }
            )

        # Must specify step
        if action.step is None:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={"reason": "missing_step", "task_id": task.id}
            )

        step = action.step

        # Step must be in valid range
        if step < current_time or step >= horizon:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={
                    "reason": "step_out_of_range",
                    "task_id": task.id,
                    "step": step,
                    "valid_range": f"[{current_time}, {horizon-1}]"
                }
            )

        # Check capacity at new step (excluding this task if already scheduled there)
        tasks_at_step = [t_uid for t_uid in schedule.get(step, []) if t_uid != uid]
        if len(tasks_at_step) >= capacity:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={
                    "reason": "step_at_capacity",
                    "task_id": task.id,
                    "step": step,
                    "capacity": capacity
                }
            )

        return True, None

    def _validate_reject(
        self,
        task,
        uid: str,
        pending: set,
        current_time: int
    ) -> tuple[bool, Violation | None]:
        """Validate a reject action."""
        # Task must be pending
        if uid not in pending:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={
                    "reason": "task_not_pending",
                    "task_id": task.id,
                    "task_status": task.status
                }
            )

        # HARD CONSTRAINT: Cannot reject urgent tasks
        if task.priority == "urgent":
            return False, Violation(
                time=current_time,
                type="urgent_reject",
                details={"task_id": task.id, "deadline": task.deadline}
            )

        return True, None

    def _validate_cancel(
        self,
        task,
        uid: str,
        scheduled: set,
        current_time: int
    ) -> tuple[bool, Violation | None]:
        """Validate a cancel action."""
        # Task must be scheduled
        if uid not in scheduled:
            return False, Violation(
                time=current_time,
                type="invalid_action",
                details={
                    "reason": "task_not_scheduled",
                    "task_id": task.id,
                    "task_status": task.status
                }
            )

        return True, None
