"""Benchmark runner for executing multiple episodes in QBench."""

from pathlib import Path

from qbench.agent.base import Agent
from qbench.data_models.result import BenchmarkResult, EpisodeResult, Metrics
from qbench.environment.env import QueueEnv
from qbench.environment.loader import ScenarioLoader
from qbench.io.formatter import ObservationFormatter
from qbench.io.parser import ActionParser
from qbench.runner.episode import EpisodeRunner


class BenchmarkRunner:
    """
    Runs a full benchmark evaluation across multiple scenarios.

    Loads scenarios, runs episodes, and aggregates results.
    """

    def __init__(
        self,
        scenarios_dir: str | Path,
        agent: Agent,
        formatter: ObservationFormatter | None = None,
        parser: ActionParser | None = None
    ):
        """
        Initialize benchmark runner.

        Args:
            scenarios_dir: Path to scenarios directory
            agent: Agent to evaluate
            formatter: Observation formatter (optional)
            parser: Action parser (optional)
        """
        self.scenarios_dir = Path(scenarios_dir)
        self.agent = agent
        self.loader = ScenarioLoader(scenarios_dir)
        self.formatter = formatter or ObservationFormatter()
        self.parser = parser or ActionParser()

    def run_all(
        self,
        scenario_types: list[str] | None = None,
        max_episodes: int | None = None,
        verbose: bool = False
    ) -> BenchmarkResult:
        """
        Run all scenarios (or subset).

        Args:
            scenario_types: List of scenario types to run (None = all)
            max_episodes: Maximum number of episodes to run (None = all)
            verbose: If True, print progress

        Returns:
            BenchmarkResult with aggregated metrics
        """
        # Get scenario types to run
        if scenario_types is None:
            scenario_types = self.loader.list_scenario_types()

        # Collect all seed files
        seed_files = []
        for scenario_type in scenario_types:
            seeds = self.loader.list_scenarios(scenario_type)
            for seed_path in seeds:
                seed_files.append((scenario_type, seed_path))

        # Limit if requested
        if max_episodes:
            seed_files = seed_files[:max_episodes]

        if verbose:
            print(f"Running {len(seed_files)} episodes across {len(scenario_types)} scenario types...")
            print()

        # Run all episodes
        results = []
        for i, (scenario_type, seed_path) in enumerate(seed_files, 1):
            if verbose:
                print(f"[{i}/{len(seed_files)}] {seed_path.stem}...", end=" ")

            # Extract seed number from filename
            seed_number = seed_path.stem.split("_")[-1]

            # Load scenario and run episode
            try:
                config = self.loader.load(seed_path)
                env = QueueEnv(config)

                runner = EpisodeRunner(
                    env=env,
                    agent=self.agent,
                    formatter=self.formatter,
                    parser=self.parser
                )

                result = runner.run(
                    scenario_type=scenario_type,
                    seed_number=seed_number,
                    verbose=False
                )

                results.append(result)

                if verbose:
                    status = "PASS ✓" if result.passed else "FAIL ✗"
                    print(f"{status} (routine_sla={result.metrics.routine_sla:.3f})")

            except Exception as e:
                if verbose:
                    print(f"ERROR: {e}")
                # Skip this episode on error
                continue

        # Aggregate results
        return self._aggregate_results(results)

    def run_scenario_type(
        self,
        scenario_type: str,
        verbose: bool = False
    ) -> BenchmarkResult:
        """
        Run all seeds for a specific scenario type.

        Args:
            scenario_type: Scenario type to run
            verbose: If True, print progress

        Returns:
            BenchmarkResult for this scenario type
        """
        return self.run_all(
            scenario_types=[scenario_type],
            verbose=verbose
        )

    def _aggregate_results(self, results: list[EpisodeResult]) -> BenchmarkResult:
        """
        Aggregate episode results into benchmark result.

        Args:
            results: List of episode results

        Returns:
            BenchmarkResult with aggregated metrics
        """
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

        return BenchmarkResult(
            total_episodes=total,
            passed=passed,
            failed=failed,
            results=results,
            aggregate_metrics=aggregate_metrics,
            pass_rate=pass_rate
        )
