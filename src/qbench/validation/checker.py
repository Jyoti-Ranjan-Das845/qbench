"""Constraint checker for hard constraints in QBench."""

from qbench.data_models.violation import Violation


class ConstraintChecker:
    """
    Checks hard constraints that must hold for episode to PASS.

    Hard constraints:
    1. Urgent SLA miss - urgent task not completed by deadline
    2. Over-capacity - more tasks scheduled than capacity allows
    3. Double-booking - two tasks in same slot

    Note: urgent_reject and invalid_action are handled by ActionValidator
    """

    def check(self, env_state: dict, current_time: int) -> list[Violation]:
        """
        Check all hard constraints at current time step.

        Args:
            env_state: Dictionary containing:
                - tasks: dict[str, Task]
                - pending: set[str]
                - scheduled: set[str]
                - schedule: dict[int, list[str]]
                - capacity_per_step: int
            current_time: Current time step

        Returns:
            List of violations (empty if all constraints satisfied)
        """
        violations = []

        # Check urgent SLA miss
        violations.extend(self._check_urgent_sla_miss(env_state, current_time))

        # Check over-capacity
        violations.extend(self._check_overcapacity(env_state, current_time))

        # Check double-booking
        violations.extend(self._check_double_booking(env_state, current_time))

        return violations

    def _check_urgent_sla_miss(
        self,
        env_state: dict,
        current_time: int
    ) -> list[Violation]:
        """
        Check for urgent tasks that missed their deadlines.

        An urgent task misses SLA if:
        - priority == "urgent"
        - status in {pending, scheduled}
        - current_time > deadline
        """
        violations = []
        tasks = env_state["tasks"]
        pending = env_state["pending"]
        scheduled = env_state["scheduled"]

        # Check all pending and scheduled tasks
        for uid in pending | scheduled:
            task = tasks[uid]

            # Only check urgent tasks
            if task.priority != "urgent":
                continue

            # Check if past deadline
            if current_time > task.deadline:
                violations.append(Violation(
                    time=current_time,
                    type="urgent_sla_miss",
                    details={
                        "task_id": task.id,
                        "deadline": task.deadline,
                        "status": task.status
                    }
                ))

        return violations

    def _check_overcapacity(
        self,
        env_state: dict,
        current_time: int
    ) -> list[Violation]:
        """
        Check if any time step has more tasks scheduled than capacity allows.

        Checks all future steps (from current_time onward).
        """
        violations = []
        schedule = env_state["schedule"]
        capacity = env_state["capacity_per_step"]

        for step, task_ids in schedule.items():
            # Only check current and future steps
            if step < current_time:
                continue

            if len(task_ids) > capacity:
                violations.append(Violation(
                    time=current_time,
                    type="overcapacity",
                    details={
                        "step": step,
                        "scheduled_count": len(task_ids),
                        "capacity": capacity,
                        "task_ids": task_ids
                    }
                ))

        return violations

    def _check_double_booking(
        self,
        env_state: dict,
        current_time: int
    ) -> list[Violation]:
        """
        Check if any slot has multiple tasks assigned.

        In Tier-1, each task takes 1 slot. Double-booking would mean
        the same slot_index used twice at the same step.

        Note: Since we don't use slot_index in current implementation
        (schedule is just step -> [task_ids]), double-booking is
        detected as overcapacity. This method is here for future
        extensibility when slot_index is used.
        """
        # In current Tier-1 implementation, overcapacity check covers this
        # This is a placeholder for Tier-2 when explicit slot tracking is added
        return []
