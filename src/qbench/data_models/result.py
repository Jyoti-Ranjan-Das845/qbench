"""Result data models for episode and benchmark outcomes."""

from pydantic import BaseModel, Field

from qbench.data_models.violation import Violation


class Metrics(BaseModel):
    """
    Soft metrics computed for an episode.

    These metrics are used for ranking passing agents.
    """

    routine_sla: float = Field(ge=0, le=1, description="Routine SLA compliance (0-1)")
    avg_wait_time: float = Field(ge=0, description="Average wait time for completed tasks")
    avg_backlog: float = Field(ge=0, description="Average pending queue size")
    max_backlog: int = Field(ge=0, description="Maximum pending queue size")
    avg_utilization: float = Field(ge=0, le=1, description="Average capacity utilization (0-1)")

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"Metrics(routine_sla={self.routine_sla:.3f}, "
            f"wait={self.avg_wait_time:.1f}, "
            f"backlog={self.avg_backlog:.1f}/{self.max_backlog}, "
            f"util={self.avg_utilization:.3f})"
        )


class EpisodeResult(BaseModel):
    """
    Final output of a single episode.

    Contains PASS/FAIL status, violations, metrics, and summary statistics.
    """

    passed: bool = Field(description="True if no hard constraint violations occurred")
    violations: list[Violation] = Field(
        default_factory=list,
        description="List of all hard constraint violations (empty if passed)"
    )
    metrics: Metrics = Field(description="Soft metrics for ranking")
    summary: dict = Field(
        default_factory=dict,
        description="Task counts: completed, missed, rejected, etc."
    )
    scenario_type: str | None = Field(default=None, description="Scenario type identifier")
    seed_number: str | None = Field(default=None, description="Seed number")
    execution_time: float | None = Field(default=None, description="Episode execution time in seconds")

    def __str__(self) -> str:
        """Human-readable string representation."""
        status = "PASS ✓" if self.passed else "FAIL ✗"
        violations_str = f" ({len(self.violations)} violations)" if not self.passed else ""
        return f"{status}{violations_str} - {self.metrics}"


class BenchmarkResult(BaseModel):
    """
    Aggregate results across all episodes in a benchmark run.

    Contains overall pass/fail counts, aggregated metrics, and per-episode results.
    """

    total_episodes: int = Field(ge=0, description="Total number of episodes run")
    passed: int = Field(ge=0, description="Number of episodes that passed")
    failed: int = Field(ge=0, description="Number of episodes that failed")
    results: list[EpisodeResult] = Field(
        default_factory=list,
        description="Individual episode results"
    )
    aggregate_metrics: Metrics | None = Field(
        default=None,
        description="Aggregated metrics across all passing episodes"
    )
    pass_rate: float = Field(ge=0, le=1, description="Percentage of episodes passed (0-1)")

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"BenchmarkResult({self.passed}/{self.total_episodes} passed, "
            f"{self.pass_rate:.1%} pass rate)"
        )
