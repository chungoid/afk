import json
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type

import jsonschema
from jsonschema import Draft7Validator, ValidationError as JsonSchemaValidationError

try:
    from google.protobuf.json_format import ParseDict, MessageConversionError
    from google.protobuf.message import Message as ProtoMessage
except ImportError:
    ParseDict = None
    MessageConversionError = None
    ProtoMessage = None

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class SchemaValidationError(Exception):
    """
    Exception raised when schema validation fails.
    Contains a list of structured error messages.
    """
    def __init__(self, errors: List[Dict[str, Any]]):
        super().__init__("Schema validation failed")
        self.errors = errors

class SchemaValidator:
    """
    Validates Python dicts against a JSON Schema or Protobuf message schema.
    """

    DEFAULT_JSON_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "config" / "schema" / "tasks.schema.json"

    def __init__(
        self,
        json_schema_path: Optional[Path] = None,
        proto_message_cls: Optional[Type[ProtoMessage]] = None
    ):
        """
        :param json_schema_path: Path to JSON Schema file.
        :param proto_message_cls: Protobuf message class to validate against.
        """
        self.json_schema_path = json_schema_path or self.DEFAULT_JSON_SCHEMA_PATH
        self._json_schema = None
        self._json_validator = None
        self.proto_message_cls = proto_message_cls
        self._load_json_schema()

    def _load_json_schema(self) -> None:
        if not self.json_schema_path.exists():
            msg = f"JSON Schema file not found at {self.json_schema_path}"
            logger.error(msg)
            raise FileNotFoundError(msg)
        with open(self.json_schema_path, 'r', encoding='utf-8') as f:
            self._json_schema = json.load(f)
        self._json_validator = Draft7Validator(self._json_schema)
        logger.debug("Loaded JSON Schema from %s", self.json_schema_path)

    def validate_json(self, obj: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate a dict against the loaded JSON Schema.
        :returns: (is_valid, errors)
        """
        errors: List[Dict[str, Any]] = []
        for err in self._json_validator.iter_errors(obj):
            error_detail = {
                "message": err.message,
                "path": list(err.absolute_path),
                "schema_path": list(err.absolute_schema_path)
            }
            errors.append(error_detail)
        is_valid = not errors
        if is_valid:
            logger.debug("JSON validation succeeded")
        else:
            logger.warning("JSON validation failed with %d errors", len(errors))
        return is_valid, errors

    def validate_proto(self, obj: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate a dict by parsing it into a Protobuf message.
        :returns: (is_valid, errors)
        """
        if self.proto_message_cls is None or ParseDict is None:
            msg = "Protobuf validation requested but no proto_message_cls provided or protobuf libraries not available"
            logger.error(msg)
            raise RuntimeError(msg)
        try:
            message: ProtoMessage = self.proto_message_cls()
            ParseDict(obj, message)
            logger.debug("Protobuf validation succeeded")
            return True, []
        except MessageConversionError as e:
            logger.warning("Protobuf validation failed: %s", str(e))
            return False, [{"message": str(e), "path": []}]

    def validate(
        self,
        obj: Dict[str, Any],
        schema_type: str = "json",
        raise_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        Validate an object against the selected schema type.
        :param obj: Python dict to validate.
        :param schema_type: "json" or "proto"
        :param raise_on_error: if True, raises SchemaValidationError on failure.
        :returns: {"valid": bool, "errors": List[Dict]}
        """
        if schema_type == "json":
            valid, errors = self.validate_json(obj)
        elif schema_type == "proto":
            valid, errors = self.validate_proto(obj)
        else:
            msg = f"Unsupported schema_type '{schema_type}'"
            logger.error(msg)
            raise ValueError(msg)

        result = {"valid": valid, "errors": errors}
        if not valid:
            if raise_on_error:
                raise SchemaValidationError(errors)
        return result

# Example usage:
# from my_proto_module import TaskMessage
# validator = SchemaValidator(proto_message_cls=TaskMessage)
# result = validator.validate(task_dict, schema_type="proto")
# if result["valid"]:
#     # proceed
# else:
#     # handle errors in result["errors"]