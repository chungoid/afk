#!/usr/bin/env python3
"""
Orchestrator Agent - Coordinates the entire multi-agent pipeline.
Subscribes to: tasks.analysis, tasks.planning, tasks.blueprint, tasks.coding, tasks.testing
Publishes to: orchestration.events
"""

import asyncio
import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Set
from contextlib import asynccontextmanager
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Import the existing messaging infrastructure
import sys
sys.path.append('/app')
from src.common.messaging_simple import create_messaging_client, MessagingClient
from src.common.config import Settings

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("orchestrator-agent")

# Prometheus metrics - with unique names to avoid conflicts
try:
    PIPELINE_MESSAGES_RECEIVED = Counter(
        'orchestrator_agent_messages_received_total',
        'Total number of pipeline messages received',
        ['stage']
    )
    PIPELINE_STAGES_COMPLETED = Counter(
        'orchestrator_agent_stages_completed_total',
        'Total number of pipeline stages completed',
        ['stage', 'status']
    )
    PIPELINE_DURATION = Histogram(
        'orchestrator_agent_pipeline_duration_seconds',
        'Time taken for complete pipeline execution'
    )
    ACTIVE_PIPELINES = Gauge(
        'orchestrator_agent_active_pipelines',
        'Number of currently active pipelines'
    )
    AGENT_HEALTH_STATUS = Gauge(
        'orchestrator_agent_health_status',
        'Health status of monitored agents',
        ['agent_name']
    )
    ORCHESTRATOR_ERRORS = Counter(
        'orchestrator_agent_errors_total',
        'Total number of orchestrator errors'
    )
except Exception as e:
    logger.warning(f"Error initializing metrics, using dummy metrics: {e}")
    # Fallback to avoid startup issues
    class DummyMetric:
        def __init__(self):
            self._value = type('obj', (object,), {'value': 0})()
        def inc(self): 
            self._value.value += 1
        def dec(self): 
            self._value.value -= 1
        def observe(self, value): 
            self._value.value = value
        def set(self, value):
            self._value.value = value
        def labels(self, **kwargs): 
            return self
    
    PIPELINE_MESSAGES_RECEIVED = DummyMetric()
    PIPELINE_STAGES_COMPLETED = DummyMetric()
    PIPELINE_DURATION = DummyMetric()
    ACTIVE_PIPELINES = DummyMetric()
    AGENT_HEALTH_STATUS = DummyMetric()
    ORCHESTRATOR_ERRORS = DummyMetric()

# Configuration
SUBSCRIBE_TOPICS = os.getenv("SUBSCRIBE_TOPICS", "tasks.analysis,tasks.planning,tasks.blueprint,tasks.coding,tasks.testing").split(",")
PUBLISH_TOPIC = os.getenv("ORCHESTRATION_EVENTS_TOPIC", "orchestration.events")
DASHBOARD_WS_URL = os.getenv("DASHBOARD_WS_URL", "ws://localhost:8000/ws")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Pydantic models
class PipelineMessage(BaseModel):
    """Generic pipeline message"""
    message_id: str
    stage: str
    status: str
    timestamp: float
    data: Dict[str, Any]
    metadata: Dict[str, Any] = {}

class PipelineStatus(BaseModel):
    """Overall pipeline status"""
    pipeline_id: str
    request_id: str
    current_stage: str
    stages_completed: List[str]
    stages_pending: List[str]
    start_time: float
    last_update_time: float
    total_duration: Optional[float] = None
    status: str  # "running", "completed", "failed", "stalled"
    error_message: Optional[str] = None

class AgentStatus(BaseModel):
    """Individual agent status"""
    agent_name: str
    is_healthy: bool
    last_heartbeat: float
    messages_processed: int
    current_load: float
    error_count: int

class OrchestrationEvent(BaseModel):
    """Event to publish about orchestration state"""
    event_id: str
    event_type: str  # "pipeline_started", "stage_completed", "pipeline_completed", "agent_status", "error"
    pipeline_id: Optional[str] = None
    stage: Optional[str] = None
    agent: Optional[str] = None
    data: Dict[str, Any]
    timestamp: float

class OrchestratorAgent:
    """
    Orchestrator Agent that coordinates the entire multi-agent pipeline
    """
    
    def __init__(self):
        self.messaging_client: Optional[MessagingClient] = None
        self.is_running = False
        
        # Pipeline tracking
        self.active_pipelines: Dict[str, PipelineStatus] = {}
        self.agent_statuses: Dict[str, AgentStatus] = {}
        self.message_history: List[PipelineMessage] = []
        self.websocket_connections: Set[WebSocket] = set()
        
        # Stage order for pipeline tracking
        self.stage_order = ["analysis", "planning", "blueprint", "coding", "testing", "deployment"]
        self.stage_topics = {
            "analysis": "tasks.analysis",
            "planning": "tasks.planning", 
            "blueprint": "tasks.blueprint",
            "coding": "tasks.coding",
            "testing": "tasks.testing",
            "deployment": "tasks.deployment"
        }
        
    async def start(self):
        """Initialize the messaging client and start listening"""
        logger.info("Starting Orchestrator Agent...")
        
        # Initialize messaging client 
        self.messaging_client = create_messaging_client()
        await self.messaging_client.start()
        
        # Subscribe to all pipeline topics
        for topic in SUBSCRIBE_TOPICS:
            topic = topic.strip()
            self.messaging_client.subscribe(
                topic=topic,
                callback=self.process_pipeline_message,
                group_id="orchestrator-agent-group"
            )
            logger.info(f"Subscribed to {topic}")
        
        # Start background tasks
        asyncio.create_task(self.pipeline_monitoring_loop())
        asyncio.create_task(self.agent_health_monitoring_loop())
        asyncio.create_task(self.cleanup_old_pipelines_loop())
        
        self.is_running = True
        logger.info(f"Orchestrator Agent started, monitoring {len(SUBSCRIBE_TOPICS)} topics")
        
    async def stop(self):
        """Stop the messaging client"""
        logger.info("Stopping Orchestrator Agent...")
        self.is_running = False
        if self.messaging_client:
            await self.messaging_client.stop()
        
        # Close all websocket connections
        for ws in self.websocket_connections.copy():
            try:
                await ws.close()
            except:
                pass
        
        logger.info("Orchestrator Agent stopped")
        
    async def process_pipeline_message(self, message: Dict[str, Any]):
        """Process a message from any pipeline stage"""
        try:
            # Determine stage from topic or message content
            stage = self.determine_stage_from_message(message)
            
            # Extract or generate pipeline/request ID
            pipeline_id = self.extract_pipeline_id(message)
            
            # Create pipeline message
            pipeline_msg = PipelineMessage(
                message_id=f"msg_{int(time.time())}_{hash(str(message)) % 10000}",
                stage=stage,
                status="received",
                timestamp=time.time(),
                data=message,
                metadata={"topic": stage, "size": len(str(message))}
            )
            
            # Track the message
            self.message_history.append(pipeline_msg)
            if len(self.message_history) > 1000:  # Keep last 1000 messages
                self.message_history = self.message_history[-1000:]
                
            # Update pipeline status
            await self.update_pipeline_status(pipeline_id, stage, pipeline_msg)
            
            # Update metrics
            PIPELINE_MESSAGES_RECEIVED.labels(stage=stage, status="received").inc()
            
            # Broadcast to WebSocket clients
            await self.broadcast_to_websockets({
                "type": "pipeline_message",
                "stage": stage,
                "pipeline_id": pipeline_id,
                "message": pipeline_msg.dict()
            })
            
            logger.info(f"Processed {stage} message for pipeline {pipeline_id}")
            
        except Exception as e:
            ORCHESTRATOR_ERRORS.labels(error_type="message_processing").inc()
            logger.error(f"Error processing pipeline message: {e}", exc_info=True)
            
    def determine_stage_from_message(self, message: Dict[str, Any]) -> str:
        """Determine pipeline stage from message content"""
        # Check for TestOutput (deployment) messages first
        if any(field in message for field in ["test_results", "coverage_report", "quality_metrics", "overall_status"]):
            return "deployment"
            
        # Check message metadata first
        if "agent" in message.get("metadata", {}):
            agent = message["metadata"]["agent"]
            if "test-agent" in agent:
                return "deployment"
            elif "planning" in agent:
                return "planning"
            elif "blueprint" in agent:
                return "blueprint"
            elif "code" in agent:
                return "coding"
            elif "analysis" in agent:
                return "analysis"
                
        # Check message structure
        if "plan_id" in message:
            return "planning"
        elif "blueprint_id" in message:
            return "blueprint"
        elif "code_id" in message:
            return "coding"
        elif "test_id" in message:
            return "testing"
        elif "tasks" in message:
            return "analysis"
            
        return "unknown"
        
    def extract_pipeline_id(self, message: Dict[str, Any]) -> str:
        """Extract or generate pipeline ID from message"""
        # Try to extract from various fields
        for field in ["pipeline_id", "request_id", "plan_id", "blueprint_id", "code_id", "test_id"]:
            if field in message:
                return str(message[field])
                
        # Check metadata
        metadata = message.get("metadata", {})
        for field in ["pipeline_id", "request_id", "parent_id"]:
            if field in metadata:
                return str(metadata[field])
                
        # Generate from message hash if no ID found
        return f"pipeline_{hash(str(message)) % 100000}"
        
    async def update_pipeline_status(self, pipeline_id: str, stage: str, message: PipelineMessage):
        """Update the status of a pipeline"""
        current_time = time.time()
        
        if pipeline_id not in self.active_pipelines:
            # Create new pipeline status
            self.active_pipelines[pipeline_id] = PipelineStatus(
                pipeline_id=pipeline_id,
                request_id=pipeline_id,
                current_stage=stage,
                stages_completed=[],
                stages_pending=self.stage_order.copy(),
                start_time=current_time,
                last_update_time=current_time,
                status="running"
            )
            ACTIVE_PIPELINES.inc()
            
            # Publish pipeline started event
            await self.publish_orchestration_event("pipeline_started", pipeline_id, stage, {
                "pipeline_id": pipeline_id,
                "start_time": current_time
            })
        
        pipeline = self.active_pipelines[pipeline_id]
        
        # Update pipeline state
        pipeline.current_stage = stage
        pipeline.last_update_time = current_time
        
        # Mark stage as completed if not already
        if stage not in pipeline.stages_completed:
            pipeline.stages_completed.append(stage)
            PIPELINE_STAGES_COMPLETED.labels(stage=stage).inc()
            
            # Remove from pending
            if stage in pipeline.stages_pending:
                pipeline.stages_pending.remove(stage)
                
            # Publish stage completed event
            await self.publish_orchestration_event("stage_completed", pipeline_id, stage, {
                "stage": stage,
                "completion_time": current_time,
                "duration": current_time - pipeline.start_time
            })
            
        # Check if pipeline is complete
        if len(pipeline.stages_completed) >= len(self.stage_order):
            pipeline.status = "completed"
            pipeline.total_duration = current_time - pipeline.start_time
            PIPELINE_DURATION.observe(pipeline.total_duration)
            ACTIVE_PIPELINES.dec()
            
            # Publish pipeline completed event
            await self.publish_orchestration_event("pipeline_completed", pipeline_id, stage, {
                "pipeline_id": pipeline_id,
                "total_duration": pipeline.total_duration,
                "stages_completed": pipeline.stages_completed
            })
            
        # Check for stalled pipelines (no updates for 10 minutes)
        elif current_time - pipeline.last_update_time > 600:
            pipeline.status = "stalled"
            await self.publish_orchestration_event("pipeline_stalled", pipeline_id, stage, {
                "pipeline_id": pipeline_id,
                "last_update": pipeline.last_update_time,
                "current_stage": pipeline.current_stage
            })
            
    async def publish_orchestration_event(self, event_type: str, pipeline_id: str, stage: str, data: Dict[str, Any]):
        """Publish orchestration events"""
        try:
            event = OrchestrationEvent(
                event_id=f"event_{int(time.time())}_{hash(pipeline_id) % 10000}",
                event_type=event_type,
                pipeline_id=pipeline_id,
                stage=stage,
                data=data,
                timestamp=time.time()
            )
            
            await self.messaging_client.publish(PUBLISH_TOPIC, event.dict())
            logger.info(f"Published {event_type} event for pipeline {pipeline_id}")
            
        except Exception as e:
            ORCHESTRATOR_ERRORS.labels(error_type="event_publishing").inc()
            logger.error(f"Failed to publish orchestration event: {e}")
            
    async def pipeline_monitoring_loop(self):
        """Background task to monitor pipeline health"""
        while self.is_running:
            try:
                current_time = time.time()
                
                for pipeline_id, pipeline in self.active_pipelines.items():
                    # Check for stalled pipelines
                    if pipeline.status == "running" and current_time - pipeline.last_update_time > 300:  # 5 minutes
                        logger.warning(f"Pipeline {pipeline_id} may be stalled - no updates for {current_time - pipeline.last_update_time:.0f}s")
                        
                        # Update status to stalled if over 10 minutes
                        if current_time - pipeline.last_update_time > 600:
                            pipeline.status = "stalled"
                            await self.publish_orchestration_event("pipeline_stalled", pipeline_id, pipeline.current_stage, {
                                "pipeline_id": pipeline_id,
                                "stall_duration": current_time - pipeline.last_update_time
                            })
                            
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in pipeline monitoring loop: {e}")
                await asyncio.sleep(60)
                
    async def agent_health_monitoring_loop(self):
        """Background task to monitor agent health"""
        while self.is_running:
            try:
                # This would typically ping each agent's health endpoint
                # For now, we'll track based on message activity
                current_time = time.time()
                
                # Simulate agent health based on recent message activity
                agent_activity = defaultdict(int)
                recent_messages = [msg for msg in self.message_history if current_time - msg.timestamp < 300]  # Last 5 minutes
                
                for msg in recent_messages:
                    agent_name = msg.data.get("metadata", {}).get("agent", f"{msg.stage}-agent")
                    agent_activity[agent_name] += 1
                    
                # Update agent health metrics
                for agent_name, activity in agent_activity.items():
                    health_score = min(1.0, activity / 10.0)  # Normalize to 0-1
                    AGENT_HEALTH_STATUS.labels(agent=agent_name).set(health_score)
                    
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                logger.error(f"Error in agent health monitoring loop: {e}")
                await asyncio.sleep(120)
                
    async def cleanup_old_pipelines_loop(self):
        """Background task to cleanup old completed pipelines"""
        while self.is_running:
            try:
                current_time = time.time()
                cutoff_time = current_time - 3600  # Keep pipelines for 1 hour
                
                pipelines_to_remove = []
                for pipeline_id, pipeline in self.active_pipelines.items():
                    if pipeline.status in ["completed", "failed"] and pipeline.last_update_time < cutoff_time:
                        pipelines_to_remove.append(pipeline_id)
                        
                for pipeline_id in pipelines_to_remove:
                    del self.active_pipelines[pipeline_id]
                    logger.info(f"Cleaned up old pipeline {pipeline_id}")
                    
                await asyncio.sleep(1800)  # Cleanup every 30 minutes
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(1800)
                
    async def broadcast_to_websockets(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
            
        disconnected = set()
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(message)
            except:
                disconnected.add(websocket)
                
        # Remove disconnected clients
        self.websocket_connections -= disconnected

# Global agent instance
orchestrator_agent = OrchestratorAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the agent lifecycle"""
    await orchestrator_agent.start()
    yield
    await orchestrator_agent.stop()

# FastAPI app
app = FastAPI(
    title="Orchestrator Agent", 
    description="Coordinates the entire multi-agent pipeline",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "orchestrator-agent",
        "is_running": orchestrator_agent.is_running,
        "subscribe_topics": SUBSCRIBE_TOPICS,
        "publish_topic": PUBLISH_TOPIC,
        "active_pipelines": len(orchestrator_agent.active_pipelines),
        "websocket_connections": len(orchestrator_agent.websocket_connections)
    }

@app.get("/health/liveness")
async def liveness():
    """Kubernetes liveness probe"""
    return {"status": "alive"}

@app.get("/health/readiness") 
async def readiness():
    """Kubernetes readiness probe"""
    is_ready = orchestrator_agent.is_running and orchestrator_agent.messaging_client is not None
    if not is_ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from fastapi import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/status")
async def status():
    """Get current orchestrator status"""
    return {
        "agent": "orchestrator-agent",
        "is_running": orchestrator_agent.is_running,
        "topics": {
            "subscribe": SUBSCRIBE_TOPICS,
            "publish": PUBLISH_TOPIC
        },
        "pipelines": {
            "active": len(orchestrator_agent.active_pipelines),
            "total_processed": len(orchestrator_agent.message_history)
        },
        "websockets": {
            "active_connections": len(orchestrator_agent.websocket_connections)
        },
        "metrics": {
            "messages_received": getattr(getattr(PIPELINE_MESSAGES_RECEIVED, '_value', None), 'value', 0),
            "stages_completed": getattr(getattr(PIPELINE_STAGES_COMPLETED, '_value', None), 'value', 0),
            "active_pipelines": getattr(getattr(ACTIVE_PIPELINES, '_value', None), 'value', 0),
            "errors": getattr(getattr(ORCHESTRATOR_ERRORS, '_value', None), 'value', 0)
        }
    }

@app.get("/pipelines")
async def get_pipelines():
    """Get all active pipelines"""
    return {
        "active_pipelines": {
            pid: pipeline.dict() for pid, pipeline in orchestrator_agent.active_pipelines.items()
        },
        "recent_messages": [msg.dict() for msg in orchestrator_agent.message_history[-50:]]
    }

@app.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """Get specific pipeline details"""
    if pipeline_id not in orchestrator_agent.active_pipelines:
        raise HTTPException(status_code=404, detail="Pipeline not found")
        
    pipeline = orchestrator_agent.active_pipelines[pipeline_id]
    related_messages = [msg for msg in orchestrator_agent.message_history if pipeline_id in str(msg.data)]
    
    return {
        "pipeline": pipeline.dict(),
        "messages": [msg.dict() for msg in related_messages]
    }

@app.get("/")
async def dashboard():
    """Simple HTML dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Multi-Agent Pipeline Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .pipeline { border: 1px solid #ccc; margin: 10px; padding: 10px; border-radius: 5px; }
            .stage { display: inline-block; margin: 5px; padding: 5px 10px; border-radius: 3px; }
            .completed { background-color: #d4edda; }
            .running { background-color: #fff3cd; }
            .pending { background-color: #f8d7da; }
            #messages { height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; }
        </style>
    </head>
    <body>
        <h1>Multi-Agent Pipeline Dashboard</h1>
        <div id="status"></div>
        <div id="pipelines"></div>
        <h3>Recent Messages</h3>
        <div id="messages"></div>
        
        <script>
            const ws = new WebSocket('ws://localhost:8000/ws');
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            function updateDashboard(data) {
                const messages = document.getElementById('messages');
                messages.innerHTML += '<div>' + JSON.stringify(data) + '</div>';
                messages.scrollTop = messages.scrollHeight;
            }
            
            // Fetch initial status
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').innerHTML = 
                        '<h3>Status: ' + (data.is_running ? 'Running' : 'Stopped') + '</h3>' +
                        '<p>Active Pipelines: ' + data.pipelines.active + '</p>';
                });
                
            // Fetch pipelines
            fetch('/pipelines')
                .then(response => response.json())
                .then(data => {
                    let html = '';
                    for (const [id, pipeline] of Object.entries(data.active_pipelines)) {
                        html += '<div class="pipeline">';
                        html += '<h4>Pipeline: ' + id + '</h4>';
                        html += '<p>Status: ' + pipeline.status + '</p>';
                        html += '<p>Current Stage: ' + pipeline.current_stage + '</p>';
                        html += '</div>';
                    }
                    document.getElementById('pipelines').innerHTML = html;
                });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await websocket.accept()
    orchestrator_agent.websocket_connections.add(websocket)
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "status",
            "data": {
                "active_pipelines": len(orchestrator_agent.active_pipelines),
                "recent_messages": len(orchestrator_agent.message_history)
            }
        })
        
        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        orchestrator_agent.websocket_connections.discard(websocket)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8000,
        log_level=LOG_LEVEL.lower(),
        reload=False
    )