import os
import json
import importlib
import logging
from pathlib import Path

import openai

from analysis_agent.utils.validator import validate, ValidationError
from analysis_agent.utils.mcp_publisher import publish_tasks, PublishError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Orchestrator:
    def __init__(
        self,
        steps: list[str] = None,
        templates_dir: Path = None,
        schemas_dir: Path = None,
    ):
        self.steps = steps or ["intent_extraction", "requirement_decomposition"]
        base_dir = Path(__file__).parent
        project_root = base_dir.parent.parent
        self.templates_dir = templates_dir or project_root / "prompts"
        self.schemas_dir = schemas_dir or project_root / "schemas"

        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise RuntimeError("Environment variable OPENAI_API_KEY must be set")

    def run(self, user_input: str) -> list[dict]:
        context: dict = {"input_text": user_input}

        for step in self.steps:
            logger.info(f"Starting prompt step: {step}")
            try:
                module = importlib.import_module(f"analysis_agent.prompt_steps.{step}")
            except ModuleNotFoundError as e:
                logger.error(f"Prompt step module not found: {step}")
                raise

            try:
                step_output = module.run(context, self.templates_dir)
            except Exception as e:
                logger.exception(f"Error running prompt step '{step}': {e}")
                raise

            schema_name = self._schema_name_for_step(step)
            logger.info(f"Validating output of '{step}' with schema '{schema_name}'")
            try:
                validate(step_output, schema_name)
            except ValidationError as e:
                logger.error(f"Schema validation failed for step '{step}': {e}")
                raise

            context.update(step_output)

        tasks = context.get("tasks")
        if tasks is None:
            logger.error("Final context missing 'tasks' key")
            raise ValueError("Expected 'tasks' in final output")
        if not isinstance(tasks, list):
            logger.error("Final 'tasks' output is not a list")
            raise ValueError("Final output 'tasks' must be a list")

        logger.info("Validating final tasks against schema 'task'")
        try:
            validate(tasks, "task")
        except ValidationError as e:
            logger.error(f"Final tasks schema validation failed: {e}")
            raise

        logger.info("Publishing tasks via MCP")
        try:
            publish_tasks(tasks)
        except PublishError as e:
            logger.error(f"Failed to publish tasks: {e}")
            raise

        logger.info("Orchestration complete, tasks published successfully")
        return tasks

    def _schema_name_for_step(self, step: str) -> str:
        mapping = {
            "intent_extraction": "intent",
            "requirement_decomposition": "decomposition",
        }
        return mapping.get(step, step)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run the Analysis Agent orchestrator")
    parser.add_argument("input", help="Input text to analyze")
    args = parser.parse_args()

    orchestrator = Orchestrator()
    tasks = orchestrator.run(args.input)
    print(json.dumps(tasks, indent=2))


if __name__ == "__main__":
    main()