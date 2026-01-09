"""Integration tests using actual scenarios from QBench-suite."""

from pathlib import Path

import pytest

from qbench.data_models.action import Action
from qbench.environment.env import QueueEnv
from qbench.environment.loader import ScenarioLoader


@pytest.fixture
def scenarios_path():
    """Get path to scenarios directory."""
    # Assuming tests are in qbench/tests/ and scenarios in qbench/scenarios/
    test_dir = Path(__file__).parent
    scenarios_dir = test_dir.parent / "scenarios"

    if not scenarios_dir.exists():
        pytest.skip("Scenarios directory not found")

    return scenarios_dir


def test_load_actual_scenario(scenarios_path):
    """Test loading an actual scenario from QBench-suite."""
    loader = ScenarioLoader(scenarios_path)

    # Load no_traffic_health_check seed
    config = loader.load("no_traffic_health_check/seed_1.json")

    assert config.horizon == 20
    assert config.capacity_per_step == 3
    # This scenario has no events
    assert len(config.events) == 0


def test_run_no_traffic_scenario(scenarios_path):
    """Test running the no_traffic health check scenario."""
    loader = ScenarioLoader(scenarios_path)
    config = loader.load("no_traffic_health_check/seed_1.json")

    env = QueueEnv(config)
    obs = env.reset()

    # Run through entire episode with noop
    done = False
    steps = 0
    while not done:
        obs, done = env.act([Action(type="noop")])
        steps += 1

        # Safety check
        if steps > 25:
            break

    assert done
    assert env.time == env.horizon
    assert steps == 20  # Should take exactly horizon steps


def test_run_late_burst_scenario(scenarios_path):
    """Test running late_burst_slack_trap scenario."""
    loader = ScenarioLoader(scenarios_path)
    config = loader.load("late_burst_slack_trap/seed_1.json")

    env = QueueEnv(config)
    obs = env.reset()

    assert obs.horizon == 20
    assert obs.capacity_per_step == 3

    # Step through and collect task arrivals
    all_arrivals = []
    done = False
    step = 0

    while not done:
        if len(obs.arrivals) > 0:
            all_arrivals.extend(obs.arrivals)
            print(f"Step {obs.time}: {len(obs.arrivals)} arrivals")

        # Simple greedy scheduling: schedule all pending tasks ASAP
        actions = []
        for task in obs.pending[:obs.capacity_per_step]:
            # Schedule to next available slot
            action = Action(type="schedule", task_id=task.id, step=obs.time + 1)
            actions.append(action)

        obs, done = env.act(actions)
        step += 1

        if step > 25:
            break

    # Verify we saw the late burst
    assert len(all_arrivals) > 0
    # Check that we have both routine and urgent tasks
    priorities = {task.priority for task in all_arrivals}
    assert "urgent" in priorities
    assert "routine" in priorities


def test_list_all_scenarios(scenarios_path):
    """Test that we can list all scenario types."""
    loader = ScenarioLoader(scenarios_path)

    scenario_types = loader.list_scenario_types()

    # Should have many scenario types
    assert len(scenario_types) > 30
    assert "no_traffic_health_check" in scenario_types
    assert "late_burst_slack_trap" in scenario_types


def test_load_all_seeds_for_scenario(scenarios_path):
    """Test loading all 3 seeds for a scenario type."""
    loader = ScenarioLoader(scenarios_path)

    seeds = loader.list_scenarios("no_traffic_health_check")

    # Each scenario should have 3 seeds
    assert len(seeds) >= 3

    # All should be loadable
    for seed in seeds[:3]:
        config = loader.load(seed)
        assert config.horizon > 0
        assert config.capacity_per_step > 0
