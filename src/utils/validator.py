from pathlib import Path
import json
from jsonschema import Draft7Validator
from typing import Any, Dict

class ValidatorError(Exception):
    """Exception raised when JSON schema validation fails."""
    def __init__(self, schema_name: str, message: str):
        self.schema_name = schema_name
        self.message = message
        super().__init__(f"Schema '{schema_name}' validation error: {message}")

def _load_schemas() -> Dict[str, Dict[str, Any]]:
    """Load all JSON schemas from the schemas directory."""
    schemas: Dict[str, Dict[str, Any]] = {}
    base_dir = Path(__file__).resolve().parents[1] / "schemas"
    if not base_dir.is_dir():
        raise RuntimeError(f"Schemas directory not found at {base_dir}")
    for path in base_dir.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                schemas[path.stem] = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in schema file {path}: {e}")
    return schemas

_SCHEMAS = _load_schemas()

def _validate(name: str, payload: Any) -> Any:
    """Validate a payload against a named JSON schema."""
    schema = _SCHEMAS.get(name)
    if schema is None:
        raise ValidatorError(name, f"Schema '{name}' not found")
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        error = errors[0]
        path = ".".join(str(p) for p in error.absolute_path) or "<root>"
        raise ValidatorError(name, f"At '{path}': {error.message}")
    return payload

def validate_input(name: str, payload: Any) -> Any:
    """
    Validate payload as input against the specified schema.
    Raises ValidatorError on validation failure.
    """
    return _validate(name, payload)

def validate_output(name: str, payload: Any) -> Any:
    """
    Validate payload as output against the specified schema.
    Raises ValidatorError on validation failure.
    """
    return _validate(name, payload)