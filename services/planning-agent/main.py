#!/usr/bin/env python3
"""
Planning Agent - Receives tasks from Analysis Agent and creates prioritized plans.
Subscribes to: tasks.analysis
Publishes to: tasks.planning
"""

import asyncio

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass

import os

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass

import json

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass

import logging

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass

import time

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass

from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass

# Removed prometheus imports for now

# Import the existing messaging infrastructure
import sys

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass

sys.path.append('/app')
from src.common.messaging_simple import create_messaging_client, MessagingClient
from src.common.config import Settings

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("planning-agent")

# Prometheus metrics
MESSAGES_RECEIVED = DummyMetric()
MESSAGES_PUBLISHED = DummyMetric()
PLANNING_DURATION = DummyMetric()
ACTIVE_PLANS = DummyMetric()
PLANNING_ERRORS = DummyMetric()

# Configuration
SUBSCRIBE_TOPIC = os.getenv("SUBSCRIBE_TOPIC", "tasks.analysis")
PUBLISH_TOPIC = os.getenv("PUBLISH_TOPIC", "tasks.planning")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Pydantic models
class TaskInput(BaseModel):
    """Task from analysis agent"""
    id: str
    title: str
    description: str
    dependencies: List[str] = []
    metadata: Dict[str, Any] = {}

class PlanningOutput(BaseModel):
    """Planning result to publish"""
    plan_id: str
    original_tasks: List[TaskInput]
    prioritized_tasks: List[Dict[str, Any]]
    estimated_duration: float
    risk_assessment: Dict[str, Any]
    execution_sequence: List[List[str]]  # Groups of tasks that can run in parallel
    metadata: Dict[str, Any]

class PlanningAgent:
    """
    Planning Agent that prioritizes and sequences tasks from the analysis stage
    """
    
    def __init__(self):
        self.messaging_client: Optional[MessagingClient] = None
        self.is_running = False
        
    async def start(self):
        """Initialize the messaging client and start listening"""
        logger.info("Starting Planning Agent...")
        
        # Initialize messaging client 
        self.messaging_client = create_messaging_client()
        await self.messaging_client.start()
        
        # Subscribe to analysis topic
        self.messaging_client.subscribe(
            topic=SUBSCRIBE_TOPIC,
            callback=self.process_analysis_message,
            group_id="planning-agent-group"
        )
        
        self.is_running = True
        logger.info(f"Planning Agent started, subscribed to {SUBSCRIBE_TOPIC}")
        
    async def stop(self):
        """Stop the messaging client"""
        logger.info("Stopping Planning Agent...")
        self.is_running = False
        if self.messaging_client:
            await self.messaging_client.stop()
        logger.info("Planning Agent stopped")
        
    async def process_analysis_message(self, message: Dict[str, Any]):
        """Process a message from the analysis topic"""
        start_time = time.time()
        
        try:
            MESSAGES_RECEIVED.inc()
            ACTIVE_PLANS.inc()
            
            logger.info(f"Received analysis message: {message}")
            
            # Parse the tasks from analysis
            if "tasks" not in message:
                raise ValueError("Message missing 'tasks' field")
                
            tasks_data = message["tasks"]
            if not isinstance(tasks_data, list):
                raise ValueError("Tasks must be a list")
                
            # Convert to TaskInput objects
            tasks = [TaskInput(**task) for task in tasks_data]
            
            # Generate the plan
            plan = await self.create_plan(tasks, message.get("metadata", {}))
            
            # Publish the plan
            await self.publish_plan(plan)
            
            duration = time.time() - start_time
            PLANNING_DURATION.observe(duration)
            
            logger.info(f"Successfully processed plan {plan.plan_id} in {duration:.2f}s")
            
        except Exception as e:
            PLANNING_ERRORS.inc()
            logger.error(f"Error processing analysis message: {e}", exc_info=True)
            raise
        finally:
            ACTIVE_PLANS.dec()
            
    async def create_plan(self, tasks: List[TaskInput], metadata: Dict[str, Any]) -> PlanningOutput:
        """Create a prioritized plan from the input tasks"""
        
        # Generate unique plan ID
        plan_id = f"plan_{int(time.time())}_{len(tasks)}"
        
        # Step 1: Prioritize tasks based on dependencies and complexity
        prioritized_tasks = self.prioritize_tasks(tasks)
        
        # Step 2: Estimate duration for each task
        self.estimate_task_durations(prioritized_tasks)
        
        # Step 3: Create execution sequence (handle dependencies)
        execution_sequence = self.create_execution_sequence(prioritized_tasks)
        
        # Step 4: Risk assessment
        risk_assessment = self.assess_risks(prioritized_tasks)
        
        # Step 5: Calculate total estimated duration
        total_duration = sum(task.get("estimated_duration", 1.0) for task in prioritized_tasks)
        
        return PlanningOutput(
            plan_id=plan_id,
            original_tasks=tasks,
            prioritized_tasks=prioritized_tasks,
            estimated_duration=total_duration,
            risk_assessment=risk_assessment,
            execution_sequence=execution_sequence,
            metadata={
                **metadata,
                "created_at": time.time(),
                "agent": "planning-agent",
                "version": "1.0"
            }
        )
        
    def prioritize_tasks(self, tasks: List[TaskInput]) -> List[Dict[str, Any]]:
        """Prioritize tasks based on dependencies and complexity"""
        prioritized = []
        
        for task in tasks:
            # Convert to dict and add priority scoring
            task_dict = task.dict()
            
            # Simple priority algorithm
            priority_score = 5  # Default medium priority
            
            # Higher priority for tasks with no dependencies
            if not task.dependencies:
                priority_score += 2
                
            # Lower priority for tasks with many dependencies
            priority_score -= min(len(task.dependencies), 3)
            
            # Adjust based on description keywords
            desc_lower = task.description.lower()
            if any(word in desc_lower for word in ["critical", "urgent", "blocker"]):
                priority_score += 3
            elif any(word in desc_lower for word in ["nice to have", "optional", "future"]):
                priority_score -= 2
                
            task_dict["priority"] = max(1, min(priority_score, 10))
            prioritized.append(task_dict)
            
        # Sort by priority (higher first)
        return sorted(prioritized, key=lambda x: x["priority"], reverse=True)
        
    def estimate_task_durations(self, tasks: List[Dict[str, Any]]):
        """Add duration estimates to tasks"""
        for task in tasks:
            # Simple heuristic based on description length and complexity
            desc_length = len(task["description"])
            
            # Base estimation
            if desc_length < 50:
                base_duration = 0.5  # 30 minutes
            elif desc_length < 200:
                base_duration = 2.0  # 2 hours  
            else:
                base_duration = 8.0  # Full day
                
            # Adjust for complexity keywords
            desc_lower = task["description"].lower()
            multiplier = 1.0
            
            if any(word in desc_lower for word in ["integrate", "complex", "system", "architecture"]):
                multiplier *= 1.5
            if any(word in desc_lower for word in ["simple", "basic", "quick"]):
                multiplier *= 0.7
                
            task["estimated_duration"] = base_duration * multiplier
            
    def create_execution_sequence(self, tasks: List[Dict[str, Any]]) -> List[List[str]]:
        """Create execution sequence respecting dependencies"""
        sequence = []
        completed = set()
        remaining = {task["id"]: task for task in tasks}
        
        while remaining:
            # Find tasks with no unmet dependencies
            ready_tasks = []
            for task_id, task in remaining.items():
                deps = task.get("dependencies", [])
                if all(dep in completed for dep in deps):
                    ready_tasks.append(task_id)
                    
            if not ready_tasks:
                # Circular dependency or orphaned tasks
                logger.warning("Possible circular dependency detected, adding remaining tasks")
                ready_tasks = list(remaining.keys())
                
            # Add this batch to sequence
            sequence.append(ready_tasks)
            
            # Mark as completed and remove from remaining
            for task_id in ready_tasks:
                completed.add(task_id)
                remaining.pop(task_id, None)
                
        return sequence
        
    def assess_risks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess risks for the plan"""
        risk_assessment = {
            "overall_risk": "medium",
            "risk_factors": [],
            "mitigation_strategies": []
        }
        
        # Analyze risk factors
        total_tasks = len(tasks)
        high_priority_tasks = sum(1 for task in tasks if task.get("priority", 5) >= 8)
        complex_tasks = sum(1 for task in tasks if task.get("estimated_duration", 1) >= 4)
        
        if total_tasks > 20:
            risk_assessment["risk_factors"].append("Large number of tasks")
            risk_assessment["mitigation_strategies"].append("Consider breaking into smaller phases")
            
        if high_priority_tasks > total_tasks * 0.3:
            risk_assessment["risk_factors"].append("High proportion of critical tasks")
            risk_assessment["mitigation_strategies"].append("Focus on critical path optimization")
            
        if complex_tasks > total_tasks * 0.2:
            risk_assessment["risk_factors"].append("Multiple complex tasks")
            risk_assessment["mitigation_strategies"].append("Allocate extra time buffers")
            
        # Set overall risk level
        risk_score = len(risk_assessment["risk_factors"])
        if risk_score >= 3:
            risk_assessment["overall_risk"] = "high"
        elif risk_score >= 1:
            risk_assessment["overall_risk"] = "medium"
        else:
            risk_assessment["overall_risk"] = "low"
            
        return risk_assessment
        
    async def publish_plan(self, plan: PlanningOutput):
        """Publish the plan to the planning topic"""
        try:
            message = plan.dict()
            await self.messaging_client.publish(PUBLISH_TOPIC, message)
            MESSAGES_PUBLISHED.inc()
            logger.info(f"Published plan {plan.plan_id} to {PUBLISH_TOPIC}")
        except Exception as e:
            logger.error(f"Failed to publish plan {plan.plan_id}: {e}")
            raise

# Global agent instance
planning_agent = PlanningAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the agent lifecycle"""
    await planning_agent.start()
    yield
    await planning_agent.stop()

# FastAPI app
app = FastAPI(
    title="Planning Agent", 
    description="Prioritizes and sequences tasks from analysis agent",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "planning-agent",
        "is_running": planning_agent.is_running,
        "subscribe_topic": SUBSCRIBE_TOPIC,
        "publish_topic": PUBLISH_TOPIC
    }

@app.get("/health/liveness")
async def liveness():
    """Kubernetes liveness probe"""
    return {"status": "alive"}

@app.get("/health/readiness") 
async def readiness():
    """Kubernetes readiness probe"""
    is_ready = planning_agent.is_running and planning_agent.messaging_client is not None
    if not is_ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return {"status": "metrics disabled for now"}
    return {"status": "metrics disabled for now"}

@app.get("/status")
async def status():
    """Get current agent status"""
    return {
        "agent": "planning-agent",
        "is_running": planning_agent.is_running,
        "topics": {
            "subscribe": SUBSCRIBE_TOPIC,
            "publish": PUBLISH_TOPIC
        },
        "metrics": {
            "messages_received": MESSAGES_RECEIVED._value.get(),
            "messages_published": MESSAGES_PUBLISHED._value.get(),
            "active_plans": ACTIVE_PLANS._value.get(),
            "errors": PLANNING_ERRORS._value.get()
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8000,
        log_level=LOG_LEVEL.lower(),
        reload=False
    ) 