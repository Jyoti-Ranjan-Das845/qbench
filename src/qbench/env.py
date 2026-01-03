"""QueueEnv - Core environment for QBench."""

from copy import deepcopy

from qbench.action import Action
from qbench.loader import SeedConfig
from qbench.observation import Observation, ScheduledTask
from qbench.task import Task


class QueueEnv:
    """
    Core queue management environment.

    Maintains the full state of the queue system and processes actions
    from the Purple agent. Handles task arrivals, cancellations, scheduling,
    completions, and deadline tracking.
    """

    def __init__(self, config: SeedConfig) -> None:
        """
        Initialize the environment from a seed configuration.

        Args:
            config: Validated seed configuration
        """
        self.horizon = config.horizon
        self.initial_capacity = config.capacity_per_step
        self.capacity_per_step = config.capacity_per_step
        self.event_schedule = config.events

        # State variables
        self.time = 0
        self.tasks: dict[str, Task] = {}

        # Task status sets for quick lookups
        self.pending: set[str] = set()
        self.scheduled: set[str] = set()
        self.completed: set[str] = set()
        self.rejected: set[str] = set()
        self.cancelled: set[str] = set()
        self.missed: set[str] = set()

        # Schedule: step -> list of task IDs
        self.schedule: dict[int, list[str]] = {}

        # Track events for current step (for observation)
        self.current_arrivals: list[Task] = []
        self.current_cancellations: list[str] = []
        self.current_completions: list[str] = []
        self.current_misses: list[str] = []

    def reset(self) -> Observation:
        """
        Reset environment to initial state and inject step 0 events.

        Returns:
            Initial observation for the Purple agent
        """
        # Reset time and state
        self.time = 0
        self.capacity_per_step = self.initial_capacity
        self.tasks.clear()

        self.pending.clear()
        self.scheduled.clear()
        self.completed.clear()
        self.rejected.clear()
        self.cancelled.clear()
        self.missed.clear()

        self.schedule.clear()

        self.current_arrivals.clear()
        self.current_cancellations.clear()
        self.current_completions.clear()
        self.current_misses.clear()

        # Inject events for step 0
        self._inject_events(0)

        # Build and return initial observation
        return self._build_observation()

    def step(self, actions: list[Action]) -> tuple[Observation, bool]:
        """
        Apply Purple agent actions and advance time by one step.

        Process flow:
        1. Apply agent actions (schedule, reschedule, reject, cancel)
        2. Process completions (tasks scheduled for current time)
        3. Mark deadline misses
        4. Advance time
        5. Inject next step's events
        6. Build next observation

        Args:
            actions: List of actions from the Purple agent

        Returns:
            Tuple of (next_observation, done)
            - done is True when time reaches horizon
        """
        # Clear current step tracking
        self.current_completions.clear()
        self.current_misses.clear()

        # Apply each action
        for action in actions:
            if action.type != "noop":
                self._apply_action(action)

        # Process completions for tasks scheduled at current time
        self._process_completions()

        # Advance time
        self.time += 1

        # Mark tasks that missed their deadlines (check after time advancement)
        self._mark_deadline_misses()

        # Check if episode is done
        done = self.time >= self.horizon

        # If not done, inject events for next step
        if not done:
            self._inject_events(self.time)

        # Build observation
        obs = self._build_observation()

        return obs, done

    def _inject_events(self, step: int) -> None:
        """
        Inject events scheduled for the given step.

        Handles arrivals, cancellations, and capacity changes.

        Args:
            step: The time step to inject events for
        """
        self.current_arrivals.clear()
        self.current_cancellations.clear()

        # Get events for this step (events dict uses string keys)
        events = self.event_schedule.get(str(step), [])

        for event in events:
            if event.type == "arrival" and event.task:
                # Create new task
                task_data = event.task
                task = Task(
                    id=task_data["id"],
                    arrival_time=task_data["arrival_time"],
                    priority=task_data["priority"],
                    deadline=task_data["deadline"],
                    status="pending",
                )
                self.tasks[task.id] = task
                self.pending.add(task.id)
                self.current_arrivals.append(task)

            elif event.type == "cancel" and event.task_id:
                # External cancellation (not agent-initiated)
                task_id = event.task_id
                if task_id in self.tasks:
                    task = self.tasks[task_id]

                    # Remove from current status set
                    if task_id in self.pending:
                        self.pending.remove(task_id)
                    elif task_id in self.scheduled:
                        self.scheduled.remove(task_id)
                        # Remove from schedule
                        if task.scheduled_slot is not None:
                            slot = task.scheduled_slot
                            if slot in self.schedule and task_id in self.schedule[slot]:
                                self.schedule[slot].remove(task_id)

                    # Mark as cancelled
                    task.status = "cancelled"
                    self.cancelled.add(task_id)
                    self.current_cancellations.append(task_id)

            elif event.type == "capacity_change" and event.new_capacity is not None:
                # Tier-2 feature: dynamic capacity changes
                self.capacity_per_step = event.new_capacity

    def _apply_action(self, action: Action) -> None:
        """
        Apply a single agent action to update the environment state.

        Note: This implementation does NOT validate actions - it assumes
        valid actions. Validation should be done by a separate ActionValidator.

        Args:
            action: The action to apply
        """
        if action.task_id is None:
            return

        task_id = action.task_id

        # Skip if task doesn't exist or is not in valid state
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]

        if action.type == "schedule":
            if task.status == "pending" and action.step is not None:
                # Schedule the task
                task.status = "scheduled"
                task.scheduled_slot = action.step

                # Update state sets
                self.pending.discard(task_id)
                self.scheduled.add(task_id)

                # Add to schedule
                if action.step not in self.schedule:
                    self.schedule[action.step] = []
                self.schedule[action.step].append(task_id)

        elif action.type == "reschedule":
            if task.status == "scheduled" and action.step is not None:
                # Remove from old slot
                old_slot = task.scheduled_slot
                if old_slot is not None and old_slot in self.schedule:
                    if task_id in self.schedule[old_slot]:
                        self.schedule[old_slot].remove(task_id)

                # Add to new slot
                task.scheduled_slot = action.step
                if action.step not in self.schedule:
                    self.schedule[action.step] = []
                self.schedule[action.step].append(task_id)

        elif action.type == "reject":
            if task.status == "pending":
                # Reject the task (only valid for routine tasks)
                task.status = "rejected"
                self.pending.discard(task_id)
                self.rejected.add(task_id)

        elif action.type == "cancel":
            # Agent-initiated cancellation
            if task.status == "scheduled":
                # Remove from schedule
                if task.scheduled_slot is not None:
                    slot = task.scheduled_slot
                    if slot in self.schedule and task_id in self.schedule[slot]:
                        self.schedule[slot].remove(task_id)

                # Mark as cancelled
                task.status = "cancelled"
                self.scheduled.discard(task_id)
                self.cancelled.add(task_id)

    def _process_completions(self) -> None:
        """
        Process task completions for tasks scheduled at the current time.

        Tasks scheduled for the current step are marked as completed.
        """
        if self.time not in self.schedule:
            return

        for task_id in self.schedule[self.time][:]:  # Copy list to avoid modification issues
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status == "scheduled":
                    task.status = "completed"
                    task.completed_time = self.time

                    self.scheduled.discard(task_id)
                    self.completed.add(task_id)
                    self.current_completions.append(task_id)

    def _mark_deadline_misses(self) -> None:
        """
        Mark tasks that have passed their deadline without completion.

        Checks all pending and scheduled tasks to see if current time
        exceeds their deadline.
        """
        # Check pending tasks
        for task_id in list(self.pending):  # Copy to avoid modification during iteration
            task = self.tasks[task_id]
            if self.time > task.deadline:
                task.status = "missed"
                self.pending.remove(task_id)
                self.missed.add(task_id)
                self.current_misses.append(task_id)

        # Check scheduled tasks
        for task_id in list(self.scheduled):
            task = self.tasks[task_id]
            if self.time > task.deadline:
                # Remove from schedule
                if task.scheduled_slot is not None:
                    slot = task.scheduled_slot
                    if slot in self.schedule and task_id in self.schedule[slot]:
                        self.schedule[slot].remove(task_id)

                task.status = "missed"
                self.scheduled.remove(task_id)
                self.missed.add(task_id)
                self.current_misses.append(task_id)

    def _build_observation(self) -> Observation:
        """
        Build the current observation snapshot for the Purple agent.

        Returns:
            Observation containing current state and events
        """
        # Get all pending tasks
        pending_tasks = [self.tasks[tid] for tid in self.pending]

        # Get all scheduled tasks
        scheduled_tasks = [
            ScheduledTask(task=self.tasks[tid], slot=self.tasks[tid].scheduled_slot or 0)
            for tid in self.scheduled
            if self.tasks[tid].scheduled_slot is not None
        ]

        return Observation(
            time=self.time,
            horizon=self.horizon,
            capacity_per_step=self.capacity_per_step,
            arrivals=deepcopy(self.current_arrivals),
            cancellations=self.current_cancellations.copy(),
            pending=deepcopy(pending_tasks),
            scheduled=deepcopy(scheduled_tasks),
            completed_this_step=self.current_completions.copy(),
            missed_this_step=self.current_misses.copy(),
        )

    def get_state_summary(self) -> dict[str, int]:
        """
        Get a summary of current state counts.

        Returns:
            Dictionary with counts of tasks in each status
        """
        return {
            "time": self.time,
            "pending": len(self.pending),
            "scheduled": len(self.scheduled),
            "completed": len(self.completed),
            "rejected": len(self.rejected),
            "cancelled": len(self.cancelled),
            "missed": len(self.missed),
            "total_tasks": len(self.tasks),
        }
