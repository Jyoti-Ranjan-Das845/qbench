"""Observation data model for QBench."""

from pydantic import BaseModel, Field

from qbench.task import Task


class ScheduledTask(BaseModel):
    """Represents a task that has been scheduled to a specific slot."""

    task: Task = Field(description="The scheduled task")
    slot: int = Field(ge=0, description="The time step when task is scheduled")


class Observation(BaseModel):
    """
    Observable state snapshot sent to the Purple agent at each time step.

    Contains current system state including pending/scheduled tasks,
    new arrivals, cancellations, and capacity information.
    """

    time: int = Field(ge=0, description="Current time step")
    horizon: int = Field(gt=0, description="Total episode horizon")
    capacity_per_step: int = Field(gt=0, description="Available slots per time step")

    # Events this step
    arrivals: list[Task] = Field(default_factory=list, description="Tasks arriving at current step")
    cancellations: list[str] = Field(
        default_factory=list, description="Task IDs cancelled this step"
    )

    # Current state
    pending: list[Task] = Field(default_factory=list, description="All pending tasks")
    scheduled: list[ScheduledTask] = Field(
        default_factory=list, description="All currently scheduled tasks"
    )

    # Optional feedback (recommended but not required)
    completed_this_step: list[str] = Field(
        default_factory=list, description="Task IDs completed this step"
    )
    missed_this_step: list[str] = Field(
        default_factory=list, description="Task IDs that became missed this step"
    )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"Observation(t={self.time}/{self.horizon}, "
            f"capacity={self.capacity_per_step}, "
            f"arrivals={len(self.arrivals)}, "
            f"pending={len(self.pending)}, "
            f"scheduled={len(self.scheduled)})"
        )
