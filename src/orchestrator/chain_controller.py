import logging
import time
import hashlib
from typing import List, Dict, Any

from .intent_extractor import IntentExtractor
from .edge_expander import EdgeExpander
from .task_decomposer import TaskDecomposer
from rag.pinecone_client import PineconeClient
from schema.validator import Validator, ValidationError
from publisher.mcp_publisher import MCPPublisher, PublisherError
from utils.metrics import Metrics
from utils.error_types import LLMError, VectorStoreError

class ChainController:
    """
    Orchestrates the multi-step LLM-driven analysis pipeline:
      1. Intent Extraction
      2. Edge-Case Expansion
      3. Task Decomposition
      4. Schema Validation
      5. Publishing tasks to MCP topic "tasks.analysis"
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics = Metrics(namespace="chain_controller")
        self.intent_extractor = IntentExtractor()
        self.edge_expander = EdgeExpander()
        self.task_decomposer = TaskDecomposer()
        self.rag_client = PineconeClient()
        self.validator = Validator(schema_path="config/schema/tasks.schema.json")
        self.publisher = MCPPublisher(topic="tasks.analysis")

    def process_request(self, requirement: str, request_id: str) -> Dict[str, Any]:
        """
        Main entrypoint for the Analysis Agent.
        Returns a summary including counts, errors, and published message IDs.
        """
        start_time = time.time()
        summary = {
            "request_id": request_id,
            "succeeded": 0,
            "failed": 0,
            "errors": [],
            "message_ids": []
        }
        try:
            self.logger.info("Processing request %s", request_id)
            self.metrics.increment("requests_received")

            # Normalize and hash context key
            normalized = requirement.strip()
            context_key = hashlib.sha256((request_id + normalized).encode()).hexdigest()

            # 1. Intent Extraction
            try:
                self.metrics.increment("intent_extraction_calls")
                intent_payload = self.intent_extractor.extract_intent(normalized, request_id)
                self.logger.debug("Extracted intent: %s", intent_payload)
            except Exception as e:
                self.metrics.increment("errors.intent_extraction")
                raise LLMError("Intent extraction failed", e)

            # fetch RAG context before edge expansion
            try:
                self.metrics.increment("rag.fetch_calls")
                rag_snippets = self.rag_client.fetch_context(context_key, top_k=3)
            except Exception as e:
                self.metrics.increment("errors.rag_fetch")
                raise VectorStoreError("RAG context fetch failed", e)

            # 2. Edge-Case Expansion
            try:
                self.metrics.increment("edge_expansion_calls")
                corner_cases = self.edge_expander.expand_edges(intent_payload, rag_snippets)
                self.logger.debug("Corner cases: %s", corner_cases)
            except Exception as e:
                self.metrics.increment("errors.edge_expansion")
                raise LLMError("Edge-case expansion failed", e)

            # 3. Task Decomposition
            try:
                self.metrics.increment("task_decomposition_calls")
                rag_snippets = self.rag_client.fetch_context(context_key, top_k=3)
                tasks = self.task_decomposer.decompose(intent_payload, corner_cases, rag_snippets)
                self.logger.debug("Decomposed tasks: %s", tasks)
            except Exception as e:
                self.metrics.increment("errors.task_decomposition")
                raise LLMError("Task decomposition failed", e)

            valid_tasks = []
            # 4. Schema Validation
            for idx, task in enumerate(tasks):
                try:
                    self.metrics.increment("schema_validation_calls")
                    self.validator.validate(task)
                    valid_tasks.append(task)
                except ValidationError as ve:
                    self.metrics.increment("errors.schema_validation")
                    error_detail = {"task_index": idx, "errors": ve.errors}
                    summary["errors"].append(error_detail)

            # 5. Publish valid tasks
            for task in valid_tasks:
                published = False
                backoff = 1.0
                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        self.metrics.increment("publish_attempts")
                        msg_id = self.publisher.publish(task, idempotency_key=request_id)
                        summary["message_ids"].append(msg_id)
                        published = True
                        break
                    except PublisherError as pe:
                        self.metrics.increment("errors.publish")
                        self.logger.warning("Publish attempt %d failed: %s", attempt, pe)
                        time.sleep(backoff)
                        backoff *= 2
                if not published:
                    summary["errors"].append({
                        "task": task,
                        "error": "Failed to publish after retries"
                    })

            summary["succeeded"] = len(summary["message_ids"])
            summary["failed"] = len(tasks) - summary["succeeded"]

            return summary

        except (LLMError, VectorStoreError, PublisherError) as orchestrator_exc:
            self.logger.error("Orchestration failed for %s: %s", request_id, orchestrator_exc, exc_info=True)
            summary["errors"].append({"error": str(orchestrator_exc)})
            summary["failed"] = len(tasks) if 'tasks' in locals() else 1
            return summary

        finally:
            elapsed = time.time() - start_time
            self.metrics.observe("request_latency_seconds", elapsed)
            self.logger.info("Request %s completed in %.2fs", request_id, elapsed)