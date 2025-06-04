from pathlib import Path
import json

class SchemaLoaderError(Exception):
    """Exception raised when schema loading or retrieval fails."""
    pass

_schemas = {}

def load_schemas(schemas_dir: Path = None) -> dict:
    """
    Load all JSON schema files from the given directory into memory.

    Args:
        schemas_dir (Path, optional): Directory containing .json schema files.
            Defaults to project_root/schemas.

    Returns:
        dict: Mapping of schema_name to its loaded JSON content.

    Raises:
        SchemaLoaderError: If directory doesn't exist or JSON parsing fails.
    """
    global _schemas
    if schemas_dir is None:
        # src/analysis_agent/utils/schema_loader.py -> project root is parents[3]
        schemas_dir = Path(__file__).resolve().parents[3] / "schemas"
    if not schemas_dir.exists() or not schemas_dir.is_dir():
        raise SchemaLoaderError(f"Schemas directory '{schemas_dir}' does not exist or is not a directory.")
    for schema_path in schemas_dir.glob("*.json"):
        try:
            with schema_path.open("r", encoding="utf-8") as f:
                schema_data = json.load(f)
            _schemas[schema_path.stem] = schema_data
        except json.JSONDecodeError as e:
            raise SchemaLoaderError(f"Failed to parse JSON in '{schema_path}': {e}") from e
        except OSError as e:
            raise SchemaLoaderError(f"Failed to read schema file '{schema_path}': {e}") from e
    return _schemas

def get_schema(schema_name: str) -> dict:
    """
    Retrieve a loaded schema by name. Loads all schemas on first call.

    Args:
        schema_name (str): The base filename (without .json) of the schema.

    Returns:
        dict: The JSON schema.

    Raises:
        SchemaLoaderError: If the named schema is not found.
    """
    if not _schemas:
        load_schemas()
    try:
        return _schemas[schema_name]
    except KeyError:
        available = ", ".join(sorted(_schemas.keys()))
        raise SchemaLoaderError(f"Schema '{schema_name}' not found. Available schemas: {available}") from None