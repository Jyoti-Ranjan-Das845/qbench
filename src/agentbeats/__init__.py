"""AgentBeats - QBench A2A Integration Package

This package provides Agent-to-Agent (A2A) protocol integration for QBench,
enabling remote evaluation of agents via HTTP/A2A communication.
"""

from agentbeats.models import EvalRequest, EvalResult
from agentbeats.green_executor import GreenExecutor, GreenAgent
from agentbeats.client import send_message
from agentbeats.tool_provider import ToolProvider

__all__ = [
    "EvalRequest",
    "EvalResult",
    "GreenExecutor",
    "GreenAgent",
    "send_message",
    "ToolProvider",
]
