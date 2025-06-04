from __future__ import annotations
import subprocess
import json
import logging
from typing import Any, Sequence

logger = logging.getLogger(__name__)

class PublishError(Exception):
    """Raised when publishing tasks via MCP fails."""

def publish_tasks(tasks: Sequence[Any], timeout: int = 60, dry_run: bool = False) -> Any:
    """
    Publish a list of validated task objects to the MCP tasks.analysis channel.

    This function invokes the `mcp-use tasks.analysis publish` CLI with
    the JSON payload. It expects that `tasks` are already validated
    against the proper schema.

    Args:
        tasks: A sequence of task dicts, already validated.
        timeout: Seconds to wait for the subprocess to complete.
        dry_run: If True, no subprocess is executed; logs the payload instead.

    Returns:
        The parsed JSON result from MCP, or raw stdout if JSON parsing fails.

    Raises:
        PublishError: On subprocess failure or JSON decoding issues.
    """
    payload = None
    try:
        payload = json.dumps(tasks)
    except (TypeError, ValueError) as e:
        logger.exception("Failed to serialize tasks payload to JSON")
        raise PublishError(f"Invalid tasks payload: {e}") from e

    if dry_run:
        logger.info("Dry-run mode enabled. Payload to publish: %s", payload)
        return {"dry_run": True, "payload": tasks}

    cmd = ["mcp-use", "tasks.analysis", "publish", "--payload", payload]
    logger.debug("Running MCP publish command: %s", cmd)

    try:
        proc = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as e:
        logger.error(
            "MCP publish command failed with return code %s. stdout: %s stderr: %s",
            e.returncode, e.stdout, e.stderr
        )
        raise PublishError(
            f"MCP publish failed (code {e.returncode}): {e.stderr.strip()}"
        ) from e
    except subprocess.TimeoutExpired as e:
        logger.error("MCP publish command timed out after %s seconds", timeout)
        raise PublishError(f"MCP publish timed out after {timeout} seconds") from e
    except Exception as e:
        logger.exception("Unexpected error running MCP publish command")
        raise PublishError(f"Unexpected error: {e}") from e

    stdout = proc.stdout.strip()
    logger.debug("MCP publish stdout: %s", stdout)

    if not stdout:
        return {}

    try:
        result = json.loads(stdout)
        return result
    except json.JSONDecodeError:
        logger.warning("MCP publish returned non-JSON output; returning raw stdout")
        return stdout