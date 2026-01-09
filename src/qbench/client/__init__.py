"""A2A client utilities for QBench.

This module provides client-side utilities for communicating with
QBench green agents via the A2A protocol.
"""

from qbench.client.a2a_client import send_eval_request, get_agent_info

__all__ = [
    "send_eval_request",
    "get_agent_info",
]
