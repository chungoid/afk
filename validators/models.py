from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Type, Dict

class IntentData(BaseModel):
    user_intent: str = Field(..., description="Extracted intent from raw requirement")
    domain: Optional[str] = Field(None, description="Optional domain of the intent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for intent extraction")

class Task(BaseModel):
    id: str = Field(..., description="Unique identifier for the task")
    title: str = Field(..., description="Title of the task")
    description: str = Field(..., description="Detailed description of the task")
    dependencies: List[str] = Field(default_factory=list, description="IDs of tasks this task depends on")
    estimated_time: Optional[float] = Field(None, gt=0.0, description="Estimated time to complete the task in hours")
    priority: Literal["low", "medium", "high"] = Field("medium", description="Priority level of the task")

MODEL_MAP: Dict[str, Type[BaseModel]] = {
    "intent": IntentData,
    "task": Task
}