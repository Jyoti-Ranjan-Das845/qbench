"""Action data model for QBench."""

from typing import Literal

from pydantic import BaseModel, Field


class Action(BaseModel):
    """
    Represents an action the Purple agent can take.

    Actions allow the agent to control the queue system by scheduling,
    rescheduling, rejecting, or cancelling tasks.
    """

    type: Literal["schedule", "reschedule", "reject", "cancel", "noop"] = Field(
        description="Type of action to perform"
    )
    task_id: str | None = Field(default=None, description="ID of task to act on")
    step: int | None = Field(
        default=None, ge=0, description="Time step to schedule/reschedule task to"
    )
    slot_index: int | None = Field(
        default=None, ge=0, description="Slot index within the step (0-indexed)"
    )

    def __str__(self) -> str:
        """Human-readable string representation."""
        if self.type == "noop":
            return "Action(noop)"
        if self.type in ("schedule", "reschedule"):
            return f"Action({self.type} {self.task_id} → step {self.step})"
        return f"Action({self.type} {self.task_id})"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"Action(type={self.type!r}, task_id={self.task_id!r}, "
            f"step={self.step}, slot_index={self.slot_index})"
        )
