"""Comprehensive validation of all 105 seed files from QBench-suite.

This test suite validates every seed file to ensure:
- Correct JSON structure
- Valid configuration (horizon, capacity, events)
- Proper task definitions
- QueueEnv can initialize
- No duplicate task IDs
- Deadlines within horizon

Result: 105 tests (35 scenario types × 3 seeds each)
"""

from pathlib import Path

import pytest

from qbench import QueueEnv, ScenarioLoader
from qbench.loader import SeedConfig


def validate_seed_structure(config: SeedConfig, seed_path: str) -> tuple[bool, str]:
    """
    Validate a loaded seed configuration structure.

    Args:
        config: The loaded seed configuration
        seed_path: Path to seed file (for error messages)

    Returns:
        Tuple of (is_valid, error_message)
        - If valid: (True, "")
        - If invalid: (False, "description of error")
    """
    # Scenarios that intentionally have duplicate IDs (testing edge cases)
    ALLOW_DUPLICATE_IDS = [
        "conflicting_duplicate_id_robustness",
        "duplicate_arrival_idempotency",
    ]

    # Check if this scenario allows duplicate IDs
    allow_duplicates = any(scenario in seed_path for scenario in ALLOW_DUPLICATE_IDS)
    # Check horizon is positive
    if config.horizon <= 0:
        return False, f"Invalid horizon: {config.horizon}"

    # Check capacity is positive
    if config.capacity_per_step <= 0:
        return False, f"Invalid capacity: {config.capacity_per_step}"

    # Validate all events
    task_ids = set()
    for step_str, events_list in config.events.items():
        try:
            step = int(step_str)
        except ValueError:
            return False, f"Invalid step key: {step_str}"

        # Check step is within horizon
        if step < 0:
            return False, f"Negative step: {step}"

        if step >= config.horizon:
            return False, f"Step {step} >= horizon {config.horizon}"

        # Validate each event
        for event in events_list:
            if event.type == "arrival" and event.task:
                task = event.task

                # Check task has required fields
                if "id" not in task:
                    return False, f"Task missing 'id' at step {step}"

                task_id = task["id"]

                # Check for duplicate IDs (unless scenario allows them)
                if not allow_duplicates:
                    if task_id in task_ids:
                        return False, f"Duplicate task ID: {task_id}"
                task_ids.add(task_id)

                # Check deadline
                if "deadline" in task:
                    deadline = task["deadline"]
                    if deadline < 0:
                        return False, f"Task {task_id} has negative deadline: {deadline}"
                    if deadline >= config.horizon:
                        return (
                            False,
                            f"Task {task_id} deadline {deadline} >= horizon {config.horizon}",
                        )

                # Check priority
                if "priority" in task:
                    priority = task["priority"]
                    if priority not in ["urgent", "routine"]:
                        return False, f"Task {task_id} has invalid priority: {priority}"

    return True, ""


@pytest.fixture
def scenarios_path():
    """Get path to scenarios directory."""
    test_dir = Path(__file__).parent
    scenarios_dir = test_dir.parent / "scenarios"

    if not scenarios_dir.exists():
        pytest.skip("Scenarios directory not found")

    return scenarios_dir


@pytest.fixture
def all_scenario_seeds(scenarios_path):
    """Generate list of all scenario seeds to test."""
    loader = ScenarioLoader(scenarios_path)
    scenario_types = loader.list_scenario_types()

    # Collect all (scenario_type, seed_number) pairs
    test_cases = []
    for scenario_type in scenario_types:
        seeds = loader.list_scenarios(scenario_type)
        for seed_path in seeds:
            # Extract seed number from filename (e.g., "seed_1.json" -> 1)
            seed_name = seed_path.stem  # "seed_1"
            seed_num = seed_name.split("_")[-1]  # "1"
            test_cases.append((scenario_type, seed_num))

    return test_cases


def test_count_all_seeds(scenarios_path):
    """Verify we have 105 seeds total (35 scenarios × 3 seeds)."""
    loader = ScenarioLoader(scenarios_path)
    scenario_types = loader.list_scenario_types()

    total_seeds = 0
    for scenario_type in scenario_types:
        seeds = loader.list_scenarios(scenario_type)
        total_seeds += len(seeds)

    print(f"\n✓ Found {len(scenario_types)} scenario types")
    print(f"✓ Found {total_seeds} total seed files")

    assert len(scenario_types) >= 35, f"Expected at least 35 scenario types, got {len(scenario_types)}"
    assert total_seeds >= 105, f"Expected at least 105 seeds, got {total_seeds}"


def test_validate_individual_seed(scenarios_path, scenario_type, seed_num):
    """
    Validate individual seed file.

    This test runs once for each seed file (105 times total).
    Each test validates:
    - Seed loads correctly
    - Structure is valid
    - QueueEnv can initialize
    - Environment can reset
    """
    seed_path = f"{scenario_type}/seed_{seed_num}.json"

    # 1. Load seed
    loader = ScenarioLoader(scenarios_path)
    try:
        config = loader.load(seed_path)
    except Exception as e:
        pytest.fail(f"Failed to load {seed_path}: {e}")

    # 2. Validate structure
    is_valid, error_msg = validate_seed_structure(config, seed_path)
    assert is_valid, f"Invalid seed structure in {seed_path}: {error_msg}"

    # 3. Initialize environment
    try:
        env = QueueEnv(config)
    except Exception as e:
        pytest.fail(f"Failed to initialize QueueEnv for {seed_path}: {e}")

    # 4. Reset environment
    try:
        obs = env.reset()
    except Exception as e:
        pytest.fail(f"Failed to reset environment for {seed_path}: {e}")

    # 5. Basic sanity checks on observation
    assert obs.time == 0, f"Initial time should be 0, got {obs.time}"
    assert obs.horizon == config.horizon, "Horizon mismatch"
    assert obs.capacity_per_step == config.capacity_per_step, "Capacity mismatch"


def pytest_generate_tests(metafunc):
    """
    Dynamically generate test parameters for all seed files.

    This pytest hook generates 105 parameterized tests, one for each seed file.
    """
    if "scenario_type" in metafunc.fixturenames and "seed_num" in metafunc.fixturenames:
        # Get scenarios path from fixture
        test_dir = Path(__file__).parent
        scenarios_dir = test_dir.parent / "scenarios"

        if not scenarios_dir.exists():
            pytest.skip("Scenarios directory not found")
            return

        # Collect all (scenario_type, seed_num) pairs
        loader = ScenarioLoader(scenarios_dir)
        scenario_types = loader.list_scenario_types()

        # Edge-case scenarios that intentionally fail strict validation
        edge_case_scenarios = {
            "conflicting_duplicate_id_robustness",
            "duplicate_arrival_idempotency",
        }

        test_cases = []
        marks_list = []

        for scenario_type in scenario_types:
            seeds = loader.list_scenarios(scenario_type)
            for seed_path in seeds:
                # Extract seed number from filename
                seed_name = seed_path.stem
                if "_" in seed_name:
                    seed_num = seed_name.split("_")[-1]
                    test_cases.append((scenario_type, seed_num))

                    # Mark edge cases as expected failures
                    if scenario_type in edge_case_scenarios:
                        marks_list.append(
                            pytest.param(
                                scenario_type,
                                seed_num,
                                marks=pytest.mark.xfail(
                                    reason="Edge-case scenario with intentional duplicate IDs",
                                    strict=True,
                                ),
                            )
                        )
                    else:
                        marks_list.append((scenario_type, seed_num))

        # Parameterize the test with marks
        metafunc.parametrize("scenario_type,seed_num", marks_list)


def test_validate_all_seeds_summary(scenarios_path):
    """
    Summary test: validate all seeds and report results.

    This provides a nice summary of all validation results.
    """
    loader = ScenarioLoader(scenarios_path)
    scenario_types = loader.list_scenario_types()

    print("\n" + "=" * 70)
    print("SEED VALIDATION SUMMARY")
    print("=" * 70)

    total_seeds = 0
    valid_seeds = 0
    invalid_seeds = []

    for scenario_type in sorted(scenario_types):
        seeds = loader.list_scenarios(scenario_type)

        for seed_path in seeds:
            total_seeds += 1

            try:
                # Load seed
                config = loader.load(seed_path)

                # Validate structure
                is_valid, error_msg = validate_seed_structure(config, str(seed_path))

                if is_valid:
                    # Try to initialize environment
                    env = QueueEnv(config)
                    env.reset()
                    valid_seeds += 1
                else:
                    invalid_seeds.append((seed_path, error_msg))

            except Exception as e:
                invalid_seeds.append((seed_path, str(e)))

    print(f"\nTotal seeds tested: {total_seeds}")
    print(f"Valid seeds: {valid_seeds}")
    print(f"Invalid seeds: {len(invalid_seeds)}")

    if invalid_seeds:
        print("\n❌ Invalid seeds:")
        for seed_path, error in invalid_seeds:
            print(f"  - {seed_path}: {error}")
    else:
        print("\n✅ All seeds are valid!")

    print("=" * 70 + "\n")

    # Special edge-case scenarios that intentionally have duplicate IDs
    # These test robustness but fail strict validation
    expected_edge_cases = {
        "conflicting_duplicate_id_robustness",
        "duplicate_arrival_idempotency",
    }

    # Separate edge cases from actual errors
    edge_case_failures = [
        (path, error)
        for path, error in invalid_seeds
        if any(edge_case in str(path) for edge_case in expected_edge_cases)
    ]
    actual_failures = [
        (path, error)
        for path, error in invalid_seeds
        if not any(edge_case in str(path) for edge_case in expected_edge_cases)
    ]

    if edge_case_failures:
        print(f"\n⚠️  Edge-case scenarios (intentionally malformed): {len(edge_case_failures)}")
        for path, error in edge_case_failures:
            print(f"  - {path.name}: {error}")

    # Assert no actual failures (edge cases are expected)
    assert len(actual_failures) == 0, f"Found {len(actual_failures)} unexpected failures"
    assert valid_seeds == (total_seeds - len(edge_case_failures)), (
        f"Expected {total_seeds - len(edge_case_failures)} valid seeds, got {valid_seeds}"
    )
