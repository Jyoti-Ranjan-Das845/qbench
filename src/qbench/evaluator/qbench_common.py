"""Common models and utilities for QBench AgentBeats integration."""

import asyncio
import json
import logging
import time
from typing import Optional

from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from pydantic import BaseModel

from agentbeats.tool_provider import ToolProvider
from qbench.agent.base import Agent

logger = logging.getLogger(__name__)


# Task instructions sent to purple agent at the start of each episode
QBENCH_TASK_PROMPT = """
You are being evaluated on an ONLINE QUEUE MANAGEMENT task (QueueOps-Bench).

You control a real-time scheduling system where tasks arrive over time and must be scheduled into limited-capacity slots. At each step you will receive a QUEUE STATUS snapshot (a state report). Your job is to return valid JSON actions to manage the queue.

========================
QUEUE STATUS FORMAT
========================
Every step message contains ALL of the following sections (always present; empty sections show "none"):

1) HEADER
   "QUEUE STATUS — Step t of H"
   - t = current time step
   - H = episode horizon (total steps)

2) CAPACITY
   "CAPACITY: K slots per step"
   - Each step has slot_index in [0..K-1]
   - Capacity constraints apply per step

3) NEW ARRIVALS
   Tasks that arrived at the current step.
   Each task shows: id, priority (URGENT/ROUTINE), arrived, deadline.

4) CANCELLATIONS
   Task IDs cancelled by the environment at the current step (not agent-initiated).

5) PENDING TASKS
   All tasks currently waiting to be scheduled.
   Each task shows: id, priority, arrived, deadline.

6) SCHEDULED TASKS
   All tasks assigned to specific slots.
   Each scheduled task shows: id, slot [step, slot_index], priority, arrived, deadline.
   A task completes when the current time reaches its scheduled step.

7) COMPLETED THIS STEP
   Task IDs that completed at this step.

8) MISSED THIS STEP
   Task IDs that missed their deadline at this step.
   - Routine misses are a soft penalty.
   - Urgent misses cause a hard failure.

You will NOT be shown future arrivals/cancellations/capacity changes or the episode seed.

You may compute:
- slack = deadline - t
- waiting = t - arrived

========================
ALLOWED ACTIONS (JSON)
========================
Return either:
- a single JSON action object, OR
- a JSON list of action objects

Allowed actions:

1) schedule
   Assign a pending task to a step:
   {"type":"schedule","task_id":"t1","step":5}

2) reschedule
   Move an already scheduled task to a new step:
   {"type":"reschedule","task_id":"t2","step":8}

3) reject
   Refuse a ROUTINE task only:
   {"type":"reject","task_id":"r3"}

4) cancel
   Agent-initiated cancellation of a task you previously scheduled:
   {"type":"cancel","task_id":"t4"}

5) noop
   Do nothing:
   {"type":"noop"}

========================
HARD CONSTRAINTS (PASS/FAIL)
========================
An episode FAILS if any hard constraint is violated at any time:

1) Urgent SLA miss: an urgent task is not completed by its deadline
2) Urgent reject: rejecting an urgent task is forbidden
3) Overcapacity: more than K tasks scheduled in the same step
4) Double booking: two tasks assigned to the same slot [step, slot_index]
5) Invalid action: malformed JSON, unknown action type, invalid task_id, out-of-range step, or wrong task state

The episode runs to the fixed horizon; violations are recorded and evaluated at the end.

========================
SOFT METRICS (RANKING AMONG PASSING RUNS)
========================
Computed only if the run PASSes:

1) Routine SLA (primary): % routine tasks completed on-time
2) Average wait time: mean(completed_time - arrived)
3) Average backlog: mean(pending_count per step)
4) Max backlog: max(pending_count per step)
5) Average utilization: mean(slots_used / capacity_per_step)

Return JSON actions for each QUEUE STATUS snapshot.
""".strip()


class A2AAgentWrapper(Agent):
    """
    Adapts an A2A purple agent to the qbench.Agent interface.

    This allows remote A2A-compatible agents to be evaluated by QBench
    without needing to implement QBench-specific code.
    """

    def __init__(self, url: str, tool_provider: ToolProvider):
        """
        Initialize the A2A agent wrapper.

        Args:
            url: The purple agent's A2A endpoint URL
            tool_provider: ToolProvider instance for A2A communication
        """
        self.url = url
        self.tool_provider = tool_provider

    def act(self, observation_text: str) -> str:
        """
        Send observation to purple agent via A2A and get actions response.

        Args:
            observation_text: Formatted observation from ObservationFormatter

        Returns:
            Agent's response containing actions (JSON or text format)
        """
        # Track timing for this agent call
        start_time = time.time()
        logger.info(f"[TIMING] Sending request to purple agent at {self.url}")

        # Retry logic for agent crashes
        max_retries = 3
        retry_delay = 2.0  # seconds

        for attempt in range(max_retries):
            try:
                # Use asyncio to call the async tool_provider method
                # Always use new_conversation=True for stateless operation
                # Try to get existing event loop, otherwise create new one
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    # No event loop running, create new one
                    loop = None

                if loop is not None:
                    # We're in an async context, need to run in executor
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self.tool_provider.talk_to_agent(
                                message=observation_text,
                                url=self.url,
                                new_conversation=True
                            )
                        )
                        response = future.result()
                else:
                    # No event loop, safe to use asyncio.run()
                    response = asyncio.run(
                        self.tool_provider.talk_to_agent(
                            message=observation_text,
                            url=self.url,
                            new_conversation=True
                        )
                    )

                elapsed = time.time() - start_time
                logger.info(f"[TIMING] Purple agent response received in {elapsed:.2f}s")
                return response

            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"[ERROR] Agent call failed (attempt {attempt + 1}/{max_retries}) after {elapsed:.2f}s: {e}")

                if attempt < max_retries - 1:
                    logger.info(f"[RETRY] Waiting {retry_delay}s before retry...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"[ERROR] All {max_retries} attempts failed. Returning noop action.")
                    # Return a safe noop action as fallback
                    return json.dumps({"type": "noop", "error": f"Agent unreachable: {str(e)}"})


class QBenchMetrics(BaseModel):
    """QBench evaluation metrics."""
    pass_rate: float
    passed_episodes: int
    failed_episodes: int
    total_episodes: int
    routine_sla: Optional[float] = None
    avg_wait_time: Optional[float] = None
    avg_backlog: Optional[float] = None
    max_backlog: Optional[int] = None
    avg_utilization: Optional[float] = None


def qbench_evaluator_agent_card(name: str, url: str) -> AgentCard:
    """
    Create the agent card for the QBench evaluator.

    Args:
        name: Agent name
        url: Agent's A2A endpoint URL

    Returns:
        AgentCard with QBench evaluator metadata
    """
    skill = AgentSkill(
        id="queue_management_evaluation",
        name="Queue Management Agent Evaluation",
        description="Evaluates agents on online queue management tasks with dynamic load, limited capacity, and strict deadlines",
        tags=["benchmark", "queue-management", "scheduling", "resource-allocation"],
        examples=[
            '''{"participants": {"agent": "http://localhost:9019"}, "config": {"max_episodes": 10, "scenario_types": ["late_burst_slack_trap"]}}''',
            '''{"participants": {"agent": "http://localhost:9019"}, "config": {"max_episodes": 20}}''',
            '''{"participants": {"agent": "http://localhost:9019"}, "config": {"scenario_types": ["capacity_cliff", "urgent_flood"], "max_episodes": 15}}'''
        ]
    )

    return AgentCard(
        name=name,
        description="QBench - Queue Management Benchmark for AI Agents. Evaluates agents on 105 scenarios across 35 challenge types including urgent task handling, capacity management, deadline pressure, and dynamic load patterns.",
        url=url,
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )
