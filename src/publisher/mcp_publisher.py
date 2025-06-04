import os
import time
import json
import logging
from typing import Any, Dict, List, Optional

from utils.metrics import MetricsClient
from utils.errors import TransientError, PermanentError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PublisherError(Exception):
    """Base exception for publisher errors."""

class MCPPublisher:
    """
    MCPPublisher publishes validated tasks to the MCP 'tasks.analysis' topic.
    Retries on transient failures, logs metrics for publish attempts.
    """
    def __init__(
        self,
        topic: Optional[str] = None,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        initial_backoff: float = 1.0
    ):
        self.topic = topic or os.getenv("MCP_ANALYSIS_TOPIC", "tasks.analysis")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.initial_backoff = initial_backoff
        self.metrics = MetricsClient()
        # credentials loaded via environment by underlying MCP client
        from mcp_use import MCPClient  # assumed installed library
        self.client = MCPClient()

    def publish(self, task: Dict[str, Any], request_id: str) -> str:
        """
        Publish a single task to the analysis topic.
        Attaches request_id for idempotency.
        Returns the message ID on success.
        Raises PublisherError on permanent failure.
        """
        payload = {
            "request_id": request_id,
            "task": task
        }
        body = json.dumps(payload)
        headers = {"request_id": request_id}
        attempt = 0
        backoff = self.initial_backoff
        while attempt <= self.max_retries:
            try:
                start = time.time()
                message_id = self.client.publish(
                    topic=self.topic,
                    body=body,
                    headers=headers
                )
                latency = time.time() - start
                self.metrics.record_timer("mcp.publish.latency", latency)
                self.metrics.increment_counter("mcp.publish.success")
                logger.info(f"Published task id={task.get('id')} msg_id={message_id}")
                return message_id
            except TransientError as te:
                attempt += 1
                self.metrics.increment_counter("mcp.publish.retry")
                logger.warning(
                    f"Transient error publishing task id={task.get('id')} attempt={attempt}/{self.max_retries}: {te}"
                )
                if attempt > self.max_retries:
                    self.metrics.increment_counter("mcp.publish.failure")
                    raise PublisherError(f"Max retries exceeded for task {task.get('id')}") from te
                time.sleep(backoff)
                backoff *= self.backoff_factor
            except PermanentError as pe:
                self.metrics.increment_counter("mcp.publish.failure")
                logger.error(f"Permanent error publishing task id={task.get('id')}: {pe}")
                raise PublisherError(f"Permanent failure for task {task.get('id')}") from pe
            except Exception as e:
                self.metrics.increment_counter("mcp.publish.failure")
                logger.exception(f"Unexpected error publishing task id={task.get('id')}")
                raise PublisherError(f"Unexpected error for task {task.get('id')}: {e}") from e

    def publish_all(self, tasks: List[Dict[str, Any]], request_id: str) -> Dict[str, Any]:
        """
        Publish all validated tasks. Returns a summary dict:
          {
            "published": [message_id, ...],
            "failed": [{"task_id": ..., "error": ...}, ...]
          }
        """
        summary = {"published": [], "failed": []}
        for task in tasks:
            try:
                msg_id = self.publish(task, request_id)
                summary["published"].append(msg_id)
            except PublisherError as e:
                summary["failed"].append({
                    "task_id": task.get("id"),
                    "error": str(e)
                })
        return summary

if __name__ == "__main__":
    # example usage
    import uuid
    request_id = str(uuid.uuid4())
    sample_tasks = [{"id": "t1", "description": "do X"}, {"id": "t2", "description": "do Y"}]
    publisher = MCPPublisher()
    result = publisher.publish_all(sample_tasks, request_id)
    print(json.dumps(result, indent=2))