"""Minimal GPT-5.2 agent for QBench standalone mode."""

import os
import logging
from litellm import completion

from qbench import Agent
from .prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class GPT52Agent(Agent):
    """
    Simple GPT-5.2 agent for queue management.

    Uses litellm to call GPT-5.2 and returns raw LLM responses.
    """

    def __init__(self, model: str = "gpt-5.2-2025-12-11", temperature: float = 1.0):
        """
        Initialize GPT-5.2 agent.

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

        logger.info(f"Initialized GPT-5.2 agent with model: {model}")

    def act(self, observation_text: str) -> str:
        """
        Receive observation and return actions via LLM.

        Args:
            observation_text: Formatted observation from environment

        Returns:
            LLM response as string (will be parsed by QBench)
        """
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

            # Extract and return response
            llm_response = response.choices[0].message.content
            return llm_response

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # Return empty actions on error
            return '{"assign": [], "reject": [], "cancel": []}'
