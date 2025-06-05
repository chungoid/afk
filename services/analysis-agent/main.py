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
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Import the existing messaging infrastructure and analysis code
import sys
sys.path.append('/app')
from src.common.messaging_simple import create_messaging_client, MessagingClient
from src.common.config import Settings

# Import existing analysis functionality
from src.analysis_agent.prompt_steps.analysis_steps import AnalysisSteps
from src.analysis_agent.utils.task_analyzer import TaskAnalyzer
from src.common.file_handler import ProjectFiles

# Add project paths for imports
sys.path.append('/home/flip/Desktop/test_swarm')

# Import MCP-enhanced orchestrator
from src.analysis_agent.orchestrator import Orchestrator

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("analysis-agent")

# Prometheus metrics
ANALYSIS_REQUESTS_TOTAL = Counter(
    'analysis_requests_total',
    'Total number of analysis requests processed',
    ['status']
)
ANALYSIS_DURATION = Histogram(
    'analysis_duration_seconds',
    'Time spent on analysis requests'
)
ANALYSIS_ERRORS = Counter(
    'analysis_errors_total',
    'Total number of analysis errors',
    ['error_type']
)
ACTIVE_ANALYSES = Gauge(
    'active_analyses',
    'Number of currently active analyses'
)

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
    project_type: str = "new"  # "new", "existing_git", "existing_local"
    # NEW: Add support for existing project files
    project_files: Optional[Dict[str, Any]] = None
    git_info: Optional[Dict[str, str]] = None
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
        
        # Initialize MCP-enhanced orchestrator
        self.orchestrator = Orchestrator(enable_mcp=True)
        
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
            logger.info(f"PUBLISH_TOPIC is set to: {PUBLISH_TOPIC}")
            logger.info(f"Messaging client type: {type(self.messaging_client)}")
            ACTIVE_ANALYSES.inc()
            
            # Track active analysis
            self.active_analyses[request_id] = request
            
            # Perform the analysis using existing functionality
            analysis_result = await self.analyze_project(request)
            
            # Quick test: try to publish a simple test message first
            try:
                test_message = {"test": "message", "request_id": request_id}
                await self.messaging_client.publish("test.topic", test_message)
                logger.info("Test message published successfully")
            except Exception as test_error:
                logger.error(f"Test message failed: {test_error}", exc_info=True)
            
            # Publish result to planning topic
            try:
                logger.info(f"About to serialize analysis result for publishing...")
                result_dict = analysis_result.dict()
                logger.info(f"Successfully serialized. Publishing to {PUBLISH_TOPIC} with keys: {list(result_dict.keys())}")
                logger.info(f"Tasks field contains {len(result_dict.get('tasks', []))} tasks")
                
                await self.messaging_client.publish(PUBLISH_TOPIC, result_dict)
                logger.info(f"Successfully published message to {PUBLISH_TOPIC}")
            except Exception as publish_error:
                logger.error(f"Failed to publish analysis result: {publish_error}", exc_info=True)
                raise
            
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
            # NEW: Handle existing projects differently
            if request.project_type in ["existing_git", "existing_local"] and request.project_files:
                logger.info(f"Analyzing existing codebase for request {request.request_id}")
                return await self._analyze_existing_codebase(request)
            else:
                logger.info(f"Analyzing new project for request {request.request_id}")
                return await self._analyze_new_project(request)
                
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

    async def _analyze_new_project(self, request: AnalysisRequest) -> AnalysisResult:
        """Analyze new project from requirements"""
        
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

    async def _analyze_existing_codebase(self, request: AnalysisRequest) -> AnalysisResult:
        """Analyze existing codebase and plan integration/modification tasks"""
        
        project_files = request.project_files
        files = project_files.get("files", {})
        
        # Analyze existing codebase structure
        codebase_analysis = await self._perform_codebase_analysis(files, project_files)
        
        # Plan integration tasks based on requirements and existing code
        integration_plan = await self._plan_integrations(
            request.project_description,
            request.requirements,
            codebase_analysis
        )
        
        # Generate modification tasks
        tasks = await self._generate_modification_tasks(
            request,
            codebase_analysis,
            integration_plan
        )
        
        total_hours = sum(task.estimated_hours for task in tasks)
        
        return AnalysisResult(
            analysis_id=f"analysis_{uuid.uuid4().hex[:8]}",
            request_id=request.request_id,
            project_summary=f"Enhancement of {codebase_analysis.get('project_type', 'existing')} project: {request.project_description}",
            tasks=tasks,
            total_estimated_hours=total_hours,
            recommended_team_size=max(1, min(6, int(total_hours / 120))),  # Existing projects often need less coordination
            critical_path=self._identify_critical_path(tasks),
            risk_factors=codebase_analysis.get("risk_factors", []),
            technology_recommendations=codebase_analysis.get("technology_recommendations", []),
            metadata={
                "agent": "analysis-agent",
                "analysis_method": "existing_codebase_analysis",
                "codebase_analysis": codebase_analysis,
                "original_request": request.dict()
            },
            timestamp=time.time()
        )

    async def _perform_codebase_analysis(self, files: Dict[str, str], project_files: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze existing codebase to understand structure and patterns"""
        
        detected_language = project_files.get("detected_language")
        detected_framework = project_files.get("detected_framework")
        
        analysis = {
            "detected_language": detected_language,
            "detected_framework": detected_framework,
            "file_count": len(files),
            "project_type": f"{detected_language}_{detected_framework}" if detected_framework else detected_language,
            "existing_features": await self._extract_existing_features(files, detected_language),
            "integration_points": await self._find_integration_points(files, detected_language, detected_framework),
            "architectural_patterns": await self._identify_patterns(files, detected_language, detected_framework),
            "test_coverage": await self._assess_test_coverage(files),
            "risk_factors": [],
            "technology_recommendations": []
        }
        
        # Add language-specific analysis
        if detected_language == "python":
            analysis.update(await self._analyze_python_codebase(files))
        elif detected_language in ["javascript", "typescript"]:
            analysis.update(await self._analyze_js_codebase(files))
        elif detected_language == "java":
            analysis.update(await self._analyze_java_codebase(files))
        elif detected_language == "go":
            analysis.update(await self._analyze_go_codebase(files))
        
        # Ensure detected_framework is not None for downstream usage
        if not analysis.get("detected_framework"):
            analysis["detected_framework"] = "general"
        
        return analysis

    async def _extract_existing_features(self, files: Dict[str, str], language: str) -> List[str]:
        """Extract existing features from codebase"""
        features = []
        
        # Generic feature detection based on file names and common patterns
        file_paths = set(files.keys())
        
        # Authentication features
        auth_patterns = ["auth", "login", "register", "jwt", "token", "session"]
        if any(pattern in " ".join(file_paths).lower() for pattern in auth_patterns):
            features.append("Authentication System")
            
        # API features
        api_patterns = ["api", "endpoint", "route", "controller"]
        if any(pattern in " ".join(file_paths).lower() for pattern in api_patterns):
            features.append("API Endpoints")
            
        # Database features
        db_patterns = ["model", "schema", "database", "migration", "entity"]
        if any(pattern in " ".join(file_paths).lower() for pattern in db_patterns):
            features.append("Database Layer")
            
        # Frontend features
        frontend_patterns = ["component", "view", "page", "template"]
        if any(pattern in " ".join(file_paths).lower() for pattern in frontend_patterns):
            features.append("Frontend Components")
            
        # Testing
        test_patterns = ["test", "spec", "__test__"]
        if any(pattern in " ".join(file_paths).lower() for pattern in test_patterns):
            features.append("Test Suite")
        
        return features

    async def _find_integration_points(self, files: Dict[str, str], language: str, framework: str) -> List[Dict[str, str]]:
        """Find points where new features can be integrated"""
        integration_points = []
        
        # Generic integration points
        for file_path, content in files.items():
            if "main" in file_path.lower() or "app" in file_path.lower():
                integration_points.append({
                    "type": "main_application",
                    "file": file_path,
                    "description": "Main application entry point"
                })
            
            if "route" in file_path.lower() or "endpoint" in file_path.lower():
                integration_points.append({
                    "type": "api_routes",
                    "file": file_path, 
                    "description": "API route definitions"
                })
                
            if "model" in file_path.lower() or "schema" in file_path.lower():
                integration_points.append({
                    "type": "data_models",
                    "file": file_path,
                    "description": "Data model definitions"
                })
        
        return integration_points[:10]  # Limit to avoid overwhelming

    async def _identify_patterns(self, files: Dict[str, str], language: str, framework: str) -> List[str]:
        """Identify architectural patterns in the codebase"""
        patterns = []
        
        file_paths = list(files.keys())
        
        # MVC pattern
        has_models = any("model" in path.lower() for path in file_paths)
        has_views = any("view" in path.lower() or "template" in path.lower() for path in file_paths)
        has_controllers = any("controller" in path.lower() or "route" in path.lower() for path in file_paths)
        
        if has_models and has_views and has_controllers:
            patterns.append("MVC Architecture")
        
        # Microservices pattern
        if len([p for p in file_paths if "service" in p.lower()]) > 2:
            patterns.append("Service-Oriented Architecture")
            
        # Layered architecture
        has_api = any("api" in path.lower() for path in file_paths)
        has_business = any("business" in path.lower() or "logic" in path.lower() for path in file_paths)
        has_data = any("data" in path.lower() or "repository" in path.lower() for path in file_paths)
        
        if has_api and has_business and has_data:
            patterns.append("Layered Architecture")
            
        return patterns

    async def _assess_test_coverage(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Assess existing test coverage"""
        test_files = [f for f in files.keys() if "test" in f.lower() or "spec" in f.lower()]
        source_files = [f for f in files.keys() if f not in test_files and not any(skip in f.lower() for skip in ["node_modules", ".git", "dist", "build"])]
        
        return {
            "test_files_count": len(test_files),
            "source_files_count": len(source_files),
            "test_ratio": len(test_files) / max(len(source_files), 1),
            "has_testing_framework": len(test_files) > 0
        }

    async def _analyze_python_codebase(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Python-specific codebase analysis"""
        analysis = {}
        
        # Check for common Python patterns
        has_fastapi = any("fastapi" in content.lower() for content in files.values())
        has_django = any("django" in content.lower() for content in files.values())
        has_flask = any("flask" in content.lower() for content in files.values())
        
        if has_fastapi:
            analysis["framework_details"] = "FastAPI - Modern async API framework"
        elif has_django:
            analysis["framework_details"] = "Django - Full-featured web framework"
        elif has_flask:
            analysis["framework_details"] = "Flask - Lightweight web framework"
            
        return analysis

    async def _analyze_js_codebase(self, files: Dict[str, str]) -> Dict[str, Any]:
        """JavaScript/TypeScript-specific codebase analysis"""
        analysis = {}
        
        # Check package.json for dependencies
        if "package.json" in files:
            try:
                import json
                package_data = json.loads(files["package.json"])
                deps = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
                
                if "react" in deps:
                    analysis["framework_details"] = "React - Component-based UI library"
                elif "vue" in deps:
                    analysis["framework_details"] = "Vue.js - Progressive frontend framework" 
                elif "angular" in deps:
                    analysis["framework_details"] = "Angular - Full-featured frontend framework"
                elif "express" in deps:
                    analysis["framework_details"] = "Express.js - Node.js web framework"
                    
            except json.JSONDecodeError:
                pass
                
        return analysis

    async def _analyze_java_codebase(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Java-specific codebase analysis"""
        analysis = {}
        
        # Check for Spring Boot
        has_spring = any("spring" in content.lower() for content in files.values())
        if has_spring:
            analysis["framework_details"] = "Spring Framework - Enterprise Java platform"
            
        return analysis

    async def _analyze_go_codebase(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Go-specific codebase analysis"""
        analysis = {}
        
        # Check for common Go patterns
        has_gin = any("gin" in content.lower() for content in files.values())
        has_echo = any("echo" in content.lower() for content in files.values())
        
        if has_gin:
            analysis["framework_details"] = "Gin - HTTP web framework for Go"
        elif has_echo:
            analysis["framework_details"] = "Echo - High performance Go web framework"
            
        return analysis

    async def _plan_integrations(self, description: str, requirements: List[str], codebase_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Plan how to integrate new features with existing codebase"""
        
        existing_features = codebase_analysis.get("existing_features", [])
        integration_points = codebase_analysis.get("integration_points", [])
        
        plan = {
            "modification_strategy": "incremental_enhancement",
            "integration_approach": "pattern_matching",
            "files_to_modify": [],
            "files_to_create": [],
            "dependencies_to_add": [],
            "conflicts": []
        }
        
        # Identify what needs to be added vs modified
        for req in requirements:
            req_lower = req.lower()
            
            # Check if feature already exists
            feature_exists = any(req_lower in feature.lower() for feature in existing_features)
            
            if feature_exists:
                plan["conflicts"].append(f"Feature '{req}' may already exist - will enhance existing implementation")
            else:
                plan["files_to_create"].append(f"New files for: {req}")
                
        # Identify files that likely need modification
        for point in integration_points:
            if point["type"] in ["main_application", "api_routes"]:
                plan["files_to_modify"].append(point["file"])
                
        return plan

    async def _generate_modification_tasks(self, request: AnalysisRequest, codebase_analysis: Dict[str, Any], integration_plan: Dict[str, Any]) -> List[TaskResult]:
        """Generate tasks for modifying existing codebase"""
        
        tasks = []
        task_id = 1
        
        # 1. Codebase Understanding Task
        tasks.append(TaskResult(
            task_id=f"task_{request.request_id}_{task_id}",
            name="Codebase Analysis and Understanding",
            description=f"Analyze existing {codebase_analysis.get('project_type', 'codebase')} to understand architecture and patterns",
            type="analysis",
            priority=1,
            estimated_hours=4.0,
            dependencies=[],
            skills_required=[codebase_analysis.get("detected_language", "programming")],
            complexity="medium"
        ))
        task_id += 1
        
        # 2. Integration Planning Task
        tasks.append(TaskResult(
            task_id=f"task_{request.request_id}_{task_id}",
            name="Integration Planning",
            description="Plan how new features will integrate with existing architecture",
            type="planning",
            priority=2,
            estimated_hours=3.0,
            dependencies=[f"task_{request.request_id}_1"],
            skills_required=["software-architecture", codebase_analysis.get("detected_language", "programming")],
            complexity="medium"
        ))
        task_id += 1
        
        # 3. Generate feature implementation tasks
        for req in request.requirements:
            tasks.append(TaskResult(
                task_id=f"task_{request.request_id}_{task_id}",
                name=f"Implement {req}",
                description=f"Implement {req} by modifying existing code and adding new components as needed",
                type="feature_implementation",
                priority=3,
                estimated_hours=self._estimate_feature_hours(req, codebase_analysis),
                dependencies=[f"task_{request.request_id}_2"],
                skills_required=[codebase_analysis.get("detected_language", "programming"), 
                              codebase_analysis.get("detected_framework", "general")],
                complexity=self._assess_feature_complexity(req, codebase_analysis)
            ))
            task_id += 1
            
        # 4. Integration Testing Task
        tasks.append(TaskResult(
            task_id=f"task_{request.request_id}_{task_id}",
            name="Integration Testing",
            description="Test new features with existing codebase to ensure compatibility",
            type="testing",
            priority=4,
            estimated_hours=6.0,
            dependencies=[f"task_{request.request_id}_{i}" for i in range(3, task_id)],
            skills_required=["testing", codebase_analysis.get("detected_language", "programming")],
            complexity="medium"
        ))
        task_id += 1
        
        # 5. Documentation Update Task  
        tasks.append(TaskResult(
            task_id=f"task_{request.request_id}_{task_id}",
            name="Documentation Update",
            description="Update project documentation to reflect new features and changes",
            type="documentation",
            priority=5,
            estimated_hours=2.0,
            dependencies=[f"task_{request.request_id}_{task_id-1}"],
            skills_required=["documentation"],
            complexity="low"
        ))
        
        return tasks

    def _estimate_feature_hours(self, feature: str, codebase_analysis: Dict[str, Any]) -> float:
        """Estimate hours for implementing a feature in existing codebase"""
        base_hours = 8.0
        
        # Adjust based on codebase complexity
        if codebase_analysis.get("file_count", 0) > 50:
            base_hours *= 1.5  # Larger codebase = more complexity
            
        # Adjust based on feature type
        feature_lower = feature.lower()
        if any(keyword in feature_lower for keyword in ["auth", "authentication", "security"]):
            base_hours *= 1.8  # Security features are complex
        elif any(keyword in feature_lower for keyword in ["api", "endpoint", "service"]):
            base_hours *= 1.2  # API features moderately complex
        elif any(keyword in feature_lower for keyword in ["ui", "frontend", "interface"]):
            base_hours *= 1.0  # UI changes baseline
        elif any(keyword in feature_lower for keyword in ["database", "model", "schema"]):
            base_hours *= 1.4  # Database changes require care
            
        return min(base_hours, 24.0)  # Cap at 3 days per feature

    def _assess_feature_complexity(self, feature: str, codebase_analysis: Dict[str, Any]) -> str:
        """Assess complexity of implementing feature in existing codebase"""
        feature_lower = feature.lower()
        
        # High complexity features
        if any(keyword in feature_lower for keyword in ["auth", "security", "payment", "integration"]):
            return "high"
            
        # Medium complexity features  
        elif any(keyword in feature_lower for keyword in ["api", "database", "search", "notification"]):
            return "medium"
            
        # Low complexity features
        else:
            return "low"

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
    """Prometheus metrics endpoint"""
    from fastapi import Response
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

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