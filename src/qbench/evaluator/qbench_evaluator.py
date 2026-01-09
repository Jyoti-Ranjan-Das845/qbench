"""QBench Evaluator - Green agent that evaluates queue management agents."""

import argparse
import asyncio
import logging
import time
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

load_dotenv()

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import DataPart, Part, TaskState, TextPart
from a2a.utils import new_agent_text_message

from agentbeats.green_executor import GreenAgent, GreenExecutor
from agentbeats.models import EvalRequest
from agentbeats.tool_provider import ToolProvider
from qbench import BenchmarkRunner, ScenarioLoader
from qbench.config import RESULTS_DIR, DEFAULT_SEND_TASK_PROMPT
from .qbench_common import A2AAgentWrapper, QBenchMetrics, qbench_evaluator_agent_card, QBENCH_TASK_PROMPT

# Optional rate limiter imports
try:
    from agentbeats.rate_limiter import RPMLimiter, RequestQueueManager
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    RATE_LIMITING_AVAILABLE = False
    logger.warning("Rate limiting not available - install agentbeats.rate_limiter")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qbench_evaluator")


class QBenchEvaluator(GreenAgent):
    """Green agent that evaluates queue management agents using QBench."""

    def __init__(self, scenarios_dir: str = "scenarios", parallel: int = 1, verbose: bool = False, enable_rate_limiting: bool = False, requests_per_minute: int = 50, batch_size: int = 15):
        """
        Initialize the QBench evaluator.

        Args:
            scenarios_dir: Path to the scenarios directory
            parallel: Number of episodes to run concurrently (default: 1 for sequential)
            verbose: If True, show detailed step-by-step logs (default: False)
            enable_rate_limiting: (Deprecated) If True, enable rate limiting for purple agent requests
            requests_per_minute: (Deprecated) Rate limit in requests per minute (default: 50 RPM)
            batch_size: (Deprecated) Number of scenario types to process per batch (default: 15)
        """
        self._required_roles = ["agent"]  # The purple agent being tested
        self._scenarios_dir = scenarios_dir
        self._loader = ScenarioLoader(scenarios_dir)
        self._parallel = parallel
        self._verbose = verbose
        self._enable_rate_limiting = enable_rate_limiting  # Keep for backward compatibility
        self._requests_per_minute = requests_per_minute
        self._batch_size = batch_size

        # Tool provider will be created in run_eval (with or without rate limiter)
        self._tool_provider = None

    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        """
        Validate the evaluation request.

        Args:
            request: The evaluation request

        Returns:
            Tuple of (is_valid, message)
        """
        missing_roles = set(self._required_roles) - set(request.participants.keys())
        if missing_roles:
            return False, f"Missing required roles: {missing_roles}"
        return True, "ok"

    async def run_eval(self, req: EvalRequest, updater: TaskUpdater, agent_override=None) -> None:
        """
        Run the QBench evaluation.

        Args:
            req: Evaluation request with purple agent URL and config
            updater: Task updater for reporting progress
            agent_override: Optional agent instance to use instead of A2A wrapper (for standalone mode)
        """
        import json
        from pathlib import Path
        from qbench import EpisodeRunner, QueueEnv

        logger.info(f"Starting QBench evaluation: {req}")
        start_time = time.time()

        # Get configuration (backward compatible with old and new keys)
        scenario_types = req.config.get("scenario_types") or req.config.get("scenarios", None)
        seeds = req.config.get("seeds", [1, 2, 3])  # Default to all 3 seeds
        max_episodes = req.config.get("max_episodes", None)
        send_task_prompt = req.config.get("send_task_prompt", True)

        # Get the purple agent URL
        agent_url = str(req.participants["agent"])

        logger.info(f"Purple agent URL: {agent_url}")
        logger.info(f"Scenario types: {scenario_types}")
        logger.info(f"Seeds: {seeds}")
        logger.info(f"Max episodes: {max_episodes}")

        # Create timestamped runtime directory for this run
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        runtime_dir = RESULTS_DIR / f"run_{timestamp}"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        # Store runtime_dir in updater for standalone mode (allows api.py to save summary there)
        if hasattr(updater, 'runtime_dir'):
            updater.runtime_dir = runtime_dir

        logger.info(f"Runtime directory: {runtime_dir}")

        # Initialize rate limiter and tool provider
        queue_manager = None
        if self._enable_rate_limiting and RATE_LIMITING_AVAILABLE:
            logger.info(f"Enabling rate limiting: {self._requests_per_minute} RPM")

            # Create rate limiter
            rate_limiter = RPMLimiter(requests_per_minute=self._requests_per_minute)

            # Create queue manager
            queue_manager = RequestQueueManager(rate_limiter)
            await queue_manager.start()

            # Create tool provider with queue manager
            self._tool_provider = ToolProvider(queue_manager=queue_manager)

            logger.info("Rate limiting enabled with 3-worker architecture")
        else:
            # No rate limiting - direct requests
            self._tool_provider = ToolProvider()
            logger.info("Rate limiting disabled - sequential execution")

        # Build config summary
        config_parts = []
        if max_episodes:
            config_parts.append(f"max_episodes={max_episodes}")
        if scenario_types:
            config_parts.append(f"scenario_types={scenario_types}")
        if self._enable_rate_limiting:
            config_parts.append(f"rate_limit={self._requests_per_minute}RPM")
            config_parts.append("workers=3")
        config_summary = ", ".join(config_parts) if config_parts else "all scenarios"

        await updater.update_status(
            TaskState.working,
            new_agent_text_message(
                f"Starting QBench evaluation\nAgent: {agent_url}\nConfig: {config_summary}"
            )
        )

        try:
            # Send task prompt to purple agent (optional)
            if send_task_prompt:
                await updater.update_status(
                    TaskState.working,
                    new_agent_text_message("Sending task instructions to agent...")
                )

                try:
                    await self._tool_provider.talk_to_agent(
                        message=QBENCH_TASK_PROMPT,
                        url=agent_url,
                        new_conversation=True
                    )
                    logger.info("Task prompt sent successfully")
                except Exception as e:
                    logger.warning(f"Failed to send task prompt: {e}")
                    # Continue anyway - agent might work without explicit prompt

            # Create agent (use override for standalone mode, or A2A wrapper for AgentBeats mode)
            if agent_override:
                agent = agent_override
                logger.info("Using agent override (standalone mode)")
            else:
                agent = A2AAgentWrapper(agent_url, self._tool_provider)
                logger.info(f"Using A2A wrapper for {agent_url}")

            # Get list of scenarios to run
            if scenario_types is None:
                scenario_types = self._loader.list_scenario_types()

            # Group episodes by scenario type and filter by requested seeds
            episodes_by_scenario = {}
            for scenario_type in scenario_types:
                all_seed_files = self._loader.list_scenarios(scenario_type)

                # Filter to only include requested seeds
                filtered_seeds = []
                for seed_path in all_seed_files:
                    # Extract seed number from filename (e.g., "seed_1.json" -> 1)
                    seed_num = int(seed_path.stem.split("_")[-1])
                    if seed_num in seeds:
                        filtered_seeds.append(seed_path)

                episodes_by_scenario[scenario_type] = filtered_seeds

            # Calculate total episodes
            total_episodes = sum(len(seeds) for seeds in episodes_by_scenario.values())

            # Limit if requested (trim scenario types to fit max_episodes)
            if max_episodes:
                limited_scenarios = {}
                episode_count = 0
                for scenario_type, seeds in episodes_by_scenario.items():
                    if episode_count >= max_episodes:
                        break
                    remaining = max_episodes - episode_count
                    limited_scenarios[scenario_type] = seeds[:remaining]
                    episode_count += len(limited_scenarios[scenario_type])
                episodes_by_scenario = limited_scenarios
                total_episodes = episode_count

            logger.info(f"Running {total_episodes} episodes across {len(episodes_by_scenario)} scenario types")

            # Determine execution mode
            if self._parallel > 1:
                logger.info(f"Parallel mode: {self._parallel} episodes running concurrently")
            else:
                logger.info(f"Sequential mode: Running episodes one at a time")

            # Create flat list of all episodes
            all_episodes = []
            for scenario_type, seeds in episodes_by_scenario.items():
                for seed_path in seeds:
                    all_episodes.append((scenario_type, seed_path))

            await updater.update_status(
                TaskState.working,
                new_agent_text_message(
                    f"Running {total_episodes} episodes ({self._parallel} parallel)..."
                )
            )

            # Shared state for progress tracking
            results_lock = asyncio.Lock()
            results = []
            counters = {"passed": 0, "failed": 0, "completed": 0}
            episode_counter = {"current": 0}

            # Semaphore to limit concurrent episodes (for new parallel mode)
            semaphore = asyncio.Semaphore(self._parallel)

            # Function to run a single episode
            async def run_single_episode(worker_id: int, scenario_type: str, seed_path, episode_num: int):
                """Run a single episode with retry logic."""
                nonlocal results, counters

                seed_number = seed_path.stem.split("_")[-1]
                episode_name = f"{scenario_type}/seed_{seed_number}"
                episode_start_time = time.time()

                # Use simpler episode logging format
                logger.info(f"[Ep#{episode_num}/{total_episodes}] Starting: {episode_name}")

                # Create runtime directory for this episode
                episode_runtime_dir = runtime_dir / scenario_type / f"seed_{seed_number}"
                episode_runtime_dir.mkdir(parents=True, exist_ok=True)

                # Load scenario and run episode with retry logic
                max_retries = 3
                retry_delay = 2.0
                result = None
                last_error = None

                for attempt in range(max_retries):
                    try:
                        config = self._loader.load(seed_path)
                        env = QueueEnv(config)

                        episode_runner = EpisodeRunner(
                            env=env,
                            agent=agent
                        )

                        # Run episode in thread pool to avoid blocking
                        result = await asyncio.to_thread(
                            episode_runner.run,
                            scenario_type=scenario_type,
                            seed_number=seed_number,
                            verbose=self._verbose,
                            runtime_dir=episode_runtime_dir
                        )

                        # Success - break out of retry loop
                        break

                    except Exception as e:
                        last_error = e
                        logger.error(f"[Ep#{episode_num}/{total_episodes}] Attempt {attempt + 1}/{max_retries} failed: {e}")

                        if attempt < max_retries - 1:
                            logger.info(f"[Ep#{episode_num}/{total_episodes}] Retrying in {retry_delay}s...")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            logger.error(f"[Ep#{episode_num}/{total_episodes}] Failed after {max_retries} attempts")

                # Process result
                episode_duration = time.time() - episode_start_time
                worker_result = {"passed": 0, "failed": 0, "crashed": 0}

                async with results_lock:
                    if result is not None:
                        results.append(result)
                        counters["completed"] += 1

                        if result.passed:
                            counters["passed"] += 1
                            worker_result["passed"] = 1
                            status_icon = "✓"
                        else:
                            counters["failed"] += 1
                            worker_result["failed"] = 1
                            status_icon = "✗"

                        # Save episode summary
                        summary_data = {
                            "episode": episode_num,
                            "total": total_episodes,
                            "scenario_type": scenario_type,
                            "seed_number": seed_number,
                            "passed": result.passed,
                            "duration_seconds": episode_duration,
                            "metrics": result.metrics.model_dump(),
                            "violations": [v.model_dump() for v in result.violations],
                            "summary": result.summary
                        }

                        runtime_summary = episode_runtime_dir / "summary.json"
                        with open(runtime_summary, 'w') as f:
                            json.dump(summary_data, f, indent=2)

                        # Log completion
                        if result.passed:
                            logger.info(
                                f"[Ep#{episode_num}/{total_episodes}] ✓ PASS {episode_name} "
                                f"({episode_duration:.1f}s) - routine_sla={result.metrics.routine_sla:.3f}, "
                                f"wait={result.metrics.avg_wait_time:.1f}, util={result.metrics.avg_utilization:.3f}"
                            )
                        else:
                            violation_types = set(v.type for v in result.violations)
                            logger.info(
                                f"[Ep#{episode_num}/{total_episodes}] ✗ FAIL {episode_name} "
                                f"({episode_duration:.1f}s) - violations: {', '.join(violation_types)}"
                            )

                        # Send progress update
                        progress_msg = (
                            f"[Worker {worker_id}] [Episode {episode_num}/{total_episodes}] {scenario_type}/seed_{seed_number}\n"
                            f"{status_icon} {'PASS' if result.passed else 'FAIL'} ({episode_duration:.1f}s)"
                        )

                        if result.passed:
                            progress_msg += (
                                f" - routine_sla={result.metrics.routine_sla:.3f}, "
                                f"wait={result.metrics.avg_wait_time:.1f}, "
                                f"util={result.metrics.avg_utilization:.3f}"
                            )
                        else:
                            violation_types = set(v.type for v in result.violations)
                            progress_msg += f" - violations: {', '.join(violation_types)}"

                        progress_msg += f"\n\nProgress: {counters['completed']}/{total_episodes} ({100*counters['completed']/total_episodes:.1f}%) | Passed: {counters['passed']}/{counters['completed']} ({100*counters['passed']/counters['completed']:.1f}%)"

                        await updater.update_status(
                            TaskState.working,
                            new_agent_text_message(progress_msg)
                        )

                    else:
                        # Episode crashed after all retries
                        counters["failed"] += 1
                        counters["completed"] += 1
                        worker_result["crashed"] = 1

                        # Save error summary
                        error_summary = {
                            "episode": episode_num,
                            "total": total_episodes,
                            "scenario_type": scenario_type,
                            "seed_number": seed_number,
                            "passed": False,
                            "duration_seconds": episode_duration,
                            "error": str(last_error),
                            "error_type": type(last_error).__name__,
                            "retries_exhausted": True
                        }

                        runtime_summary = episode_runtime_dir / "summary.json"
                        with open(runtime_summary, 'w') as f:
                            json.dump(error_summary, f, indent=2)

                        logger.error(
                            f"[Ep#{episode_num}/{total_episodes}] ✗ CRASHED {episode_name} "
                            f"({episode_duration:.1f}s) - {type(last_error).__name__}: {str(last_error)[:100]}"
                        )

                        # Send progress update
                        progress_msg = (
                            f"[Worker {worker_id}] [Episode {episode_num}/{total_episodes}] {scenario_type}/seed_{seed_number}\n"
                            f"✗ CRASHED ({episode_duration:.1f}s) - {type(last_error).__name__}: {str(last_error)[:100]}"
                        )
                        progress_msg += f"\n\nProgress: {counters['completed']}/{total_episodes} ({100*counters['completed']/total_episodes:.1f}%) | Passed: {counters['passed']}/{counters['completed']}"

                        await updater.update_status(
                            TaskState.working,
                            new_agent_text_message(progress_msg)
                        )

                return worker_result

            # Wrapper to assign episode numbers and run with semaphore
            async def run_episode_with_number(scenario_type: str, seed_path):
                """Assign episode number and run episode."""
                # Assign episode number
                async with results_lock:
                    episode_counter["current"] += 1
                    episode_num = episode_counter["current"]

                # Run episode with semaphore control (concurrency limit)
                async with semaphore:
                    return await run_single_episode(1, scenario_type, seed_path, episode_num)

            # Run all episodes with controlled parallelism
            logger.info(f"Starting {total_episodes} episodes...")

            # Launch all episodes (semaphore controls concurrency)
            await asyncio.gather(*[
                run_episode_with_number(scenario_type, seed_path)
                for scenario_type, seed_path in all_episodes
            ])

            evaluation_time = time.time() - start_time

            # Aggregate results
            from qbench import Metrics, BenchmarkResult

            total = len(results)
            passed = sum(1 for r in results if r.passed)
            failed = total - passed
            pass_rate = passed / total if total > 0 else 0.0

            # Compute aggregate metrics (average of passing episodes)
            passing_results = [r for r in results if r.passed]

            if passing_results:
                avg_routine_sla = sum(r.metrics.routine_sla for r in passing_results) / len(passing_results)
                avg_wait = sum(r.metrics.avg_wait_time for r in passing_results) / len(passing_results)
                avg_backlog = sum(r.metrics.avg_backlog for r in passing_results) / len(passing_results)
                max_backlog_avg = sum(r.metrics.max_backlog for r in passing_results) / len(passing_results)
                avg_util = sum(r.metrics.avg_utilization for r in passing_results) / len(passing_results)

                aggregate_metrics = Metrics(
                    routine_sla=avg_routine_sla,
                    avg_wait_time=avg_wait,
                    avg_backlog=avg_backlog,
                    max_backlog=int(max_backlog_avg),
                    avg_utilization=avg_util
                )
            else:
                aggregate_metrics = None

            result = BenchmarkResult(
                total_episodes=total,
                passed=passed,
                failed=failed,
                results=results,
                aggregate_metrics=aggregate_metrics,
                pass_rate=pass_rate
            )

            # Convert to metrics
            metrics = QBenchMetrics(
                pass_rate=result.pass_rate,
                passed_episodes=result.passed,
                failed_episodes=result.failed,
                total_episodes=result.total_episodes,
                routine_sla=result.aggregate_metrics.routine_sla if result.aggregate_metrics else None,
                avg_wait_time=result.aggregate_metrics.avg_wait_time if result.aggregate_metrics else None,
                avg_backlog=result.aggregate_metrics.avg_backlog if result.aggregate_metrics else None,
                max_backlog=result.aggregate_metrics.max_backlog if result.aggregate_metrics else None,
                avg_utilization=result.aggregate_metrics.avg_utilization if result.aggregate_metrics else None,
            )

            # Create summary text
            summary = self._format_summary(metrics, evaluation_time, result)

            # Report results
            await updater.add_artifact(
                parts=[
                    Part(root=TextPart(text=summary)),
                    Part(root=DataPart(data=metrics.model_dump())),
                ],
                name="QBench Evaluation Results",
            )

            logger.info(f"Evaluation complete: {metrics.pass_rate:.1%} pass rate")

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            await updater.update_status(
                TaskState.failed,
                new_agent_text_message(f"Evaluation failed: {str(e)}")
            )
            raise

        finally:
            # Cleanup
            if self._tool_provider:
                self._tool_provider.reset()

            # Stop queue manager if it was started
            if queue_manager:
                await queue_manager.stop()
                logger.info("Rate limiter stopped")

    def _format_summary(self, metrics: QBenchMetrics, evaluation_time: float, result) -> str:
        """
        Format evaluation results as human-readable summary.

        Args:
            metrics: Computed metrics
            evaluation_time: Time taken for evaluation
            result: BenchmarkResult object

        Returns:
            Formatted summary string
        """
        summary = f"""QBench Queue Management Evaluation Results
{'=' * 60}

Overall Performance:
  Pass Rate: {metrics.pass_rate:.1%}
  Episodes: {metrics.passed_episodes}/{metrics.total_episodes} passed
  Failed: {metrics.failed_episodes}
  Evaluation Time: {evaluation_time:.1f}s

"""

        if metrics.routine_sla is not None:
            summary += f"""Soft Metrics (Passing Episodes Average):
  Routine SLA Compliance: {metrics.routine_sla:.1%}
  Avg Wait Time: {metrics.avg_wait_time:.2f} steps
  Avg Backlog: {metrics.avg_backlog:.2f} tasks
  Max Backlog: {metrics.max_backlog} tasks
  Avg Utilization: {metrics.avg_utilization:.1%}

"""

        # Add per-episode breakdown
        summary += "Episode Results:\n"
        for episode_result in result.results[:10]:  # Show first 10
            status = "✓" if episode_result.passed else "✗"
            scenario_type = episode_result.scenario_type or "unknown"
            seed = episode_result.seed_number or "?"
            routine_sla = episode_result.metrics.routine_sla if episode_result.passed else 0.0
            summary += f"  {status} {scenario_type}/seed_{seed}: routine_sla={routine_sla:.3f}\n"

        if len(result.results) > 10:
            summary += f"  ... and {len(result.results) - 10} more episodes\n"

        return summary


class StandaloneUpdater:
    """Mock updater for standalone mode that captures results instead of sending A2A updates."""

    def __init__(self):
        """Initialize the standalone updater."""
        self.artifacts = []
        self.final_summary = None
        self.final_metrics = None
        self.runtime_dir = None  # Will be set by evaluator to track where results are saved

    async def update_status(self, state: TaskState, message: any) -> None:
        """Log status update instead of sending A2A update."""
        logger.debug(f"Status update: {state}")

    async def add_artifact(self, parts: list, name: str) -> None:
        """Capture artifact data for later saving."""
        logger.debug(f"Artifact added: {name}")
        self.artifacts.append({"parts": parts, "name": name})

        # Extract summary and metrics from parts
        for part in parts:
            if hasattr(part, 'root'):
                if isinstance(part.root, TextPart):
                    self.final_summary = part.root.text
                elif isinstance(part.root, DataPart):
                    self.final_metrics = part.root.data


async def main():
    """Main entry point for the QBench evaluator green agent."""
    parser = argparse.ArgumentParser(description="Run the QBench evaluator green agent.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server")
    parser.add_argument("--port", type=int, default=9009, help="Port to bind the server")
    parser.add_argument("--card-url", type=str, help="External URL for the agent card")
    parser.add_argument("--scenarios-dir", type=str, default="scenarios", help="Path to scenarios directory")
    parser.add_argument("--parallel", type=int, default=1, help="Number of episodes to run in parallel (default: 1 for sequential)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed step-by-step logs")
    parser.add_argument("--enable-rate-limiting", action="store_true", help="Enable rate limiting (deprecated - use --parallel instead)")
    parser.add_argument("--rpm", type=int, default=50, help="Requests per minute rate limit (default: 50, deprecated)")
    parser.add_argument("--batch-size", type=int, default=15, help="Number of scenario types per batch (default: 15, deprecated)")

    # Standalone mode flags
    parser.add_argument("--standalone", action="store_true", help="Run evaluation directly without A2A server")
    parser.add_argument("--purple-agent-url", type=str, default="http://127.0.0.1:9019", help="URL of purple agent (default: http://127.0.0.1:9019)")
    parser.add_argument("--output", type=str, help="Output file path for results (default: <project_root>/results/run_{timestamp}/results.json)")
    parser.add_argument("--max-episodes", type=int, help="Limit number of episodes to run (default: None = all 105)")
    parser.add_argument("--scenario-types", type=str, help="Comma-separated scenario types to run (default: None = all)")
    parser.add_argument("--seeds", type=str, default="1,2,3", help="Comma-separated seed indices to run (default: 1,2,3)")

    args = parser.parse_args()

    # Create the green agent
    agent = QBenchEvaluator(
        scenarios_dir=args.scenarios_dir,
        parallel=args.parallel,
        verbose=args.verbose,
        enable_rate_limiting=args.enable_rate_limiting,
        requests_per_minute=args.rpm,
        batch_size=args.batch_size
    )

    # Check if standalone mode
    if args.standalone:
        # Standalone mode: run evaluation directly without A2A server
        import json
        from datetime import datetime
        from pydantic import HttpUrl

        logger.info("=" * 70)
        logger.info("QBench Evaluator - Standalone Mode")
        logger.info("=" * 70)
        logger.info(f"Purple agent URL: {args.purple_agent_url}")
        logger.info(f"Parallel episodes: {args.parallel}")
        logger.info(f"Verbose logging: {args.verbose}")
        logger.info(f"Max episodes: {args.max_episodes or 'All'}")
        logger.info(f"Scenario types: {args.scenario_types or 'All'}")
        logger.info(f"Seeds: {args.seeds}")
        logger.info("=" * 70)
        logger.info("")

        # Output file path (will be determined after evaluation if not specified)
        output_file = args.output

        # Parse scenario types
        scenario_types_list = None
        if args.scenario_types:
            scenario_types_list = [s.strip() for s in args.scenario_types.split(",")]

        # Parse seeds
        seeds_list = [int(s.strip()) for s in args.seeds.split(",")]

        # Create EvalRequest
        req = EvalRequest(
            participants={"agent": HttpUrl(args.purple_agent_url)},
            config={
                "max_episodes": args.max_episodes,
                "scenario_types": scenario_types_list,
                "seeds": seeds_list,
                "send_task_prompt": DEFAULT_SEND_TASK_PROMPT
            }
        )

        # Create standalone updater
        updater = StandaloneUpdater()

        # Run evaluation
        logger.info("Starting evaluation...")
        await agent.run_eval(req, updater)

        # Save results to JSON file in runtime directory
        from pathlib import Path
        if output_file is None:
            if updater.runtime_dir is None:
                raise RuntimeError("Runtime directory not set by evaluator")
            output_path = updater.runtime_dir / "results.json"
        else:
            output_path = Path(output_file)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        result_data = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "purple_agent_url": args.purple_agent_url,
                "parallel": args.parallel,
                "verbose": args.verbose,
                "max_episodes": args.max_episodes,
                "scenario_types": scenario_types_list,
                "seeds": seeds_list,
            },
            "summary": updater.final_summary,
            "metrics": updater.final_metrics,
        }

        with open(output_path, 'w') as f:
            json.dump(result_data, f, indent=2)

        logger.info("")
        logger.info("=" * 70)
        logger.info("Evaluation complete!")
        logger.info(f"Results saved to: {output_path}")
        logger.info(f"Runtime directory: {updater.runtime_dir}")
        logger.info("=" * 70)
        logger.info("")

        # Print summary
        if updater.final_summary:
            logger.info("Summary:")
            logger.info(updater.final_summary)

        return

    # A2A server mode (existing behavior)
    agent_url = args.card_url or f"http://{args.host}:{args.port}/"
    executor = GreenExecutor(agent)
    agent_card = qbench_evaluator_agent_card("QBenchEvaluator", agent_url)

    # Create A2A server
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    logger.info(f"Starting QBench evaluator at {agent_url}")
    uvicorn_config = uvicorn.Config(server.build(), host=args.host, port=args.port)
    uvicorn_server = uvicorn.Server(uvicorn_config)
    await uvicorn_server.serve()


if __name__ == "__main__":
    asyncio.run(main())
