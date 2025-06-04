from dataclasses import dataclass
import json
from typing import Any, Dict
from utils.validator import validate_input as _validate_input, validate_output as _validate_output
from llm_client import llm_client, LLMClientError

@dataclass
class PromptTemplate:
    template: str = (
        "You are an AI assistant. "
        "Given a software requirement, extract the primary intent. "
        "Requirement: {requirement}. "
        "Respond in JSON with a single key 'intent', whose value is a concise statement."
    )

    def format(self, data: Dict[str, Any]) -> str:
        """
        Format the prompt text with the provided data.

        Args:
            data: A dict containing the requirement.

        Returns:
            A string with the formatted prompt.
        """
        return self.template.format(**data)

@dataclass
class Intent:
    intent: str

def validate_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate input payload for step 1 (intent extraction) against JSON schema.

    Args:
        data: The input dictionary to validate.

    Returns:
        The validated input dict.

    Raises:
        ValidatorError: If validation fails.
    """
    return _validate_input("intent_input", data)

def validate_output(response: Dict[str, Any]) -> Intent:
    """
    Validate the LLM response against the intent output schema and convert to Intent.

    Args:
        response: The raw response dict from the LLM.

    Returns:
        An Intent object.

    Raises:
        ValidatorError: If validation fails.
    """
    validated = _validate_output("intent_output", response)
    return Intent(**validated)

def call_llm(validated_input: Dict[str, Any]) -> Intent:
    """
    Call the LLM to extract the intent based on validated input.

    Args:
        validated_input: Input dict after schema validation.

    Returns:
        An Intent object parsed from the LLM response.

    Raises:
        LLMClientError: If the LLM call fails.
        ValidatorError: If response doesn't match the output schema.
    """
    prompt = PromptTemplate().format(validated_input)
    try:
        raw_response = llm_client.generate(prompt)
    except LLMClientError:
        raise
    try:
        response_json = json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise LLMClientError(f"Failed to parse LLM response as JSON: {e}")
    return validate_output(response_json)