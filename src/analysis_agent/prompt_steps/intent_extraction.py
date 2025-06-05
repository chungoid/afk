import json
import logging
from pathlib import Path
from typing import Any, Dict
import openai
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger(__name__)

class IntentExtractionError(Exception):
    """Raised when intent extraction step fails."""

def run(input: Dict[str, Any], templates_dir: Path) -> Dict[str, Any]:
    """
    Run the intent extraction prompt step.
    Renders the intent extraction template, calls the LLM, and parses the JSON result.

    Args:
        input: Context dictionary for prompt rendering.
        templates_dir: Path to the directory containing Jinja2 prompt templates.

    Returns:
        A dictionary representing the extracted intents.

    Raises:
        IntentExtractionError: On template load error, LLM call failure, invalid JSON, or unexpected structure.
    """
    try:
        env = Environment(loader=FileSystemLoader(str(templates_dir)))
        template = env.get_template("01_intent_extraction.jinja2")
    except TemplateNotFound as e:
        msg = f"Intent extraction template not found: {e.name}"
        logger.error(msg)
        raise IntentExtractionError(msg) from e

    try:
        prompt = template.render(input)
        logger.debug("Rendered intent extraction prompt: %s", prompt)
    except Exception as e:
        msg = f"Error rendering template: {e}"
        logger.error(msg)
        raise IntentExtractionError(msg) from e

    try:
        # Use OpenAI v1.x compatible API
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
        )
        logger.debug("LLM API response: %s", response)
    except Exception as e:
        msg = f"LLM invocation failed: {e}"
        logger.error(msg)
        raise IntentExtractionError(msg) from e

    try:
        content = response.choices[0].message.content
        logger.debug("LLM response content: %s", content)
    except Exception as e:
        msg = f"Unexpected LLM response structure: {e}"
        logger.error(msg)
        raise IntentExtractionError(msg) from e

    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        msg = f"Response is not valid JSON: {e.msg}"
        logger.error(msg)
        raise IntentExtractionError(msg) from e

    if not isinstance(result, dict):
        msg = f"Expected JSON object for intent extraction, got {type(result).__name__}"
        logger.error(msg)
        raise IntentExtractionError(msg)

    return result