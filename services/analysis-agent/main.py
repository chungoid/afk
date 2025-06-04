#!/usr/bin/env python3
"""
Analysis Agent Service - Service wrapper around existing analysis functionality.
Subscribes to: tasks.analysis 
Publishes to: tasks.planning
"""

import asyncio
import os
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
# Removed prometheus imports for now

# Import the existing messaging infrastructure and analysis code
import sys
sys.path.append('/app')
from src.common.messaging_simple import create_messaging_client, MessagingClient
from src.common.config import Settings

# Import existing analysis functionality
from src.analysis_agent.prompt_steps.analysis_steps import AnalysisSteps
from src.analysis_agent.utils.task_analyzer import TaskAnalyzer

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("analysis-agent")

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self

ANALYSIS_REQUESTS_TOTAL = DummyMetric()
ANALYSIS_DURATION = DummyMetric()
ANALYSIS_ERRORS = DummyMetric()
ACTIVE_ANALYSES = DummyMetric()

# Configuration
SUBSCRIBE_TOPIC = os.getenv("SUBSCRIBE_TOPIC", "tasks.analysis")
PUBLISH_TOPIC = os.getenv("PUBLISH_TOPIC", "tasks.planning")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Pydantic models
class AnalysisRequest(BaseModel):
    """Incoming analysis request"""
    request_id: str
    project_description: str
    requirements: List[str] = []
    constraints: List[str] = []
    metadata: Dict[str, Any] = {}

class TaskResult(BaseModel):
    """Individual task analysis result"""
    task_id: str
    name: str
    description: str
    type: str
    priority: int
    estimated_hours: float
    dependencies: List[str] = []
    skills_required: List[str] = []
    complexity: str  # "low", "medium", "high"

class AnalysisResult(BaseModel):
    """Complete analysis result"""
    analysis_id: str
    request_id: str
    project_summary: str
    tasks: List[TaskResult]
    total_estimated_hours: float
    recommended_team_size: int
    critical_path: List[str]
    risk_factors: List[str] = []
    technology_recommendations: List[str] = []
    metadata: Dict[str, Any]
    timestamp: float

class AnalysisAgent:
    """
    Analysis Agent Service that wraps existing analysis functionality
    """
    
    def __init__(self):
        self.messaging_client: Optional[MessagingClient] = None
        self.is_running = False
        
        # Initialize analysis components
        self.analysis_steps = AnalysisSteps()
        self.task_analyzer = TaskAnalyzer()
        
        # Track active analyses
        self.active_analyses: Dict[str, AnalysisRequest] = {}
        
    async def start(self):
        """Initialize the messaging client and start listening"""
        logger.info("Starting Analysis Agent Service...")
        
        # Initialize messaging client 
        self.messaging_client = create_messaging_client()
        await self.messaging_client.start()
        
        # Subscribe to analysis topic
        self.messaging_client.subscribe(
            topic=SUBSCRIBE_TOPIC,
            callback=self.process_analysis_request,
            group_id="analysis-agent-group"
        )
        
        self.is_running = True
        logger.info(f"Analysis Agent Service started, subscribed to {SUBSCRIBE_TOPIC}")
        
    async def stop(self):
        """Stop the messaging client"""
        logger.info("Stopping Analysis Agent Service...")
        self.is_running = False
        if self.messaging_client:
            await self.messaging_client.stop()
        logger.info("Analysis Agent Service stopped")
        
    async def process_analysis_request(self, message: Dict[str, Any]):
        """Process incoming analysis request"""
        analysis_start = time.time()
        
        try:
            # Parse the analysis request
            request = AnalysisRequest(**message)
            request_id = request.request_id
            
            logger.info(f"Processing analysis request {request_id}")
            ACTIVE_ANALYSES.inc()
            
            # Track active analysis
            self.active_analyses[request_id] = request
            
            # Perform the analysis using existing functionality
            analysis_result = await self.analyze_project(request)
            
            # Publish result to planning topic
            await self.messaging_client.publish(PUBLISH_TOPIC, analysis_result.dict())
            
            # Update metrics
            ANALYSIS_REQUESTS_TOTAL.labels(status="success").inc()
            ANALYSIS_DURATION.observe(time.time() - analysis_start)
            ACTIVE_ANALYSES.dec()
            
            # Remove from active analyses
            self.active_analyses.pop(request_id, None)
            
            logger.info(f"Completed analysis for request {request_id}, identified {len(analysis_result.tasks)} tasks")
            
        except Exception as e:
            ANALYSIS_ERRORS.labels(error_type="processing").inc()
            ANALYSIS_REQUESTS_TOTAL.labels(status="error").inc()
            ACTIVE_ANALYSES.dec()
            
            logger.error(f"Error processing analysis request: {e}", exc_info=True)
            
            # Try to publish error result
            try:
                error_result = {
                    "analysis_id": f"error_{int(time.time())}",
                    "request_id": message.get("request_id", "unknown"),
                    "error": str(e),
                    "timestamp": time.time(),
                    "metadata": {"agent": "analysis-agent", "status": "error"}
                }
                await self.messaging_client.publish(PUBLISH_TOPIC, error_result)
            except:
                pass
                
    async def analyze_project(self, request: AnalysisRequest) -> AnalysisResult:
        """Perform project analysis using existing analysis functionality"""
        
        try:
            # Use existing analysis steps
            raw_analysis = await self.analysis_steps.analyze_project_requirements(
                project_description=request.project_description,
                requirements=request.requirements,
                constraints=request.constraints
            )
            
            # Use task analyzer to break down into tasks
            task_breakdown = await self.task_analyzer.analyze_and_breakdown(
                project_description=request.project_description,
                analysis_result=raw_analysis
            )
            
            # Convert to our result format
            tasks = []
            total_hours = 0
            
            for i, task_data in enumerate(task_breakdown.get("tasks", [])):
                task = TaskResult(
                    task_id=f"task_{request.request_id}_{i+1}",
                    name=task_data.get("name", f"Task {i+1}"),
                    description=task_data.get("description", ""),
                    type=task_data.get("type", "development"),
                    priority=task_data.get("priority", 5),
                    estimated_hours=task_data.get("estimated_hours", 8.0),
                    dependencies=task_data.get("dependencies", []),
                    skills_required=task_data.get("skills_required", []),
                    complexity=task_data.get("complexity", "medium")
                )
                tasks.append(task)
                total_hours += task.estimated_hours
                
            # Generate analysis result
            analysis_result = AnalysisResult(
                analysis_id=f"analysis_{uuid.uuid4().hex[:8]}",
                request_id=request.request_id,
                project_summary=raw_analysis.get("summary", request.project_description),
                tasks=tasks,
                total_estimated_hours=total_hours,
                recommended_team_size=max(1, min(10, int(total_hours / 160))),  # Assume 160 hours per team member
                critical_path=self._identify_critical_path(tasks),
                risk_factors=raw_analysis.get("risk_factors", []),
                technology_recommendations=raw_analysis.get("technology_recommendations", []),
                metadata={
                    "agent": "analysis-agent",
                    "analysis_method": "prompt_steps_with_task_analyzer",
                    "original_request": request.dict()
                },
                timestamp=time.time()
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            
            # Return minimal result in case of failure
            return AnalysisResult(
                analysis_id=f"fallback_{uuid.uuid4().hex[:8]}",
                request_id=request.request_id,
                project_summary=request.project_description,
                tasks=[
                    TaskResult(
                        task_id=f"task_{request.request_id}_fallback",
                        name="Project Implementation",
                        description=request.project_description,
                        type="development",
                        priority=1,
                        estimated_hours=40.0,
                        complexity="medium"
                    )
                ],
                total_estimated_hours=40.0,
                recommended_team_size=1,
                critical_path=["task_fallback"],
                risk_factors=["Analysis failed - manual review required"],
                metadata={
                    "agent": "analysis-agent",
                    "analysis_method": "fallback",
                    "error": str(e)
                },
                timestamp=time.time()
            )
            
    def _identify_critical_path(self, tasks: List[TaskResult]) -> List[str]:
        """Identify critical path through tasks"""
        # Simple critical path: longest chain of dependencies
        # For more sophisticated analysis, this could use proper CPM algorithms
        
        task_map = {task.task_id: task for task in tasks}
        visited = set()
        longest_path = []
        
        def dfs(task_id: str, current_path: List[str]) -> List[str]:
            if task_id in visited or task_id not in task_map:
                return current_path
                
            visited.add(task_id)
            current_path = current_path + [task_id]
            
            task = task_map[task_id]
            best_path = current_path
            
            for dep_id in task.dependencies:
                dep_path = dfs(dep_id, current_path)
                if len(dep_path) > len(best_path):
                    best_path = dep_path
                    
            return best_path
            
        # Find the longest path starting from any task
        for task in tasks:
            visited.clear()
            path = dfs(task.task_id, [])
            if len(path) > len(longest_path):
                longest_path = path
                
        return longest_path

# Global agent instance
analysis_agent = AnalysisAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the agent lifecycle"""
    await analysis_agent.start()
    yield
    await analysis_agent.stop()

# FastAPI app
app = FastAPI(
    title="Analysis Agent", 
    description="Analyzes project requirements and breaks them down into tasks",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "analysis-agent",
        "is_running": analysis_agent.is_running,
        "subscribe_topic": SUBSCRIBE_TOPIC,
        "publish_topic": PUBLISH_TOPIC,
        "active_analyses": len(analysis_agent.active_analyses)
    }

@app.get("/health/liveness")
async def liveness():
    """Kubernetes liveness probe"""
    return {"status": "alive"}

@app.get("/health/readiness") 
async def readiness():
    """Kubernetes readiness probe"""
    is_ready = analysis_agent.is_running and analysis_agent.messaging_client is not None
    if not is_ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}

@app.get("/metrics")
async def metrics():
    """Metrics endpoint (simplified)"""
    return {"status": "metrics disabled for now"}

@app.get("/status")
async def status():
    """Get current agent status"""
    return {
        "agent": "analysis-agent",
        "is_running": analysis_agent.is_running,
        "topics": {
            "subscribe": SUBSCRIBE_TOPIC,
            "publish": PUBLISH_TOPIC
        },
        "active_analyses": len(analysis_agent.active_analyses),
        "metrics": {
            "requests_total": 0,
            "active_analyses": len(analysis_agent.active_analyses),
            "errors_total": 0
        }
    }

@app.post("/analyze", response_model=AnalysisResult)
async def analyze_direct(request: AnalysisRequest):
    """Direct analysis endpoint (for testing)"""
    try:
        result = await analysis_agent.analyze_project(request)
        return result
    except Exception as e:
        logger.error(f"Direct analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8000,
        log_level=LOG_LEVEL.lower(),
        reload=False
    ) 