"""Simple API for running QBench evaluations."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from qbench.agent.base import Agent
from qbench.scenarios import get_scenario_names, get_scenario_count
from qbench.config import (
    DEFAULT_PURPLE_AGENT_URL,
    DEFAULT_SCENARIOS_DIR,
    DEFAULT_PARALLEL,
    DEFAULT_SEND_TASK_PROMPT,
    MIN_PARALLEL,
    MAX_PARALLEL,
    MIN_EPISODES,
    RESULTS_DIR,
)

logger = logging.getLogger("qbench.api")


class AgentAdapter:
    """Adapter to wrap Agent interface for use with existing evaluator."""
    
    def __init__(self, agent: Agent):
        self.agent = agent
    
    def act(self, observation: str) -> str:
        """Forward to wrapped agent."""
        return self.agent.act(observation)


def run_qbench(
    agent: Agent,
    scenarios: Optional[List[str]] = None,
    seeds: Optional[List[int]] = None,
    parallel: int = DEFAULT_PARALLEL,
    verbose: bool = False,
    output_path: Optional[str] = None,
    save_results: bool = True,
    max_episodes: Optional[int] = None,
    purple_agent_url: str = DEFAULT_PURPLE_AGENT_URL,
    scenarios_dir: str = DEFAULT_SCENARIOS_DIR
) -> Dict[str, Any]:
    """
    Run QBench evaluation on an agent (standalone mode).

    This is the main entry point for testing your agent with QBench.

    Args:
        agent: Your agent instance (must extend Agent base class)
        scenarios: List of scenario names to run, or None for all (default: all 35 scenarios)
        seeds: List of seed indices to run (1, 2, or 3), or None for all 3 seeds (default: [1,2,3])
        parallel: Number of episodes to run concurrently (default: 1 for sequential)
        verbose: Show detailed step-by-step logs (default: False)
        output_path: Path to save results JSON, or None for auto-generated (default: None)
        save_results: Whether to save results to file (default: True)
        max_episodes: Limit total episodes to run (default: None for all)
        purple_agent_url: URL for purple agent (used internally, default: http://127.0.0.1:9019)
        scenarios_dir: Directory containing scenarios (default: "scenarios")
    
    Returns:
        Dictionary containing:
            - pass_rate: float (0.0 to 1.0)
            - passed_episodes: int
            - failed_episodes: int
            - total_episodes: int
            - metrics: dict with:
                - routine_sla: float
                - avg_wait_time: float
                - avg_backlog: float
                - max_backlog: int
                - avg_utilization: float
            - summary: str (text summary of results)
            - output_file: str (path where results were saved, if save_results=True)
    
    Example:
        ```python
        from qbench import Agent, run_qbench

        class MyAgent(Agent):
            def act(self, observation: str) -> str:
                # Your logic
                return actions

        # Run all scenarios with all seeds
        results = run_qbench(agent=MyAgent())

        # Run specific scenarios with specific seeds
        results = run_qbench(
            agent=MyAgent(),
            scenarios=["backlog_cap_stability_guard", "cold_start_to_surge"],
            seeds=[1, 2],  # Only run seeds 1 and 2
            parallel=10,
            verbose=True
        )

        print(f"Pass rate: {results['pass_rate']:.1%}")
        ```
    
    Raises:
        ValueError: If invalid scenario names or parameters provided
        ImportError: If required dependencies not available
    """
    # Validate input parameters
    if parallel < MIN_PARALLEL:
        raise ValueError(
            f"parallel must be at least {MIN_PARALLEL}, got {parallel}"
        )
    if parallel > MAX_PARALLEL:
        logger.warning(
            f"parallel={parallel} exceeds recommended maximum of {MAX_PARALLEL}. "
            f"This may cause high resource usage."
        )

    if max_episodes is not None and max_episodes < MIN_EPISODES:
        raise ValueError(
            f"max_episodes must be at least {MIN_EPISODES}, got {max_episodes}"
        )

    # Import here to avoid circular dependencies
    try:
        from qbench.evaluator.qbench_evaluator import QBenchEvaluator, StandaloneUpdater
        from agentbeats.models import EvalRequest
        from pydantic import HttpUrl
    except ImportError as e:
        raise ImportError(
            f"Required dependencies not available: {e}. "
            "Make sure QBench is properly installed."
        )

    # Validate scenarios
    scenario_names = get_scenario_names(scenarios)
    num_scenarios = get_scenario_count(scenarios)
    
    logger.info(f"Running QBench evaluation with {num_scenarios} scenarios")
    if verbose:
        logger.info(f"Scenarios: {', '.join(scenario_names[:5])}{'...' if len(scenario_names) > 5 else ''}")
    
    # Create evaluator
    evaluator = QBenchEvaluator(
        scenarios_dir=scenarios_dir,
        parallel=parallel,
        verbose=verbose
    )
    
    # Wrap agent
    wrapped_agent = AgentAdapter(agent)
    
    # Create eval request (mimics AgentBeats structure but runs standalone)
    req = EvalRequest(
        participants={"agent": HttpUrl(purple_agent_url)},
        config={
            "scenario_types": scenario_names if scenarios else None,
            "seeds": seeds if seeds is not None else [1, 2, 3],
            "max_episodes": max_episodes,
            "send_task_prompt": DEFAULT_SEND_TASK_PROMPT
        }
    )
    
    # Create standalone updater to capture results
    updater = StandaloneUpdater()
    
    # Run evaluation
    logger.info("Starting evaluation...")
    start_time = datetime.now()
    
    try:
        # Run async evaluation
        asyncio.run(evaluator.run_eval(req, updater, agent_override=wrapped_agent))
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"Evaluation completed in {duration:.1f}s")
    
    # Extract results
    results = {
        "pass_rate": updater.final_metrics.get("pass_rate", 0.0) if updater.final_metrics else 0.0,
        "passed_episodes": updater.final_metrics.get("passed_episodes", 0) if updater.final_metrics else 0,
        "failed_episodes": updater.final_metrics.get("failed_episodes", 0) if updater.final_metrics else 0,
        "total_episodes": updater.final_metrics.get("total_episodes", 0) if updater.final_metrics else 0,
        "metrics": {
            "routine_sla": updater.final_metrics.get("routine_sla", 0.0) if updater.final_metrics else 0.0,
            "avg_wait_time": updater.final_metrics.get("avg_wait_time", 0.0) if updater.final_metrics else 0.0,
            "avg_backlog": updater.final_metrics.get("avg_backlog", 0.0) if updater.final_metrics else 0.0,
            "max_backlog": updater.final_metrics.get("max_backlog", 0) if updater.final_metrics else 0,
            "avg_utilization": updater.final_metrics.get("avg_utilization", 0.0) if updater.final_metrics else 0.0,
        },
        "summary": updater.final_summary or "No summary available",
        "duration_seconds": duration,
    }
    
    # Save results if requested
    if save_results:
        try:
            # Use the runtime directory created by the evaluator
            if output_path is None:
                if updater.runtime_dir is None:
                    raise RuntimeError("Runtime directory not set by evaluator")
                output_file = updater.runtime_dir / "results.json"
            else:
                output_file = Path(output_path)

            # Create parent directories if needed
            output_file.parent.mkdir(parents=True, exist_ok=True)

            result_data = {
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "scenarios": scenario_names if scenarios else "all",
                    "seeds": seeds if seeds is not None else [1, 2, 3],
                    "parallel": parallel,
                    "max_episodes": max_episodes,
                },
                **results
            }

            # Write results to file
            with open(output_file, 'w') as f:
                json.dump(result_data, f, indent=2)

            results["output_file"] = str(output_file)
            results["runtime_dir"] = str(updater.runtime_dir)
            logger.info(f"Results saved to: {output_file}")
            logger.info(f"Runtime directory: {updater.runtime_dir}")

        except (OSError, IOError) as e:
            error_msg = f"Failed to save results to '{output_path if output_path else 'runtime directory'}': {e}"
            logger.error(error_msg)
            results["save_error"] = error_msg
        except Exception as e:
            error_msg = f"Unexpected error saving results: {e}"
            logger.error(error_msg)
            results["save_error"] = error_msg
    
    return results
