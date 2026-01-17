"""GPT-5.2 purple agent for QBench with AgentBeats (A2A protocol)."""

import os
import logging
import subprocess
import time
import uvicorn
from litellm import completion

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentSkill, AgentCapabilities
from a2a.utils import new_agent_text_message

from gpt52_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class GPT52AgentExecutor(AgentExecutor):
    """
    GPT-5.2 based purple agent for queue management.

    Uses OpenAI's GPT-5.2 model via litellm to make queue management decisions.
    Communicates with QBench green agent via A2A protocol.
    """

    def __init__(self, model: str = "gpt-5.2-2025-12-11", temperature: float = 1.0):
        """
        Initialize GPT-5.2 agent executor.

        Args:
            model: OpenAI model name (default: gpt-5.2-2025-12-11)
            temperature: Sampling temperature for LLM (default: 1.0, required by GPT-5.2)

        Raises:
            ValueError: If OPENAI_API_KEY environment variable is not set
        """
        self.model = model
        self.temperature = temperature
        self.api_key = os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set. "
                "Please set it before running the agent."
            )

        logger.info(f"Initialized GPT-5.2 agent executor with model: {model}")

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Execute a task (receive observation, return actions via GPT-5.2).

        Args:
            context: Request context containing the observation
            event_queue: Event queue to publish response

        Returns:
            None (publishes response to event_queue)
        """
        # Get observation from context
        observation_text = context.get_user_input()

        try:
            # Call GPT-5.2 via litellm
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": observation_text}
                ],
                temperature=self.temperature,
                api_key=self.api_key
            )

            # Extract response
            llm_response = response.choices[0].message.content
            logger.info(f"GPT-5.2 response: {llm_response[:100]}...")

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # Return empty actions on error
            llm_response = '{"type": "noop"}'

        # Publish response to event queue
        response_message = new_agent_text_message(
            llm_response,
            context_id=context.context_id
        )
        await event_queue.enqueue_event(response_message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Cancel a running task.

        Args:
            context: Request context
            event_queue: Event queue to publish cancellation status
        """
        # For QBench, cancellation is handled by the environment
        # This is a no-op implementation as required by AgentExecutor
        pass


def create_agent_card(base_url: str) -> AgentCard:
    """Create agent card for A2A protocol."""
    return AgentCard(
        name="GPT52PurpleAgent",
        description="GPT-5.2 based purple agent for QBench queue management",
        url=base_url,
        version="0.1.0",
        capabilities=AgentCapabilities(),
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[
            AgentSkill(
                id="queue_management",
                name="queue_management",
                description="Manage task queue with GPT-5.2 driven scheduling decisions",
                tags=["scheduling", "queue", "gpt-5.2", "llm"]
            )
        ]
    )


def kill_process_on_port(port: int) -> None:
    """Kill any process using the specified port and wait for release."""
    try:
        # Find process using the port
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                print(f"Killing existing process on port {port} (PID: {pid})...")
                subprocess.run(["kill", "-9", pid], check=True)
                print(f"Process {pid} killed")

            # Wait for port to be released
            print(f"Waiting for port {port} to be released...")
            time.sleep(2)

            # Verify port is free
            check_result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True
            )
            if check_result.stdout.strip():
                print(f"Warning: Port {port} still in use, waiting longer...")
                time.sleep(2)
            else:
                print(f"Port {port} is now free")
        else:
            print(f"No existing process found on port {port}")
    except Exception as e:
        print(f"Note: Could not check/kill existing process: {e}")


def main():
    """Run the GPT-5.2 purple agent server."""
    import argparse

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="GPT-5.2 Purple Agent for QBench")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind the server")
    parser.add_argument("--port", type=int, default=9019, help="Port to bind the server")
    parser.add_argument("--card-url", type=str, help="Agent card URL (optional, for compatibility)")
    args = parser.parse_args()

    PORT = args.port
    HOST = args.host

    # Kill any existing process on this port
    kill_process_on_port(PORT)

    # Create executor
    executor = GPT52AgentExecutor()

    # Create request handler
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore()
    )

    # Create agent card
    # Use HOST:PORT for agent card URL (works in Docker and locally)
    card = create_agent_card(f"http://{HOST}:{PORT}")

    # Create app
    a2a_app = A2AStarletteApplication(
        agent_card=card,
        http_handler=request_handler
    )

    # Build the Starlette app
    app = a2a_app.build()

    print(f"Starting GPT-5.2 purple agent on {HOST}:{PORT}...")
    print(f"Agent URL: http://{HOST}:{PORT}")
    print(f"Model: {executor.model}, Temperature: {executor.temperature}")

    # Run server
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
