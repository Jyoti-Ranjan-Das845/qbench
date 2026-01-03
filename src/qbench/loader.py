"""Scenario loader for QBench seed files."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TaskEvent(BaseModel):
    """Event representing a task arrival."""

    type: str = Field(description="Event type (arrival, cancel, capacity_change)")
    task: dict[str, Any] | None = Field(default=None, description="Task data for arrivals")
    task_id: str | None = Field(default=None, description="Task ID for cancellations")
    new_capacity: int | None = Field(default=None, description="New capacity for capacity changes")


class SeedConfig(BaseModel):
    """Validated seed configuration."""

    horizon: int = Field(gt=0, description="Total time steps for the episode")
    capacity_per_step: int = Field(gt=0, description="Slots available per step")
    events: dict[str, list[TaskEvent]] = Field(
        default_factory=dict, description="Events scheduled at each time step"
    )

    @field_validator("events", mode="before")
    @classmethod
    def validate_events(cls, v: dict[str, Any]) -> dict[str, list[TaskEvent]]:
        """Validate and convert event structure."""
        if not isinstance(v, dict):
            raise ValueError("events must be a dictionary")

        validated_events: dict[str, list[TaskEvent]] = {}
        for step_str, events_list in v.items():
            # Validate step is a valid integer string
            try:
                step = int(step_str)
                if step < 0:
                    raise ValueError(f"Event step must be non-negative: {step}")
            except ValueError as e:
                raise ValueError(f"Invalid event step key: {step_str}") from e

            # Validate events list
            if not isinstance(events_list, list):
                raise ValueError(f"Events at step {step} must be a list")

            validated_events[step_str] = [TaskEvent.model_validate(e) for e in events_list]

        return validated_events


class ScenarioLoader:
    """Loads and validates QBench scenario seed files."""

    def __init__(self, scenarios_dir: str | Path = "scenarios") -> None:
        """
        Initialize the scenario loader.

        Args:
            scenarios_dir: Path to the scenarios directory
        """
        self.scenarios_dir = Path(scenarios_dir)
        if not self.scenarios_dir.exists():
            raise ValueError(f"Scenarios directory not found: {self.scenarios_dir}")

    def load(self, path: str | Path) -> SeedConfig:
        """
        Load and validate a seed JSON file.

        Args:
            path: Path to the seed file (absolute or relative to scenarios_dir)

        Returns:
            Validated SeedConfig object

        Raises:
            FileNotFoundError: If seed file doesn't exist
            ValueError: If seed file is invalid
            json.JSONDecodeError: If JSON is malformed
        """
        seed_path = Path(path)

        # If path is not absolute, try relative to scenarios_dir
        if not seed_path.is_absolute():
            seed_path = self.scenarios_dir / seed_path

        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_path}")

        # Load JSON
        with open(seed_path) as f:
            raw_config = json.load(f)

        # Validate with pydantic
        config = SeedConfig.model_validate(raw_config)

        # Additional validation
        self._validate_config(config)

        return config

    def _validate_config(self, config: SeedConfig) -> None:
        """
        Perform additional validation on the config.

        Args:
            config: The seed configuration to validate

        Raises:
            ValueError: If validation fails
        """
        # Check all event times are within horizon
        for step_str in config.events.keys():
            step = int(step_str)
            if step >= config.horizon:
                raise ValueError(f"Event scheduled at step {step} but horizon is {config.horizon}")

        # Check all task deadlines are valid
        task_ids = set()
        for events_list in config.events.values():
            for event in events_list:
                if event.type == "arrival" and event.task:
                    task_id = event.task.get("id")
                    deadline = event.task.get("deadline")
                    arrival_time = event.task.get("arrival_time")

                    # Check for duplicate task IDs
                    if task_id in task_ids:
                        raise ValueError(f"Duplicate task ID: {task_id}")
                    task_ids.add(task_id)

                    # Check deadline is within horizon
                    if deadline is not None and deadline >= config.horizon:
                        raise ValueError(
                            f"Task {task_id} deadline {deadline} exceeds horizon {config.horizon}"
                        )

                    # Check arrival_time is valid
                    if arrival_time is not None and arrival_time < 0:
                        raise ValueError(
                            f"Task {task_id} has negative arrival_time: {arrival_time}"
                        )

    def list_scenarios(self, scenario_type: str | None = None) -> list[Path]:
        """
        List all seed files in the scenarios directory.

        Args:
            scenario_type: Optional scenario type subdirectory to filter by

        Returns:
            List of paths to seed files
        """
        if scenario_type:
            search_dir = self.scenarios_dir / scenario_type
            if not search_dir.exists():
                raise ValueError(f"Scenario type not found: {scenario_type}")
        else:
            search_dir = self.scenarios_dir

        # Find all .json files recursively
        seed_files = list(search_dir.rglob("*.json"))
        return sorted(seed_files)

    def list_scenario_types(self) -> list[str]:
        """
        List all scenario type directories.

        Returns:
            List of scenario type names
        """
        # Get all subdirectories that contain .json files
        scenario_types = set()
        for seed_file in self.scenarios_dir.rglob("*.json"):
            # Get the immediate parent directory name
            scenario_type = seed_file.parent.name
            if scenario_type and scenario_type != self.scenarios_dir.name:
                scenario_types.add(scenario_type)

        return sorted(scenario_types)
