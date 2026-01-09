from agentbeats.client import send_message

# Optional import for rate limiting
try:
    from agentbeats.rate_limiter import RequestQueueManager
except ImportError:
    RequestQueueManager = None


class ToolProvider:
    def __init__(self, queue_manager: 'RequestQueueManager | None' = None):
        """Initialize ToolProvider with optional rate limiting.

        Args:
            queue_manager: Optional RequestQueueManager for rate-limited requests.
                          If None, requests are made directly without rate limiting.
        """
        self._context_ids = {}
        self._queue_manager = queue_manager

    async def talk_to_agent(self, message: str, url: str, new_conversation: bool = False):
        """
        Communicate with another agent by sending a message and receiving their response.

        Args:
            message: The message to send to the agent
            url: The agent's URL endpoint
            new_conversation: If True, start fresh conversation; if False, continue existing conversation

        Returns:
            str: The agent's response message
        """
        # If queue manager is provided, submit request through rate limiter
        if self._queue_manager:
            # Create request function
            async def make_request():
                outputs = await send_message(
                    message=message,
                    base_url=url,
                    context_id=None if new_conversation else self._context_ids.get(url, None)
                )
                if outputs.get("status", "completed") != "completed":
                    raise RuntimeError(f"{url} responded with: {outputs}")
                self._context_ids[url] = outputs.get("context_id", None)
                return outputs["response"]

            # Submit through queue manager (rate limited)
            return await self._queue_manager.submit_request(
                make_request,
                request_id=f"{url.split(':')[-1]}"  # Use port as simple ID
            )

        else:
            # Direct request (no rate limiting) - original behavior
            outputs = await send_message(
                message=message,
                base_url=url,
                context_id=None if new_conversation else self._context_ids.get(url, None)
            )
            if outputs.get("status", "completed") != "completed":
                raise RuntimeError(f"{url} responded with: {outputs}")
            self._context_ids[url] = outputs.get("context_id", None)
            return outputs["response"]

    def reset(self):
        """Reset all cached context IDs."""
        self._context_ids = {}

    def reset_context(self, url: str) -> None:
        """
        Reset context ID for a specific agent URL.

        Args:
            url: The agent URL to reset
        """
        if url in self._context_ids:
            del self._context_ids[url]
