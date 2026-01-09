"""A2A client for sending evaluation requests to green agent."""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger("qbench.client.a2a")


async def send_eval_request(
    green_agent_url: str,
    purple_agent_url: str,
    scenarios: list[str],
    seeds: list[int],
    parallel: int = 1,
    timeout: int = 300,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Send an evaluation request to the green agent via A2A protocol.

    Args:
        green_agent_url: URL of the green agent (e.g., "http://localhost:9018")
        purple_agent_url: URL of the purple agent to test (e.g., "http://localhost:9019")
        scenarios: List of scenario names to evaluate
        seeds: List of seed indices to use
        parallel: Number of parallel workers
        timeout: Timeout per episode in seconds
        verbose: Enable verbose logging

    Returns:
        Evaluation results dictionary

    Raises:
        ImportError: If a2a-sdk not installed
        Exception: If communication fails
    """
    try:
        import httpx
        from a2a.client import A2AClient, A2ACardResolver
        from a2a.types import (
            JSONRPCErrorResponse,
            Message,
            MessageSendParams,
            Part,
            Role,
            SendMessageRequest,
            SendMessageSuccessResponse,
            TextPart,
        )
    except ImportError as e:
        raise ImportError(
            "A2A SDK required for remote mode. Install with:\n"
            "  pip install a2a-sdk\n"
            "or:\n"
            "  uv pip install a2a-sdk"
        ) from e

    logger.info(f"Sending evaluation request to green agent at {green_agent_url}")
    logger.info(f"Testing purple agent at {purple_agent_url}")
    logger.info(f"Scenarios: {len(scenarios)}, Seeds: {len(seeds)}, Total episodes: {len(scenarios) * len(seeds)}")

    # Build EvalRequest (use evaluator-compatible keys)
    eval_request = {
        "participants": {
            "agent": purple_agent_url
        },
        "config": {
            "scenario_types": scenarios,  # Evaluator expects "scenario_types"
            "seeds": seeds,
            "parallel": parallel,
            "timeout": timeout,
            "verbose": verbose
        }
    }

    # Get agent card
    async with httpx.AsyncClient(timeout=120.0) as httpx_client:
        try:
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=green_agent_url)
            agent_card = await resolver.get_agent_card()

            if agent_card is None:
                raise Exception(f"Could not get agent card from {green_agent_url}")

            logger.info(f"Connected to green agent: {agent_card.name if hasattr(agent_card, 'name') else 'Unknown'}")

            # Create A2A client
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

            # Create message
            message_id = uuid.uuid4().hex
            request_id = uuid.uuid4().hex

            message = Message(
                role=Role.user,
                parts=[Part(root=TextPart(text=json.dumps(eval_request)))],
                message_id=message_id,
            )

            params = MessageSendParams(message=message)
            request = SendMessageRequest(id=request_id, params=params)

            # Send request
            logger.info("Sending evaluation request...")
            if verbose:
                logger.info(f"Request: {json.dumps(eval_request, indent=2)}")

            response = await client.send_message(request=request)

            # Parse response
            if not response or not response.root:
                raise Exception("Empty response from green agent")

            if isinstance(response.root, JSONRPCErrorResponse):
                raise Exception(f"Error response from green agent: {response.root}")

            if not isinstance(response.root, SendMessageSuccessResponse):
                raise Exception(f"Unexpected response type from green agent: {type(response.root)}")

            logger.info("Evaluation complete, processing results...")

            # Extract results from response
            # The green agent should return results as artifacts
            # Pass the unwrapped success response (response.root)
            results = await _extract_results_from_response(response.root)

            return results

        except httpx.HTTPError as e:
            raise Exception(f"HTTP error communicating with green agent: {e}") from e
        except Exception as e:
            raise Exception(f"Failed to communicate with green agent: {e}") from e


async def _extract_results_from_response(response) -> Dict[str, Any]:
    """
    Extract evaluation results from A2A response.

    The green agent returns results as artifacts with DataPart.

    Args:
        response: SendMessageSuccessResponse from A2A (response.root from SendMessageResponse)

    Returns:
        Results dictionary
    """
    try:
        # Check if response has artifacts
        if hasattr(response.result, 'artifacts') and response.result.artifacts:
            for artifact in response.result.artifacts:
                if hasattr(artifact, 'parts') and artifact.parts:
                    for part in artifact.parts:
                        # Look for DataPart with results
                        if hasattr(part, 'root') and hasattr(part.root, 'data'):
                            return part.root.data
                        # Also try TextPart with JSON
                        elif hasattr(part, 'root') and hasattr(part.root, 'text'):
                            try:
                                return json.loads(part.root.text)
                            except json.JSONDecodeError:
                                pass

        # Fallback: try to parse from message parts
        if hasattr(response.result, 'message') and hasattr(response.result.message, 'parts'):
            for part in response.result.message.parts:
                if hasattr(part, 'root') and hasattr(part.root, 'text'):
                    try:
                        return json.loads(part.root.text)
                    except json.JSONDecodeError:
                        pass

        # If we get here, couldn't extract results
        logger.warning("Could not extract results from response, returning raw response")
        return {
            "error": "Could not parse results from green agent response",
            "raw_response": str(response)
        }

    except Exception as e:
        logger.error(f"Error extracting results: {e}")
        return {
            "error": f"Failed to extract results: {e}",
            "raw_response": str(response)
        }


async def get_agent_info(agent_url: str) -> Optional[Dict[str, Any]]:
    """
    Get agent card information from an A2A agent.

    Args:
        agent_url: Agent URL

    Returns:
        Agent card as dictionary, or None if failed
    """
    try:
        import httpx
        from a2a.client import A2ACardResolver
    except ImportError:
        logger.error("a2a-sdk not installed")
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resolver = A2ACardResolver(httpx_client=client, base_url=agent_url)
            card = await resolver.get_agent_card()

            if card:
                return {
                    "name": getattr(card, 'name', 'Unknown'),
                    "description": getattr(card, 'description', ''),
                    "version": getattr(card, 'version', ''),
                    "url": getattr(card, 'url', agent_url),
                }
    except Exception as e:
        logger.error(f"Failed to get agent info from {agent_url}: {e}")

    return None
