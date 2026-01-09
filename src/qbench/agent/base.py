"""Base agent interface for QBench."""

from abc import ABC, abstractmethod


class Agent(ABC):
    """
    Base interface for QBench agents.

    All agents (whether standalone or via AgentBeats) must implement this interface.

    **For Standalone Usage:**
    Extend this class and implement the act() method to test your agent with QBench.

    Example:
        ```python
        from qbench import Agent, run_qbench
        import json

        class MyAgent(Agent):
            def act(self, observation_text: str) -> str:
                # Your logic here
                obs = json.loads(observation_text)
                actions = {"assign": [], "reject": [], "cancel": []}
                # ... decision logic ...
                return json.dumps(actions)

        # Run evaluation
        results = run_qbench(agent=MyAgent(), parallel=10, verbose=True)
        ```
    """

    @abstractmethod
    def act(self, observation_text: str) -> str:
        """
        Receive observation and return actions.

        Args:
            observation_text: Formatted observation from the environment.
                Can be JSON string containing:
                {
                    "time": int,
                    "queue": [...],        # Currently assigned tasks
                    "pending": [...],      # Tasks awaiting assignment
                    "capacity": int
                }

        Returns:
            String containing actions (JSON or text format).
            Will be parsed by ActionParser.

        Example JSON response:
            {
                "assign": [
                    {"task_id": "r1", "step": 5}
                ],
                "reject": ["r2"],
                "cancel": ["r3"]
            }

        Example text response:
            schedule t1 at step 5
            reject t2

        Note:
            - Return valid JSON or parseable text format
            - Follow task constraints (valid_time_range, capacity, etc.)
            - Routine tasks must complete within valid_time_range for 100% SLA
        """
        pass


class RandomAgent(Agent):
    """
    Simple random agent for testing.

    Makes random valid decisions.
    """

    def __init__(self, seed: int | None = None):
        """Initialize random agent."""
        import random
        self.random = random.Random(seed)

    def act(self, observation_text: str) -> str:
        """Return noop (minimal agent for testing)."""
        return '{"type": "noop"}'


class GreedyAgent(Agent):
    """
    Simple greedy agent that schedules tasks ASAP.

    Schedules pending tasks to the nearest available slot.
    """

    def __init__(self):
        """Initialize greedy agent."""
        pass

    def act(self, observation_text: str) -> str:
        """
        Greedy scheduling strategy.

        For each pending task, schedule to the earliest available slot.
        """
        # Parse observation (this is a simplified implementation)
        # In practice, the agent would parse the text observation

        # For now, return noop (this is a placeholder)
        # A real implementation would parse observation_text and generate actions
        return '{"type": "noop"}'
