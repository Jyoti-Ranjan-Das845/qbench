"""Tests for ScenarioLoader."""

import json
import tempfile
from pathlib import Path

import pytest

from qbench.environment.loader import ScenarioLoader, SeedConfig


def test_seed_config_validation():
    """Test SeedConfig validation."""
    config = SeedConfig(
        horizon=20,
        capacity_per_step=3,
        events={
            "0": [
                {
                    "type": "arrival",
                    "task": {
                        "id": "task1",
                        "arrival_time": 0,
                        "priority": "urgent",
                        "deadline": 10,
                    },
                }
            ]
        },
    )
    assert config.horizon == 20
    assert config.capacity_per_step == 3
    assert "0" in config.events


def test_seed_config_invalid_horizon():
    """Test that invalid horizon is rejected."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SeedConfig(horizon=0, capacity_per_step=3, events={})


def test_scenario_loader_init():
    """Test ScenarioLoader initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = ScenarioLoader(tmpdir)
        assert loader.scenarios_dir == Path(tmpdir)


def test_scenario_loader_missing_dir():
    """Test ScenarioLoader with non-existent directory."""
    with pytest.raises(ValueError, match="not found"):
        ScenarioLoader("/nonexistent/directory")


def test_load_valid_seed():
    """Test loading a valid seed file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a valid seed file
        seed_data = {
            "horizon": 20,
            "capacity_per_step": 3,
            "events": {
                "0": [
                    {
                        "type": "arrival",
                        "task": {
                            "id": "task1",
                            "arrival_time": 0,
                            "priority": "urgent",
                            "deadline": 10,
                        },
                    }
                ]
            },
        }

        seed_file = Path(tmpdir) / "seed_1.json"
        with open(seed_file, "w") as f:
            json.dump(seed_data, f)

        loader = ScenarioLoader(tmpdir)
        config = loader.load(seed_file)

        assert config.horizon == 20
        assert config.capacity_per_step == 3


def test_load_seed_with_deadline_beyond_horizon():
    """Test that deadline beyond horizon is caught."""
    with tempfile.TemporaryDirectory() as tmpdir:
        seed_data = {
            "horizon": 10,
            "capacity_per_step": 3,
            "events": {
                "0": [
                    {
                        "type": "arrival",
                        "task": {
                            "id": "task1",
                            "arrival_time": 0,
                            "priority": "urgent",
                            "deadline": 20,  # Beyond horizon!
                        },
                    }
                ]
            },
        }

        seed_file = Path(tmpdir) / "seed_bad.json"
        with open(seed_file, "w") as f:
            json.dump(seed_data, f)

        loader = ScenarioLoader(tmpdir)
        with pytest.raises(ValueError, match="exceeds horizon"):
            loader.load(seed_file)


def test_load_seed_with_duplicate_task_ids():
    """Test that duplicate task IDs are allowed (handled with UUIDs internally)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        seed_data = {
            "horizon": 20,
            "capacity_per_step": 3,
            "events": {
                "0": [
                    {
                        "type": "arrival",
                        "task": {
                            "id": "task1",
                            "arrival_time": 0,
                            "priority": "urgent",
                            "deadline": 10,
                        },
                    },
                    {
                        "type": "arrival",
                        "task": {
                            "id": "task1",  # Duplicate ID - now allowed
                            "arrival_time": 0,
                            "priority": "routine",
                            "deadline": 15,
                        },
                    },
                ]
            },
        }

        seed_file = Path(tmpdir) / "seed_dup.json"
        with open(seed_file, "w") as f:
            json.dump(seed_data, f)

        loader = ScenarioLoader(tmpdir)
        # Should load successfully - duplicates are handled internally with UUIDs
        config = loader.load(seed_file)
        assert config.horizon == 20
        assert len(config.events["0"]) == 2


def test_list_scenarios():
    """Test listing scenario files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some seed files
        scenario_dir = Path(tmpdir) / "test_scenario"
        scenario_dir.mkdir()

        for i in range(3):
            seed_file = scenario_dir / f"seed_{i + 1}.json"
            with open(seed_file, "w") as f:
                json.dump({"horizon": 20, "capacity_per_step": 3, "events": {}}, f)

        loader = ScenarioLoader(tmpdir)
        seeds = loader.list_scenarios()

        assert len(seeds) == 3
        assert all(s.suffix == ".json" for s in seeds)
