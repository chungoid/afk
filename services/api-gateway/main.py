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

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Import the existing messaging infrastructure
import sys
sys.path.append('/app')
from src.common.messaging_simple import create_messaging_client, MessagingClient
from src.common.config import Settings
from src.common.file_handler import FileHandler, ProjectFiles, process_uploaded_zip, process_git_repo, process_file_dict
from src.common.tracing import setup_agent_tracing, trace_operation
from dataclasses import asdict

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("api-gateway")

# Prometheus metrics - with unique names to avoid conflicts
try:
    REQUESTS_TOTAL = Counter(
        'api_gateway_requests_total',
        'Total number of API requests',
        ['method', 'endpoint', 'status']
    )
    REQUEST_DURATION = Histogram(
        'api_gateway_request_duration_seconds',
        'API request duration',
        ['method', 'endpoint']
    )
    ACTIVE_PIPELINES = Gauge(
        'api_gateway_active_pipelines',
        'Number of currently active pipelines'
    )
    PIPELINE_SUBMISSIONS = Counter(
        'api_gateway_pipeline_submissions_total',
        'Total number of pipeline submissions',
        ['status']
    )
except Exception as e:
    logger.warning(f"Error initializing metrics, using dummy metrics: {e}")
    # Fallback to avoid startup issues
    class DummyMetric:
        def inc(self): pass
        def dec(self): pass
        def observe(self, value): pass
        def labels(self, **kwargs): return self
        def time(self): return self
        def __enter__(self): return self
        def __exit__(self, *args): pass

    REQUESTS_TOTAL = DummyMetric()
    REQUEST_DURATION = DummyMetric()
    ACTIVE_PIPELINES = DummyMetric()
    PIPELINE_SUBMISSIONS = DummyMetric()

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
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    deadline: Optional[str] = None
    technology_preferences: List[str] = Field(default_factory=list, max_items=10)
    
    # Project source options
    project_type: str = Field(default="new", pattern="^(new|existing_git|existing_local)$")
    
    # Git repository options
    git_url: Optional[str] = None
    git_branch: Optional[str] = "main"
    git_credentials: Optional[Dict[str, str]] = None
    
    # Local project hints
    main_language: Optional[str] = None
    framework: Optional[str] = None
    ignore_patterns: List[str] = Field(default_factory=list)
    
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
        
        # Initialize tracing
        self.tracer = None
        
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
        
    async def submit_project_request(self, request: ProjectRequest, project_files: Optional[ProjectFiles] = None) -> str:
        """Submit a project request to the analysis pipeline"""
        request_id = f"req_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        
        # Create trace for this operation
        with trace_operation(self.tracer, "submit_project_request", 
                           request_id=request_id, 
                           project_name=request.project_name,
                           project_type=request.project_type):
            
            # Create analysis request message
            analysis_request = {
                "request_id": request_id,
                "project_description": request.description,
                "requirements": request.requirements,
                "constraints": request.constraints,
                "project_type": request.project_type,
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
        
        # Add project files if provided
        if project_files:
            analysis_request["project_files"] = {
                "files": project_files.files,
                "metadata": project_files.metadata,
                "source_type": project_files.source_type,
                "total_files": project_files.total_files,
                "total_size": project_files.total_size,
                "detected_language": project_files.detected_language,
                "detected_framework": project_files.detected_framework,
                "project_structure": project_files.project_structure
            }
        
        # Add Git information if applicable
        if request.project_type == "existing_git" and request.git_url:
            analysis_request["git_info"] = {
                "git_url": request.git_url,
                "git_branch": request.git_branch,
                "git_credentials": request.git_credentials
            }
        
        # Track the request
        self.active_requests[request_id] = {
            "status": "submitted",
            "created_at": time.time(),
            "updated_at": time.time(),
            "original_request": request.model_dump(),
            "project_files": asdict(project_files) if project_files else None
        }
        
        # Publish to analysis topic
        await self.messaging_client.publish(PUBLISH_TOPIC, analysis_request)
        
        # Update metrics
        ACTIVE_PIPELINES.inc()
        PIPELINE_SUBMISSIONS.labels(status="success").inc()
        
        logger.info(f"Submitted project request {request_id}: {request.project_name} (type: {request.project_type})")
        return request_id
        
    async def submit_project_with_files(self, request: ProjectRequest, uploaded_files: Optional[ProjectFiles]) -> str:
        """Submit a project with uploaded files"""
        return await self.submit_project_request(request, uploaded_files)

# Global gateway instance
api_gateway = APIGateway()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the gateway lifecycle"""
    # Initialize tracing before starting
    api_gateway.tracer = setup_agent_tracing("api-gateway", app)
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

@app.post("/submit_with_files", response_model=SubmissionResponse)
async def submit_project_with_files(
    project_data: str = Form(...),  # JSON string of ProjectRequest
    project_files: Optional[UploadFile] = File(None)  # ZIP file
):
    """Submit a project with optional file upload"""
    try:
        # Parse project data
        project_request_data = json.loads(project_data)
        request = ProjectRequest(**project_request_data)
        
        # Handle file upload if provided
        uploaded_files = None
        if project_files and request.project_type == "existing_local":
            if not project_files.filename.lower().endswith('.zip'):
                raise HTTPException(status_code=400, detail="Only ZIP files are supported")
            
            if project_files.size and project_files.size > 50 * 1024 * 1024:  # 50MB limit
                raise HTTPException(status_code=400, detail="File too large (max 50MB)")
            
            # Read file content
            file_content = await project_files.read()
            
            # Process uploaded files using the file handler
            hints = {
                "ignore_patterns": request.ignore_patterns,
                "main_language": request.main_language,
                "framework": request.framework
            }
            uploaded_files = await process_uploaded_zip(file_content, project_files.filename, hints)
            
        elif request.project_type == "existing_git" and request.git_url:
            # Process Git repository
            hints = {
                "ignore_patterns": request.ignore_patterns,
                "main_language": request.main_language,
                "framework": request.framework
            }
            uploaded_files = await process_git_repo(
                git_url=request.git_url,
                branch=request.git_branch or "main",
                credentials=request.git_credentials,
                hints=hints
            )
        
        # Submit with uploaded files
        with REQUEST_DURATION.time():
            request_id = await api_gateway.submit_project_with_files(request, uploaded_files)
        
        REQUESTS_TOTAL.labels(endpoint="submit_with_files", method="POST", status="success").inc()
        
        file_info = ""
        if uploaded_files:
            file_info = f" with {uploaded_files.total_files} files ({uploaded_files.total_size} bytes)"
            if uploaded_files.detected_language:
                file_info += f", detected language: {uploaded_files.detected_language}"
            if uploaded_files.detected_framework:
                file_info += f", framework: {uploaded_files.detected_framework}"
        
        return SubmissionResponse(
            request_id=request_id,
            status="submitted",
            message=f"Project '{request.project_name}'{file_info} submitted successfully",
            dashboard_url=f"{ORCHESTRATOR_URL}/dashboard",
            api_status_url=f"/status/{request_id}"
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid project data JSON")
    except Exception as e:
        REQUESTS_TOTAL.labels(endpoint="submit_with_files", method="POST", status="error").inc()
        PIPELINE_SUBMISSIONS.labels(status="error").inc()
        logger.error(f"Failed to submit project with files: {e}")
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
    from fastapi import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Modern professional dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Multi-Agent Development Pipeline</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            .gradient-bg {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .card-hover {
                transition: all 0.3s ease;
            }
            .card-hover:hover {
                transform: translateY(-2px);
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            }
            .status-indicator {
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .nav-link {
                transition: all 0.2s ease;
            }
            .nav-link:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            .grafana-dropdown:hover .dropdown-menu {
                opacity: 1;
                visibility: visible;
                transform: translateY(0);
            }
            .dropdown-menu {
                transform: translateY(-10px);
            }
            .form-input {
                border: 2px solid #e5e7eb;
                transition: border-color 0.2s ease, box-shadow 0.2s ease;
            }
            .form-input:focus {
                outline: none;
                border-color: #6366f1;
                box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
            }
        </style>
    </head>
    <body class="bg-gray-100">
        <!-- Navigation Header -->
        <nav class="gradient-bg shadow-lg">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between h-16">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <h1 class="text-xl font-bold text-white">Multi-Agent Development Pipeline</h1>
                        </div>
                    </div>
                    <div class="flex items-center space-x-4">
                        <a href="#submit" class="nav-link text-white px-3 py-2 rounded-md text-sm font-medium">Submit Project</a>
                        <a href="#monitoring" class="nav-link text-white px-3 py-2 rounded-md text-sm font-medium">Monitoring</a>
                        <a href="#projects" class="nav-link text-white px-3 py-2 rounded-md text-sm font-medium">Projects</a>
                        <div id="statusIndicator" class="flex items-center">
                            <div class="w-3 h-3 bg-green-400 rounded-full status-indicator mr-2"></div>
                            <span class="text-white text-sm">System Online</span>
                        </div>
                    </div>
                </div>
            </div>
        </nav>

        <!-- Main Content -->
        <div class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            <!-- System Status Cards -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div class="bg-white overflow-hidden shadow rounded-lg card-hover">
                    <div class="p-5">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <i class="fas fa-server text-blue-500 text-2xl"></i>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">Active Agents</dt>
                                    <dd id="activeAgents" class="text-lg font-medium text-gray-900">6</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="bg-white overflow-hidden shadow rounded-lg card-hover">
                    <div class="p-5">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <i class="fas fa-tasks text-green-500 text-2xl"></i>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">Active Projects</dt>
                                    <dd id="activeProjects" class="text-lg font-medium text-gray-900">0</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="bg-white overflow-hidden shadow rounded-lg card-hover">
                    <div class="p-5">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <i class="fas fa-clock text-yellow-500 text-2xl"></i>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">Queue Status</dt>
                                    <dd id="queueStatus" class="text-lg font-medium text-gray-900">Idle</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="bg-white overflow-hidden shadow rounded-lg card-hover">
                    <div class="p-5">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <i class="fas fa-chart-line text-purple-500 text-2xl"></i>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">System Health</dt>
                                    <dd class="text-lg font-medium text-green-600">Healthy</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Quick Access Links -->
            <div id="monitoring" class="bg-white shadow rounded-lg mb-8">
                <div class="px-4 py-5 sm:p-6">
                    <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Monitoring & Analytics</h3>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div class="relative grafana-dropdown">
                            <a href="http://localhost:3001/dashboards" target="_blank" class="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 card-hover">
                                <i class="fas fa-chart-bar text-orange-500 text-xl mr-3"></i>
                                <div>
                                    <p class="text-sm font-medium text-gray-900">Grafana Dashboards</p>
                                    <p class="text-sm text-gray-500">System metrics & visualization</p>
                                </div>
                                <i class="fas fa-chevron-down text-gray-400 ml-auto"></i>
                            </a>
                            <!-- Dropdown menu -->
                            <div class="dropdown-menu absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible transition-all duration-200 z-10">
                                <div class="p-2">
                                    <a href="http://localhost:3001/d/4f8b233e-ccab-4535-82ca-7f0b139f9945/multi-agent-pipeline-monitoring" target="_blank" class="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md">
                                        <i class="fas fa-robot mr-2 text-blue-500"></i>Multi-Agent Pipeline Monitoring
                                    </a>
                                    <a href="http://localhost:3001/d/5ff87470-568f-4af5-ae74-17c2b7d647c8/rabbitmq-message-queue-monitoring" target="_blank" class="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md">
                                        <i class="fas fa-exchange-alt mr-2 text-purple-500"></i>RabbitMQ Message Queue Monitoring
                                    </a>
                                    <a href="http://localhost:3001/d/743fb8f9-423a-44c5-8f68-0ae0fb9dff42/rabbitmq-system-monitoring-simple" target="_blank" class="block px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md">
                                        <i class="fas fa-server mr-2 text-orange-500"></i>RabbitMQ System Monitoring
                                        <span class="text-xs text-blue-600 ml-1">Simplified</span>
                                    </a>
                                    <div class="border-t border-gray-100 my-1"></div>
                                    <a href="http://localhost:3001/dashboards" target="_blank" class="block px-3 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50 rounded-md">
                                        <i class="fas fa-th-large mr-2"></i>All Dashboards
                                    </a>
                                    <a href="http://localhost:3001/?search=open" target="_blank" class="block px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-md">
                                        <i class="fas fa-search mr-2"></i>Search Dashboards
                                    </a>
                                </div>
                            </div>
                        </div>
                        <a href="http://localhost:9090" target="_blank" class="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 card-hover">
                            <i class="fas fa-database text-red-500 text-xl mr-3"></i>
                            <div>
                                <p class="text-sm font-medium text-gray-900">Prometheus Metrics</p>
                                <p class="text-sm text-gray-500">Raw metrics & queries</p>
                            </div>
                        </a>
                        <a href="http://localhost:15672" target="_blank" class="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 card-hover">
                            <i class="fas fa-exchange-alt text-blue-500 text-xl mr-3"></i>
                            <div>
                                <p class="text-sm font-medium text-gray-900">RabbitMQ Management</p>
                                <p class="text-sm text-gray-500">Message queue monitoring</p>
                            </div>
                        </a>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                        <a href="http://localhost:16686" target="_blank" class="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 card-hover">
                            <i class="fas fa-route text-green-500 text-xl mr-3"></i>
                            <div>
                                <p class="text-sm font-medium text-gray-900">Jaeger Tracing</p>
                                <p class="text-sm text-gray-500">Distributed request tracing</p>
                            </div>
                        </a>
                        <a href="/docs" target="_blank" class="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 card-hover">
                            <i class="fas fa-book text-indigo-500 text-xl mr-3"></i>
                            <div>
                                <p class="text-sm font-medium text-gray-900">API Documentation</p>
                                <p class="text-sm text-gray-500">Interactive API explorer</p>
                            </div>
                        </a>
                    </div>
                </div>
            </div>

            <!-- Project Submission Form -->
            <div id="submit" class="bg-white shadow rounded-lg mb-8">
                <div class="px-4 py-5 sm:p-6">
                    <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">Submit New Project</h3>
                    <form id="projectForm" class="space-y-6">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label for="projectName" class="block text-sm font-medium text-gray-700 mb-2">Project Name</label>
                                <input type="text" id="projectName" name="projectName" required
                                    placeholder="Enter your project name"
                                    class="form-input block w-full rounded-md shadow-sm sm:text-sm">
                            </div>
                            <div>
                                <label for="priority" class="block text-sm font-medium text-gray-700 mb-2">Priority</label>
                                <select id="priority" name="priority"
                                    class="form-input block w-full rounded-md shadow-sm sm:text-sm">
                                    <option value="low">Low</option>
                                    <option value="medium" selected>Medium</option>
                                    <option value="high">High</option>
                                    <option value="urgent">Urgent</option>
                                </select>
                            </div>
                        </div>

                        <div>
                            <label for="description" class="block text-sm font-medium text-gray-700 mb-2">Project Description</label>
                            <textarea id="description" name="description" rows="3" required
                                placeholder="Describe your project requirements in detail..."
                                class="form-input block w-full rounded-md shadow-sm sm:text-sm"></textarea>
                        </div>

                        <div>
                            <label for="requirements" class="block text-sm font-medium text-gray-700 mb-2">Requirements (one per line)</label>
                            <textarea id="requirements" name="requirements" rows="4"
                                placeholder="User authentication&#10;REST API with CRUD operations&#10;PostgreSQL database&#10;Docker deployment"
                                class="form-input block w-full rounded-md shadow-sm sm:text-sm"></textarea>
                        </div>

                        <div>
                            <label for="technologies" class="block text-sm font-medium text-gray-700 mb-2">Technology Preferences</label>
                            <input type="text" id="technologies" name="technologies"
                                placeholder="Python, FastAPI, React, PostgreSQL"
                                class="form-input block w-full rounded-md shadow-sm sm:text-sm">
                        </div>

                        <div>
                            <button type="submit"
                                class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                                <i class="fas fa-rocket mr-2"></i>
                                Launch Development Pipeline
                            </button>
                        </div>
                    </form>

                    <!-- Status Message -->
                    <div id="submissionStatus" class="mt-4 hidden"></div>
                </div>
            </div>

            <!-- Recent Projects -->
            <div id="projects" class="bg-white shadow rounded-lg">
                <div class="px-4 py-5 sm:p-6">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg leading-6 font-medium text-gray-900">Recent Projects</h3>
                        <button onclick="loadProjects()" class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                            <i class="fas fa-sync-alt mr-2"></i>
                            Refresh
                        </button>
                    </div>
                    <div id="projectsList" class="space-y-4">
                        <div class="text-center py-8 text-gray-500">
                            <i class="fas fa-folder-open text-4xl mb-2"></i>
                            <p>No projects submitted yet</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- JavaScript -->
        <script>
            // Form submission handler
            document.getElementById('projectForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const statusDiv = document.getElementById('submissionStatus');
                statusDiv.className = 'mt-4 p-4 rounded-md';
                statusDiv.innerHTML = '<div class="flex items-center"><i class="fas fa-spinner fa-spin mr-2"></i>Submitting project...</div>';
                statusDiv.classList.remove('hidden');
                
                const formData = new FormData(e.target);
                const requirements = formData.get('requirements').split('\\n').filter(r => r.trim());
                const technologies = formData.get('technologies').split(',').map(t => t.trim()).filter(t => t);
                
                const projectData = {
                    project_name: formData.get('projectName'),
                    description: formData.get('description'),
                    requirements: requirements,
                    priority: formData.get('priority'),
                    technology_preferences: technologies,
                    project_type: 'new'
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
                        statusDiv.className = 'mt-4 p-4 rounded-md bg-green-50 border border-green-200';
                        statusDiv.innerHTML = `
                            <div class="flex">
                                <i class="fas fa-check-circle text-green-400 mr-2 mt-0.5"></i>
                                <div>
                                    <h4 class="text-sm font-medium text-green-800">Project Submitted Successfully!</h4>
                                    <div class="mt-2 text-sm text-green-700">
                                        <p>Request ID: <span class="font-mono">${result.request_id}</span></p>
                                        <p class="mt-1">${result.message}</p>
                                        <div class="mt-3 space-x-2">
                                            <a href="${result.api_status_url}" target="_blank" class="text-green-600 hover:text-green-500 underline">
                                                <i class="fas fa-external-link-alt mr-1"></i>Check Status
                                            </a>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                        e.target.reset();
                        loadProjects();
                        updateSystemStatus();
                    } else {
                        throw new Error(result.detail || 'Submission failed');
                    }
                } catch (error) {
                    statusDiv.className = 'mt-4 p-4 rounded-md bg-red-50 border border-red-200';
                    statusDiv.innerHTML = `
                        <div class="flex">
                            <i class="fas fa-exclamation-circle text-red-400 mr-2 mt-0.5"></i>
                            <div>
                                <h4 class="text-sm font-medium text-red-800">Submission Failed</h4>
                                <p class="mt-1 text-sm text-red-700">${error.message}</p>
                            </div>
                        </div>
                    `;
                }
            });

            // Load projects list
            async function loadProjects() {
                try {
                    const response = await fetch('/requests');
                    const data = await response.json();
                    
                    const projectsList = document.getElementById('projectsList');
                    
                    if (data.requests.length === 0) {
                        projectsList.innerHTML = `
                            <div class="text-center py-8 text-gray-500">
                                <i class="fas fa-folder-open text-4xl mb-2"></i>
                                <p>No projects submitted yet</p>
                            </div>
                        `;
                        return;
                    }
                    
                    projectsList.innerHTML = data.requests.map(request => `
                        <div class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                            <div class="flex justify-between items-start">
                                <div class="flex-1">
                                    <h4 class="text-sm font-medium text-gray-900">${request.project_name}</h4>
                                    <p class="text-sm text-gray-500 mt-1">ID: <span class="font-mono">${request.request_id}</span></p>
                                    <p class="text-sm text-gray-500">Created: ${new Date(request.created_at * 1000).toLocaleString()}</p>
                                </div>
                                <div class="ml-4">
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(request.status)}">
                                        ${request.status}
                                    </span>
                                </div>
                            </div>
                        </div>
                    `).join('');
                    
                    // Update active projects count
                    document.getElementById('activeProjects').textContent = data.requests.filter(r => !['completed', 'failed'].includes(r.status)).length;
                    
                } catch (error) {
                    console.error('Failed to load projects:', error);
                }
            }

            // Get status color classes
            function getStatusColor(status) {
                const colors = {
                    'submitted': 'bg-blue-100 text-blue-800',
                    'analysis': 'bg-yellow-100 text-yellow-800',
                    'planning': 'bg-purple-100 text-purple-800',
                    'blueprint': 'bg-indigo-100 text-indigo-800',
                    'coding': 'bg-orange-100 text-orange-800',
                    'testing': 'bg-pink-100 text-pink-800',
                    'completed': 'bg-green-100 text-green-800',
                    'failed': 'bg-red-100 text-red-800',
                    'cancelled': 'bg-gray-100 text-gray-800'
                };
                return colors[status] || 'bg-gray-100 text-gray-800';
            }

            // Update system status
            async function updateSystemStatus() {
                try {
                    // Check agent health
                    const agentHealth = await fetch('http://localhost:9090/api/v1/query?query=up{job=~".*-agent"}');
                    const agentData = await agentHealth.json();
                    const activeAgents = agentData.data.result.filter(r => r.value[1] === '1').length;
                    document.getElementById('activeAgents').textContent = activeAgents;

                    // Update status indicator
                    const statusIndicator = document.getElementById('statusIndicator');
                    if (activeAgents >= 6) {
                        statusIndicator.innerHTML = `
                            <div class="w-3 h-3 bg-green-400 rounded-full status-indicator mr-2"></div>
                            <span class="text-white text-sm">System Online</span>
                        `;
                    } else {
                        statusIndicator.innerHTML = `
                            <div class="w-3 h-3 bg-yellow-400 rounded-full status-indicator mr-2"></div>
                            <span class="text-white text-sm">Partial Service</span>
                        `;
                    }

                } catch (error) {
                    console.error('Failed to update system status:', error);
                    const statusIndicator = document.getElementById('statusIndicator');
                    statusIndicator.innerHTML = `
                        <div class="w-3 h-3 bg-red-400 rounded-full status-indicator mr-2"></div>
                        <span class="text-white text-sm">Status Unknown</span>
                    `;
                }
            }

            // Smooth scrolling for navigation links
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function (e) {
                    e.preventDefault();
                    const target = document.querySelector(this.getAttribute('href'));
                    if (target) {
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                });
            });

            // Load Grafana dashboard links dynamically
            async function loadGrafanaDashboards() {
                try {
                    // Try to get dashboard list from Grafana API with authentication
                    const response = await fetch('http://localhost:3001/api/search?type=dash-db', {
                        headers: {
                            'Authorization': 'Basic ' + btoa('admin:admin')
                        }
                    });
                    const dashboards = await response.json();
                    
                    // Update dropdown links with actual dashboard URLs
                    const dropdownLinks = [
                        { text: 'Multi-Agent Pipeline Monitoring', icon: 'fas fa-robot text-blue-500' },
                        { text: 'Pipeline Monitoring (Fixed)', icon: 'fas fa-tools text-green-500' },
                        { text: 'RabbitMQ Message Queue', icon: 'fas fa-exchange-alt text-purple-500' },
                        { text: 'RabbitMQ System (Simple)', icon: 'fas fa-server text-orange-500' }
                    ];
                    
                    const dropdown = document.querySelector('.dropdown-menu .p-2');
                    if (dropdown && dashboards.length > 0) {
                        // Clear existing links except separators and static ones
                        const staticLinks = dropdown.querySelectorAll('a[href*="dashboards"], a[href*="search"]');
                        dropdown.innerHTML = '';
                        
                        // Add dashboard links
                        dashboards.forEach(dashboard => {
                            if (dashboard.type === 'dash-db') {
                                const link = document.createElement('a');
                                link.href = `http://localhost:3001${dashboard.url}`;
                                link.target = '_blank';
                                link.className = 'block px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md';
                                
                                // Clean up dashboard names and add badges
                                let displayName = dashboard.title;
                                let icon = 'fas fa-chart-line text-gray-500';
                                let badge = '';
                                
                                if (dashboard.title.toLowerCase().includes('multi-agent') || dashboard.title.toLowerCase().includes('pipeline')) {
                                    displayName = 'Multi-Agent Pipeline Monitoring';
                                    icon = 'fas fa-robot text-blue-500';
                                } else if (dashboard.title.toLowerCase().includes('rabbitmq')) {
                                    if (dashboard.title.toLowerCase().includes('simple')) {
                                        displayName = 'RabbitMQ System Monitoring';
                                        icon = 'fas fa-server text-orange-500';
                                        badge = '<span class="text-xs text-blue-600 ml-1">Simplified</span>';
                                    } else {
                                        displayName = 'RabbitMQ Message Queue Monitoring';
                                        icon = 'fas fa-exchange-alt text-purple-500';
                                    }
                                }
                                
                                link.innerHTML = `<i class="${icon} mr-2"></i>${displayName} ${badge}`;
                                dropdown.appendChild(link);
                            }
                        });
                        
                        // Add separator
                        const separator = document.createElement('div');
                        separator.className = 'border-t border-gray-100 my-1';
                        dropdown.appendChild(separator);
                        
                        // Re-add static links
                        staticLinks.forEach(staticLink => {
                            dropdown.appendChild(staticLink.cloneNode(true));
                        });
                    }
                } catch (error) {
                    console.log('Could not load Grafana dashboards:', error);
                    // Links will remain as static fallback
                }
            }

            // Initialize page
            document.addEventListener('DOMContentLoaded', function() {
                loadProjects();
                updateSystemStatus();
                loadGrafanaDashboards();
                
                // Auto-refresh every 30 seconds
                setInterval(() => {
                    loadProjects();
                    updateSystemStatus();
                }, 30000);
            });
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