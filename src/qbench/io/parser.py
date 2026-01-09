"""Action parser for converting agent responses to Action objects."""

import json
import re
from typing import Any

from pydantic import ValidationError

from qbench.data_models.action import Action


class ActionParser:
    """
    Parses agent responses into Action objects.

    Supports:
    - JSON array format: [{"type": "schedule", "task_id": "t1", "step": 5}, ...]
    - JSON object format: {"type": "schedule", "task_id": "t1", "step": 5}
    - Text format with action commands

    Returns InvalidActionError if response is unparseable.
    """

    def parse(self, response: str) -> list[Action]:
        """
        Parse agent response into list of actions.

        Args:
            response: Agent's response string

        Returns:
            List of Action objects

        Raises:
            ValueError: If response cannot be parsed
        """
        # Try JSON parsing first
        try:
            return self._parse_json(response)
        except (json.JSONDecodeError, ValueError):
            pass

        # Try text parsing
        try:
            return self._parse_text(response)
        except ValueError:
            pass

        # If all parsing fails, raise error
        raise ValueError(f"Could not parse response: {response[:200]}...")

    def _parse_json(self, response: str) -> list[Action]:
        """
        Parse JSON-formatted response.

        Accepts:
        - Array: [{"type": "schedule", ...}, ...]
        - Object: {"type": "schedule", ...}
        - Object with "actions" key: {"actions": [...]}
        """
        data = json.loads(response)

        # Handle different JSON structures
        if isinstance(data, list):
            actions_data = data
        elif isinstance(data, dict):
            if "actions" in data:
                actions_data = data["actions"]
            else:
                # Single action object
                actions_data = [data]
        else:
            raise ValueError("JSON must be object or array")

        # Parse each action
        actions = []
        for action_dict in actions_data:
            try:
                action = Action(**action_dict)
                actions.append(action)
            except ValidationError as e:
                raise ValueError(f"Invalid action format: {e}")

        return actions if actions else [Action(type="noop")]

    def _parse_text(self, response: str) -> list[Action]:
        """
        Parse text-formatted response.

        Expected formats:
        - "schedule t1 at step 5"
        - "reject t2"
        - "reschedule t3 to step 7"
        - "cancel t4"
        - "noop"

        Multiple actions can be on separate lines.
        """
        actions = []
        lines = response.strip().split("\n")

        for line in lines:
            line = line.strip().lower()
            if not line or line.startswith("#"):
                continue

            # Try to match action patterns
            action = self._parse_text_line(line)
            if action:
                actions.append(action)

        return actions if actions else [Action(type="noop")]

    def _parse_text_line(self, line: str) -> Action | None:
        """Parse a single line of text into an Action."""
        # Noop
        if "noop" in line or "no-op" in line or "nothing" in line:
            return Action(type="noop")

        # Schedule: "schedule t1 at step 5" or "schedule t1 5"
        match = re.search(
            r"schedule\s+(\S+)\s+(?:at\s+step\s+)?(\d+)",
            line
        )
        if match:
            task_id = match.group(1)
            step = int(match.group(2))
            return Action(type="schedule", task_id=task_id, step=step)

        # Reschedule: "reschedule t1 to step 7" or "reschedule t1 7"
        match = re.search(
            r"reschedule\s+(\S+)\s+(?:to\s+step\s+)?(\d+)",
            line
        )
        if match:
            task_id = match.group(1)
            step = int(match.group(2))
            return Action(type="reschedule", task_id=task_id, step=step)

        # Reject: "reject t2"
        match = re.search(r"reject\s+(\S+)", line)
        if match:
            task_id = match.group(1)
            return Action(type="reject", task_id=task_id)

        # Cancel: "cancel t3"
        match = re.search(r"cancel\s+(\S+)", line)
        if match:
            task_id = match.group(1)
            return Action(type="cancel", task_id=task_id)

        # If no match, ignore this line
        return None

    def parse_safe(self, response: str) -> list[Action]:
        """
        Parse response and return noop if parsing fails.

        This is a safe version that doesn't raise exceptions.

        Args:
            response: Agent's response string

        Returns:
            List of Action objects, or [noop] if parsing fails
        """
        try:
            return self.parse(response)
        except (ValueError, Exception):
            # If parsing fails, return noop
            return [Action(type="noop")]
