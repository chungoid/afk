from pathlib import Path
import json
import logging
import os
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape
import openai

logger = logging.getLogger(__name__)

class PromptError(Exception):
    """Raised when an error occurs during the requirement decomposition prompt step."""

def run(input: Dict[str, Any], templates_dir: Path) -> Dict[str, Any]:
    """
    Execute the requirement decomposition prompt step.

    Args:
        input: Context from the previous step.
        templates_dir: Directory containing prompt templates.

    Returns:
        Parsed JSON output from the LLM as a dictionary.

    Raises:
        PromptError: For template rendering, LLM call, or JSON parsing failures.
    """
    try:
        env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape()
        )
        template = env.get_template("02_requirement_decomposition.jinja2")
        prompt = template.render(input)
        logger.debug("Rendered prompt for requirement decomposition: %s", prompt)
    except Exception as e:
        logger.error("Template rendering error", exc_info=True)
        raise PromptError(f"Template rendering error: {e}") from e

    try:
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        logger.debug("Received LLM response: %s", content)
    except Exception as e:
        logger.error("LLM API call failed", exc_info=True)
        raise PromptError(f"LLM API error: {e}") from e

    try:
        output = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("JSON decoding failed", exc_info=True)
        raise PromptError(f"Invalid JSON response: {e}\nResponse content: {content}") from e

    if not isinstance(output, dict):
        logger.error("Parsed JSON is not a dictionary: %s", type(output))
        raise PromptError(f"Expected JSON object but got {type(output).__name__}")

    return output