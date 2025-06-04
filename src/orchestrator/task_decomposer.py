import os
import json
import json5
import logging
import time
from pathlib import Path
from typing import List, Dict, Any

from schema.validator import Validator
from utils.llm_client import LLMClient
from utils.errors import LLMServiceError, SchemaValidationError

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROMPT_PATH = BASE_DIR / "config" / "prompts" / "decompose.json5"
SCHEMA_PATH = BASE_DIR / "config" / "schema" / "tasks.schema.json"

class TaskDecomposer:
    """
    TaskDecomposer uses an LLM to turn a high-level intent and edge cases into
    an array of discrete task drafts, then validates them against a schema.
    """

    def __init__(self,
                 llm_client: LLMClient = None,
                 validator: Validator = None,
                 prompt_path: Path = None,
                 schema_path: Path = None):
        self.llm = llm_client or LLMClient()
        self.validator = validator or Validator(schema_path or SCHEMA_PATH)
        self.prompt_template = self._load_prompt(prompt_path or PROMPT_PATH)

    def _load_prompt(self, path: Path) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json5.load(f)
            template = data.get("template") or data.get("prompt") or json.dumps(data)
            return template
        except Exception as e:
            logger.exception("Failed to load prompt template from %s", path)
            raise

    def decompose(self,
                  intent: Dict[str, Any],
                  edge_cases: List[str],
                  context_snippets: List[str],
                  request_id: str = None,
                  max_retries: int = 2,
                  retry_backoff: float = 1.0
                  ) -> List[Dict[str, Any]]:
        """
        Performs task decomposition:
        1. Renders prompt
        2. Calls LLM
        3. Parses JSON output
        4. Validates each task draft
        Returns list of validated task dicts or raises on error.
        """
        prompt = self._render_prompt(intent, edge_cases, context_snippets)
        last_error = None
        for attempt in range(1, max_retries + 2):
            try:
                logger.debug("TaskDecomposer attempt %d prompt: %s", attempt, prompt)
                response = self.llm.chat(prompt)
                tasks = self._parse_response(response)
                validated = [self._validate_task(task) for task in tasks]
                return validated
            except (LLMServiceError, SchemaValidationError, json.JSONDecodeError) as e:
                last_error = e
                logger.warning("Decompose attempt %d failed: %s", attempt, e)
                if attempt <= max_retries:
                    time.sleep(retry_backoff * attempt)
                    continue
                logger.error("All decompose attempts failed for request_id=%s", request_id)
                raise last_error

    def _render_prompt(self,
                       intent: Dict[str, Any],
                       edge_cases: List[str],
                       context_snippets: List[str]) -> str:
        try:
            rendered = self.prompt_template.format(
                intent=json.dumps(intent, ensure_ascii=False),
                edge_cases=json.dumps(edge_cases, ensure_ascii=False),
                context=json.dumps(context_snippets, ensure_ascii=False)
            )
            return rendered
        except Exception as e:
            logger.exception("Failed to render prompt template")
            raise

    def _parse_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Expects LLM response with a JSON array of task objects in `content`.
        """
        content = response.get("content", "").strip()
        try:
            tasks = json.loads(content)
            if not isinstance(tasks, list):
                raise ValueError("LLM response is not a list")
            return tasks
        except json.JSONDecodeError as e:
            logger.exception("Failed to decode LLM JSON response: %s", content)
            raise

    def _validate_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs schema validation on a single task draft.
        Raises SchemaValidationError on failure.
        """
        try:
            self.validator.validate(task)
            task["_schema_valid"] = True
            return task
        except Exception as e:
            logger.exception("Schema validation failed for task: %s", task)
            raise SchemaValidationError(errors=e, data=task)

# Example usage for chain controller integration:
# decomposer = TaskDecomposer()
# tasks = decomposer.decompose(intent_obj, edge_list, context_list, request_id="1234")