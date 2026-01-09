"""QBench - Queue Management Benchmark for AI Agents."""

# Data models
from qbench.data_models.action import Action
from qbench.data_models.observation import Observation, ScheduledTask
from qbench.data_models.result import BenchmarkResult, EpisodeResult, Metrics
from qbench.data_models.task import Task
from qbench.data_models.violation import Violation

# Environment
from qbench.environment.env import QueueEnv
from qbench.environment.loader import ScenarioLoader, SeedConfig

# Validation
from qbench.validation.checker import ConstraintChecker
from qbench.validation.validator import ActionValidator

# Metrics
from qbench.metrics.accumulator import MetricsAccumulator

# IO
from qbench.io.formatter import ObservationFormatter
from qbench.io.parser import ActionParser

# Agent
from qbench.agent.base import Agent, GreedyAgent, RandomAgent

# Runners
from qbench.runner.benchmark import BenchmarkRunner
from qbench.runner.episode import EpisodeRunner

# API (new - for easy standalone usage)
from qbench.api import run_qbench

# Scenarios
from qbench.scenarios import list_scenarios, AVAILABLE_SCENARIOS

__version__ = "0.1.0"

__all__ = [
    # Data models
    "Task",
    "Action",
    "Observation",
    "ScheduledTask",
    "Violation",
    "Metrics",
    "EpisodeResult",
    "BenchmarkResult",
    # Environment
    "QueueEnv",
    "ScenarioLoader",
    "SeedConfig",
    # Validation
    "ActionValidator",
    "ConstraintChecker",
    # Metrics
    "MetricsAccumulator",
    # IO
    "ObservationFormatter",
    "ActionParser",
    # Agent
    "Agent",
    "RandomAgent",
    "GreedyAgent",
    # Runners
    "EpisodeRunner",
    "BenchmarkRunner",
    # API (new)
    "run_qbench",
    "list_scenarios",
    "AVAILABLE_SCENARIOS",
]
