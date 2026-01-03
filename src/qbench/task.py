"""Task data model for QBench."""

from typing import Literal

from pydantic import BaseModel, Field


class Task(BaseModel):
    """
    Represents a single task in the queue system.

    A task arrives at a specific time, has a priority level and deadline,
    and transitions through various states as it's processed.
    """

    id: str = Field(description="Unique identifier for the task")
    arrival_time: int = Field(ge=0, description="Time step when task arrives")
    priority: Literal["urgent", "routine"] = Field(description="Task priority level")
    deadline: int = Field(ge=0, description="Latest step by which task must complete")
    status: Literal["pending", "scheduled", "completed", "rejected", "cancelled", "missed"] = Field(
        default="pending", description="Current status of the task"
    )
    scheduled_slot: int | None = Field(
        default=None, description="Time step when task is scheduled (if scheduled)"
    )
    completed_time: int | None = Field(
        default=None, description="Time step when task completed (if completed)"
    )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Task({self.id}, {self.priority}, deadline={self.deadline}, status={self.status})"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"Task(id={self.id!r}, arrival_time={self.arrival_time}, "
            f"priority={self.priority!r}, deadline={self.deadline}, "
            f"status={self.status!r}, scheduled_slot={self.scheduled_slot}, "
            f"completed_time={self.completed_time})"
        )
