import json
from typing import TypedDict, List
from pydantic import BaseModel
from utils.validator import validate_input as _validate_input, validate_output as _validate_output
from utils.llm import llm_client

class PromptTemplate(BaseModel):
    """
    Prompt template for extracting edge cases.
    """
    template: str = (
        "Requirement:\n{requirement}\n\n"
        "Subtasks:\n{subtasks}\n\n"
        "Identify potential edge cases related to these subtasks. "
        "Respond with a JSON object matching the edge_output schema."
    )

    def render(self, data: dict) -> str:
        return self.template.format(
            requirement=data["requirement"],
            subtasks=json.dumps(data["subtasks"], indent=2)
        )

class EdgeCase(TypedDict):
    id: str
    title: str
    description: str
    related_subtask_ids: List[str]

class EdgeCaseOutput(TypedDict):
    edge_cases: List[EdgeCase]

def validate_input(data: dict) -> dict:
    """
    Validate input payload against edge_input schema.
    """
    return _validate_input("edge_input", data)

def call_llm(validated_input: dict) -> dict:
    """
    Call the LLM to generate edge cases based on requirement and subtasks.
    """
    prompt = PromptTemplate().render(validated_input)
    response = llm_client.chat(messages=[{"role": "user", "content": prompt}])
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected LLM response format: {e}") from e
    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM response is not valid JSON: {e}") from e
    return result

def validate_output(response: dict) -> EdgeCaseOutput:
    """
    Validate the LLM output against edge_output schema.
    """
    return _validate_output("edge_output", response) 