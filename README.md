# QBench - Queue Management Benchmark for AI Agents

QBench is a benchmark for evaluating AI agents on **online queue management** — the ability to make scheduling decisions under dynamic load, limited capacity, and strict deadlines.

Part of the **AgentBeats Competition** (Phase 1 - Green Agent).

## Overview

QBench evaluates **Purple agents** (being tested) on their ability to manage a real-time queueing system with:
- **Dynamic task arrivals** with varying priorities (urgent/routine)
- **Strict capacity limits** (slots per time step)
- **Hard deadlines** (urgent tasks must complete on time)
- **Soft metrics** (routine SLA, wait time, utilization)

## Installation

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager

### Install

```bash
# Install dependencies
make dev

# Or using uv directly
uv sync --extra dev
```

## Project Structure

```
qbench/
├── src/qbench/          # Core implementation
│   ├── task.py          # Task data model
│   ├── action.py        # Action data model
│   ├── observation.py   # Observation data model
│   ├── env.py           # QueueEnv - core environment
│   └── loader.py        # ScenarioLoader - load seed files
├── scenarios/           # Test scenarios (from QBench-suite)
│   ├── no_traffic_health_check/
│   ├── late_burst_slack_trap/
│   ├── ...
│   └── (36 scenario types × 3 seeds each)
└── tests/              # Test suite
```

## Quick Start

### Loading a Scenario

```python
from qbench import ScenarioLoader, QueueEnv

# Load a seed file
loader = ScenarioLoader("scenarios")
config = loader.load("no_traffic_health_check/seed_1.json")

# Create environment
env = QueueEnv(config)

# Reset to initial state
obs = env.reset()
print(f"Time: {obs.time}/{obs.horizon}")
print(f"Capacity: {obs.capacity_per_step} slots/step")
print(f"Arrivals: {len(obs.arrivals)}")
print(f"Pending: {len(obs.pending)}")
```

### Running an Episode

```python
from qbench import Action

# Simple agent: schedule all pending tasks ASAP
done = False
while not done:
    # Agent decides what actions to take
    actions = []
    for task in obs.pending:
        # Schedule task to next available step
        action = Action(
            type="schedule",
            task_id=task.id,
            step=obs.time + 1
        )
        actions.append(action)

    # Apply actions and advance time
    obs, done = env.step(actions)

    print(f"Step {obs.time}: {len(obs.pending)} pending, {len(obs.scheduled)} scheduled")

# Episode complete
print(f"Final state: {env.get_state_summary()}")
```

### Listing Available Scenarios

```python
loader = ScenarioLoader("scenarios")

# List all scenario types
scenario_types = loader.list_scenario_types()
print(f"Found {len(scenario_types)} scenario types")

# List all seeds for a specific scenario
seeds = loader.list_scenarios("late_burst_slack_trap")
print(f"Seeds: {seeds}")
```

## Data Models

### Task
Represents a single task in the queue:
- `id`: unique identifier
- `arrival_time`: when task arrives
- `priority`: "urgent" or "routine"
- `deadline`: latest step for completion
- `status`: pending | scheduled | completed | rejected | cancelled | missed

### Action
Agent actions to control the queue:
- `schedule`: assign pending task to a future slot
- `reschedule`: move scheduled task to different slot
- `reject`: refuse a routine task (urgent cannot be rejected)
- `cancel`: agent-initiated cancellation
- `noop`: do nothing

### Observation
What the agent sees each step:
- `time`: current time step
- `horizon`: total episode length
- `capacity_per_step`: available slots per step
- `arrivals`: new tasks this step
- `cancellations`: cancelled task IDs this step
- `pending`: all pending tasks
- `scheduled`: all scheduled tasks

## Development

### Run Tests

```bash
make test

# Or with coverage
uv run pytest --cov=qbench --cov-report=html
```

### Linting & Formatting

```bash
# Check code style
make lint

# Auto-format code
make format

# Type checking
make typecheck
```

### Run All Checks

```bash
make all
```

## Scenario Structure

Each seed file defines one test episode:

```json
{
  "horizon": 20,
  "capacity_per_step": 3,
  "events": {
    "0": [
      {
        "type": "arrival",
        "task": {
          "id": "u1",
          "arrival_time": 0,
          "priority": "urgent",
          "deadline": 12
        }
      }
    ],
    "5": [
      {
        "type": "cancel",
        "task_id": "r1"
      }
    ]
  }
}
```

**Event types:**
- `arrival`: new task enters system
- `cancel`: external cancellation
- `capacity_change`: capacity increases/decreases (Tier-2)

## Architecture

### QueueEnv Responsibilities

The `QueueEnv` class handles:
- ✅ State management (tasks, schedule, capacity)
- ✅ Event injection (arrivals, cancellations)
- ✅ Action application (schedule, reschedule, reject, cancel)
- ✅ Task completion processing
- ✅ Deadline miss detection
- ✅ Observation generation

### NOT in QueueEnv (Separate Components)

The following are handled by separate evaluation components:
- ❌ Action validation (ActionValidator)
- ❌ Constraint checking (ConstraintChecker)
- ❌ Metrics accumulation (MetricsAccumulator)
- ❌ PASS/FAIL determination (EpisodeResult)

## Contributing

This is part of the AgentBeats Competition submission. For issues or questions:
- Open an issue on GitHub
- Check the [AgentBeats Competition docs](https://agentbeats.ai)

## License

[Add your license here]

## Acknowledgments

- Scenarios from [QBench-suite](https://github.com/Jyoti-Ranjan-Das845/QBench-suite.git)
- Inspired by tau2-bench architecture
- Part of AgentBeats Competition 2025
