import json
import logging
from pathlib import Path
from typing import Any, Dict

import jsonschema
from jsonschema import Draft7Validator


class ValidationError(Exception):
    """Raised when data does not conform to a JSON schema."""
    pass


_schemas: Dict[str, Draft7Validator] = {}


def _load_schemas() -> None:
    """
    Load all JSON schema files from the project's schemas directory
    and compile them into Draft7Validator instances.
    """
    # Determine the project root (assumes this file is at src/analysis_agent/utils)
    project_root = Path(__file__).parents[3]
    schemas_dir = project_root / "schemas"
    if not schemas_dir.is_dir():
        raise RuntimeError(f"Schemas directory not found: {schemas_dir}")

    for schema_path in schemas_dir.glob("*.json"):
        try:
            with schema_path.open("r", encoding="utf-8") as f:
                raw_schema = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in schema file {schema_path}: {e}") from e

        try:
            validator = Draft7Validator(raw_schema)
        except jsonschema.exceptions.SchemaError as e:
            raise RuntimeError(f"Invalid JSON Schema in file {schema_path}: {e}") from e

        schema_name = schema_path.stem
        _schemas[schema_name] = validator
        logging.debug(f"Loaded JSON schema '{schema_name}' from {schema_path}")


_load_schemas()


def validate(data: Any, schema_name: str) -> None:
    """
    Validate a Python object against a named JSON schema.

    Args:
        data: The data to validate (typically a dict or list).
        schema_name: The basename (without .json) of the schema to use.

    Raises:
        ValidationError: If the named schema is not found or data fails validation.
    """
    if schema_name not in _schemas:
        available = ", ".join(sorted(_schemas.keys()))
        raise ValidationError(f"Schema '{schema_name}' not found. Available schemas: {available}")

    validator = _schemas[schema_name]
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)

    if errors:
        messages = []
        for error in errors:
            path = ".".join(str(p) for p in error.path) or "<root>"
            messages.append(f"{path}: {error.message}")
        detail = "; ".join(messages)
        raise ValidationError(f"Validation failed for schema '{schema_name}': {detail}")