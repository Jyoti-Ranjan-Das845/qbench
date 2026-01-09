"""Utility functions for QBench runners."""

import asyncio
import subprocess
import time
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger("qbench.runner.utils")


def parse_scenarios(
    scenarios_arg: Optional[str],
    scenarios_dir: Path
) -> List[str]:
    """
    Parse scenario selection argument.

    Supports multiple formats:
    - None: All scenarios
    - "5": First 5 scenarios
    - "1,5,10": Specific scenario names or indices
    - "1-10": Range of scenarios by index
    - "name1,name2": Scenario names
    - "1-5,10,15-20": Mixed format

    Args:
        scenarios_arg: Scenario selection string or None
        scenarios_dir: Path to scenarios directory

    Returns:
        List of scenario directory names

    Examples:
        >>> parse_scenarios("5", Path("scenarios"))
        ['scenario_001', 'scenario_002', ..., 'scenario_005']

        >>> parse_scenarios("backlog_cap,cold_start", Path("scenarios"))
        ['backlog_cap_stability_guard', 'cold_start_to_surge']

        >>> parse_scenarios("1-3,10", Path("scenarios"))
        ['scenario_001', 'scenario_002', 'scenario_003', 'scenario_010']
    """
    # Get all scenario directories
    all_scenarios = sorted([
        d.name for d in scenarios_dir.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    ])

    if scenarios_arg is None or scenarios_arg == "all":
        return all_scenarios

    # If it's just a number, return first N scenarios
    if scenarios_arg.isdigit():
        n = int(scenarios_arg)
        if n <= 0:
            raise ValueError(f"Number of scenarios must be positive, got {n}")
        if n > len(all_scenarios):
            logger.warning(
                f"Requested {n} scenarios but only {len(all_scenarios)} available. "
                f"Running all scenarios."
            )
            return all_scenarios
        return all_scenarios[:n]

    # Parse complex format
    selected = []
    parts = [p.strip() for p in scenarios_arg.split(',')]

    for part in parts:
        if '-' in part and not part.startswith('-'):
            # Range by index: "1-10"
            try:
                start_str, end_str = part.split('-', 1)
                start = int(start_str)
                end = int(end_str)

                if start < 1 or end > len(all_scenarios):
                    raise ValueError(
                        f"Range {start}-{end} out of bounds. "
                        f"Valid range: 1-{len(all_scenarios)}"
                    )
                if start > end:
                    raise ValueError(f"Invalid range: {start}-{end} (start > end)")

                # 1-indexed to 0-indexed
                selected.extend(all_scenarios[start-1:end])
            except ValueError as e:
                # Not a valid range, try as scenario name
                if part in all_scenarios:
                    selected.append(part)
                else:
                    raise ValueError(f"Invalid scenario range or name: '{part}'") from e
        else:
            # Single scenario - try by name first, then by index
            if part in all_scenarios:
                selected.append(part)
            else:
                # Try to find by partial name match
                matches = [s for s in all_scenarios if part.lower() in s.lower()]
                if len(matches) == 1:
                    selected.append(matches[0])
                elif len(matches) > 1:
                    raise ValueError(
                        f"Ambiguous scenario name '{part}'. Matches: {matches}"
                    )
                else:
                    raise ValueError(
                        f"Unknown scenario: '{part}'. "
                        f"Use 'qbench list-scenarios' to see available scenarios."
                    )

    if not selected:
        raise ValueError("No scenarios selected")

    # Remove duplicates while preserving order
    seen = set()
    result = []
    for s in selected:
        if s not in seen:
            seen.add(s)
            result.append(s)

    return result


def parse_seeds(seeds_arg: str = "1,2,3") -> List[int]:
    """
    Parse seed selection argument.

    Supports:
    - "1": Single seed
    - "1,2": Multiple seeds
    - "1,2,3": All three seeds (default)
    - "1-3": Range

    Args:
        seeds_arg: Seed selection string

    Returns:
        List of seed indices

    Examples:
        >>> parse_seeds("1")
        [1]

        >>> parse_seeds("1,3")
        [1, 3]

        >>> parse_seeds("1-3")
        [1, 2, 3]
    """
    if '-' in seeds_arg:
        # Range: "1-3"
        try:
            start, end = map(int, seeds_arg.split('-'))
            if start < 1 or end < 1:
                raise ValueError("Seed indices must be positive")
            if start > end:
                raise ValueError(f"Invalid seed range: {start}-{end}")
            return list(range(start, end + 1))
        except ValueError as e:
            raise ValueError(f"Invalid seed range '{seeds_arg}': {e}") from e

    # Comma-separated: "1,2,3"
    try:
        seeds = [int(s.strip()) for s in seeds_arg.split(',')]
        if any(s < 1 for s in seeds):
            raise ValueError("Seed indices must be positive")
        return sorted(set(seeds))  # Remove duplicates and sort
    except ValueError as e:
        raise ValueError(f"Invalid seed specification '{seeds_arg}': {e}") from e


async def wait_for_agent(url: str, timeout: int = 30) -> bool:
    """
    Wait for an A2A agent to become ready.

    Checks the agent's /.well-known/agent-card endpoint.

    Args:
        url: Agent URL (e.g., "http://localhost:9018")
        timeout: Maximum wait time in seconds

    Returns:
        True if agent becomes ready, False if timeout
    """
    try:
        import httpx
        from a2a.client import A2ACardResolver
    except ImportError as e:
        raise ImportError(
            "A2A SDK required for remote mode. Install with: pip install a2a-sdk"
        ) from e

    logger.info(f"Waiting for agent at {url} to be ready...")
    start_time = time.time()

    async with httpx.AsyncClient(timeout=2.0) as client:
        while time.time() - start_time < timeout:
            try:
                resolver = A2ACardResolver(httpx_client=client, base_url=url)
                card = await resolver.get_agent_card()
                if card is not None:
                    logger.info(f"Agent ready: {card.name if hasattr(card, 'name') else 'Unknown'}")
                    return True
            except Exception:
                # Agent not ready yet
                pass

            await asyncio.sleep(1)

    logger.error(f"Timeout waiting for agent at {url} after {timeout}s")
    return False


def start_green_agent_subprocess(port: int, scenarios_dir: str, parallel: int, verbose: bool) -> subprocess.Popen:
    """
    Start the green agent server in a subprocess.

    Args:
        port: Port to run green agent on
        scenarios_dir: Path to scenarios directory
        parallel: Number of parallel workers
        verbose: Enable verbose logging

    Returns:
        Process handle
    """
    import sys

    cmd = [
        sys.executable,
        "-m",
        "qbench.evaluator.qbench_evaluator",
        "--port", str(port),
        "--scenarios-dir", scenarios_dir,
        "--parallel", str(parallel),
    ]

    if verbose:
        cmd.append("--verbose")

    logger.info(f"Starting green agent: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE if not verbose else None,
        stderr=subprocess.PIPE if not verbose else None,
        text=True,
        start_new_session=True
    )

    return process


def format_results_summary(results: dict, verbose: bool = False) -> str:
    """
    Format evaluation results as a readable summary.

    Args:
        results: Results dictionary
        verbose: Include detailed breakdown

    Returns:
        Formatted string
    """
    summary = []
    summary.append("\n" + "="*70)
    summary.append("QBench Evaluation Results")
    summary.append("="*70)

    # Overall metrics
    summary.append(f"\nOverall Performance:")
    summary.append(f"  Pass Rate: {results.get('pass_rate', 0):.1%}")
    summary.append(f"  Passed: {results.get('passed_episodes', 0)}/{results.get('total_episodes', 0)}")
    summary.append(f"  Failed: {results.get('failed_episodes', 0)}")

    # Soft metrics
    metrics = results.get('metrics', {})
    if metrics:
        summary.append(f"\nSoft Metrics (Passing Episodes):")
        summary.append(f"  Routine SLA: {(metrics.get('routine_sla') or 0):.1%}")
        summary.append(f"  Avg Wait Time: {(metrics.get('avg_wait_time') or 0.0):.2f} steps")
        summary.append(f"  Avg Backlog: {(metrics.get('avg_backlog') or 0.0):.2f} tasks")
        summary.append(f"  Max Backlog: {(metrics.get('max_backlog') or 0)} tasks")
        summary.append(f"  Avg Utilization: {(metrics.get('avg_utilization') or 0):.1%}")

    # Category breakdown if verbose
    if verbose and 'category_breakdown' in results:
        summary.append(f"\nCategory Breakdown:")
        for category, cat_metrics in results['category_breakdown'].items():
            summary.append(f"  {category}:")
            summary.append(f"    Pass Rate: {cat_metrics.get('pass_rate', 0):.1%}")
            summary.append(f"    Passed: {cat_metrics.get('passed', 0)}/{cat_metrics.get('total', 0)}")

    summary.append("="*70)

    return "\n".join(summary)


def save_results_to_file(results: dict, output_path: Optional[str] = None) -> str:
    """
    Save evaluation results to JSON file.

    Args:
        results: Results dictionary
        output_path: Path to save to, or None for auto-generated

    Returns:
        Path where results were saved
    """
    import json
    from datetime import datetime

    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"qbench_results_{timestamp}.json"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results saved to: {output_path}")
    return str(output_path)
