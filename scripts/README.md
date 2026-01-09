# QBench Scripts

Helper scripts to quickly run QBench evaluations.

## Quick Reference

| Script | What It Does | Duration | When to Use |
|--------|--------------|----------|-------------|
| `run_quick_test.sh` | 2 episodes (quick test) | 1-2 min | Development, smoke testing |
| `run_full_benchmark.sh` | 105 episodes (full benchmark) | 1-45 min* | Complete evaluation, benchmarking |

*Duration depends on parallelism (see presets below)

---

## 1. Quick Test Script

**Run 2 episodes for quick validation**

### Simplest Way (Interactive)
```bash
./scripts/run_quick_test.sh
```
Script will ask you what agent to test.

### With Your Agent
```bash
# Python agent
./scripts/run_quick_test.sh --agent examples.standalone.agent.GPT52Agent

# Remote agent (start agent first on port 9019)
./scripts/run_quick_test.sh --agent-url http://localhost:9019
```

### Options
- `--scenarios N` - Number of scenarios (default: 2)
- `--seeds 1,2,3` - Which seeds to test (default: 1)
- `--parallel N` - Parallel workers (default: 1)
- `--verbose` - Show detailed logs
- `--output FILE` - Save results to custom file

---

## 2. Full Benchmark Script

**Run all 105 episodes (35 scenarios × 3 seeds)**

### Simplest Way (Interactive)
```bash
./scripts/run_full_benchmark.sh
```
Script will ask you:
1. Which agent to test
2. Performance preset (sequential/balanced/fast)

### With Presets
```bash
# Balanced (recommended) - 4-5 minutes
./scripts/run_full_benchmark.sh --agent examples.standalone.agent.GPT52Agent --balanced

# Fast - 1-2 minutes (requires good hardware)
./scripts/run_full_benchmark.sh --agent examples.standalone.agent.GPT52Agent --fast

# Sequential - 35-45 minutes (easier debugging)
./scripts/run_full_benchmark.sh --agent examples.standalone.agent.GPT52Agent --sequential
```

### Performance Presets

| Preset | Parallel Workers | Duration | Use Case |
|--------|------------------|----------|----------|
| `--sequential` | 1 | 35-45 min | Debugging, single-threaded agents |
| `--balanced` | 10 | 4-5 min | **Recommended** for most cases |
| `--fast` | 50 | 1-2 min | Production, requires good hardware |

### Options
- `--parallel N` - Custom parallel workers (overrides presets)
- `--verbose` - Show detailed logs
- `--output FILE` - Save results to custom file

---

## Remote/A2A Mode

For both scripts, if testing a remote agent:

**Step 1:** Start your agent
```bash
cd examples/agentbeats
python gpt52_purple_agent.py  # Starts on port 9019
```

**Step 2:** Run script with `--agent-url`
```bash
./scripts/run_quick_test.sh --agent-url http://localhost:9019
./scripts/run_full_benchmark.sh --agent-url http://localhost:9019 --balanced
```

---

## Results

Results are automatically saved to JSON files:

**Quick test:**
- Location: Current directory
- Format: `qbench_results_YYYYMMDD_HHMMSS.json`

**Full benchmark:**
- Location: `results/` directory
- Format: `results/full_benchmark_YYYYMMDD_HHMMSS.json`

**Override location:**
```bash
./scripts/run_quick_test.sh --agent <agent> --output my_results.json
```

---

## Troubleshooting

### Permission Denied
```bash
chmod +x scripts/*.sh
```

### OPENAI_API_KEY Not Set
```bash
export OPENAI_API_KEY=your_key_here
```
Or create `.env` file in project root with `OPENAI_API_KEY=your_key_here`

### Module Not Found
Make sure you run from the qbench root directory:
```bash
cd /path/to/qbench
./scripts/run_quick_test.sh --agent examples.standalone.agent.GPT52Agent
```

### Port Already in Use (Remote Mode)
```bash
lsof -ti:9019 | xargs kill -9
python examples/agentbeats/gpt52_purple_agent.py
```

### UV Not Found
Install uv package manager:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Examples

**Quick development test:**
```bash
./scripts/run_quick_test.sh --agent examples.standalone.agent.GPT52Agent --verbose
```

**Test with more scenarios:**
```bash
./scripts/run_quick_test.sh --agent examples.standalone.agent.GPT52Agent --scenarios 5 --seeds 1,2,3
```

**Full benchmark (recommended settings):**
```bash
./scripts/run_full_benchmark.sh --agent examples.standalone.agent.GPT52Agent --balanced
```

**Fast full benchmark:**
```bash
./scripts/run_full_benchmark.sh --agent examples.standalone.agent.GPT52Agent --fast
```

**Remote agent test:**
```bash
# Terminal 1
python examples/agentbeats/gpt52_purple_agent.py

# Terminal 2
./scripts/run_quick_test.sh --agent-url http://localhost:9019
```
