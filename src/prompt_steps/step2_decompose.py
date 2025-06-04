from typing import Any, Dict, List, TypedDict
from utils.validator import validate_input as _validate_input, validate_output as _validate_output, ValidatorError
from utils.llm import llm_client

class Subtask(TypedDict):
    id: str
    title: str
    description: str
    metadata: Dict[str, Any]
    dependencies: List[str]

class DecomposeOutput(TypedDict):
    subtasks: List[Subtask]

class PromptTemplate:
    """
    Defines the prompt template for decomposing a requirement into subtasks.
    """
    template: str = (
        "You are an expert software engineer. "
        "Given the following high-level requirement, break it down into a list of subtasks. "
        "Each subtask should have an id, title, description, metadata, and dependencies.\n\n"
        "Requirement:\n{requirement}\n\n"
        "Return JSON with the key 'subtasks' containing an array of subtasks."
    )

    def format(self, inputs: Dict[str, Any]) -> str:
        """
        Formats the template with the provided inputs.

        Args:
            inputs: A dict containing keys required by the template.

        Returns:
            A fully formatted prompt string.
        """
        return self.template.format(**inputs)

def validate_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates input payload against the decompose_input schema.

    Args:
        data: The raw input payload.

    Returns:
        The validated input dict.

    Raises:
        ValidatorError: If validation fails.
    """
    return _validate_input("decompose_input", data)

def call_llm(validated_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls the LLM client with the formatted decomposition prompt.

    Args:
        validated_input: The validated input payload.

    Returns:
        Raw response dict from the LLM.

    Raises:
        Exception: Propagates errors from the LLM client.
    """
    prompt = PromptTemplate().format(validated_input)
    response = llm_client.generate(prompt)
    if not isinstance(response, dict):
        raise RuntimeError(f"LLM client returned unexpected type: {type(response)}")
    return response

def validate_output(response: Dict[str, Any]) -> DecomposeOutput:
    """
    Validates the LLM response against the decompose_output schema.

    Args:
        response: The raw LLM response dict.

    Returns:
        A DecomposeOutput TypedDict with validated subtasks.

    Raises:
        ValidatorError: If output validation fails.
    """
    validated = _validate_output("decompose_output", response)
    return validated  # type: ignore[arg-type]