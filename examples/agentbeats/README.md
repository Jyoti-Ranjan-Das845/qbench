# AgentBeats Mode Example

This directory contains a GPT-5.2 agent that runs QBench evaluations in **AgentBeats mode** using the A2A protocol (HTTP-based agent communication).

## What's Here

- `gpt52_purple_agent.py` - GPT-5.2 A2A server implementation (purple agent)
- `gpt52_prompt.py` - System prompt for the agent
- `README.md` - This file

## Architecture

```
┌─────────────────────┐         A2A Protocol         ┌─────────────────────┐
│  Purple Agent       │◄─────────(HTTP)──────────────►│  Green Agent        │
│  (GPT-5.2)          │                               │  (QBench Evaluator) │
│  Port 9019          │                               │  (qbench CLI)       │
└─────────────────────┘                               └─────────────────────┘
        │                                                      │
        │ Calls GPT-5.2                                        │ Sends
        │ via litellm                                          │ observations
        │                                                      │ & runs scenarios
        └──────────────────────────────────────────────────────┘
```

**Two processes required:**
1. **Purple agent** - Your AI agent running as HTTP server
2. **Green agent** - QBench evaluator that sends scenarios to your agent

## Quick Start

### 1. Install & Configure

```bash
# Install litellm for GPT-5.2
pip install litellm

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

### 2. Start Purple Agent (Terminal 1)

```bash
cd examples/agentbeats
python gpt52_purple_agent.py
# Server starts on http://localhost:9019
```

### 3. Run Evaluation (Terminal 2)

```bash
# Test with 1 scenario, 1 seed
qbench eval --agent-url http://localhost:9019 \
  --scenarios backlog_cap_stability_guard \
  --seeds 1 \
  --verbose

# Run full benchmark (all 105 episodes)
qbench eval --agent-url http://localhost:9019 \
  --parallel 10 \
  --verbose
```

### 4. Stop Agent

Press `Ctrl+C` in Terminal 1 to stop the purple agent.

## Usage

### Command Structure

```bash
qbench eval --agent-url <purple-agent-url> [options]
```

**Options:**
- `--agent-url` - URL of your purple agent (required)
- `--scenarios` - Comma-separated scenario names (default: all 35)
- `--seeds` - Comma-separated seed numbers (1,2,3) (default: all)
- `--parallel` - Number of concurrent episodes (default: 1)
- `--verbose` - Show detailed logs
- `--output` - Custom output directory

### Examples

```bash
# Specific scenarios and seeds
qbench eval --agent-url http://localhost:9019 \
  --scenarios backlog_cap_stability_guard,cold_start_to_surge \
  --seeds 1,2 \
  --parallel 5

# Quick test → Medium test → Full evaluation
qbench eval --agent-url http://localhost:9019 --scenarios backlog_cap_stability_guard --seeds 1
qbench eval --agent-url http://localhost:9019 --scenarios backlog_cap_stability_guard,cold_start_to_surge --parallel 3
qbench eval --agent-url http://localhost:9019 --parallel 10
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

## Standalone vs AgentBeats

| Feature | Standalone | AgentBeats |
|---------|-----------|------------|
| Communication | Direct function calls | HTTP (A2A protocol) |
| Setup | Single process | Two processes |
| Command | `qbench eval --agent examples.standalone.agent.GPT52Agent` | `qbench eval --agent-url http://localhost:9019` |
| Speed | Faster (no network) | Network overhead |
| Use Case | Python agents | Remote/service agents |
| Agent Config | Same GPT-5.2, prompt, temperature | Same GPT-5.2, prompt, temperature |

**Note:** Both modes use identical GPT-5.2 configuration (model: `gpt-5.2-2025-12-11`, temperature: `1.0`).

## Troubleshooting

**Port Already in Use**
```bash
lsof -ti:9019 | xargs kill -9
```

**API Key Error**
```
ValueError: OPENAI_API_KEY environment variable not set
```
→ Run: `export OPENAI_API_KEY="your-key"`

**Connection Refused**
```
Connection refused to http://localhost:9019
```
→ Ensure purple agent is running (Terminal 1) before evaluation

**Import Error**
```
ImportError: No module named 'litellm'
```
→ Run: `pip install litellm`

**Temperature Error**
```
litellm.UnsupportedParamsError: gpt-5 models don't support temperature=0.1
```
→ GPT-5.2 only supports `temperature=1.0` (already set correctly in this example)

## Customization

**Change model or temperature:**
Edit `gpt52_purple_agent.py` and modify the `__init__` parameters:
```python
def __init__(self, model: str = "gpt-4", temperature: float = 0.7):
```

**Modify system prompt:**
Edit `gpt52_prompt.py` to change agent instructions.

**Note:** QBench automatically prepends full task specifications (with JSON format instructions) to each observation, so the system prompt can remain minimal.

## How It Works

1. Purple agent starts as A2A HTTP server (port 9019)
2. Green agent (QBench CLI) sends observation text via HTTP
3. Purple agent calls GPT-5.2 with system prompt + observation
4. GPT-5.2 returns JSON actions
5. Purple agent sends response back via A2A protocol
6. Green agent validates actions and computes metrics
