import os
import json
import logging
from typing import Any, Dict, List

import json5
import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.rag.pinecone_client import PineconeClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class IntentExtractionError(Exception):
    pass

class IntentExtractor:
    """
    IntentExtractor drives the LLM-based extraction of a canonical intent object
    from a raw requirement string, optionally enriching with RAG-based context.
    """
    def __init__(self,
                 pinecone_client: PineconeClient = None,
                 prompt_path: str = None):
        self.pinecone_client = pinecone_client or PineconeClient()
        self.prompt_path = prompt_path or os.getenv("INTENT_PROMPT_PATH", "config/prompts/intent.json5")
        self.prompt_config = self._load_prompt_template()
        openai.api_key = os.getenv("LLM_API_KEY")

    def _load_prompt_template(self) -> Dict[str, Any]:
        try:
            with open(self.prompt_path, "r") as f:
                return json5.load(f)
        except Exception as e:
            logger.error(f"Failed to load intent prompt template from {self.prompt_path}: {e}")
            raise IntentExtractionError(f"Prompt load failure: {e}")

    def _preprocess(self, text: str) -> str:
        # simple normalization: trim whitespace; extendable for markup stripping
        return text.strip()

    def _retrieve_context(self, request_id: str, top_k: int = 3) -> List[str]:
        try:
            return self.pinecone_client.query_context(request_id, top_k=top_k)
        except Exception as e:
            logger.warning(f"Context retrieval failed (continuing without RAG): {e}")
            return []

    @retry(retry=retry_if_exception_type(openai.error.RateLimitError),
           wait=wait_exponential(multiplier=1, min=1, max=10),
           stop=stop_after_attempt(3))
    def _call_llm(self, messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: int) -> str:
        try:
            resp = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def extract_intent(self, requirement: str, request_id: str) -> Dict[str, Any]:
        """
        Main entrypoint: returns a dict matching the canonical intent schema.
        """
        cleaned = self._preprocess(requirement)
        contexts = self._retrieve_context(request_id)
        system_msg = self.prompt_config.get("system_instructions", "You are a helpful assistant.")
        template = self.prompt_config.get("template", "")
        try:
            prompt_text = template.format(requirement=cleaned, context="\n".join(contexts))
        except Exception as e:
            logger.error(f"Prompt formatting failed: {e}")
            raise IntentExtractionError(f"Prompt formatting error: {e}")

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt_text}
        ]

        model = self.prompt_config.get("model", "gpt-4")
        temperature = self.prompt_config.get("temperature", 0.0)
        max_tokens = self.prompt_config.get("max_tokens", 512)

        try:
            raw_output = self._call_llm(messages, model, temperature, max_tokens)
        except Exception as e:
            raise IntentExtractionError(f"LLM extraction failed: {e}")

        try:
            intent_obj = json.loads(raw_output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM output: {e}\nOutput was: {raw_output}")
            raise IntentExtractionError(f"Invalid JSON output: {e}")

        # Optionally attach metadata
        metadata = {
            "request_id": request_id,
            "raw_response": raw_output
        }
        return {"intent": intent_obj, "metadata": metadata}