import pytest
from jsonschema import ValidationError, Draft7Validator
import analysis_agent.utils.validator as validator

@pytest.fixture(autouse=True)
def patch_schemas(monkeypatch):
    schema_name = "person"
    schema = {
        "type": "object",
        "required": ["name", "age"],
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"}
        },
        "additionalProperties": False
    }
    v = Draft7Validator(schema)
    # Patch validator's internal registry for schemas
    monkeypatch.setattr(validator, "_VALIDATORS", {schema_name: v}, raising=False)
    monkeypatch.setattr(validator, "_SCHEMA_VALIDATORS", {schema_name: v}, raising=False)
    return schema_name

def test_validate_success(patch_schemas):
    data = {"name": "Alice", "age": 30}
    # Should not raise any exception
    validator.validate(data, patch_schemas)

def test_validate_missing_required_field(patch_schemas):
    data = {"name": "Alice"}
    with pytest.raises(ValidationError) as excinfo:
        validator.validate(data, patch_schemas)
    assert "age" in str(excinfo.value)

def test_validate_wrong_type(patch_schemas):
    data = {"name": "Alice", "age": "30"}
    with pytest.raises(ValidationError) as excinfo:
        validator.validate(data, patch_schemas)
    msg = str(excinfo.value)
    assert "is not of type 'integer'" in msg or "type" in msg

def test_validate_additional_property(patch_schemas):
    data = {"name": "Alice", "age": 30, "extra": "value"}
    with pytest.raises(ValidationError) as excinfo:
        validator.validate(data, patch_schemas)
    assert "additionalProperties" in str(excinfo.value)

def test_validate_schema_not_found():
    data = {"foo": "bar"}
    with pytest.raises(KeyError):
        validator.validate(data, "nonexistent_schema")