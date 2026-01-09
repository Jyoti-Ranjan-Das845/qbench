"""A2A Remote Runner - Run evaluation with external A2A purple agent."""

import asyncio
import logging
import os
import signal
from pathlib import Path
from typing import Dict, Any, Optional

from qbench.runner.utils import (
    wait_for_agent,
    start_green_agent_subprocess,
    format_results_summary,
    save_results_to_file,
)
from qbench.client.a2a_client import send_eval_request, get_agent_info

logger = logging.getLogger("qbench.runner.a2a_remote")


async def run_a2a_remote_evaluation(
    purple_agent_url: str,
    scenarios: list[str],
    seeds: list[int],
    parallel: int = 1,
    timeout: int = 300,
    green_agent_port: int = 9018,
    scenarios_dir: str = "scenarios",
    output_file: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False
) -> Dict[str, Any]:
    """
    Run QBench evaluation with an external A2A purple agent.

    This mode:
    1. Starts the QBench green agent server
    2. Waits for it to be ready
    3. Sends an evaluation request via A2A protocol
    4. Collects and displays results
    5. Shuts down the green agent

    Args:
        purple_agent_url: URL of the purple agent to test (e.g., "http://localhost:9019")
        scenarios: List of scenario names to evaluate
        seeds: List of seed indices
        parallel: Number of parallel workers
        timeout: Timeout per episode in seconds
        green_agent_port: Port for green agent server
        scenarios_dir: Directory containing scenarios
        output_file: Optional path to save results JSON
        verbose: Enable verbose logging
        quiet: Minimal output

    Returns:
        Evaluation results dictionary

    Example:
        ```python
        # Terminal 1: Start your purple agent
        # python my_purple_agent.py --port 9019

        # Terminal 2: Run evaluation
        results = await run_a2a_remote_evaluation(
            purple_agent_url="http://localhost:9019",
            scenarios=["backlog_cap_stability_guard", "cold_start_to_surge"],
            seeds=[1, 2, 3],
            parallel=50
        )
        ```
    """
    green_agent_url = f"http://localhost:{green_agent_port}"
    green_process = None

    try:
        if not quiet:
            print(f"\n{'='*70}")
            print("QBench A2A Remote Evaluation")
            print(f"{'='*70}")
            print(f"Purple Agent: {purple_agent_url}")
            print(f"Green Agent:  {green_agent_url}")
            print(f"Scenarios:    {len(scenarios)}")
            print(f"Seeds:        {seeds}")
            print(f"Episodes:     {len(scenarios) * len(seeds)}")
            print(f"Parallel:     {parallel}")
            print(f"{'='*70}\n")

        # Step 1: Check if purple agent is running
        if not quiet:
            print("Step 1/5: Checking purple agent...")

        purple_info = await get_agent_info(purple_agent_url)
        if purple_info:
            if not quiet:
                print(f"  ✓ Purple agent ready: {purple_info.get('name', 'Unknown')}")
        else:
            raise Exception(
                f"Purple agent not responding at {purple_agent_url}\n"
                f"Make sure your agent is running first:\n"
                f"  python my_purple_agent.py --port {purple_agent_url.split(':')[-1]}"
            )

        # Step 2: Start green agent
        if not quiet:
            print("Step 2/5: Starting green agent...")

        green_process = start_green_agent_subprocess(
            port=green_agent_port,
            scenarios_dir=scenarios_dir,
            parallel=parallel,
            verbose=verbose
        )

        # Step 3: Wait for green agent to be ready
        if not quiet:
            print("Step 3/5: Waiting for green agent to be ready...")

        ready = await wait_for_agent(green_agent_url, timeout=30)
        if not ready:
            raise Exception("Green agent failed to start")

        if not quiet:
            print("  ✓ Green agent ready")

        # Step 4: Send evaluation request
        if not quiet:
            print(f"\nStep 4/5: Running evaluation ({len(scenarios) * len(seeds)} episodes)...")
            if parallel > 1:
                print(f"  Using {parallel} parallel workers")

        results = await send_eval_request(
            green_agent_url=green_agent_url,
            purple_agent_url=purple_agent_url,
            scenarios=scenarios,
            seeds=seeds,
            parallel=parallel,
            timeout=timeout,
            verbose=verbose
        )

        # Step 5: Display results
        if not quiet:
            print("\nStep 5/5: Processing results...")

        if not quiet:
            summary = format_results_summary(results, verbose=verbose)
            print(summary)

        # Save results if requested
        if output_file:
            saved_path = save_results_to_file(results, output_file)
            if not quiet:
                print(f"\nResults saved to: {saved_path}")

        return results

    except KeyboardInterrupt:
        logger.info("Evaluation interrupted by user")
        raise

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        raise

    finally:
        # Clean up: shut down green agent
        if green_process and green_process.poll() is None:
            if not quiet:
                print("\nShutting down green agent...")

            try:
                # Try graceful shutdown first
                green_process.terminate()
                try:
                    green_process.wait(timeout=5)
                except:
                    # Force kill if doesn't stop
                    green_process.kill()
                    green_process.wait()

                if not quiet:
                    print("  ✓ Green agent stopped")
            except Exception as e:
                logger.error(f"Error stopping green agent: {e}")


def run_a2a_remote_sync(*args, **kwargs) -> Dict[str, Any]:
    """
    Synchronous wrapper for run_a2a_remote_evaluation.

    Use this when calling from synchronous code.
    """
    return asyncio.run(run_a2a_remote_evaluation(*args, **kwargs))
