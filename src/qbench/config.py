"""QBench configuration constants.

This module contains all configuration defaults and constants used throughout QBench.
Users can override these values by passing parameters to the API functions.
"""

from pathlib import Path


def get_project_root() -> Path:
    """Get the absolute path to the QBench project root directory.

    The project root is identified by the presence of pyproject.toml.
    This ensures results are saved to a consistent location regardless of
    where QBench commands are run from.

    Returns:
        Path: Absolute path to project root directory

    Raises:
        RuntimeError: If pyproject.toml cannot be found
    """
    # Start from this config file's directory
    current = Path(__file__).resolve().parent

    # Walk up the directory tree looking for pyproject.toml
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent

    # Fallback: if not found, use the parent of the src directory
    # This handles edge cases in development
    if current.name == "qbench" and current.parent.name == "src":
        return current.parent.parent

    raise RuntimeError("Could not find QBench project root (pyproject.toml not found)")


# Results directory - absolute path to ensure single source of truth
RESULTS_DIR = get_project_root() / "results"
"""Absolute path to results directory. All evaluation results save here."""

# Default directories
DEFAULT_SCENARIOS_DIR = "scenarios"
"""Default directory containing scenario seed files."""

# Default URLs for AgentBeats mode
DEFAULT_PURPLE_AGENT_URL = "http://127.0.0.1:9019"
"""Default URL for purple agent (participant agent under test)."""

DEFAULT_GREEN_AGENT_PORT = 9018
"""Default port for green agent server (QBench evaluator)."""

# Default evaluation settings
DEFAULT_PARALLEL = 1
"""Default number of episodes to run concurrently."""

DEFAULT_SEND_TASK_PROMPT = True
"""Whether to send task prompt to agent (default: True to ensure agents receive instructions)."""

# Output settings
DEFAULT_RESULTS_FILENAME_PATTERN = "qbench_results_{timestamp}.json"
"""Pattern for auto-generated result filenames. {timestamp} will be replaced."""

# Validation limits
MIN_PARALLEL = 1
"""Minimum allowed value for parallel execution."""

MAX_PARALLEL = 100
"""Maximum recommended value for parallel execution."""

MIN_EPISODES = 1
"""Minimum allowed value for max_episodes."""
