# Scenario X Seed - Tier-1 QueueEnv Test Suite

A comprehensive test scenario collection for evaluating scheduling and queueing systems under diverse conditions. Developed for the **QBench team**.

## Overview

This repository contains **35 carefully designed test scenarios** covering the full spectrum of challenges that slot-based queue schedulers must handle:

- **105 seed files** (3 variations per scenario) for reproducible testing
- **10 distinct categories** testing different system capabilities
- **Hard SLA constraints** with priorities, deadlines, and capacity dynamics
- **Real-world stress patterns** including bursts, overload, and edge cases

## Collection Statistics

| Metric | Count |
|--------|-------|
| Total Scenarios | 35 |
| Seed Files | 105 (3 per scenario) |
| Categories | 10 |
| Test Coverage | Baseline, Load Patterns, Priority/Deadline Handling, Capacity Dynamics, Cancellations, Robustness, Adversarial |

## Repository Structure

```
scenario X seed/
├── README.md                          # This file
├── SCENARIO_CATEGORIES.md             # Category-wise scenario mapping with descriptions
├── scenario X seed.pdf                # Full specification document
│
├── [scenario_name]/                   # 35 scenario folders
│   ├── info.md                        # What this scenario tests
│   ├── seed_1.json                    # First seed variation
│   ├── seed_2.json                    # Second seed variation
│   └── seed_3.json                    # Third seed variation
```

### File Types

- **`seed_*.json`** - Test data files containing task arrivals, cancellations, capacity changes, and priority updates for each scenario episode
- **`info.md`** - Human-readable documentation explaining what each scenario tests and its category
- **`SCENARIO_CATEGORIES.md`** - Complete category breakdown with all scenarios grouped by testing purpose
- **`scenario X seed.pdf`** - Original specification document with detailed scenario definitions

## Scenario Categories

The 35 scenarios are organized into 10 thematic categories:

| Category | Count | Focus Area |
|----------|-------|------------|
| **Baseline** | 2 | Health checks and low-load baseline behavior |
| **Load Patterns** | 10 | Various traffic patterns from steady to bursts and spikes |
| **Regime Shifts** | 2 | Non-stationary workload changes |
| **Priority Handling** | 3 | Priority-based scheduling and triage |
| **Deadline Handling** | 4 | Deadline-aware scheduling and expiry management |
| **Capacity Stress** | 3 | System limits, overload, and fairness |
| **Capacity Dynamics** | 4 | Capacity changes over time |
| **Cancellations** | 4 | Cancellation handling and backfill |
| **Env Robustness** | 2 | Input validation and idempotency |
| **Adversarial** | 1 | Adversarial load patterns |

📄 See [`SCENARIO_CATEGORIES.md`](./SCENARIO_CATEGORIES.md) for the complete breakdown with scenario descriptions.

## Seed File Structure

Each scenario contains **3 seed files** providing different variations of the same test pattern:

- Different random seeds for arrival timing
- Varied task counts within the same pattern
- Different capacity/deadline configurations

This ensures test coverage across statistical variations while maintaining the core scenario intent.

## Quick Start

### Finding Scenarios by Category

1. Open [`SCENARIO_CATEGORIES.md`](./SCENARIO_CATEGORIES.md) to browse all scenarios organized by category
2. Click on any scenario name to navigate to its folder
3. Read `info.md` in the scenario folder for details on what it tests

### Understanding a Scenario

For any scenario (e.g., `late_burst_slack_trap/`):

1. **Read `info.md`** - Understand what the scenario tests and why
2. **Check seed files** - Review `seed_1.json`, `seed_2.json`, `seed_3.json` for test data
3. **Refer to PDF** - See `scenario X seed.pdf` for full specification details

### Navigating by Testing Purpose

- **Testing basic correctness?** → Start with **Baseline** scenarios
- **Load handling?** → Explore **Load Patterns** scenarios
- **Priority/deadline logic?** → Check **Priority Handling** and **Deadline Handling** scenarios
- **Capacity adaptation?** → Review **Capacity Dynamics** scenarios
- **Edge cases?** → Examine **Cancellations**, **Env Robustness**, and **Adversarial** scenarios

## Scenario Design Principles

Each scenario is designed to test specific system capabilities:

- **Single concern** - Each scenario focuses on one primary testing dimension
- **Reproducible** - Fixed seed files ensure consistent test execution
- **Graduated difficulty** - From simple baseline checks to complex adversarial patterns
- **Real-world inspired** - Patterns reflect actual production workload characteristics

## What Gets Tested

The Tier-1 QueueEnv scenarios evaluate:

✅ **Scheduling correctness** under various load conditions
✅ **SLA compliance** with hard deadlines and priorities
✅ **Capacity adaptation** to dynamic resource changes
✅ **Fairness and stability** under sustained overload
✅ **Robustness** to cancellations and invalid inputs
✅ **Graceful degradation** when demand exceeds capacity

## Reference Documentation

- **Full Specification**: See [`scenario X seed.pdf`](./scenario%20X%20seed.pdf)
- **Category Breakdown**: See [`SCENARIO_CATEGORIES.md`](./SCENARIO_CATEGORIES.md)
- **Individual Scenarios**: Check `info.md` in each scenario folder

---

**Developed for QBench team** | Tier-1 QueueEnv Test Suite
