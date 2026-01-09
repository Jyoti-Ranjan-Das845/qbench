"""Observation formatter for converting observations to agent-readable text."""

from qbench.data_models.observation import Observation


class ObservationFormatter:
    """
    Converts Observation objects to human-readable text for Purple agents.

    Format includes:
    - Current time and horizon
    - Capacity
    - New arrivals with priority and deadline
    - Current pending tasks
    - Current scheduled tasks
    - Recent completions and misses (optional)
    """

    def format(self, obs: Observation) -> str:
        """
        Convert observation to formatted text.

        Args:
            obs: Observation object

        Returns:
            Human-readable string representation
        """
        lines = []

        # Header
        lines.append("=" * 70)
        lines.append(f"QUEUE STATUS — Step {obs.time} of {obs.horizon}")
        lines.append("=" * 70)
        lines.append("")

        # Capacity
        lines.append(f"CAPACITY: {obs.capacity_per_step} slots per step")
        lines.append("")

        # New arrivals
        if obs.arrivals:
            lines.append(f"NEW ARRIVALS ({len(obs.arrivals)}):")
            for task in obs.arrivals:
                lines.append(
                    f"  {task.id} [{task.priority.upper()}] "
                    f"arrived: {task.arrival_time}, deadline: {task.deadline}"
                )
        else:
            lines.append("NEW ARRIVALS: none")
        lines.append("")

        # Cancellations
        if obs.cancellations:
            lines.append(f"CANCELLATIONS ({len(obs.cancellations)}):")
            for task_id in obs.cancellations:
                lines.append(f"  {task_id}")
        else:
            lines.append("CANCELLATIONS: none")
        lines.append("")

        # Pending tasks
        if obs.pending:
            lines.append(f"PENDING TASKS ({len(obs.pending)}):")
            # Sort by deadline for easier viewing
            pending_sorted = sorted(obs.pending, key=lambda t: (t.deadline, t.priority))
            for task in pending_sorted:
                lines.append(
                    f"  {task.id} [{task.priority.upper()}] "
                    f"arrived: {task.arrival_time}, deadline: {task.deadline}"
                )
        else:
            lines.append("PENDING TASKS: none")
        lines.append("")

        # Scheduled tasks
        if obs.scheduled:
            lines.append(f"SCHEDULED TASKS ({len(obs.scheduled)}):")

            # Group tasks by step and auto-assign slot_index (0, 1, 2, ...)
            from collections import defaultdict
            tasks_by_step = defaultdict(list)
            for scheduled_task in obs.scheduled:
                tasks_by_step[scheduled_task.slot].append(scheduled_task)

            # Sort by step, then assign slot indices within each step
            for step in sorted(tasks_by_step.keys()):
                step_tasks = tasks_by_step[step]
                # Sort tasks within the step for consistent ordering
                step_tasks_sorted = sorted(step_tasks, key=lambda st: st.task.id)

                for slot_index, scheduled_task in enumerate(step_tasks_sorted):
                    task = scheduled_task.task
                    lines.append(
                        f"  {task.id} → slot [{step}, {slot_index}] "
                        f"[{task.priority.upper()}] arrived: {task.arrival_time}, deadline: {task.deadline}"
                    )
        else:
            lines.append("SCHEDULED TASKS: none")
        lines.append("")

        # Recent completions
        if obs.completed_this_step:
            lines.append(f"COMPLETED THIS STEP ({len(obs.completed_this_step)}):")
            for task_id in obs.completed_this_step:
                lines.append(f"  {task_id}")
        else:
            lines.append("COMPLETED THIS STEP: none")
        lines.append("")

        # Recent misses
        if obs.missed_this_step:
            lines.append(f"MISSED THIS STEP ({len(obs.missed_this_step)}):")
            for task_id in obs.missed_this_step:
                lines.append(f"  {task_id}")
        else:
            lines.append("MISSED THIS STEP: none")
        lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    def format_compact(self, obs: Observation) -> str:
        """
        Format observation in compact JSON-like format.

        Useful for agents that prefer structured data.

        Args:
            obs: Observation object

        Returns:
            JSON string representation
        """
        import json
        return json.dumps({
            "time": obs.time,
            "horizon": obs.horizon,
            "capacity": obs.capacity_per_step,
            "arrivals": [
                {
                    "id": t.id,
                    "priority": t.priority,
                    "deadline": t.deadline
                } for t in obs.arrivals
            ],
            "cancellations": obs.cancellations,
            "pending": [
                {
                    "id": t.id,
                    "priority": t.priority,
                    "deadline": t.deadline
                } for t in obs.pending
            ],
            "scheduled": [
                {
                    "id": st.task.id,
                    "step": st.slot,
                    "priority": st.task.priority,
                    "deadline": st.task.deadline
                } for st in obs.scheduled
            ],
            "completed_this_step": obs.completed_this_step,
            "missed_this_step": obs.missed_this_step
        }, indent=2)
