import os
import json
from typing import List, Optional, Any, Dict
import logging

import openai
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from validators.validate import validate
from validators.models import IntentData

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class PromptChainError(Exception):
    """Custom exception for prompt chain errors."""
    pass

class AnalysisPromptChain:
    """
    Encapsulates the multi-step LLM prompting and decomposition logic.
    Methods:
        extract_intent(raw_requirement: str) -> IntentData
        decompose(intent: IntentData) -> List[Dict[str, Any]]
    """
    def __init__(
        self,
        llm_api_key: Optional[str] = None,
        model: str = "gpt-4",
        template_dir: Optional[str] = None,
        system_prompt: str = "You are an expert analysis assistant."
    ):
        if llm_api_key:
            openai.api_key = llm_api_key
        if not openai.api_key:
            raise PromptChainError("OpenAI API key must be provided either via llm_api_key or environment")
        self.model = model
        self.system_prompt = system_prompt
        base_dir = template_dir or os.path.join(os.path.dirname(__file__), "prompt_templates")
        if not os.path.isdir(base_dir):
            raise PromptChainError(f"Template directory not found: {base_dir}")
        self.env = Environment(
            loader=FileSystemLoader(base_dir),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )

    def extract_intent(self, raw_requirement: str) -> IntentData:
        """
        Extract the user's intent from a raw requirement string.
        Returns an IntentData Pydantic model.
        """
        try:
            template = self.env.get_template("intent_extraction.j2")
        except TemplateNotFound as e:
            logger.error("Intent extraction template not found")
            raise PromptChainError("Missing intent_extraction.j2 template") from e

        prompt = template.render(requirement=raw_requirement)
        logger.debug("Extract intent prompt: %s", prompt)
        response_content = self._call_llm(prompt)
        try:
            data = json.loads(response_content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from intent extraction response: %s", response_content)
            raise PromptChainError("Invalid JSON in intent extraction response") from e

        try:
            intent = validate("intent", data)
        except Exception as e:
            logger.error("Intent validation failed: %s", e)
            raise PromptChainError("Intent data validation error") from e
        return intent

    def decompose(self, intent: IntentData, context: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Decompose an intent into a list of raw task dicts.
        Optional context can be provided to inform decomposition.
        """
        try:
            template = self.env.get_template("decomposition_step.j2")
        except TemplateNotFound as e:
            logger.error("Decomposition template not found")
            raise PromptChainError("Missing decomposition_step.j2 template") from e

        prompt = template.render(intent=intent.dict(), context=context or [])
        logger.debug("Decompose prompt: %s", prompt)
        response_content = self._call_llm(prompt)
        try:
            tasks = json.loads(response_content)
            if not isinstance(tasks, list):
                raise PromptChainError("Decomposition response is not a list")
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from decomposition response: %s", response_content)
            raise PromptChainError("Invalid JSON in decomposition response") from e

        return tasks

    def _call_llm(self, prompt: str) -> str:
        """
        Internal helper to call the OpenAI chat completion API.
        Returns the assistant response as a string.
        """
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            content = response.choices[0].message.content.strip()
            logger.debug("LLM response: %s", content)
            return content
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            raise PromptChainError("LLM call failed") from e