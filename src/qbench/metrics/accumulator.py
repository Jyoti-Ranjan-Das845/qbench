"""Metrics accumulator for tracking soft metrics in QBench."""

from qbench.data_models.result import Metrics


class MetricsAccumulator:
    """
    Tracks soft metrics throughout an episode.

    Soft metrics:
    1. Routine SLA compliance - % routine tasks completed on-time
    2. Average wait time - mean(completed_time - arrival_time)
    3. Backlog size - avg and max pending queue size
    4. Utilization - % capacity used

    These metrics are used for ranking passing agents.
    """

    def __init__(self):
        """Initialize metric trackers."""
        # Per-step tracking
        self.backlog_samples = []
        self.utilization_samples = []

        # Task tracking
        self.routine_tasks_total = 0
        self.routine_tasks_on_time = 0
        self.wait_times = []

        # Overall
        self.steps_recorded = 0

    def record_step(
        self,
        pending_count: int,
        scheduled_count: int,
        capacity: int
    ) -> None:
        """
        Record metrics for current time step.

        Args:
            pending_count: Number of pending tasks
            scheduled_count: Number of tasks scheduled for future
            capacity: Capacity per step
        """
        # Record backlog
        self.backlog_samples.append(pending_count)

        # Record utilization (we don't track per-step utilization directly,
        # instead we compute it from schedule at the end)
        self.steps_recorded += 1

    def record_task_arrival(self, task) -> None:
        """
        Record when a routine task arrives.

        Args:
            task: Task that arrived
        """
        if task.priority == "routine":
            self.routine_tasks_total += 1

    def record_task_completion(self, task, completion_time: int) -> None:
        """
        Record when a task completes.

        Args:
            task: Task that completed
            completion_time: Step when task completed
        """
        # Record wait time for all completed tasks
        wait_time = completion_time - task.arrival_time
        self.wait_times.append(wait_time)

        # Check if routine task met SLA
        if task.priority == "routine":
            if completion_time <= task.deadline:
                self.routine_tasks_on_time += 1

    def record_schedule_utilization(self, schedule: dict, horizon: int, capacity: int) -> None:
        """
        Record utilization based on final schedule.

        This is called at the end of episode to compute actual utilization.

        Args:
            schedule: dict[int, list[str]] mapping step -> task_ids
            horizon: Total episode length
            capacity: Capacity per step
        """
        self.utilization_samples = []
        for step in range(horizon):
            tasks_at_step = len(schedule.get(step, []))
            utilization = tasks_at_step / capacity if capacity > 0 else 0
            self.utilization_samples.append(utilization)

    def finalize(self, schedule: dict, horizon: int, capacity: int) -> Metrics:
        """
        Compute final metrics at end of episode.

        Args:
            schedule: Final schedule dict
            horizon: Total episode length
            capacity: Capacity per step

        Returns:
            Metrics object with all computed metrics
        """
        # Compute routine SLA compliance
        if self.routine_tasks_total > 0:
            routine_sla = self.routine_tasks_on_time / self.routine_tasks_total
        else:
            routine_sla = 1.0  # No routine tasks = perfect compliance

        # Compute average wait time
        if self.wait_times:
            avg_wait = sum(self.wait_times) / len(self.wait_times)
        else:
            avg_wait = 0.0

        # Compute backlog stats
        if self.backlog_samples:
            avg_backlog = sum(self.backlog_samples) / len(self.backlog_samples)
            max_backlog = max(self.backlog_samples)
        else:
            avg_backlog = 0.0
            max_backlog = 0

        # Compute utilization (from final schedule)
        self.record_schedule_utilization(schedule, horizon, capacity)
        if self.utilization_samples:
            avg_utilization = sum(self.utilization_samples) / len(self.utilization_samples)
        else:
            avg_utilization = 0.0

        return Metrics(
            routine_sla=routine_sla,
            avg_wait_time=avg_wait,
            avg_backlog=avg_backlog,
            max_backlog=max_backlog,
            avg_utilization=avg_utilization
        )
