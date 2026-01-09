# Configuration Files

This directory contains pre-configured TOML files for common QBench evaluation scenarios. Configuration files let you save and reuse evaluation settings instead of specifying them via command-line flags.

## Available Configs

### `basic_eval.toml`
**Use case:** Default evaluation with all scenarios
- All 35 scenarios × 3 seeds = 105 episodes
- Sequential execution (parallel=1)
- Standard timeout (300s)
- Good for: Complete benchmark runs

```bash
qbench eval --config examples/configs/basic_eval.toml
```

### `parallel_eval.toml`
**Use case:** Fast evaluation with high throughput
- First 10 scenarios × 3 seeds = 30 episodes
- Parallel execution (parallel=10)
- Higher timeout (600s)
- Good for: Quick full benchmarks, CI/CD pipelines

```bash
qbench eval --config examples/configs/parallel_eval.toml
```

### `seed_selection.toml`
**Use case:** Targeted testing with specific scenarios
- 3 specific scenarios × 1 seed = 3 episodes
- Parallel execution (parallel=3)
- Verbose logging enabled
- Good for: Development, debugging, reproducibility testing

```bash
qbench eval --config examples/configs/seed_selection.toml
```

## Usage

### Basic Usage

```bash
# Use a config file
qbench eval --config examples/configs/basic_eval.toml

# Override config settings via CLI
qbench eval --config examples/configs/basic_eval.toml --parallel 5 --verbose
```

### Creating Your Own Config

Copy and modify an existing config:

```bash
cp examples/configs/basic_eval.toml my_config.toml
# Edit my_config.toml
qbench eval --config my_config.toml
```

## Config Structure

```toml
[agents]
purple_agent_url = "http://localhost:9019"  # Your agent URL
green_agent_port = 9018                      # Evaluator port

[evaluation]
scenarios = "all"          # "all", "10", ["scenario_name"], etc.
seeds = [1, 2, 3]         # Which seeds to run (1, 2, or 3)
parallel = 1              # Number of concurrent episodes
timeout = 300             # Timeout per episode (seconds)

[output]
output_file = "results/my_results.json"
verbose = false           # Show detailed logs
quiet = false            # Suppress all output
```

## Scenario Selection

You can specify scenarios in multiple ways:

```toml
scenarios = "all"                          # All 35 scenarios
scenarios = "10"                           # First 10 scenarios
scenarios = ["backlog_cap_stability_guard"] # Specific scenario
scenarios = ["backlog_cap", "cold_start"]  # Multiple scenarios
```

## Performance Tips

**Development:** Use `parallel=1` for easier debugging
```toml
parallel = 1
verbose = true
```

**CI/CD:** Use `parallel=10-20` for balanced speed
```toml
parallel = 10
timeout = 600
```

**Production:** Use `parallel=50+` for maximum throughput
```toml
parallel = 50
timeout = 1200
```

Note: Higher parallelism requires your agent to handle concurrent requests.

## Prerequisites

Before using any config:

1. **Start your purple agent:**
   ```bash
   # Standalone mode
   python examples/standalone/agent.py

   # AgentBeats mode
   python examples/agentbeats/gpt52_purple_agent.py
   ```

2. **Ensure agent URL matches config:**
   Check that `purple_agent_url` in the TOML file matches your agent's URL
