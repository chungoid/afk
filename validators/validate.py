from pathlib import Path
import json
import importlib
from typing import Any, Type
from jsonschema import validate as jsonschema_validate, ValidationError as JsonSchemaValidationError
from pydantic import BaseModel, ValidationError as PydanticValidationError

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
MODELS_MODULE = "validators.models"

class ValidationError(Exception):
    """
    Unified validation error for JSON Schema and Pydantic model validation.
    errors: list of error details from JSON Schema or Pydantic
    """
    def __init__(self, errors: Any):
        super().__init__("Validation failed")
        self.errors = errors

def _load_json_schema(schema_name: str) -> dict:
    schema_file = SCHEMA_DIR / f"{schema_name}.schema.json"
    if not schema_file.exists():
        raise FileNotFoundError(f"JSON Schema file not found: {schema_file}")
    with open(schema_file, "r", encoding="utf-8") as f:
        return json.load(f)

def _get_model_class(schema_name: str) -> Type[BaseModel]:
    try:
        module = importlib.import_module(MODELS_MODULE)
    except ImportError as e:
        raise ImportError(f"Could not import models module '{MODELS_MODULE}': {e}") from e
    class_name = "".join(part.capitalize() for part in schema_name.split("_"))
    model_class = getattr(module, class_name, None)
    if model_class is None:
        raise ImportError(f"Pydantic model '{class_name}' not found in '{MODELS_MODULE}'")
    if not issubclass(model_class, BaseModel):
        raise TypeError(f"{class_name} is not a subclass of pydantic.BaseModel")
    return model_class

def validate(schema_name: str, data: dict) -> BaseModel:
    """
    Validate the given data against the JSON Schema and Pydantic model for schema_name.

    Args:
        schema_name: Name of the schema/model (without extension or suffix).
        data: The raw dict to validate.

    Returns:
        An instance of the corresponding Pydantic model.

    Raises:
        ValidationError: Aggregated validation errors from JSON Schema or Pydantic.
        FileNotFoundError: If the JSON Schema file is missing.
        ImportError: If the Pydantic model cannot be imported.
        TypeError: If the imported model is not a BaseModel subclass.
    """
    errors = []
    # 1. JSON Schema validation
    try:
        schema = _load_json_schema(schema_name)
        jsonschema_validate(instance=data, schema=schema)
    except FileNotFoundError:
        # No JSON Schema to validate against, skip
        pass
    except JsonSchemaValidationError as e:
        errors.append({
            "type": "jsonschema",
            "message": e.message,
            "validator": e.validator,
            "path": list(e.path),
        })
    # 2. Pydantic model validation
    model_class = _get_model_class(schema_name)
    model_instance = None
    try:
        model_instance = model_class.parse_obj(data)
    except PydanticValidationError as e:
        for err in e.errors():
            errors.append({
                "type": "pydantic",
                "loc": err.get("loc"),
                "msg": err.get("msg"),
                "type_detail": err.get("type"),
            })
    # Raise if any errors encountered
    if errors:
        raise ValidationError(errors)
    return model_instance