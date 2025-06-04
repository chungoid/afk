import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from orchestrator.chain_controller import ChainController
from schema.validator import Validator
from publisher.mcp_publisher import MCPPublisher

app = FastAPI()
logger = logging.getLogger("analysis_agent_api")
logger.setLevel(logging.INFO)

processed_requests = set()

chain_controller = ChainController()
validator = Validator(schema_path=os.getenv("TASK_SCHEMA_PATH", "config/schema/tasks.schema.json"))
publisher = MCPPublisher(
    topic=os.getenv("MCP_TASKS_TOPIC", "tasks.analysis"),
    retry_attempts=int(os.getenv("PUBLISH_RETRY_ATTEMPTS", "3")),
    backoff_factor=float(os.getenv("PUBLISH_BACKOFF_FACTOR", "0.5"))
)

class AnalyzeRequest(BaseModel):
    requirement: str = Field(..., description="Raw requirement or intent to analyze")
    request_id: str = Field(..., description="Unique ID for idempotency")

class TaskValidationError(BaseModel):
    task_index: int
    errors: List[str]

class AnalyzeResponse(BaseModel):
    succeeded: int
    failed: int
    errors: List[TaskValidationError]
    message_ids: List[str]

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    if req.request_id in processed_requests:
        logger.info(f"Duplicate request received: {req.request_id}. Skipping processing.")
        return AnalyzeResponse(succeeded=0, failed=0, errors=[], message_ids=[])

    processed_requests.add(req.request_id)
    try:
        draft_tasks = await chain_controller.process(requirement=req.requirement, request_id=req.request_id)
    except Exception as e:
        logger.exception("Error in chain controller")
        raise HTTPException(status_code=500, detail="Error processing LLM chain")

    valid_tasks = []
    validation_errors: List[TaskValidationError] = []

    for idx, task in enumerate(draft_tasks):
        try:
            validator.validate(task)
            valid_tasks.append(task)
        except Exception as ve:
            errs = ve.errors() if hasattr(ve, "errors") else [str(ve)]
            validation_errors.append(TaskValidationError(task_index=idx, errors=errs))

    message_ids: List[str] = []
    if valid_tasks:
        try:
            message_ids = await publisher.publish_all(valid_tasks, metadata={"request_id": req.request_id})
        except Exception as pe:
            logger.exception("Error publishing tasks")
            raise HTTPException(status_code=502, detail="Failed to publish tasks to MCP")

    return AnalyzeResponse(
        succeeded=len(valid_tasks),
        failed=len(validation_errors),
        errors=validation_errors,
        message_ids=message_ids
    )

@app.get("/health")
def health_check():
    return {"status": "ok"}