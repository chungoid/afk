#!/usr/bin/env python3
"""
API Gateway - Main entry point for the multi-agent pipeline.
Receives user requests and initiates the pipeline flow.
Publishes to: tasks.analysis
"""

import asyncio
import os
import json
import logging
import uuid
import time
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Import the existing messaging infrastructure
import sys
sys.path.append('/app')
from src.common.messaging import create_messaging_client, MessagingClient
from src.common.config import Settings

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("api-gateway")

# Prometheus metrics
REQUESTS_TOTAL = Counter('gateway_requests_total', 'Total API requests', ['endpoint', 'method', 'status'])
REQUEST_DURATION = Histogram('gateway_request_duration_seconds', 'Request processing time')
ACTIVE_PIPELINES = Gauge('gateway_active_pipelines', 'Number of active pipelines initiated')
PIPELINE_SUBMISSIONS = Counter('gateway_pipeline_submissions_total', 'Total pipeline submissions', ['status'])

# Configuration
PUBLISH_TOPIC = os.getenv("PUBLISH_TOPIC", "tasks.analysis")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator-agent:8000")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Pydantic models
class ProjectRequest(BaseModel):
    """User project request"""
    project_name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=10, max_length=5000)
    requirements: List[str] = Field(default_factory=list, max_items=50)
    constraints: List[str] = Field(default_factory=list, max_items=20)
    priority: str = Field(default="medium", regex="^(low|medium|high|urgent)$")
    deadline: Optional[str] = None
    technology_preferences: List[str] = Field(default_factory=list, max_items=10)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PipelineStatus(BaseModel):
    """Pipeline status response"""
    request_id: str
    status: str  # "submitted", "processing", "completed", "failed"
    current_stage: str
    stages_completed: List[str]
    stages_pending: List[str]
    created_at: float
    updated_at: float
    estimated_completion: Optional[float] = None
    error_message: Optional[str] = None

class SubmissionResponse(BaseModel):
    """Response when submitting a new request"""
    request_id: str
    status: str
    message: str
    dashboard_url: str
    api_status_url: str

class APIGateway:
    """
    API Gateway that serves as the main entry point for the multi-agent pipeline
    """
    
    def __init__(self):
        self.messaging_client: Optional[MessagingClient] = None
        self.is_running = False
        
        # Track active requests
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        
    async def start(self):
        """Initialize the messaging client"""
        logger.info("Starting API Gateway...")
        
        # Initialize messaging client 
        self.messaging_client = create_messaging_client()
        await self.messaging_client.start()
        
        self.is_running = True
        logger.info("API Gateway started")
        
    async def stop(self):
        """Stop the messaging client"""
        logger.info("Stopping API Gateway...")
        self.is_running = False
        if self.messaging_client:
            await self.messaging_client.stop()
        logger.info("API Gateway stopped")
        
    async def submit_project_request(self, request: ProjectRequest) -> str:
        """Submit a project request to the analysis pipeline"""
        request_id = f"req_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        
        # Create analysis request message
        analysis_request = {
            "request_id": request_id,
            "project_description": request.description,
            "requirements": request.requirements,
            "constraints": request.constraints,
            "metadata": {
                "project_name": request.project_name,
                "priority": request.priority,
                "deadline": request.deadline,
                "technology_preferences": request.technology_preferences,
                "submitted_at": time.time(),
                "source": "api-gateway",
                **request.metadata
            }
        }
        
        # Track the request
        self.active_requests[request_id] = {
            "status": "submitted",
            "created_at": time.time(),
            "updated_at": time.time(),
            "original_request": request.dict()
        }
        
        # Publish to analysis topic
        await self.messaging_client.publish(PUBLISH_TOPIC, analysis_request)
        
        # Update metrics
        ACTIVE_PIPELINES.inc()
        PIPELINE_SUBMISSIONS.labels(status="success").inc()
        
        logger.info(f"Submitted project request {request_id}: {request.project_name}")
        return request_id

# Global gateway instance
api_gateway = APIGateway()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the gateway lifecycle"""
    await api_gateway.start()
    yield
    await api_gateway.stop()

# FastAPI app
app = FastAPI(
    title="Multi-Agent Pipeline API Gateway", 
    description="Entry point for the multi-agent software development pipeline",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Multi-Agent Pipeline API Gateway",
        "status": "running" if api_gateway.is_running else "stopped",
        "version": "1.0.0",
        "endpoints": {
            "submit": "/submit",
            "status": "/status/{request_id}",
            "dashboard": "/dashboard",
            "health": "/health",
            "metrics": "/metrics"
        }
    }

@app.post("/submit", response_model=SubmissionResponse)
async def submit_project(request: ProjectRequest):
    """Submit a new project for the multi-agent pipeline"""
    try:
        with REQUEST_DURATION.time():
            request_id = await api_gateway.submit_project_request(request)
            
        REQUESTS_TOTAL.labels(endpoint="submit", method="POST", status="success").inc()
        
        return SubmissionResponse(
            request_id=request_id,
            status="submitted",
            message=f"Project '{request.project_name}' submitted successfully",
            dashboard_url=f"{ORCHESTRATOR_URL}/dashboard",
            api_status_url=f"/status/{request_id}"
        )
        
    except Exception as e:
        REQUESTS_TOTAL.labels(endpoint="submit", method="POST", status="error").inc()
        PIPELINE_SUBMISSIONS.labels(status="error").inc()
        logger.error(f"Failed to submit project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{request_id}", response_model=PipelineStatus)
async def get_request_status(request_id: str):
    """Get the status of a specific request"""
    try:
        if request_id not in api_gateway.active_requests:
            raise HTTPException(status_code=404, detail="Request not found")
            
        request_data = api_gateway.active_requests[request_id]
        
        REQUESTS_TOTAL.labels(endpoint="status", method="GET", status="success").inc()
        
        return PipelineStatus(
            request_id=request_id,
            status=request_data["status"],
            current_stage=request_data.get("current_stage", "analysis"),
            stages_completed=request_data.get("stages_completed", []),
            stages_pending=request_data.get("stages_pending", ["analysis", "planning", "blueprint", "coding", "testing"]),
            created_at=request_data["created_at"],
            updated_at=request_data["updated_at"],
            estimated_completion=request_data.get("estimated_completion"),
            error_message=request_data.get("error_message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        REQUESTS_TOTAL.labels(endpoint="status", method="GET", status="error").inc()
        logger.error(f"Failed to get status for {request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/requests")
async def list_requests():
    """List all active requests"""
    try:
        REQUESTS_TOTAL.labels(endpoint="requests", method="GET", status="success").inc()
        
        return {
            "active_requests": len(api_gateway.active_requests),
            "requests": [
                {
                    "request_id": req_id,
                    "project_name": data["original_request"]["project_name"],
                    "status": data["status"],
                    "created_at": data["created_at"],
                    "updated_at": data["updated_at"]
                }
                for req_id, data in api_gateway.active_requests.items()
            ]
        }
        
    except Exception as e:
        REQUESTS_TOTAL.labels(endpoint="requests", method="GET", status="error").inc()
        logger.error(f"Failed to list requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "is_running": api_gateway.is_running,
        "publish_topic": PUBLISH_TOPIC,
        "active_requests": len(api_gateway.active_requests)
    }

@app.get("/health/liveness")
async def liveness():
    """Kubernetes liveness probe"""
    return {"status": "alive"}

@app.get("/health/readiness") 
async def readiness():
    """Kubernetes readiness probe"""
    is_ready = api_gateway.is_running and api_gateway.messaging_client is not None
    if not is_ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from fastapi.responses import Response
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Simple submission dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Multi-Agent Pipeline</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 20px; 
                background-color: #f5f5f5;
            }
            .container { 
                max-width: 800px; 
                margin: 0 auto; 
                background: white; 
                padding: 20px; 
                border-radius: 8px; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .form-group { 
                margin-bottom: 15px; 
            }
            label { 
                display: block; 
                margin-bottom: 5px; 
                font-weight: bold;
            }
            input, textarea, select { 
                width: 100%; 
                padding: 8px; 
                border: 1px solid #ccc; 
                border-radius: 4px;
                box-sizing: border-box;
            }
            textarea { 
                height: 100px; 
                resize: vertical;
            }
            button { 
                background-color: #007bff; 
                color: white; 
                padding: 10px 20px; 
                border: none; 
                border-radius: 4px; 
                cursor: pointer;
                font-size: 16px;
            }
            button:hover { 
                background-color: #0056b3; 
            }
            .status { 
                margin-top: 20px; 
                padding: 10px; 
                border-radius: 4px;
            }
            .success { 
                background-color: #d4edda; 
                color: #155724; 
                border: 1px solid #c3e6cb;
            }
            .error { 
                background-color: #f8d7da; 
                color: #721c24; 
                border: 1px solid #f5c6cb;
            }
            .requests-list {
                margin-top: 30px;
            }
            .request-item {
                padding: 10px;
                margin: 10px 0;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f9f9f9;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Multi-Agent Pipeline</h1>
            <p>Submit your software project requirements and let our AI agents handle the development!</p>
            
            <form id="projectForm">
                <div class="form-group">
                    <label for="projectName">Project Name:</label>
                    <input type="text" id="projectName" name="projectName" required>
                </div>
                
                <div class="form-group">
                    <label for="description">Project Description:</label>
                    <textarea id="description" name="description" required 
                        placeholder="Describe your project requirements in detail..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="requirements">Requirements (one per line):</label>
                    <textarea id="requirements" name="requirements" 
                        placeholder="User authentication&#10;REST API with CRUD operations&#10;PostgreSQL database&#10;Docker deployment"></textarea>
                </div>
                
                <div class="form-group">
                    <label for="priority">Priority:</label>
                    <select id="priority" name="priority">
                        <option value="low">Low</option>
                        <option value="medium" selected>Medium</option>
                        <option value="high">High</option>
                        <option value="urgent">Urgent</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="technologies">Technology Preferences (comma-separated):</label>
                    <input type="text" id="technologies" name="technologies" 
                        placeholder="Python, FastAPI, React, PostgreSQL">
                </div>
                
                <button type="submit">🚀 Launch Pipeline</button>
            </form>
            
            <div id="status"></div>
            
            <div class="requests-list">
                <h3>Recent Submissions</h3>
                <div id="requestsList"></div>
                <button type="button" onclick="loadRequests()">🔄 Refresh</button>
            </div>
        </div>
        
        <script>
            document.getElementById('projectForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const requirements = formData.get('requirements').split('\\n').filter(r => r.trim());
                const technologies = formData.get('technologies').split(',').map(t => t.trim()).filter(t => t);
                
                const projectData = {
                    project_name: formData.get('projectName'),
                    description: formData.get('description'),
                    requirements: requirements,
                    priority: formData.get('priority'),
                    technology_preferences: technologies
                };
                
                try {
                    const response = await fetch('/submit', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(projectData)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        document.getElementById('status').innerHTML = 
                            '<div class="status success">' +
                            '<h4>✅ Project Submitted Successfully!</h4>' +
                            '<p>Request ID: ' + result.request_id + '</p>' +
                            '<p><a href="' + result.dashboard_url + '" target="_blank">View Dashboard</a></p>' +
                            '<p><a href="' + result.api_status_url + '" target="_blank">Check Status</a></p>' +
                            '</div>';
                        e.target.reset();
                        loadRequests();
                    } else {
                        throw new Error(result.detail || 'Submission failed');
                    }
                } catch (error) {
                    document.getElementById('status').innerHTML = 
                        '<div class="status error">' +
                        '<h4>❌ Submission Failed</h4>' +
                        '<p>' + error.message + '</p>' +
                        '</div>';
                }
            });
            
            async function loadRequests() {
                try {
                    const response = await fetch('/requests');
                    const data = await response.json();
                    
                    const requestsList = document.getElementById('requestsList');
                    requestsList.innerHTML = '';
                    
                    if (data.requests.length === 0) {
                        requestsList.innerHTML = '<p>No active requests</p>';
                        return;
                    }
                    
                    data.requests.forEach(request => {
                        const div = document.createElement('div');
                        div.className = 'request-item';
                        div.innerHTML = 
                            '<strong>' + request.project_name + '</strong> ' +
                            '<span style="float: right">' + request.status + '</span><br>' +
                            '<small>ID: ' + request.request_id + '</small><br>' +
                            '<small>Created: ' + new Date(request.created_at * 1000).toLocaleString() + '</small>';
                        requestsList.appendChild(div);
                    });
                } catch (error) {
                    console.error('Failed to load requests:', error);
                }
            }
            
            // Load requests on page load
            loadRequests();
            
            // Auto-refresh every 30 seconds
            setInterval(loadRequests, 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8000,
        log_level=LOG_LEVEL.lower(),
        reload=False
    )