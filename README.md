<div align="center">

  <!-- Hero Banner -->
  <img src="assets/logo.png?v=2" alt="QBench" width="100%"/>

  <h2>🎯 Queue Management Benchmark for AI Agents</h2>

  <p><i>Evaluate AI agents on real-time queue management with dynamic load, capacity constraints, and strict deadlines</i></p>

  <p>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"/></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"/></a>
    <img src="https://img.shields.io/badge/tests-passing-brightgreen.svg" alt="Tests"/>
    <a href="https://agentbeats.ai"><img src="https://img.shields.io/badge/AgentBeats-Phase%201-purple.svg" alt="AgentBeats"/></a>
  </p>

  <h3>
    <a href="#-quick-start">Quick Start</a> •
    <a href="docs/">Documentation</a> •
    <a href="#-examples">Examples</a> •
    <a href="https://agentbeats.ai">Competition</a>
  </h3>

</div>

## 📑 Table of Contents

- [🎯 What is QBench?](#-what-is-qbench)
- [⚡ Quick Start](#-quick-start)
- [🚀 Deployment Modes](#-deployment-modes)
- [📊 Scenarios](#-scenarios)
- [💻 CLI Reference](#-cli-reference)
- [📖 Examples](#-examples)
- [📈 How Evaluation Works](#-how-evaluation-works)
- [📂 Project Structure](#-project-structure)
- [🧪 Development](#-development)
- [📚 Documentation](#-documentation)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## 🎯 What is QBench?

QBench evaluates how well AI agents can manage an online queueing system under realistic operational constraints:

- ⏱️ **Dynamic task arrivals** with varying priorities (urgent/routine)
- 🎚️ **Limited capacity** (fixed slots per time step)
- ⚠️ **Hard deadlines** (urgent tasks must complete on time or fail)
- 📊 **Soft optimization** (minimize wait time, maximize utilization, meet routine SLA)

### Why QBench?

| Feature | Description |
|---------|-------------|
| 🔬 **Research-Grade** | Rigorous benchmark with reproducible scenarios |
| 🏆 **Competition-Ready** | Official benchmark for AgentBeats Competition Phase 1 |
| 📊 **Comprehensive** | 35 scenario types × 3 seeds = 105 episodes |
| 🎓 **Educational** | Learn queue theory and scheduling algorithms |
| 🔌 **Flexible APIs** | Simple to advanced - choose your complexity level |

---

## ⚡ Quick Start

### Installation

```bash
# Prerequisites: Python 3.10+ and uv package manager
# Install uv: https://github.com/astral-sh/uv

# Clone repository
git clone https://github.com/your-org/qbench.git
cd qbench

# Install dependencies
make dev

# Or using uv directly
uv sync --extra dev
```

**Note**: After installation, the `qbench` package and `examples` module are automatically importable!

### Run Your First Evaluation

<table>
<tr>
<td width="33%">

**🐍 Python API**
```python
from qbench import Agent, run_qbench

class MyAgent(Agent):
    def act(self, obs: str) -> str:
        # Your logic here
        return '{"assign": [], "reject": [], "cancel": []}'

# Run evaluation
results = run_qbench(MyAgent())
print(f"Pass Rate: {results['pass_rate']:.1%}")
```

</td>
<td width="33%">

**💻 CLI**
```bash
# Standalone mode
qbench eval \
  --agent examples.standalone.agent.GPT52Agent \
  --scenarios 5 \
  --seeds 1 \
  --verbose

# Remote mode
qbench eval \
  --agent-url http://localhost:9019 \
  --parallel 10
```

</td>
<td width="33%">

**📜 Scripts**
```bash
# Quick test (2 episodes)
./scripts/run_quick_test.sh

# Full benchmark (105 episodes)
./scripts/run_full_benchmark.sh --balanced

# Interactive prompts guide you
```

</td>
</tr>
</table>

---

## 🚀 Deployment Modes

QBench supports **two deployment patterns** depending on your setup:

### 🖥️ Standalone Mode (Recommended for Development)

Your agent runs in the **same Python process** as QBench. Perfect for research, development, and local testing.

**Choose your API level:**

<details>
<summary><b>Level 1: Simple API</b> - Quickest start</summary>

```python
from qbench import Agent, run_qbench

class MyAgent(Agent):
    def act(self, observation: str) -> str:
        # Your scheduling logic
        return '{"assign": [], "reject": [], "cancel": []}'

# One-line evaluation
results = run_qbench(MyAgent(), parallel=10, max_episodes=20)
print(f"Pass Rate: {results['pass_rate']:.1%}")
```

✅ **Best for**: Quick experiments, getting started, simple testing

</details>

<details>
<summary><b>Level 2: Runner API</b> - More control</summary>

```python
from qbench import BenchmarkRunner, Agent

class MyAgent(Agent):
    def act(self, observation: str) -> str:
        return actions

# More control over evaluation
runner = BenchmarkRunner("scenarios", MyAgent())
result = runner.run_all(
    max_episodes=10,
    scenario_types=["late_burst_slack_trap"],
    verbose=True
)

print(f"Pass rate: {result.pass_rate:.1%}")
print(f"Routine SLA: {result.aggregate_metrics.routine_sla:.3f}")
```

✅ **Best for**: Custom scenario selection, detailed metrics analysis

</details>

<details>
<summary><b>Level 3: Environment API</b> - Full control</summary>

```python
from qbench import QueueEnv, ScenarioLoader

# Load specific scenario
loader = ScenarioLoader("scenarios")
config = loader.load("late_burst_slack_trap/seed_1.json")

# Create environment
env = QueueEnv(config)
obs = env.reset()

# Step-by-step control
done = False
while not done:
    actions = my_custom_algorithm(obs)
    obs, done = env.step(actions)

# Access detailed state
metrics = env.get_metrics()
```

✅ **Best for**: Research, custom metrics, algorithm analysis, step-by-step debugging

</details>

---

### 🌐 A2A Remote Mode (Competition & Production)

Your agent runs as a **separate HTTP service**, QBench connects via **A2A protocol**. For competition and testing deployed agents.

```bash
# Terminal 1: Start your A2A-compatible agent
python my_purple_agent.py --port 9019

# Terminal 2: Run evaluation against your agent
qbench eval --agent-url http://localhost:9019 \
           --scenarios 5 \
           --seeds 1,2 \
           --parallel 10
```

✅ **Best for**: AgentBeats competition, testing production agents, distributed systems

📖 **See**: [examples/agentbeats/README.md](examples/agentbeats/README.md) for full A2A setup guide

---

## 📊 Scenarios

QBench includes **35 scenario types** across 10 categories:

<div align="center">

| Category | Count | Focus Area |
|----------|-------|------------|
| **🏥 Baseline** | 2 | Health checks, low load |
| **📈 Load Patterns** | 10 | Steady, bursts, spikes, waves |
| **🔄 Regime Shifts** | 2 | Non-stationary workload changes |
| **⭐ Priority Handling** | 3 | Priority-based scheduling |
| **⏰ Deadline Handling** | 4 | Deadline-aware scheduling |
| **🔥 Capacity Stress** | 3 | Overload, fairness |
| **⚡ Capacity Dynamics** | 4 | Capacity changes over time |
| **❌ Cancellations** | 4 | Cancellation handling |
| **🛡️ Env Robustness** | 2 | Input validation, idempotency |
| **👾 Adversarial** | 1 | Adversarial patterns |

</div>

**Each scenario has 3 seed files = 105 total episodes**

📄 **Full descriptions**: [docs/SCENARIOS.md](docs/SCENARIOS.md)

---

## 💻 CLI Reference

### `qbench eval` - Unified Evaluation Command

The `qbench eval` command supports all evaluation modes with a clean, intuitive interface.

#### Mode 1: Standalone (Python Agent)

```bash
qbench eval --agent examples.standalone.my_agent.MyAgent \
           --scenarios 10 \
           --seeds 1,2 \
           --parallel 5 \
           --verbose
```

#### Mode 2: A2A Remote (HTTP Agent)

```bash
# First, start your agent:
python my_purple_agent.py --port 9019

# Then run evaluation:
qbench eval --agent-url http://localhost:9019 \
           --scenarios "backlog_cap,cold_start,urgent_flood" \
           --seeds 1,2,3 \
           --parallel 10 \
           --output results.json
```

#### Mode 3: Config File (Full Orchestration)

```bash
qbench eval --config examples/configs/parallel_eval.toml
```

### Common Options

**Evaluation Scope:**
- `--scenarios N|IDS|RANGE`: Select scenarios
  - `--scenarios 10` → First 10 scenarios
  - `--scenarios 1,5,10` → Specific scenarios by index
  - `--scenarios 1-10` → Range of scenarios
  - `--scenarios "backlog_cap,cold_start"` → By name (partial match OK)
- `--seeds SEEDS`: Select seed files (default: `1,2,3`)
  - `--seeds 1` → Only seed 1
  - `--seeds 1,2` → Seeds 1 and 2
  - `--seeds 1-3` → All three seeds

**Execution:**
- `--parallel N`: Number of concurrent episodes (default: 1)
- `--timeout SEC`: Timeout per episode in seconds (default: 300)

**Output:**
- `--output FILE`: Save results to JSON file
- `--verbose`: Show detailed logs
- `--quiet`: Minimal output (only final results)

### Quick Examples

```bash
# Quick test: First 5 scenarios, seed 1 only = 5 episodes
qbench eval --agent my_agent.MyAgent --scenarios 5 --seeds 1

# Full benchmark: All scenarios, all seeds = 105 episodes
qbench eval --agent my_agent.MyAgent

# Specific scenarios with all seeds
qbench eval --agent-url http://localhost:9019 \
           --scenarios "backlog_cap_stability_guard,urgent_flood" \
           --seeds 1,2,3

# Fast parallel execution
qbench eval --agent my_agent.MyAgent --parallel 50 --quiet
```

<details>
<summary><b>Other Commands</b></summary>

#### `qbench list-scenarios`

Lists all 35 available scenario types with descriptions.

```bash
qbench list-scenarios
```

#### Legacy Commands (Deprecated)

The old `qbench run` and `qbench agentbeats` commands still work but are deprecated:

```bash
# Old (still works):
qbench run --agent my_agent.MyAgent --max-episodes 20

# New (recommended):
qbench eval --agent my_agent.MyAgent --scenarios 6 --seeds 1,2,3
```

</details>

---

## 📖 Examples

### Example 1: Simple Greedy Agent

```python
from qbench import Agent, run_qbench
import json

class GreedyAgent(Agent):
    """Assign tasks to earliest available slot."""

    def act(self, observation: str) -> str:
        obs = json.loads(observation)
        actions = {"assign": [], "reject": [], "cancel": []}

        # Sort pending by priority (urgent first) then deadline
        pending = sorted(
            obs["pending"],
            key=lambda t: (0 if t["priority"] == "urgent" else 1, t["deadline"])
        )

        for task in pending:
            # Try to schedule at earliest time
            actions["assign"].append({
                "task_id": task["id"],
                "step": obs["time"]
            })

        return json.dumps(actions)

# Evaluate
results = run_qbench(GreedyAgent(), max_episodes=10)
print(f"Pass Rate: {results['pass_rate']:.1%}")
```

### Example 2: Using BenchmarkRunner

```python
from qbench import BenchmarkRunner, Agent

class MyAgent(Agent):
    def act(self, observation: str) -> str:
        # Your logic
        return actions

# Run specific scenarios
runner = BenchmarkRunner("scenarios", MyAgent())
result = runner.run_all(
    scenario_types=["late_burst_slack_trap", "capacity_cliff"],
    max_episodes=20,
    verbose=True
)

print(f"Pass rate: {result.pass_rate:.1%}")
```

### Example 3: Step-by-Step with QueueEnv

```python
from qbench import QueueEnv, ScenarioLoader, Action

loader = ScenarioLoader("scenarios")
config = loader.load("no_traffic_health_check/seed_1.json")

env = QueueEnv(config)
obs = env.reset()

done = False
while not done:
    # Your algorithm decides actions
    actions = []
    for task in obs.pending:
        action = Action(
            type="schedule",
            task_id=task.id,
            step=obs.time + 1
        )
        actions.append(action)

    obs, done = env.step(actions)
    print(f"Step {obs.time}: {len(obs.pending)} pending")

print(f"Episode complete: {env.get_state_summary()}")
```

### Example 4: Accessing Detailed Metrics

```python
results = run_qbench(MyAgent())

if results['passed_episodes'] > 0:
    print(f"Routine SLA: {results['metrics']['routine_sla']:.1%}")
    print(f"Avg Wait: {results['metrics']['avg_wait_time']:.2f} steps")
    print(f"Max Backlog: {results['metrics']['max_backlog']} tasks")
    print(f"Utilization: {results['metrics']['avg_utilization']:.1%}")
```

---

## 📈 How Evaluation Works

### Pass/Fail Criteria (Hard Constraints)

An episode **PASSES** if:
- ✅ All urgent tasks complete before their deadlines
- ✅ No capacity violations (scheduled tasks ≤ capacity at each step)
- ✅ No invalid actions (e.g., scheduling to past, double-scheduling)

An episode **FAILS** if any urgent task misses its deadline.

### Soft Metrics (Performance)

For passing episodes only:
- **Routine SLA**: % of routine tasks completed before deadline
- **Average Wait Time**: Mean time from arrival to completion
- **Average Backlog**: Mean number of pending tasks
- **Average Utilization**: Mean capacity usage

---

## 📂 Project Structure

```
qbench/
├── src/
│   ├── qbench/              # Core library
│   │   ├── agent/           # Agent base classes
│   │   ├── data_models/     # Task, Action, Observation
│   │   ├── environment/     # QueueEnv and scenario loader
│   │   ├── validation/      # Constraint checking
│   │   ├── metrics/         # Metrics accumulation
│   │   ├── runner/          # BenchmarkRunner
│   │   ├── api.py           # Simple API (run_qbench)
│   │   ├── cli.py           # Command-line interface
│   │   ├── config.py        # Configuration constants
│   │   └── scenarios.py     # Scenario catalog
│   └── agentbeats/          # AgentBeats integration
│       └── evaluator/       # A2A protocol implementation
├── scenarios/               # 35 scenario types × 3 seeds = 105 episodes
├── examples/
│   ├── standalone/          # Local deployment examples
│   ├── agentbeats/          # Remote deployment examples
│   └── configs/             # Configuration file examples
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md      # System architecture
│   ├── EVALUATION_SPEC.md   # Evaluation specifications
│   ├── SCENARIOS.md         # Scenario descriptions
│   └── TESTING.md           # Testing guide
├── scripts/                 # Utility scripts
│   ├── run_quick_test.sh
│   ├── run_full_benchmark.sh
│   └── README.md
├── tests/                   # Test suite
└── pyproject.toml           # Package configuration
```

---

## 🧪 Development

### Run Tests

```bash
# Run all tests
make test

# Run with coverage
uv run pytest --cov=qbench --cov-report=html

# Run specific test
uv run pytest tests/test_env.py -v
```

### Code Quality

```bash
# Lint
make lint

# Format
make format

# Type check
make typecheck

# Run all checks
make all
```

### Integration Tests

```bash
./scripts/test_integration.sh
```

---

## 📚 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and architecture
- **[EVALUATION_SPEC.md](docs/EVALUATION_SPEC.md)** - Evaluation specifications
- **[SCENARIOS.md](docs/SCENARIOS.md)** - All 35 scenario descriptions
- **[TESTING.md](docs/TESTING.md)** - Testing and validation guide
- **[scripts/README.md](scripts/README.md)** - Utility scripts documentation
- **[examples/standalone/README.md](examples/standalone/README.md)** - Standalone mode guide
- **[examples/agentbeats/README.md](examples/agentbeats/README.md)** - A2A mode guide
- **[examples/configs/README.md](examples/configs/README.md)** - Configuration guide

---

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run `make all` to check code quality
5. Submit a pull request

---

## 📄 License

[Add your license here - MIT recommended]

---

## 🏆 Citation

If you use QBench in your research, please cite:

```bibtex
@software{qbench2025,
  title={QBench: Queue Management Benchmark for AI Agents},
  author={[Your Name]},
  year={2025},
  url={https://github.com/your-org/qbench}
}
```

---

## 🙏 Acknowledgments

- **Scenarios**: Derived from [QBench-suite](https://github.com/Jyoti-Ranjan-Das845/QBench-suite.git)
- **Architecture**: Inspired by tau2-bench
- **Competition**: Part of AgentBeats Competition 2025

---

<div align="center">

  ### 💬 Support & Community

  📖 [Documentation](docs/) • 💬 [Discussions](https://github.com/your-org/qbench/discussions) • 🐛 [Issues](https://github.com/your-org/qbench/issues) • 🏆 [AgentBeats](https://agentbeats.ai)

  ---

  **Built with ❤️ for the AI agent research community**

  <sub>Part of AgentBeats Competition 2025</sub>
</div>
