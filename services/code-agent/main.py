#!/usr/bin/env python3
"""
Code Agent - Receives blueprints from Blueprint Agent and generates code.
Subscribes to: tasks.blueprint
Publishes to: tasks.coding
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
logger = logging.getLogger("code-agent")

# Prometheus metrics
MESSAGES_RECEIVED = DummyMetric()
MESSAGES_PUBLISHED = DummyMetric()
CODE_GENERATION_DURATION = DummyMetric()
ACTIVE_CODE_TASKS = DummyMetric()
CODE_ERRORS = DummyMetric()

# Configuration
SUBSCRIBE_TOPIC = os.getenv("SUBSCRIBE_TOPIC", "tasks.blueprint")
PUBLISH_TOPIC = os.getenv("PUBLISH_TOPIC", "tasks.coding")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Pydantic models
class BlueprintInput(BaseModel):
    """Blueprint from blueprint agent"""
    blueprint_id: str
    plan_id: str
    system_architecture: Dict[str, Any]
    technology_stack: Dict[str, Any]
    database_schema: Dict[str, Any]
    api_specifications: Dict[str, Any]
    module_specifications: List[Dict[str, Any]]
    project_type: str = "new"  # "new", "existing_git", "existing_local"
    existing_codebase: Optional[Dict[str, Any]] = None
    modification_plan: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}

class CodeArtifact(BaseModel):
    """Generated code artifact"""
    file_path: str
    content: str
    language: str
    module: str
    dependencies: List[str] = []

class CodeOutput(BaseModel):
    """Code generation result to publish"""
    code_id: str
    blueprint_id: str
    artifacts: List[CodeArtifact]
    generated_modules: List[str]
    test_files: List[CodeArtifact]
    static_analysis_results: Dict[str, Any]
    build_instructions: Dict[str, Any]
    deployment_files: List[CodeArtifact]
    metadata: Dict[str, Any]

class CodeAgent:
    """
    Code Agent that generates code from architectural blueprints
    """
    
    def __init__(self):
        self.messaging_client: Optional[MessagingClient] = None
        self.is_running = False
        
    async def start(self):
        """Initialize the messaging client and start listening"""
        logger.info("Starting Code Agent...")
        
        # Initialize messaging client 
        self.messaging_client = create_messaging_client()
        await self.messaging_client.start()
        
        # Subscribe to blueprint topic
        self.messaging_client.subscribe(
            topic=SUBSCRIBE_TOPIC,
            callback=self.process_blueprint_message,
            group_id="code-agent-group"
        )
        
        self.is_running = True
        logger.info(f"Code Agent started, subscribed to {SUBSCRIBE_TOPIC}")
        
    async def stop(self):
        """Stop the messaging client"""
        logger.info("Stopping Code Agent...")
        self.is_running = False
        if self.messaging_client:
            await self.messaging_client.stop()
        logger.info("Code Agent stopped")
        
    async def process_blueprint_message(self, message: Dict[str, Any]):
        """Process a message from the blueprint topic"""
        start_time = time.time()
        
        try:
            MESSAGES_RECEIVED.inc()
            ACTIVE_CODE_TASKS.inc()
            
            logger.info(f"Received blueprint message: {message}")
            
            # Parse the blueprint from blueprint agent
            blueprint = BlueprintInput(**message)
            
            # Generate the code
            code_output = await self.generate_code(blueprint)
            
            # Publish the code artifacts
            await self.publish_code(code_output)
            
            duration = time.time() - start_time
            CODE_GENERATION_DURATION.observe(duration)
            
            logger.info(f"Successfully processed code generation {code_output.code_id} in {duration:.2f}s")
            
        except Exception as e:
            CODE_ERRORS.inc()
            logger.error(f"Error processing blueprint message: {e}", exc_info=True)
            raise
        finally:
            ACTIVE_CODE_TASKS.dec()
            
    async def generate_code(self, blueprint: BlueprintInput) -> CodeOutput:
        """Generate code from the blueprint"""
        
        # Generate unique code ID
        code_id = f"code_{int(time.time())}_{blueprint.blueprint_id}"
        
        # Generate code artifacts
        artifacts = []
        test_files = []
        deployment_files = []
        
        # Get technology stack
        backend_framework = blueprint.technology_stack.get("backend", {}).get("framework", "FastAPI")
        frontend_framework = blueprint.technology_stack.get("frontend", {}).get("framework", "React")
        database_type = blueprint.technology_stack.get("database", {}).get("primary", "PostgreSQL")
        
        # Generate backend code
        backend_artifacts = self.generate_backend_code(blueprint, backend_framework)
        artifacts.extend(backend_artifacts)
        
        # Generate frontend code if needed
        if frontend_framework:
            frontend_artifacts = self.generate_frontend_code(blueprint, frontend_framework)
            artifacts.extend(frontend_artifacts)
            
        # Generate database code
        database_artifacts = self.generate_database_code(blueprint, database_type)
        artifacts.extend(database_artifacts)
        
        # Generate test files
        test_files = self.generate_test_files(blueprint, artifacts)
        
        # Generate deployment files
        deployment_files = self.generate_deployment_files(blueprint)
        
        # Run static analysis
        static_analysis_results = self.run_static_analysis(artifacts)
        
        # Generate build instructions
        build_instructions = self.generate_build_instructions(blueprint)
        
        return CodeOutput(
            code_id=code_id,
            blueprint_id=blueprint.blueprint_id,
            artifacts=artifacts,
            generated_modules=[module["name"] for module in blueprint.module_specifications],
            test_files=test_files,
            static_analysis_results=static_analysis_results,
            build_instructions=build_instructions,
            deployment_files=deployment_files,
            metadata={
                **blueprint.metadata,
                "created_at": time.time(),
                "agent": "code-agent",
                "version": "1.0",
                "total_files": len(artifacts),
                "total_lines": sum(len(artifact.content.split('\n')) for artifact in artifacts)
            }
        )
        
    def generate_backend_code(self, blueprint: BlueprintInput, framework: str) -> List[CodeArtifact]:
        """Generate backend code artifacts"""
        artifacts = []
        
        if framework.lower() == "fastapi":
            # Generate main application file
            main_content = self.generate_fastapi_main(blueprint)
            artifacts.append(CodeArtifact(
                file_path="src/main.py",
                content=main_content,
                language="python",
                module="main",
                dependencies=["fastapi", "uvicorn"]
            ))
            
            # Generate models
            models_content = self.generate_fastapi_models(blueprint)
            artifacts.append(CodeArtifact(
                file_path="src/models.py",
                content=models_content,
                language="python", 
                module="models",
                dependencies=["sqlalchemy", "pydantic"]
            ))
            
            # Generate API routes
            routes_content = self.generate_fastapi_routes(blueprint)
            artifacts.append(CodeArtifact(
                file_path="src/api/routes.py",
                content=routes_content,
                language="python",
                module="api",
                dependencies=["fastapi", "sqlalchemy"]
            ))
            
            # Generate database connection
            database_content = self.generate_database_connection(blueprint)
            artifacts.append(CodeArtifact(
                file_path="src/database.py",
                content=database_content,
                language="python",
                module="database",
                dependencies=["sqlalchemy", "asyncpg"]
            ))
            
        return artifacts
        
    def generate_fastapi_main(self, blueprint: BlueprintInput) -> str:
        """Generate FastAPI main application file"""
        app_name = blueprint.metadata.get("project_name", "MyApp")
        
        content = f'''"""
{app_name} - Main Application
Generated by Code Agent
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
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


from .database import init_db, close_db
from .api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    await init_db()
    yield
    # Shutdown  
    await close_db()

app = FastAPI(
    title="{app_name} API",
    description="Generated API for {app_name}",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {{"status": "healthy", "service": "{app_name.lower()}-api"}}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
'''
        return content
        
    def generate_fastapi_models(self, blueprint: BlueprintInput) -> str:
        """Generate SQLAlchemy models from database schema"""
        content = '''"""
Database Models
Generated by Code Agent
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass


Base = declarative_base()

'''
        
        # Generate models from database schema
        tables = blueprint.database_schema.get("tables", [])
        
        for table in tables:
            table_name = table["name"]
            class_name = ''.join(word.capitalize() for word in table_name.split('_'))
            
            content += f'''
class {class_name}(Base):
    __tablename__ = "{table_name}"
    
'''
            
            # Generate columns
            for column in table["columns"]:
                col_name = column["name"]
                col_type = column["type"]
                
                # Map database types to SQLAlchemy types
                if col_type == "uuid":
                    sqlalchemy_type = "UUID(as_uuid=True)"
                    if column.get("primary_key"):
                        content += f"    {col_name} = Column({sqlalchemy_type}, primary_key=True, default=uuid.uuid4)\n"
                    else:
                        content += f"    {col_name} = Column({sqlalchemy_type})\n"
                elif "varchar" in col_type:
                    size = col_type.split("(")[1].split(")")[0] if "(" in col_type else "255"
                    content += f"    {col_name} = Column(String({size}))\n"
                elif col_type == "boolean":
                    default = f", default={column.get('default', 'False')}" if 'default' in column else ""
                    content += f"    {col_name} = Column(Boolean{default})\n"
                elif col_type == "timestamp":
                    if col_name in ["created_at", "updated_at"]:
                        content += f"    {col_name} = Column(DateTime, default=datetime.utcnow)\n"
                    else:
                        content += f"    {col_name} = Column(DateTime)\n"
                elif col_type == "text":
                    content += f"    {col_name} = Column(Text)\n"
                elif col_type == "bigint":
                    content += f"    {col_name} = Column(Integer)\n"
                elif col_type == "jsonb":
                    content += f"    {col_name} = Column(Text)  # JSON data\n"
                    
        return content
        
    def generate_fastapi_routes(self, blueprint: BlueprintInput) -> str:
        """Generate FastAPI routes from API specifications"""
        content = '''"""
API Routes
Generated by Code Agent
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import *

router = APIRouter()

'''
        
        # Generate routes from API specifications
        endpoints = blueprint.api_specifications.get("endpoints", [])
        
        for endpoint in endpoints:
            path = endpoint["path"]
            method = endpoint["method"].lower()
            description = endpoint.get("description", "")
            
            # Generate route function
            func_name = self.path_to_function_name(path, method)
            
            content += f'''
@router.{method}("{path}")
async def {func_name}(db: Session = Depends(get_db)):
    """
    {description}
    """
    # TODO: Implement {func_name}
    return {{"message": "Not implemented yet"}}

'''
            
        return content
        
    def generate_database_connection(self, blueprint: BlueprintInput) -> str:
        """Generate database connection and session management"""
        content = '''"""
Database Connection and Session Management
Generated by Code Agent
"""

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

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import AsyncGenerator

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/db")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """Initialize database tables"""
    from .models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """Close database connections"""
    await engine.dispose()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
'''
        return content
        
    def generate_frontend_code(self, blueprint: BlueprintInput, framework: str) -> List[CodeArtifact]:
        """Generate frontend code artifacts"""
        artifacts = []
        
        if framework.lower() == "react":
            # Generate main App component
            app_content = self.generate_react_app(blueprint)
            artifacts.append(CodeArtifact(
                file_path="src/App.tsx",
                content=app_content,
                language="typescript",
                module="app",
                dependencies=["react", "react-dom"]
            ))
            
            # Generate package.json
            package_json = self.generate_package_json(blueprint)
            artifacts.append(CodeArtifact(
                file_path="package.json",
                content=package_json,
                language="json",
                module="config",
                dependencies=[]
            ))
            
        return artifacts
        
    def generate_react_app(self, blueprint: BlueprintInput) -> str:
        """Generate React App component"""
        app_name = blueprint.metadata.get("project_name", "MyApp")
        
        content = f'''import React from 'react';
import './App.css';

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass


function App() {{
  return (
    <div className="App">
      <header className="App-header">
        <h1>{app_name}</h1>
        <p>Generated by Code Agent</p>
      </header>
      <main>
        {{/* Your application content will go here */}}
      </main>
    </div>
  );
}}

export default App;
'''
        return content
        
    def generate_package_json(self, blueprint: BlueprintInput) -> str:
        """Generate package.json for React app"""
        app_name = blueprint.metadata.get("project_name", "my-app").lower().replace(" ", "-")
        
        content = f'''{{
  "name": "{app_name}",
  "version": "1.0.0",
  "private": true,
  "dependencies": {{
    "@types/node": "^16.18.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "typescript": "^4.9.0",
    "web-vitals": "^2.1.0"
  }},
  "scripts": {{
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  }},
  "eslintConfig": {{
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  }},
  "browserslist": {{
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }}
}}
'''
        return content
        
    def generate_database_code(self, blueprint: BlueprintInput, database_type: str) -> List[CodeArtifact]:
        """Generate database migration and initialization scripts"""
        artifacts = []
        
        if "postgresql" in database_type.lower():
            # Generate Alembic migration
            migration_content = self.generate_alembic_migration(blueprint)
            artifacts.append(CodeArtifact(
                file_path="alembic/versions/001_initial_schema.py",
                content=migration_content,
                language="python",
                module="migrations",
                dependencies=["alembic"]
            ))
            
        return artifacts
        
    def generate_alembic_migration(self, blueprint: BlueprintInput) -> str:
        """Generate Alembic migration script"""
        content = '''"""Initial schema migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass

from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create initial tables"""
'''
        
        # Generate table creation from schema
        tables = blueprint.database_schema.get("tables", [])
        
        for table in tables:
            table_name = table["name"]
            content += f'''
    op.create_table('{table_name}',
'''
            
            for column in table["columns"]:
                col_name = column["name"]
                col_type = column["type"]
                
                if col_type == "uuid":
                    content += f"        sa.Column('{col_name}', postgresql.UUID(), nullable=False),\n"
                elif "varchar" in col_type:
                    size = col_type.split("(")[1].split(")")[0] if "(" in col_type else "255"
                    content += f"        sa.Column('{col_name}', sa.String({size}), nullable=True),\n"
                elif col_type == "boolean":
                    content += f"        sa.Column('{col_name}', sa.Boolean(), nullable=True),\n"
                elif col_type == "timestamp":
                    content += f"        sa.Column('{col_name}', sa.DateTime(), nullable=True),\n"
                    
                if column.get("primary_key"):
                    content += f"        sa.PrimaryKeyConstraint('{col_name}'),\n"
                    
            content += "    )\n"
            
        content += '''

def downgrade():
    """Drop all tables"""
'''
        
        for table in reversed(tables):
            content += f"    op.drop_table('{table['name']}')\n"
            
        return content
        
    def generate_test_files(self, blueprint: BlueprintInput, artifacts: List[CodeArtifact]) -> List[CodeArtifact]:
        """Generate test files for the code artifacts"""
        test_files = []
        
        # Generate API tests
        if any(artifact.module == "api" for artifact in artifacts):
            test_content = self.generate_api_tests(blueprint)
            test_files.append(CodeArtifact(
                file_path="tests/test_api.py",
                content=test_content,
                language="python",
                module="tests",
                dependencies=["pytest", "httpx"]
            ))
            
        # Generate model tests
        if any(artifact.module == "models" for artifact in artifacts):
            test_content = self.generate_model_tests(blueprint)
            test_files.append(CodeArtifact(
                file_path="tests/test_models.py",
                content=test_content,
                language="python",
                module="tests",
                dependencies=["pytest", "sqlalchemy"]
            ))
            
        return test_files
        
    def generate_api_tests(self, blueprint: BlueprintInput) -> str:
        """Generate API tests"""
        content = '''"""
API Tests
Generated by Code Agent
"""

import pytest

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass

from httpx import AsyncClient
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

# Add more API tests here based on your endpoints
'''
        return content
        
    def generate_model_tests(self, blueprint: BlueprintInput) -> str:
        """Generate model tests"""
        content = '''"""
Model Tests
Generated by Code Agent
"""

import pytest

# Simplified metrics (remove Prometheus for now to avoid collision)
class DummyMetric:
    def inc(self): pass
    def dec(self): pass
    def observe(self, value): pass
    def labels(self, **kwargs): return self
    def time(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base

@pytest.fixture
def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

# Add model-specific tests here
'''
        return content
        
    def generate_deployment_files(self, blueprint: BlueprintInput) -> List[CodeArtifact]:
        """Generate deployment configuration files"""
        deployment_files = []
        
        # Generate Dockerfile
        dockerfile_content = self.generate_dockerfile(blueprint)
        deployment_files.append(CodeArtifact(
            file_path="Dockerfile",
            content=dockerfile_content,
            language="dockerfile",
            module="deployment",
            dependencies=[]
        ))
        
        # Generate docker-compose.yml
        compose_content = self.generate_docker_compose(blueprint)
        deployment_files.append(CodeArtifact(
            file_path="docker-compose.yml",
            content=compose_content,
            language="yaml",
            module="deployment", 
            dependencies=[]
        ))
        
        return deployment_files
        
    def generate_dockerfile(self, blueprint: BlueprintInput) -> str:
        """Generate Dockerfile"""
        content = '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
        return content
        
    def generate_docker_compose(self, blueprint: BlueprintInput) -> str:
        """Generate docker-compose.yml"""
        content = '''version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:password@db:5432/myapp
    depends_on:
      - db
      
  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=myapp
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
'''
        return content
        
    def run_static_analysis(self, artifacts: List[CodeArtifact]) -> Dict[str, Any]:
        """Run static analysis on generated code"""
        analysis_results = {
            "total_files": len(artifacts),
            "languages": {},
            "complexity": "medium",
            "issues": [],
            "metrics": {}
        }
        
        # Count files by language
        for artifact in artifacts:
            lang = artifact.language
            if lang not in analysis_results["languages"]:
                analysis_results["languages"][lang] = 0
            analysis_results["languages"][lang] += 1
            
        # Calculate basic metrics
        total_lines = sum(len(artifact.content.split('\n')) for artifact in artifacts)
        analysis_results["metrics"]["total_lines"] = total_lines
        analysis_results["metrics"]["average_file_size"] = total_lines // len(artifacts) if artifacts else 0
        
        # Simple complexity assessment
        if total_lines > 5000:
            analysis_results["complexity"] = "high"
        elif total_lines < 1000:
            analysis_results["complexity"] = "low"
            
        return analysis_results
        
    def generate_build_instructions(self, blueprint: BlueprintInput) -> Dict[str, Any]:
        """Generate build and deployment instructions"""
        return {
            "steps": [
                "1. Install dependencies: pip install -r requirements.txt",
                "2. Set up database: alembic upgrade head",
                "3. Run application: uvicorn src.main:app --reload",
                "4. Access API at: http://localhost:8000"
            ],
            "docker_steps": [
                "1. Build image: docker-compose build",
                "2. Start services: docker-compose up -d",
                "3. Access application at: http://localhost:8000"
            ],
            "environment_variables": {
                "DATABASE_URL": "Database connection string",
                "SECRET_KEY": "Application secret key", 
                "DEBUG": "Debug mode (true/false)"
            }
        }
        
    def path_to_function_name(self, path: str, method: str) -> str:
        """Convert API path to function name"""
        # Remove leading slash and parameters
        clean_path = path.strip("/").replace("{", "").replace("}", "")
        parts = clean_path.split("/")
        
        # Create function name
        func_name = method + "_" + "_".join(parts)
        return func_name.replace("-", "_")
        
    async def publish_code(self, code_output: CodeOutput):
        """Publish the code artifacts to the coding topic"""
        try:
            message = code_output.dict()
            await self.messaging_client.publish(PUBLISH_TOPIC, message)
            MESSAGES_PUBLISHED.inc()
            logger.info(f"Published code artifacts {code_output.code_id} to {PUBLISH_TOPIC}")
        except Exception as e:
            logger.error(f"Failed to publish code artifacts {code_output.code_id}: {e}")
            raise

# Global agent instance
code_agent = CodeAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the agent lifecycle"""
    await code_agent.start()
    yield
    await code_agent.stop()

# FastAPI app
app = FastAPI(
    title="Code Agent", 
    description="Generates code from architectural blueprints",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "code-agent",
        "is_running": code_agent.is_running,
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
    is_ready = code_agent.is_running and code_agent.messaging_client is not None
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
        "agent": "code-agent",
        "is_running": code_agent.is_running,
        "topics": {
            "subscribe": SUBSCRIBE_TOPIC,
            "publish": PUBLISH_TOPIC
        },
        "metrics": {
            "messages_received": MESSAGES_RECEIVED._value.get(),
            "messages_published": MESSAGES_PUBLISHED._value.get(),
            "active_tasks": ACTIVE_CODE_TASKS._value.get(),
            "errors": CODE_ERRORS._value.get()
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