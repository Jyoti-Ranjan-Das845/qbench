"""Violation data model for hard constraint violations."""

from pydantic import BaseModel, Field


class Violation(BaseModel):
    """
    Represents a hard constraint violation.

    Hard constraint violations cause an episode to FAIL immediately
    (though the episode continues to horizon for metrics collection).
    """

    time: int = Field(ge=0, description="Time step when violation was detected")
    type: str = Field(
        description="Type of violation: urgent_sla_miss, urgent_reject, "
        "overcapacity, double_booking, invalid_action"
    )
    details: dict = Field(
        default_factory=dict,
        description="Additional context: task_id, step, slot_index, etc."
    )

    def __str__(self) -> str:
        """Human-readable string representation."""
        details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
        return f"[t={self.time}] {self.type}: {details_str}"
