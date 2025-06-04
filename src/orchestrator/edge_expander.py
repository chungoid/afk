import json
import logging
from typing import Any, Dict, List

from backoff import on_exception, expo
from rag.pinecone_client import PineconeClient
from utils.llm import LLMClient
from utils.metrics import Metrics
from utils.error import EdgeExpanderError
from config.prompts.loader import load_prompt_template

logger = logging.getLogger(__name__)

class EdgeExpander:
    """
    EdgeExpander invokes the LLM to generate potential corner cases for a given intent,
    injecting contextual snippets retrieved from a vector store.
    """
    def __init__(
        self,
        llm_client: LLMClient = None,
        rag_client: PineconeClient = None,
        metrics: Metrics = None,
        prompt_name: str = "edge_cases",
        top_k: int = 5
    ):
        self.llm = llm_client or LLMClient()
        self.rag = rag_client or PineconeClient()
        self.metrics = metrics or Metrics()
        self.prompt_template = load_prompt_template(prompt_name)
        self.top_k = top_k

    @on_exception(expo, Exception, max_tries=3, jitter=None)
    def expand(self, intent: Dict[str, Any], request_id: str) -> List[str]:
        """
        Fetches context, formats the prompt, calls the LLM, and parses the result.
        Retries on transient errors.
        """
        try:
            contexts = self._retrieve_context(intent, request_id)
            prompt_text = self._build_prompt(intent, contexts)
            self.metrics.increment("edge_expander.prompt_sent")
            response = self.llm.generate(prompt_text, metadata={"step": "edge_expander", "request_id": request_id})
            self.metrics.increment("edge_expander.prompt_received")
            edge_cases = self._parse_response(response)
            self.metrics.gauge("edge_expander.cases.count", len(edge_cases))
            return edge_cases
        except Exception as e:
            logger.exception("Failed to expand edge cases")
            self.metrics.increment("edge_expander.errors")
            raise EdgeExpanderError("Error expanding edge cases") from e

    def _retrieve_context(self, intent: Dict[str, Any], request_id: str) -> List[str]:
        """
        Queries the vector store for relevant context snippets.
        """
        try:
            query = intent.get("description", "") or intent.get("intent", "")
            snippets = self.rag.query(
                namespace=request_id,
                query_text=query,
                top_k=self.top_k
            )
            return [item["text"] for item in snippets]
        except Exception as e:
            logger.warning("RAG context retrieval failed, proceeding without context", exc_info=e)
            return []

    def _build_prompt(self, intent: Dict[str, Any], contexts: List[str]) -> str:
        """
        Interpolates the prompt template with the intent and context.
        """
        data = {
            "intent": json.dumps(intent, ensure_ascii=False),
            "contexts": "\n".join(contexts)
        }
        try:
            return self.prompt_template.format(**data)
        except KeyError as e:
            logger.error("Prompt template missing placeholder: %s", e)
            raise EdgeExpanderError("Invalid prompt template") from e

    def _parse_response(self, response: str) -> List[str]:
        """
        Parses the LLM response into a list of edge-case strings.
        Supports JSON array or newline-delimited plain text.
        """
        text = response.strip()
        # Try JSON array first
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed]
            except json.JSONDecodeError:
                logger.debug("Response not valid JSON, falling back to line parse")
        # Fallback: split lines
        lines = [line.strip("-* \t") for line in text.splitlines() if line.strip()]
        if not lines:
            raise EdgeExpanderError("LLM returned no edge cases")
        return lines


# module-level default instance for convenience
edge_expander = EdgeExpander()