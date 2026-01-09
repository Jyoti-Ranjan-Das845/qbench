"""Pluggable rate limiter for controlling request rates to agents.

This module provides a pluggable rate limiting architecture that can be easily
swapped with different rate limiting strategies.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)


class RateLimiterBase(ABC):
    """Abstract base class for rate limiters.

    Subclass this to implement different rate limiting strategies
    (RPM, token bucket, leaky bucket, etc.)
    """

    @abstractmethod
    async def acquire(self) -> None:
        """Wait until a request slot is available according to rate limit."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset the rate limiter state."""
        pass


class RPMLimiter(RateLimiterBase):
    """Requests Per Minute (RPM) rate limiter.

    Enforces a fixed number of requests per minute by spacing them evenly.
    Example: 50 RPM = 1 request every 1.2 seconds
    """

    def __init__(self, requests_per_minute: int):
        """Initialize RPM limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.delay_between_requests = 60.0 / requests_per_minute  # seconds
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

        logger.info(
            f"[RATE LIMITER] Initialized: {requests_per_minute} RPM "
            f"({self.delay_between_requests:.2f}s between requests)"
        )

    async def acquire(self) -> None:
        """Wait until next request slot is available."""
        async with self._lock:
            now = time.time()
            time_since_last = now - self.last_request_time

            if time_since_last < self.delay_between_requests:
                wait_time = self.delay_between_requests - time_since_last
                logger.debug(f"[RATE LIMITER] Waiting {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()

    def reset(self) -> None:
        """Reset the rate limiter state."""
        self.last_request_time = 0.0
        logger.info("[RATE LIMITER] Reset")


class RequestQueueManager:
    """Manages a request queue with pluggable rate limiting.

    Processes requests in FIFO order while enforcing rate limits.
    Requests are function calls that return awaitable results.
    """

    def __init__(self, rate_limiter: RateLimiterBase):
        """Initialize queue manager with rate limiter.

        Args:
            rate_limiter: Rate limiter instance to control request rate
        """
        self.rate_limiter = rate_limiter
        self.queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._running = False

        logger.info("[QUEUE MANAGER] Initialized")

    async def start(self) -> None:
        """Start the queue processing worker."""
        if self._running:
            logger.warning("[QUEUE MANAGER] Already running")
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("[QUEUE MANAGER] Started worker")

    async def stop(self) -> None:
        """Stop the queue processing worker."""
        if not self._running:
            return

        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("[QUEUE MANAGER] Stopped worker")

    async def submit_request(
        self,
        request_fn: Callable[[], Awaitable[Any]],
        request_id: str | None = None
    ) -> Any:
        """Submit a request to the queue and wait for response.

        Args:
            request_fn: Async function to call (makes the actual request)
            request_id: Optional ID for logging

        Returns:
            Result from request_fn
        """
        # Create future for response
        response_future: asyncio.Future = asyncio.Future()

        # Add to queue
        await self.queue.put((request_fn, response_future, request_id))

        if request_id:
            logger.debug(f"[QUEUE MANAGER] Queued request: {request_id}")

        # Wait for response
        return await response_future

    async def _process_queue(self) -> None:
        """Process requests from queue with rate limiting (FIFO order)."""
        logger.info("[QUEUE MANAGER] Processing queue...")

        while self._running:
            try:
                # Get next request from queue
                request_fn, response_future, request_id = await self.queue.get()

                if request_id:
                    logger.debug(f"[QUEUE MANAGER] Processing request: {request_id}")

                try:
                    # Wait for rate limit
                    await self.rate_limiter.acquire()

                    # Execute request
                    result = await request_fn()

                    # Set response
                    if not response_future.done():
                        response_future.set_result(result)

                    if request_id:
                        logger.debug(f"[QUEUE MANAGER] Completed request: {request_id}")

                except Exception as e:
                    # Set exception on future
                    if not response_future.done():
                        response_future.set_exception(e)

                    logger.error(f"[QUEUE MANAGER] Request failed: {e}")

                finally:
                    self.queue.task_done()

            except asyncio.CancelledError:
                logger.info("[QUEUE MANAGER] Worker cancelled")
                break
            except Exception as e:
                logger.error(f"[QUEUE MANAGER] Worker error: {e}")
                await asyncio.sleep(1)  # Avoid tight loop on errors

        logger.info("[QUEUE MANAGER] Worker stopped")

    @property
    def queue_size(self) -> int:
        """Get current queue size."""
        return self.queue.qsize()
