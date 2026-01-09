"""Command-line interface for QBench."""

import argparse
import logging
import sys
import warnings
from pathlib import Path
from typing import List, Optional

from qbench.config import (
    DEFAULT_PURPLE_AGENT_URL,
    DEFAULT_GREEN_AGENT_PORT,
    DEFAULT_SCENARIOS_DIR,
    DEFAULT_PARALLEL,
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("qbench.cli")


def import_agent_class(module_path: str):
    """
    Dynamically import an agent class from a module path.
    
    Args:
        module_path: Path like "my_module.MyAgent" or "path.to.module.ClassName"
    
    Returns:
        The agent class
    """
    parts = module_path.rsplit('.', 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid agent path: '{module_path}'. "
            "Expected format: 'module.ClassName' (e.g., 'my_agent.MyAgent')"
        )
    
    module_name, class_name = parts
    
    try:
        import importlib
        module = importlib.import_module(module_name)
        agent_class = getattr(module, class_name)
        return agent_class
    except ImportError as e:
        raise ImportError(
            f"Could not import module '{module_name}': {e}\n"
            f"Make sure the module is in your Python path."
        )
    except AttributeError:
        raise AttributeError(
            f"Module '{module_name}' has no class '{class_name}'"
        )


def cmd_eval(args):
    """Unified evaluation command - routes to standalone, remote, or orchestrated mode."""
    from qbench.runner.utils import parse_scenarios, parse_seeds

    # Determine mode
    if args.agent:
        _cmd_eval_standalone(args)
    elif args.agent_url:
        _cmd_eval_a2a_remote(args)
    elif args.config:
        _cmd_eval_a2a_orchestrated(args)
    else:
        # Should never happen due to argparse mutual exclusion
        raise ValueError("Must specify --agent, --agent-url, or --config")


def _cmd_eval_standalone(args):
    """Run standalone evaluation mode."""
    from qbench.api import run_qbench
    from qbench.runner.utils import parse_scenarios, parse_seeds

    # Parse scenarios and seeds
    scenarios_dir = Path(DEFAULT_SCENARIOS_DIR)
    scenario_names = parse_scenarios(args.scenarios, scenarios_dir)
    seed_indices = parse_seeds(args.seeds)

    logger.info(f"Standalone mode: {len(scenario_names)} scenarios, {len(seed_indices)} seeds each")
    logger.info(f"Total episodes: {len(scenario_names) * len(seed_indices)}")

    # Import agent class
    logger.info(f"Loading agent: {args.agent}")
    AgentClass = import_agent_class(args.agent)
    agent = AgentClass()

    # Run evaluation with selected scenarios and seeds
    results = run_qbench(
        agent=agent,
        scenarios=scenario_names if scenario_names else None,
        seeds=seed_indices,
        parallel=args.parallel,
        verbose=args.verbose,
        output_path=args.output,
        save_results=args.output is not None,
    )

    # Print results
    from qbench.runner.utils import format_results_summary

    if not args.quiet:
        summary = format_results_summary(results, verbose=args.verbose)
        print(summary)

    if args.output:
        logger.info(f"Results saved to: {results.get('output_file', args.output)}")


def _cmd_eval_a2a_remote(args):
    """Run A2A remote evaluation mode."""
    from qbench.runner.a2a_remote import run_a2a_remote_sync
    from qbench.runner.utils import parse_scenarios, parse_seeds

    # Parse scenarios and seeds
    scenarios_dir = Path(DEFAULT_SCENARIOS_DIR)
    scenario_names = parse_scenarios(args.scenarios, scenarios_dir)
    seed_indices = parse_seeds(args.seeds)

    logger.info(f"A2A Remote mode: {len(scenario_names)} scenarios, {len(seed_indices)} seeds each")
    logger.info(f"Purple agent: {args.agent_url}")

    # Run evaluation
    try:
        results = run_a2a_remote_sync(
            purple_agent_url=args.agent_url,
            scenarios=scenario_names,
            seeds=seed_indices,
            parallel=args.parallel,
            timeout=args.timeout,
            green_agent_port=args.green_agent_port,
            scenarios_dir=DEFAULT_SCENARIOS_DIR,
            output_file=args.output,
            verbose=args.verbose,
            quiet=args.quiet
        )

        # Results already printed by run_a2a_remote_sync if not quiet

    except Exception as e:
        logger.error(f"A2A evaluation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _cmd_eval_a2a_orchestrated(args):
    """Run A2A orchestrated evaluation mode (TOML config)."""
    import asyncio
    from agentbeats.run_scenario import main as run_scenario_main

    logger.info(f"A2A Orchestrated mode: {args.config}")

    # Delegate to run_scenario which handles TOML orchestration
    # Temporarily override sys.argv for the orchestrator
    import sys
    old_argv = sys.argv
    try:
        sys.argv = ["qbench-run", args.config]
        if args.verbose:
            sys.argv.append("--show-logs")
        run_scenario_main()
    finally:
        sys.argv = old_argv


def cmd_run(args):
    """Run standalone evaluation (DEPRECATED - use 'qbench eval --agent' instead)."""
    warnings.warn(
        "The 'qbench run' command is deprecated and will be removed in v2.0.0. "
        "Please use 'qbench eval --agent' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    print("⚠️  WARNING: 'qbench run' is deprecated. Use 'qbench eval --agent' instead.\n")

    from qbench.api import run_qbench

    # Import agent class
    logger.info(f"Loading agent: {args.agent}")
    AgentClass = import_agent_class(args.agent)
    agent = AgentClass()

    # Run evaluation
    logger.info("Starting QBench evaluation (standalone mode)")
    results = run_qbench(
        agent=agent,
        scenarios=args.scenarios,
        parallel=args.parallel,
        verbose=args.verbose,
        output_path=args.output,
        save_results=not args.no_save,
        max_episodes=args.max_episodes
    )

    # Print results
    print("\n" + "="*60)
    print("QBench Evaluation Results")
    print("="*60)
    print(f"Pass Rate: {results['pass_rate']:.1%}")
    print(f"Passed: {results['passed_episodes']}/{results['total_episodes']}")
    print(f"Failed: {results['failed_episodes']}")
    print(f"\nSoft Metrics (Passing Episodes):")
    print(f"  Routine SLA: {results['metrics']['routine_sla']:.1%}")
    print(f"  Avg Wait Time: {results['metrics']['avg_wait_time']:.2f} steps")
    print(f"  Avg Backlog: {results['metrics']['avg_backlog']:.2f} tasks")
    print(f"  Max Backlog: {results['metrics']['max_backlog']} tasks")
    print(f"  Avg Utilization: {results['metrics']['avg_utilization']:.1%}")
    print("="*60)

    if not args.no_save:
        print(f"\nResults saved to: {results.get('output_file', 'unknown')}")


def cmd_agentbeats(args):
    """Run AgentBeats mode (DEPRECATED - use 'qbench eval --agent-url' instead)."""
    warnings.warn(
        "The 'qbench agentbeats' command is deprecated and will be removed in v2.0.0. "
        "Please use 'qbench eval --agent-url' instead.",
        DeprecationWarning,
        stacklevel=2
    )
    print("⚠️  WARNING: 'qbench agentbeats' is deprecated. Use 'qbench eval --agent-url' instead.\n")

    import asyncio
    import uvicorn
    from qbench.evaluator.qbench_evaluator import QBenchEvaluator, qbench_evaluator_agent_card
    from a2a.server.apps import A2AStarletteApplication
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.tasks import InMemoryTaskStore
    from agentbeats.green_executor import GreenExecutor
    
    logger.info("Starting QBench in AgentBeats mode")
    logger.info(f"Purple agent URL: {args.purple_agent_url}")
    
    # Create evaluator
    evaluator = QBenchEvaluator(
        scenarios_dir=DEFAULT_SCENARIOS_DIR,
        parallel=args.parallel,
        verbose=args.verbose
    )
    
    # Create green executor
    executor = GreenExecutor(evaluator)
    
    # Create request handler
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore()
    )
    
    # Create app
    card = qbench_evaluator_agent_card("QBenchEvaluator", f"http://localhost:{args.port}")
    a2a_app = A2AStarletteApplication(
        agent_card=card,
        http_handler=request_handler
    )

    # Build the Starlette app
    app = a2a_app.build()

    # Run server
    logger.info(f"Starting green agent server on port {args.port}")
    uvicorn.run(app, host="0.0.0.0", port=args.port)


def cmd_list_scenarios(args):
    """List all available scenarios."""
    from qbench.scenarios import list_scenarios
    
    scenarios = list_scenarios()
    print(f"\nAvailable QBench Scenarios ({len(scenarios)} total):\n")
    for i, scenario in enumerate(scenarios, 1):
        print(f"  {i:2d}. {scenario}")
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="QBench - Queue Management Agent Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standalone mode
  qbench eval --agent examples.standalone.my_agent.MyAgent --scenarios 10

  # A2A remote mode
  qbench eval --agent-url http://localhost:9019 --scenarios 10 --parallel 50

  # A2A orchestrated mode
  qbench eval --config config.toml

  # List scenarios
  qbench list-scenarios

Legacy commands (deprecated):
  qbench run --agent ...       # Use: qbench eval --agent ...
  qbench agentbeats --url ...  # Use: qbench eval --agent-url ...
"""
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ========== NEW: eval command (unified interface) ==========
    eval_parser = subparsers.add_parser(
        "eval",
        help="Run QBench evaluation",
        description="Unified command for running QBench evaluations in standalone, remote, or orchestrated mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standalone mode - Run your Python agent directly
  qbench eval --agent examples.standalone.my_agent.MyAgent --scenarios 5

  # A2A remote mode - Test a running A2A agent
  qbench eval --agent-url http://localhost:9019 --scenarios "1-10" --parallel 50

  # A2A orchestrated mode - Use TOML configuration
  qbench eval --config my-test.toml

Scenario selection:
  --scenarios 10                First 10 scenarios
  --scenarios "1,5,10"          Specific scenarios
  --scenarios "1-10"            Range of scenarios
  --scenarios "name1,name2"     By scenario name

Seed selection:
  --seeds "1"                   Only seed 1
  --seeds "1,2"                 Seeds 1 and 2
  --seeds "1,2,3"               All three seeds (default)
"""
    )

    # === MODE SELECTION (mutually exclusive) ===
    mode = eval_parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--agent",
        metavar="CLASS",
        help="Agent class path for standalone mode (e.g., 'examples.my_agent.MyAgent')"
    )
    mode.add_argument(
        "--agent-url",
        metavar="URL",
        help="Remote A2A agent URL (e.g., 'http://localhost:9019')"
    )
    mode.add_argument(
        "--config",
        metavar="FILE",
        help="TOML configuration file for orchestrated mode"
    )

    # === EVALUATION SCOPE ===
    eval_parser.add_argument(
        "--scenarios",
        type=str,
        metavar="N|IDS|RANGE",
        help=(
            "Scenarios to run. Examples: '10' (first 10), '1,5,10' (specific), "
            "'1-10' (range), 'name1,name2' (by name). Default: all 35 scenarios"
        )
    )
    eval_parser.add_argument(
        "--seeds",
        type=str,
        default="1,2,3",
        metavar="SEEDS",
        help="Seed files to use: '1', '1,2', '1,2,3' (default: '1,2,3')"
    )

    # === EXECUTION ===
    eval_parser.add_argument(
        "--parallel",
        type=int,
        default=DEFAULT_PARALLEL,
        metavar="N",
        help=f"Number of parallel workers (default: {DEFAULT_PARALLEL})"
    )
    eval_parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        metavar="SEC",
        help="Timeout per episode in seconds (default: 300)"
    )

    # === OUTPUT ===
    eval_parser.add_argument(
        "--output",
        type=str,
        metavar="FILE",
        help="Save results to JSON file"
    )
    eval_parser.add_argument(
        "--output-dir",
        type=str,
        metavar="DIR",
        help="Save results and logs to directory"
    )
    eval_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    eval_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output (only final results)"
    )
    eval_parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar"
    )

    # === A2A SPECIFIC ===
    eval_parser.add_argument(
        "--green-agent-port",
        type=int,
        default=DEFAULT_GREEN_AGENT_PORT,
        metavar="PORT",
        help=f"Port for green agent in A2A modes (default: {DEFAULT_GREEN_AGENT_PORT})"
    )

    eval_parser.set_defaults(func=cmd_eval)
    
    # ========== run command (standalone) ==========
    run_parser = subparsers.add_parser(
        "run",
        help="Run standalone evaluation",
        description="Test your Python agent with QBench (standalone mode - no AgentBeats needed)"
    )
    run_parser.add_argument(
        "--agent",
        required=True,
        help="Python module path to agent class (e.g., 'my_agent.MyAgent')"
    )
    run_parser.add_argument(
        "--scenarios",
        nargs="+",
        help="Specific scenarios to run (default: all). Use 'all' or space-separated names."
    )
    run_parser.add_argument(
        "--parallel",
        type=int,
        default=DEFAULT_PARALLEL,
        help=f"Number of episodes to run concurrently (default: {DEFAULT_PARALLEL})"
    )
    run_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed step-by-step logs"
    )
    run_parser.add_argument(
        "--output",
        type=str,
        help="Output file path for results (default: auto-generated timestamp)"
    )
    run_parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to file"
    )
    run_parser.add_argument(
        "--max-episodes",
        type=int,
        help="Limit total episodes to run (default: all)"
    )
    run_parser.set_defaults(func=cmd_run)
    
    # ========== agentbeats command ==========
    agentbeats_parser = subparsers.add_parser(
        "agentbeats",
        help="Run with AgentBeats (A2A mode)",
        description="Start green agent server to test black-box agents via A2A protocol"
    )
    agentbeats_parser.add_argument(
        "--purple-agent-url",
        default=DEFAULT_PURPLE_AGENT_URL,
        help=f"URL of purple agent (default: {DEFAULT_PURPLE_AGENT_URL})"
    )
    agentbeats_parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_GREEN_AGENT_PORT,
        help=f"Port for green agent server (default: {DEFAULT_GREEN_AGENT_PORT})"
    )
    agentbeats_parser.add_argument(
        "--scenarios",
        nargs="+",
        help="Specific scenarios to run (default: all)"
    )
    agentbeats_parser.add_argument(
        "--parallel",
        type=int,
        default=DEFAULT_PARALLEL,
        help=f"Number of episodes to run concurrently (default: {DEFAULT_PARALLEL})"
    )
    agentbeats_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed step-by-step logs"
    )
    agentbeats_parser.add_argument(
        "--max-episodes",
        type=int,
        help="Limit total episodes to run"
    )
    agentbeats_parser.set_defaults(func=cmd_agentbeats)
    
    # ========== list-scenarios command ==========
    list_parser = subparsers.add_parser(
        "list-scenarios",
        help="List all available scenarios"
    )
    list_parser.set_defaults(func=cmd_list_scenarios)
    
    # Parse and execute
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.command == "run" and "--verbose" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
