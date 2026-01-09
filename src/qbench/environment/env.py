"""QueueEnv - Core environment for QBench."""

from copy import deepcopy

from qbench.data_models.action import Action
from qbench.environment.loader import SeedConfig
from qbench.data_models.observation import Observation, ScheduledTask
from qbench.data_models.task import Task


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

    def find_task_by_id(
        self, task_id: str, status_set: set[str] | None = None
    ) -> tuple[Task | None, str | None]:
        """
        Find first task with given original ID (FIFO if duplicates exist).

        Args:
            task_id: Original task ID (what agent sees)
            status_set: Optional set of UIDs to search in (e.g., self.pending)

        Returns:
            (task, uid) if found, (None, None) otherwise
        """
        search_space = status_set if status_set is not None else self.tasks.keys()

        for uid in search_space:
            task = self.tasks.get(uid)
            if task and task.id == task_id:
                return task, uid

        return None, None

    def get_uid(self, task_id: str, status_set: set[str] | None = None) -> str | None:
        """
        Get internal UID for given original task ID (FIFO if duplicates).

        Args:
            task_id: Original task ID (what agent sees)
            status_set: Optional set of UIDs to search in

        Returns:
            UID if found, None otherwise
        """
        _, uid = self.find_task_by_id(task_id, status_set)
        return uid

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
        return self.observe()

    def act(self, actions: list[Action]) -> tuple[Observation, bool]:
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
        obs = self.observe()

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
                self.tasks[task.uid] = task
                self.pending.add(task.uid)
                self.current_arrivals.append(task)

            elif event.type == "cancel" and event.task_id:
                # External cancellation (not agent-initiated)
                task_id = event.task_id
                task, uid = self.find_task_by_id(task_id)
                if task and uid:
                    # Remove from current status set
                    if uid in self.pending:
                        self.pending.remove(uid)
                    elif uid in self.scheduled:
                        self.scheduled.remove(uid)
                        # Remove from schedule
                        if task.scheduled_slot is not None:
                            slot = task.scheduled_slot
                            if slot in self.schedule and uid in self.schedule[slot]:
                                self.schedule[slot].remove(uid)

                    # Mark as cancelled
                    task.status = "cancelled"
                    self.cancelled.add(uid)
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

        # Find task by original ID (FIFO if duplicates)
        task, uid = self.find_task_by_id(task_id)

        # Skip if task doesn't exist
        if not task or not uid:
            return

        if action.type == "schedule":
            if task.status == "pending" and action.step is not None:
                # Schedule the task
                task.status = "scheduled"
                task.scheduled_slot = action.step

                # Update state sets
                self.pending.discard(uid)
                self.scheduled.add(uid)

                # Add to schedule
                if action.step not in self.schedule:
                    self.schedule[action.step] = []
                self.schedule[action.step].append(uid)

        elif action.type == "reschedule":
            if task.status == "scheduled" and action.step is not None:
                # Remove from old slot
                old_slot = task.scheduled_slot
                if old_slot is not None and old_slot in self.schedule:
                    if uid in self.schedule[old_slot]:
                        self.schedule[old_slot].remove(uid)

                # Add to new slot
                task.scheduled_slot = action.step
                if action.step not in self.schedule:
                    self.schedule[action.step] = []
                self.schedule[action.step].append(uid)

        elif action.type == "reject":
            if task.status == "pending":
                # Reject the task (only valid for routine tasks)
                task.status = "rejected"
                self.pending.discard(uid)
                self.rejected.add(uid)

        elif action.type == "cancel":
            # Agent-initiated cancellation
            if task.status == "scheduled":
                # Remove from schedule
                if task.scheduled_slot is not None:
                    slot = task.scheduled_slot
                    if slot in self.schedule and uid in self.schedule[slot]:
                        self.schedule[slot].remove(uid)

                # Mark as cancelled
                task.status = "cancelled"
                self.scheduled.discard(uid)
                self.cancelled.add(uid)

    def _process_completions(self) -> None:
        """
        Process task completions for tasks scheduled at the current time.

        Tasks scheduled for the current step are marked as completed.
        """
        if self.time not in self.schedule:
            return

        for uid in self.schedule[self.time][:]:  # Copy list to avoid modification issues
            if uid in self.tasks:
                task = self.tasks[uid]
                if task.status == "scheduled":
                    task.status = "completed"
                    task.completed_time = self.time

                    self.scheduled.discard(uid)
                    self.completed.add(uid)
                    self.current_completions.append(task.id)

    def _mark_deadline_misses(self) -> None:
        """
        Mark tasks that have passed their deadline without completion.

        Checks all pending and scheduled tasks to see if current time
        exceeds their deadline.
        """
        # Check pending tasks
        for uid in list(self.pending):  # Copy to avoid modification during iteration
            task = self.tasks[uid]
            if self.time > task.deadline:
                task.status = "missed"
                self.pending.remove(uid)
                self.missed.add(uid)
                self.current_misses.append(task.id)

        # Check scheduled tasks
        for uid in list(self.scheduled):
            task = self.tasks[uid]
            if self.time > task.deadline:
                # Remove from schedule
                if task.scheduled_slot is not None:
                    slot = task.scheduled_slot
                    if slot in self.schedule and uid in self.schedule[slot]:
                        self.schedule[slot].remove(uid)

                task.status = "missed"
                self.scheduled.remove(uid)
                self.missed.add(uid)
                self.current_misses.append(task.id)

    def observe(self) -> Observation:
        """
        Build the current observation snapshot for the Purple agent.

        Returns:
            Observation containing current state and events
        """
        # Get all pending tasks
        pending_tasks = [self.tasks[uid] for uid in self.pending]

        # Get all scheduled tasks
        scheduled_tasks = [
            ScheduledTask(task=self.tasks[uid], slot=self.tasks[uid].scheduled_slot or 0)
            for uid in self.scheduled
            if self.tasks[uid].scheduled_slot is not None
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
