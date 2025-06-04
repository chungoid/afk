#!/usr/bin/env python3
"""
Blueprint Agent - Receives plans from Planning Agent and creates architectural blueprints.
Subscribes to: tasks.planning
Publishes to: tasks.blueprint
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
logger = logging.getLogger("blueprint-agent")

# Prometheus metrics
MESSAGES_RECEIVED = DummyMetric()
MESSAGES_PUBLISHED = DummyMetric()
BLUEPRINT_DURATION = DummyMetric()
ACTIVE_BLUEPRINTS = DummyMetric()
BLUEPRINT_ERRORS = DummyMetric()

# Configuration
SUBSCRIBE_TOPIC = os.getenv("SUBSCRIBE_TOPIC", "tasks.planning")
PUBLISH_TOPIC = os.getenv("PUBLISH_TOPIC", "tasks.blueprint")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Pydantic models
class PlanInput(BaseModel):
    """Plan from planning agent"""
    plan_id: str
    prioritized_tasks: List[Dict[str, Any]]
    estimated_duration: float
    risk_assessment: Dict[str, Any]
    execution_sequence: List[List[str]]
    metadata: Dict[str, Any] = {}

class ArchitecturalBlueprint(BaseModel):
    """Architectural blueprint output"""
    blueprint_id: str
    plan_id: str
    system_architecture: Dict[str, Any]
    technology_stack: Dict[str, Any]
    database_schema: Dict[str, Any]
    api_specifications: Dict[str, Any]
    deployment_architecture: Dict[str, Any]
    security_considerations: List[str]
    diagrams: Dict[str, str]  # diagram_type -> mermaid_code
    module_specifications: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class BlueprintAgent:
    """
    Blueprint Agent that creates architectural blueprints from planning stage
    """
    
    def __init__(self):
        self.messaging_client: Optional[MessagingClient] = None
        self.is_running = False
        
    async def start(self):
        """Initialize the messaging client and start listening"""
        logger.info("Starting Blueprint Agent...")
        
        # Initialize messaging client 
        self.messaging_client = create_messaging_client()
        await self.messaging_client.start()
        
        # Subscribe to planning topic
        self.messaging_client.subscribe(
            topic=SUBSCRIBE_TOPIC,
            callback=self.process_planning_message,
            group_id="blueprint-agent-group"
        )
        
        self.is_running = True
        logger.info(f"Blueprint Agent started, subscribed to {SUBSCRIBE_TOPIC}")
        
    async def stop(self):
        """Stop the messaging client"""
        logger.info("Stopping Blueprint Agent...")
        self.is_running = False
        if self.messaging_client:
            await self.messaging_client.stop()
        logger.info("Blueprint Agent stopped")
        
    async def process_planning_message(self, message: Dict[str, Any]):
        """Process a message from the planning topic"""
        start_time = time.time()
        
        try:
            MESSAGES_RECEIVED.inc()
            ACTIVE_BLUEPRINTS.inc()
            
            logger.info(f"Received planning message: {message}")
            
            # Parse the plan from planning agent
            plan = PlanInput(**message)
            
            # Generate the blueprint
            blueprint = await self.create_blueprint(plan)
            
            # Publish the blueprint
            await self.publish_blueprint(blueprint)
            
            duration = time.time() - start_time
            BLUEPRINT_DURATION.observe(duration)
            
            logger.info(f"Successfully processed blueprint {blueprint.blueprint_id} in {duration:.2f}s")
            
        except Exception as e:
            BLUEPRINT_ERRORS.inc()
            logger.error(f"Error processing planning message: {e}", exc_info=True)
            raise
        finally:
            ACTIVE_BLUEPRINTS.dec()
            
    async def create_blueprint(self, plan: PlanInput) -> ArchitecturalBlueprint:
        """Create an architectural blueprint from the plan"""
        
        # Generate unique blueprint ID
        blueprint_id = f"blueprint_{int(time.time())}_{plan.plan_id}"
        
        # Analyze the tasks to determine system requirements
        system_requirements = self.analyze_system_requirements(plan.prioritized_tasks)
        
        # Generate system architecture
        system_architecture = self.generate_system_architecture(system_requirements)
        
        # Determine technology stack
        technology_stack = self.select_technology_stack(system_requirements)
        
        # Design database schema
        database_schema = self.design_database_schema(system_requirements)
        
        # Create API specifications
        api_specifications = self.design_api_specifications(system_requirements)
        
        # Plan deployment architecture
        deployment_architecture = self.design_deployment_architecture(system_requirements)
        
        # Identify security considerations
        security_considerations = self.identify_security_considerations(system_requirements)
        
        # Generate diagrams
        diagrams = self.generate_diagrams(system_architecture, database_schema)
        
        # Create module specifications
        module_specifications = self.create_module_specifications(system_requirements, plan.execution_sequence)
        
        return ArchitecturalBlueprint(
            blueprint_id=blueprint_id,
            plan_id=plan.plan_id,
            system_architecture=system_architecture,
            technology_stack=technology_stack,
            database_schema=database_schema,
            api_specifications=api_specifications,
            deployment_architecture=deployment_architecture,
            security_considerations=security_considerations,
            diagrams=diagrams,
            module_specifications=module_specifications,
            metadata={
                **plan.metadata,
                "created_at": time.time(),
                "agent": "blueprint-agent",
                "version": "1.0",
                "estimated_complexity": self.estimate_complexity(system_requirements)
            }
        )
        
    def analyze_system_requirements(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze tasks to determine system requirements"""
        requirements = {
            "type": "web_application",  # Default
            "features": [],
            "integrations": [],
            "data_storage": [],
            "user_types": [],
            "scalability": "medium",
            "performance_requirements": []
        }
        
        # Analyze task descriptions to identify patterns
        all_descriptions = " ".join([task.get("description", "").lower() for task in tasks])
        
        # Determine application type
        if any(word in all_descriptions for word in ["api", "rest", "graphql", "microservice"]):
            requirements["type"] = "api_service"
        elif any(word in all_descriptions for word in ["mobile", "ios", "android", "react native"]):
            requirements["type"] = "mobile_application"
        elif any(word in all_descriptions for word in ["desktop", "electron", "tkinter", "pyqt"]):
            requirements["type"] = "desktop_application"
        elif any(word in all_descriptions for word in ["web", "frontend", "react", "vue", "angular"]):
            requirements["type"] = "web_application"
            
        # Identify features
        feature_keywords = {
            "authentication": ["auth", "login", "register", "signup", "jwt", "oauth"],
            "user_management": ["user", "profile", "account", "permission", "role"],
            "data_processing": ["process", "analyze", "compute", "algorithm", "ml"],
            "file_handling": ["upload", "download", "file", "document", "storage"],
            "notifications": ["notify", "email", "sms", "push", "alert"],
            "payments": ["payment", "billing", "subscription", "stripe", "paypal"],
            "search": ["search", "filter", "query", "elasticsearch", "solr"],
            "real_time": ["websocket", "real-time", "live", "streaming", "socket.io"]
        }
        
        for feature, keywords in feature_keywords.items():
            if any(keyword in all_descriptions for keyword in keywords):
                requirements["features"].append(feature)
                
        # Identify integrations
        integration_keywords = {
            "database": ["mysql", "postgresql", "mongodb", "redis", "sqlite"],
            "cloud": ["aws", "azure", "gcp", "s3", "lambda", "ec2"],
            "messaging": ["kafka", "rabbitmq", "sqs", "pubsub", "redis"],
            "external_apis": ["api", "webhook", "third-party", "integration"]
        }
        
        for integration, keywords in integration_keywords.items():
            if any(keyword in all_descriptions for keyword in keywords):
                requirements["integrations"].append(integration)
                
        # Determine scalability requirements
        if any(word in all_descriptions for word in ["scale", "high-load", "millions", "enterprise"]):
            requirements["scalability"] = "high"
        elif any(word in all_descriptions for word in ["simple", "basic", "small", "prototype"]):
            requirements["scalability"] = "low"
            
        return requirements
        
    def generate_system_architecture(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate high-level system architecture"""
        architecture = {
            "pattern": "layered",
            "layers": [],
            "components": [],
            "communication": []
        }
        
        app_type = requirements["type"]
        features = requirements["features"]
        
        if app_type == "web_application":
            architecture["pattern"] = "mvc"
            architecture["layers"] = [
                {"name": "presentation", "description": "Frontend UI components"},
                {"name": "application", "description": "Business logic and controllers"}, 
                {"name": "data", "description": "Data access and persistence"}
            ]
            architecture["components"] = [
                {"name": "web_frontend", "type": "spa", "technology": "react"},
                {"name": "api_backend", "type": "rest_api", "technology": "fastapi"},
                {"name": "database", "type": "relational", "technology": "postgresql"}
            ]
            
        elif app_type == "api_service":
            architecture["pattern"] = "microservices" if len(features) > 5 else "monolithic"
            architecture["layers"] = [
                {"name": "api_gateway", "description": "Request routing and auth"},
                {"name": "business_logic", "description": "Core service logic"},
                {"name": "data_layer", "description": "Data persistence"}
            ]
            
        elif app_type == "mobile_application":
            architecture["pattern"] = "mvvm"
            architecture["layers"] = [
                {"name": "view", "description": "UI components and screens"},
                {"name": "viewmodel", "description": "UI state and business logic"},
                {"name": "model", "description": "Data models and services"}
            ]
            
        # Add common components based on features
        if "authentication" in features:
            architecture["components"].append({
                "name": "auth_service", 
                "type": "authentication",
                "technology": "jwt"
            })
            
        if "real_time" in features:
            architecture["components"].append({
                "name": "websocket_server",
                "type": "real_time_communication", 
                "technology": "socket.io"
            })
            
        return architecture
        
    def select_technology_stack(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate technology stack"""
        stack = {
            "frontend": {},
            "backend": {},
            "database": {},
            "infrastructure": {},
            "tools": {}
        }
        
        app_type = requirements["type"]
        scalability = requirements["scalability"]
        features = requirements["features"]
        
        # Frontend technology selection
        if app_type in ["web_application", "api_service"]:
            if "real_time" in features:
                stack["frontend"] = {
                    "framework": "React",
                    "version": "18.x",
                    "additional": ["Socket.IO Client", "Redux Toolkit"]
                }
            else:
                stack["frontend"] = {
                    "framework": "React", 
                    "version": "18.x",
                    "additional": ["React Router", "Axios"]
                }
        elif app_type == "mobile_application":
            stack["frontend"] = {
                "framework": "React Native",
                "version": "0.72.x",
                "additional": ["React Navigation", "Redux Toolkit"]
            }
            
        # Backend technology selection
        if scalability == "high":
            stack["backend"] = {
                "language": "Python",
                "framework": "FastAPI",
                "version": "0.104.x",
                "additional": ["Celery", "Redis", "SQLAlchemy"]
            }
        else:
            stack["backend"] = {
                "language": "Python",
                "framework": "FastAPI", 
                "version": "0.104.x",
                "additional": ["SQLAlchemy", "Alembic"]
            }
            
        # Database selection
        if "data_processing" in features or scalability == "high":
            stack["database"] = {
                "primary": "PostgreSQL 15.x",
                "cache": "Redis 7.x",
                "search": "Elasticsearch 8.x" if "search" in features else None
            }
        else:
            stack["database"] = {
                "primary": "PostgreSQL 15.x",
                "cache": "Redis 7.x"
            }
            
        # Infrastructure
        if scalability == "high":
            stack["infrastructure"] = {
                "containerization": "Docker + Kubernetes",
                "cloud": "AWS/GCP",
                "load_balancer": "NGINX",
                "monitoring": "Prometheus + Grafana"
            }
        else:
            stack["infrastructure"] = {
                "containerization": "Docker Compose",
                "cloud": "VPS/Cloud Instance", 
                "monitoring": "Basic logging"
            }
            
        return stack
        
    def design_database_schema(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Design database schema based on requirements"""
        schema = {
            "tables": [],
            "relationships": [],
            "indexes": [],
            "constraints": []
        }
        
        features = requirements["features"]
        
        # Core tables based on features
        if "user_management" in features or "authentication" in features:
            schema["tables"].append({
                "name": "users",
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "email", "type": "varchar(255)", "unique": True},
                    {"name": "password_hash", "type": "varchar(255)"},
                    {"name": "first_name", "type": "varchar(100)"},
                    {"name": "last_name", "type": "varchar(100)"},
                    {"name": "is_active", "type": "boolean", "default": True},
                    {"name": "created_at", "type": "timestamp"},
                    {"name": "updated_at", "type": "timestamp"}
                ]
            })
            
            schema["indexes"].append({
                "table": "users",
                "columns": ["email"],
                "type": "unique"
            })
            
        if "file_handling" in features:
            schema["tables"].append({
                "name": "files",
                "columns": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "filename", "type": "varchar(255)"},
                    {"name": "file_path", "type": "text"},
                    {"name": "file_size", "type": "bigint"},
                    {"name": "mime_type", "type": "varchar(100)"},
                    {"name": "uploaded_by", "type": "uuid", "foreign_key": "users.id"},
                    {"name": "uploaded_at", "type": "timestamp"}
                ]
            })
            
        # Add audit table for compliance
        schema["tables"].append({
            "name": "audit_log",
            "columns": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "table_name", "type": "varchar(100)"},
                {"name": "record_id", "type": "uuid"},
                {"name": "action", "type": "varchar(50)"},
                {"name": "old_values", "type": "jsonb"},
                {"name": "new_values", "type": "jsonb"},
                {"name": "user_id", "type": "uuid"},
                {"name": "timestamp", "type": "timestamp"}
            ]
        })
        
        return schema
        
    def design_api_specifications(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Design API specifications"""
        api_spec = {
            "version": "1.0.0",
            "base_url": "/api/v1",
            "authentication": "Bearer Token",
            "endpoints": [],
            "schemas": []
        }
        
        features = requirements["features"]
        
        # Authentication endpoints
        if "authentication" in features:
            api_spec["endpoints"].extend([
                {
                    "path": "/auth/login",
                    "method": "POST",
                    "description": "User authentication",
                    "request_body": {"email": "string", "password": "string"},
                    "responses": {"200": {"token": "string", "user": "object"}}
                },
                {
                    "path": "/auth/register", 
                    "method": "POST",
                    "description": "User registration",
                    "request_body": {"email": "string", "password": "string", "first_name": "string", "last_name": "string"}
                }
            ])
            
        # User management endpoints
        if "user_management" in features:
            api_spec["endpoints"].extend([
                {
                    "path": "/users",
                    "method": "GET", 
                    "description": "List users with pagination",
                    "parameters": {"page": "integer", "limit": "integer"}
                },
                {
                    "path": "/users/{id}",
                    "method": "GET",
                    "description": "Get user by ID"
                },
                {
                    "path": "/users/{id}",
                    "method": "PUT",
                    "description": "Update user"
                }
            ])
            
        # File handling endpoints  
        if "file_handling" in features:
            api_spec["endpoints"].extend([
                {
                    "path": "/files/upload",
                    "method": "POST",
                    "description": "Upload file",
                    "content_type": "multipart/form-data"
                },
                {
                    "path": "/files/{id}/download",
                    "method": "GET",
                    "description": "Download file"
                }
            ])
            
        return api_spec
        
    def design_deployment_architecture(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Design deployment architecture"""
        deployment = {
            "environments": ["development", "staging", "production"],
            "infrastructure": {},
            "scaling": {},
            "monitoring": {}
        }
        
        scalability = requirements["scalability"]
        
        if scalability == "high":
            deployment["infrastructure"] = {
                "type": "kubernetes",
                "nodes": {
                    "web": {"replicas": 3, "cpu": "500m", "memory": "1Gi"},
                    "api": {"replicas": 5, "cpu": "1000m", "memory": "2Gi"},
                    "database": {"replicas": 1, "cpu": "2000m", "memory": "4Gi"},
                    "cache": {"replicas": 2, "cpu": "250m", "memory": "512Mi"}
                },
                "load_balancer": "NGINX Ingress",
                "ssl": "Let's Encrypt"
            }
            
            deployment["scaling"] = {
                "horizontal_pod_autoscaler": True,
                "metrics": ["CPU", "Memory", "Custom"],
                "min_replicas": 2,
                "max_replicas": 10
            }
            
        else:
            deployment["infrastructure"] = {
                "type": "docker_compose",
                "services": ["web", "api", "database", "cache"],
                "reverse_proxy": "NGINX",
                "ssl": "Let's Encrypt"
            }
            
            deployment["scaling"] = {
                "vertical_scaling": "Manual",
                "horizontal_scaling": "Limited"
            }
            
        deployment["monitoring"] = {
            "logs": "Centralized logging with ELK stack",
            "metrics": "Prometheus + Grafana",
            "health_checks": "Application and infrastructure",
            "alerting": "PagerDuty integration"
        }
        
        return deployment
        
    def identify_security_considerations(self, requirements: Dict[str, Any]) -> List[str]:
        """Identify security considerations"""
        security = []
        
        features = requirements["features"]
        
        # Base security requirements
        security.extend([
            "Input validation and sanitization",
            "SQL injection prevention",
            "XSS protection",
            "CSRF protection",
            "Secure headers implementation"
        ])
        
        # Feature-specific security
        if "authentication" in features:
            security.extend([
                "Password hashing with bcrypt",
                "JWT token management",
                "Rate limiting on auth endpoints",
                "Account lockout mechanisms"
            ])
            
        if "file_handling" in features:
            security.extend([
                "File type validation",
                "Virus scanning",
                "File size limits",
                "Secure file storage"
            ])
            
        if "payments" in features:
            security.extend([
                "PCI DSS compliance",
                "Secure payment processing",
                "Financial data encryption"
            ])
            
        # Infrastructure security
        security.extend([
            "Environment variable management",
            "Database encryption at rest",
            "TLS/SSL for all communications",
            "Regular security updates",
            "Backup encryption"
        ])
        
        return security
        
    def generate_diagrams(self, architecture: Dict[str, Any], database_schema: Dict[str, Any]) -> Dict[str, str]:
        """Generate Mermaid diagrams"""
        diagrams = {}
        
        # System architecture diagram
        arch_diagram = "graph TD\n"
        components = architecture.get("components", [])
        
        for i, component in enumerate(components):
            comp_id = f"comp{i}"
            arch_diagram += f"    {comp_id}[{component['name']}]\n"
            
        # Add connections between components
        if len(components) > 1:
            for i in range(len(components) - 1):
                arch_diagram += f"    comp{i} --> comp{i+1}\n"
                
        diagrams["system_architecture"] = arch_diagram
        
        # Database schema diagram
        if database_schema.get("tables"):
            db_diagram = "erDiagram\n"
            for table in database_schema["tables"]:
                table_name = table["name"].upper()
                db_diagram += f"    {table_name} {{\n"
                for column in table["columns"]:
                    db_diagram += f"        {column['type']} {column['name']}\n"
                db_diagram += "    }\n"
            diagrams["database_schema"] = db_diagram
            
        return diagrams
        
    def create_module_specifications(self, requirements: Dict[str, Any], execution_sequence: List[List[str]]) -> List[Dict[str, Any]]:
        """Create detailed module specifications"""
        modules = []
        
        # Core modules based on features
        features = requirements["features"]
        
        if "authentication" in features:
            modules.append({
                "name": "auth_module",
                "description": "User authentication and authorization",
                "dependencies": [],
                "files": [
                    "auth/models.py",
                    "auth/views.py", 
                    "auth/serializers.py",
                    "auth/permissions.py"
                ],
                "tests": [
                    "auth/test_auth.py",
                    "auth/test_permissions.py"
                ],
                "priority": 1
            })
            
        if "user_management" in features:
            modules.append({
                "name": "user_module",
                "description": "User profile and management",
                "dependencies": ["auth_module"],
                "files": [
                    "users/models.py",
                    "users/views.py",
                    "users/serializers.py"
                ],
                "tests": [
                    "users/test_users.py"
                ],
                "priority": 2
            })
            
        if "file_handling" in features:
            modules.append({
                "name": "file_module",
                "description": "File upload and management",
                "dependencies": ["auth_module"],
                "files": [
                    "files/models.py",
                    "files/views.py",
                    "files/storage.py"
                ],
                "tests": [
                    "files/test_upload.py"
                ],
                "priority": 3
            })
            
        # Add core infrastructure modules
        modules.extend([
            {
                "name": "core_module",
                "description": "Core application infrastructure",
                "dependencies": [],
                "files": [
                    "core/settings.py",
                    "core/urls.py",
                    "core/middleware.py"
                ],
                "tests": [
                    "core/test_settings.py"
                ],
                "priority": 0
            },
            {
                "name": "api_module", 
                "description": "API layer and routing",
                "dependencies": ["core_module"],
                "files": [
                    "api/views.py",
                    "api/serializers.py",
                    "api/urls.py"
                ],
                "tests": [
                    "api/test_endpoints.py"
                ],
                "priority": 1
            }
        ])
        
        return sorted(modules, key=lambda x: x["priority"])
        
    def estimate_complexity(self, requirements: Dict[str, Any]) -> str:
        """Estimate overall system complexity"""
        features_count = len(requirements["features"])
        integrations_count = len(requirements["integrations"])
        scalability = requirements["scalability"]
        
        complexity_score = features_count + integrations_count
        
        if scalability == "high":
            complexity_score += 3
        elif scalability == "medium":
            complexity_score += 1
            
        if complexity_score <= 3:
            return "low"
        elif complexity_score <= 7:
            return "medium"
        else:
            return "high"
            
    async def publish_blueprint(self, blueprint: ArchitecturalBlueprint):
        """Publish the blueprint to the blueprint topic"""
        try:
            message = blueprint.dict()
            await self.messaging_client.publish(PUBLISH_TOPIC, message)
            MESSAGES_PUBLISHED.inc()
            logger.info(f"Published blueprint {blueprint.blueprint_id} to {PUBLISH_TOPIC}")
        except Exception as e:
            logger.error(f"Failed to publish blueprint {blueprint.blueprint_id}: {e}")
            raise

# Global agent instance
blueprint_agent = BlueprintAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the agent lifecycle"""
    await blueprint_agent.start()
    yield
    await blueprint_agent.stop()

# FastAPI app
app = FastAPI(
    title="Blueprint Agent", 
    description="Creates architectural blueprints from planning specifications",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "blueprint-agent",
        "is_running": blueprint_agent.is_running,
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
    is_ready = blueprint_agent.is_running and blueprint_agent.messaging_client is not None
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
        "agent": "blueprint-agent",
        "is_running": blueprint_agent.is_running,
        "topics": {
            "subscribe": SUBSCRIBE_TOPIC,
            "publish": PUBLISH_TOPIC
        },
        "metrics": {
            "messages_received": MESSAGES_RECEIVED._value.get(),
            "messages_published": MESSAGES_PUBLISHED._value.get(),
            "active_blueprints": ACTIVE_BLUEPRINTS._value.get(),
            "errors": BLUEPRINT_ERRORS._value.get()
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