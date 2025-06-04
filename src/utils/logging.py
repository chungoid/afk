import logging
import os
import sys
import json
import time
from typing import Any, Dict, Optional
import contextvars

# Context variable for request ID propagation
_request_id_ctx_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)

def set_request_id(request_id: str) -> None:
    """
    Set the current request ID in context.
    """
    _request_id_ctx_var.set(request_id)

def get_request_id() -> Optional[str]:
    """
    Retrieve the current request ID from context.
    """
    return _request_id_ctx_var.get()

def clear_request_id() -> None:
    """
    Clear the current request ID from context.
    """
    _request_id_ctx_var.set(None)

class RequestIdFilter(logging.Filter):
    """
    Logging filter to inject request_id into log records.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs logs in JSON format.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "module": record.module,
            "funcName": record.funcName,
            "lineNo": record.lineno,
        }
        # include exception info if present
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_record["stack_info"] = self.formatStack(record.stack_info)
        # include any extra attributes
        for key, value in record.__dict__.items():
            if key not in log_record and key not in ("msg", "args", "exc_info", "stack_info"):
                log_record[key] = value
        return json.dumps(log_record, default=str)

def configure_logger(
    name: Optional[str] = None,
    level: Optional[int] = None,
    json_format: Optional[bool] = None,
    stream: Optional[Any] = None
) -> logging.Logger:
    """
    Configure and return a logger instance.
    Reads defaults from environment variables: LOG_LEVEL, LOG_JSON.
    """
    log_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    try:
        log_level = getattr(logging, log_level)
    except AttributeError:
        log_level = logging.INFO

    use_json = json_format if json_format is not None else os.getenv("LOG_JSON", "false").lower() in ("1", "true", "yes")
    handler_stream = stream or sys.stdout

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    # avoid adding multiple handlers in interactive environments
    if not logger.handlers:
        formatter = JsonFormatter() if use_json else logging.Formatter("%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s")
        handler = logging.StreamHandler(handler_stream)
        handler.setFormatter(formatter)
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger

def log_metric(name: str, value: float, tags: Optional[Dict[str, Any]] = None) -> None:
    """
    Emit a metric event into the log stream.
    The metric will appear as INFO level with structured fields.
    """
    logger = configure_logger(__name__)
    metric_record = {
        "metric": name,
        "value": value,
        "tags": tags or {},
        "timestamp": time.time(),
        "request_id": get_request_id(),
    }
    logger.info("metric", extra={"metric_record": metric_record})

class ErrorCategory:
    LLM_TIMEOUT = "llm_timeout"
    VECTOR_STORE_DOWN = "vector_store_down"
    SCHEMA_VIOLATION = "schema_violation"
    PUBLISHER_UNREACHABLE = "publisher_unreachable"
    UNKNOWN = "unknown"

def classify_error(exc: Exception) -> str:
    """
    Classify an exception into one of the predefined categories.
    """
    from requests.exceptions import Timeout, ConnectionError

    # Example LLM SDK exceptions
    class LLMTimeoutError(Exception):
        pass

    class VectorStoreError(Exception):
        pass

    if isinstance(exc, Timeout) or isinstance(exc, LLMTimeoutError):
        return ErrorCategory.LLM_TIMEOUT
    if isinstance(exc, ConnectionError) or isinstance(exc, VectorStoreError):
        return ErrorCategory.VECTOR_STORE_DOWN
    if isinstance(exc, ValueError) and "schema" in str(exc).lower():
        return ErrorCategory.SCHEMA_VIOLATION
    if isinstance(exc, OSError):
        return ErrorCategory.PUBLISHER_UNREACHABLE
    return ErrorCategory.UNKNOWN

# Provide a module-level default logger
logger = configure_logger(__name__)