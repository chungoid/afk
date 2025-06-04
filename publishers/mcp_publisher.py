import logging
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import mcp_use
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

PUBLISH_SUCCESS_COUNTER = Counter(
    "mcp_publish_success_total",
    "Total number of successful publishes to MCP",
    ["topic"]
)
PUBLISH_FAILURE_COUNTER = Counter(
    "mcp_publish_failure_total",
    "Total number of failed publishes to MCP",
    ["topic"]
)
PUBLISH_LATENCY_SECONDS = Histogram(
    "mcp_publish_latency_seconds",
    "Latency of MCP publish calls in seconds",
    ["topic"]
)

@dataclass
class PublicationResult:
    topic: str
    success: bool
    message: str
    error: Optional[Exception] = None

class McpPublisher:
    """
    McpPublisher is responsible for publishing validated tasks to the MCP messaging layer.
    It supports retries, error logging, and metrics instrumentation.
    """

    def __init__(
        self,
        topic: str = "tasks.analysis",
        client: Optional[Any] = None,
        retry_attempts: int = 3,
        wait_min_seconds: int = 1,
        wait_max_seconds: int = 10
    ):
        self.topic = topic
        self.client = client or mcp_use.Client()
        self.retry_attempts = retry_attempts
        self.wait_min_seconds = wait_min_seconds
        self.wait_max_seconds = wait_max_seconds

    @retry(
        stop=stop_after_attempt(lambda self: self.retry_attempts),
        wait=wait_exponential(multiplier=1, min=lambda self: self.wait_min_seconds, max=lambda self: self.wait_max_seconds),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def _publish_with_retry(self, key: str, payload: str) -> None:
        """
        Internal method that attempts to publish a message to MCP with retry logic.
        """
        self.client.publish(topic=self.topic, key=key, payload=payload)

    def publish(self, task: BaseModel) -> PublicationResult:
        """
        Publish a Pydantic task model to the configured MCP topic.
        Returns a PublicationResult indicating success or failure.
        """
        payload = task.json()
        key = getattr(task, "id", None) or str(uuid.uuid4())
        start_time = time.time()
        try:
            self._publish_with_retry(key=key, payload=payload)
            elapsed = time.time() - start_time
            PUBLISH_LATENCY_SECONDS.labels(topic=self.topic).observe(elapsed)
            PUBLISH_SUCCESS_COUNTER.labels(topic=self.topic).inc()
            logger.info("Successfully published task to %s with key %s", self.topic, key)
            return PublicationResult(topic=self.topic, success=True, message="Published successfully")
        except Exception as exc:
            elapsed = time.time() - start_time
            PUBLISH_LATENCY_SECONDS.labels(topic=self.topic).observe(elapsed)
            PUBLISH_FAILURE_COUNTER.labels(topic=self.topic).inc()
            logger.error("Failed to publish task to %s with key %s: %s", self.topic, key, exc, exc_info=True)
            return PublicationResult(
                topic=self.topic,
                success=False,
                message=f"Publish failed: {exc}",
                error=exc
            )