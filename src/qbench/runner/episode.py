"""Episode runner for executing single episodes in QBench."""

import time

from qbench.agent.base import Agent
from qbench.data_models.result import EpisodeResult, Metrics
from qbench.data_models.violation import Violation
from qbench.environment.env import QueueEnv
from qbench.io.formatter import ObservationFormatter
from qbench.io.parser import ActionParser
from qbench.metrics.accumulator import MetricsAccumulator
from qbench.validation.checker import ConstraintChecker
from qbench.validation.validator import ActionValidator

# Import task prompt - used for A2A agents, optional for others
try:
    from qbench.evaluator.qbench_common import QBENCH_TASK_PROMPT
except ImportError:
    # Fallback if qbench_common not available (standalone mode)
    QBENCH_TASK_PROMPT = None


class EpisodeRunner:
    """
    Runs a single episode of QBench evaluation.

    Orchestrates the interaction between:
    - QueueEnv (environment)
    - Agent (being tested)
    - ActionValidator (validates actions)
    - ConstraintChecker (checks hard constraints)
    - MetricsAccumulator (tracks soft metrics)
    """

    def __init__(
        self,
        env: QueueEnv,
        agent: Agent,
        formatter: ObservationFormatter | None = None,
        parser: ActionParser | None = None
    ):
        """
        Initialize episode runner.

        Args:
            env: QueueEnv instance (already initialized with seed)
            agent: Agent instance to evaluate
            formatter: Observation formatter (creates default if None)
            parser: Action parser (creates default if None)
        """
        self.env = env
        self.agent = agent
        self.formatter = formatter or ObservationFormatter()
        self.parser = parser or ActionParser()

        # Validators and checkers
        self.validator = ActionValidator()
        self.checker = ConstraintChecker()

        # Metrics accumulator
        self.metrics = MetricsAccumulator()

        # Violation tracking
        self.violations = []
        self.failed = False  # Absorbing state

    def run(
        self,
        scenario_type: str | None = None,
        seed_number: str | None = None,
        verbose: bool = False,
        runtime_dir: str | None = None
    ) -> EpisodeResult:
        """
        Run a complete episode.

        Args:
            scenario_type: Optional scenario type identifier
            seed_number: Optional seed number identifier
            verbose: If True, print progress
            runtime_dir: Optional directory to save step-by-step logs

        Returns:
            EpisodeResult with PASS/FAIL status, violations, and metrics
        """
        import json
        from pathlib import Path

        start_time = time.time()

        # Reset environment
        obs = self.env.reset()

        # Main loop
        done = False
        step_count = 0

        # Track steps for logging
        step_logs = [] if runtime_dir else None

        while not done:
            if verbose:
                print(f"Step {obs.time}/{obs.horizon}...", end=" ")

            # 1. Format observation for agent
            obs_text = self.formatter.format(obs)

            # Prepend task instructions on every step (for stateless A2A agents)
            if QBENCH_TASK_PROMPT is not None:
                obs_text = QBENCH_TASK_PROMPT + "\n\n" + obs_text

            # 2. Get agent actions
            response = ""
            actions = []
            step_violations = []
            try:
                response = self.agent.act(obs_text)
                actions = self.parser.parse(response)
            except Exception as e:
                # If agent crashes or returns unparseable response, treat as invalid action
                violation = Violation(
                    time=obs.time,
                    type="invalid_action",
                    details={"reason": "agent_error", "error": str(e)}
                )
                self.violations.append(violation)
                step_violations.append(violation)
                self.failed = True
                actions = []  # Continue with no actions

            # 3. Validate and apply actions
            for action in actions:
                env_state = self._get_env_state()
                is_valid, violation = self.validator.validate(
                    action, env_state, obs.time
                )

                if not is_valid:
                    # Record violation
                    self.violations.append(violation)
                    step_violations.append(violation)
                    self.failed = True
                    if verbose:
                        print(f"VIOLATION: {violation}")
                else:
                    # Apply action to environment
                    self.env._apply_action(action)

            # 4. Check hard constraints
            env_state = self._get_env_state()
            constraint_violations = self.checker.check(env_state, obs.time)
            if constraint_violations:
                self.violations.extend(constraint_violations)
                step_violations.extend(constraint_violations)
                self.failed = True
                if verbose:
                    for v in constraint_violations:
                        print(f"VIOLATION: {v}")

            # 5. Log step data (if runtime_dir provided)
            if step_logs is not None:
                step_log = {
                    "step": obs.time,
                    "observation": obs_text,
                    "agent_response": response,
                    "parsed_actions": [
                        {
                            "type": action.type,
                            "task_id": getattr(action, 'task_id', None),
                            "step": getattr(action, 'step', None),
                            "slot_index": getattr(action, 'slot_index', None)
                        }
                        for action in actions
                    ],
                    "violations": [v.model_dump() for v in step_violations],
                    "state_after": {
                        "pending_count": len(self.env.pending),
                        "scheduled_count": len(self.env.scheduled),
                        "completed_count": len(self.env.completed),
                        "missed_count": len(self.env.missed),
                        "rejected_count": len(self.env.rejected)
                    }
                }
                step_logs.append(step_log)

            # 6. Record metrics for this step
            self.metrics.record_step(
                pending_count=len(self.env.pending),
                scheduled_count=len(self.env.scheduled),
                capacity=self.env.capacity_per_step
            )

            # 7. Step environment
            obs, done = self.env.act([])  # Actions already applied

            step_count += 1

            if verbose:
                print(f"OK" if not self.failed else f"FAILED")

        # Finalize metrics
        final_metrics = self.metrics.finalize(
            schedule=self.env.schedule,
            horizon=self.env.horizon,
            capacity=self.env.capacity_per_step
        )

        # Compute summary
        summary = {
            "total_tasks": len(self.env.tasks),
            "completed": len(self.env.completed),
            "rejected": len(self.env.rejected),
            "missed": len(self.env.missed),
            "cancelled": len(self.env.cancelled),
            "pending_at_end": len(self.env.pending),
            "steps": step_count
        }

        execution_time = time.time() - start_time

        # Save step logs if runtime_dir provided
        if runtime_dir and step_logs:
            runtime_path = Path(runtime_dir)
            steps_file = runtime_path / "steps.json"
            steps_data = {
                "scenario_type": scenario_type,
                "seed_number": seed_number,
                "total_steps": step_count,
                "passed": not self.failed,
                "steps": step_logs
            }
            with open(steps_file, 'w') as f:
                json.dump(steps_data, f, indent=2)

        # Create result
        result = EpisodeResult(
            passed=not self.failed,
            violations=self.violations,
            metrics=final_metrics,
            summary=summary,
            scenario_type=scenario_type,
            seed_number=seed_number,
            execution_time=execution_time
        )

        if verbose:
            print(f"\n{result}")

        return result

    def _get_env_state(self) -> dict:
        """
        Extract current environment state for validation and checking.

        Returns:
            Dictionary with environment state
        """
        return {
            "tasks": self.env.tasks,
            "pending": self.env.pending,
            "scheduled": self.env.scheduled,
            "schedule": self.env.schedule,
            "capacity_per_step": self.env.capacity_per_step,
            "horizon": self.env.horizon
        }
