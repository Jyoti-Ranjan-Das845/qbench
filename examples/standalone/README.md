# Standalone Mode Example

This directory contains a minimal GPT-5.2 agent that runs QBench evaluations in **standalone mode** (in-process, no server required).

## What's Here

- `agent.py` - GPT-5.2 agent implementation extending `Agent` base class
- `prompt.py` - System prompt for the agent
- `__init__.py` - Module exports

## Quick Start

### 1. Install & Configure

```bash
# Install QBench and dependencies
uv sync

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

### 2. Run Single Test

```bash
# Test with 1 scenario, 1 seed
qbench eval --agent examples.standalone.agent.GPT52Agent \
  --scenarios backlog_cap_stability_guard \
  --seeds 1 \
  --verbose
```

### 3. Run Full Benchmark

```bash
# All scenarios, all seeds (105 episodes)
qbench eval --agent examples.standalone.agent.GPT52Agent \
  --parallel 10 \
  --verbose
```

## Usage

### Command Structure

```bash
qbench eval --agent <import.path.to.AgentClass> [options]
```

**Options:**
- `--scenarios` - Comma-separated scenario names (default: all 35)
- `--seeds` - Comma-separated seed numbers (1,2,3) (default: all)
- `--parallel` - Number of concurrent episodes (default: 1)
- `--verbose` - Show detailed logs
- `--output` - Custom output directory

### Examples

```bash
# Specific scenarios and seeds
qbench eval --agent examples.standalone.agent.GPT52Agent \
  --scenarios backlog_cap_stability_guard,cold_start_to_surge \
  --seeds 1,2 \
  --parallel 5

# Using Python API instead
python -c "
from qbench import run_qbench
from examples.standalone.agent import GPT52Agent

results = run_qbench(
    agent=GPT52Agent(),
    scenarios=['backlog_cap_stability_guard'],
    seeds=[1]
)
print(f'Pass rate: {results[\"pass_rate\"]:.1%}')
"
```

## Results Output

```
results/run_{timestamp}/
├── {scenario_name}/
│   └── seed_{N}/
│       ├── steps.json      # Step-by-step execution
│       └── summary.json    # Metrics and violations
└── results.json            # Benchmark summary
```

## Troubleshooting

**API Key Error**
```
ValueError: OPENAI_API_KEY environment variable not set
```
→ Run: `export OPENAI_API_KEY="your-key"`

**Import Error**
```
Could not import module 'examples.standalone.agent'
```
→ Run: `uv sync` to install the examples package

**Module Not Found**
```
ModuleNotFoundError: No module named 'litellm'
```
→ Run: `uv sync` to install all dependencies

## Customization

**Change model or temperature:**
Edit `agent.py` and modify the `__init__` parameters:
```python
def __init__(self, model: str = "gpt-4", temperature: float = 0.5):
```

**Modify system prompt:**
Edit `prompt.py` to change agent instructions.

**Note:** QBench automatically includes full task specifications with each observation, so the system prompt can remain minimal.
