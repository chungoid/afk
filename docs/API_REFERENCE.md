# API Reference

## Overview

The Multi-Agent Software Development Pipeline exposes RESTful APIs through the API Gateway and individual agent services. This document provides comprehensive documentation for all available endpoints, request/response schemas, and integration examples.

## Base URLs

- **API Gateway**: `http://localhost:8000`
- **Analysis Agent**: `http://localhost:8001`
- **Orchestrator Agent**: `http://localhost:8002`
- **Planning Agent**: `http://localhost:8003`
- **Blueprint Agent**: `http://localhost:8004`
- **Code Agent**: `http://localhost:8005`
- **Test Agent**: `http://localhost:8006`

## Authentication

Currently, the system uses API key-based authentication for external access. Include the API key in the request headers:

```
Authorization: Bearer YOUR_API_KEY
```

For development purposes, authentication may be disabled. Check the service configuration for current authentication requirements.

## API Gateway Endpoints

### Project Management

#### Submit Project

Submit a new software development project to the pipeline.

**Endpoint**: `POST /submit`

**Request Body**:
```json
{
  "project_name": "string",
  "description": "string",
  "requirements": ["string"],
  "constraints": ["string"],
  "priority": "low|medium|high",
  "technology_preferences": ["string"],
  "deadline": "2024-12-31T23:59:59Z",
  "contact_info": {
    "name": "string",
    "email": "string"
  }
}
```

**Response**:
```json
{
  "request_id": "uuid",
  "status": "submitted",
  "message": "Project submitted successfully",
  "estimated_completion": "2024-12-31T23:59:59Z",
  "tracking_url": "http://localhost:8000/status/uuid"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "E-commerce Platform",
    "description": "Modern e-commerce platform with user management and payment processing",
    "requirements": [
      "User registration and authentication",
      "Product catalog with search",
      "Shopping cart functionality",
      "Payment processing integration",
      "Order management system"
    ],
    "constraints": [
      "Must use Python FastAPI",
      "PostgreSQL database required",
      "Containerized deployment"
    ],
    "priority": "high",
    "technology_preferences": ["FastAPI", "PostgreSQL", "React", "Docker"]
  }'
```

#### Get Project Status

Retrieve the current status and progress of a submitted project.

**Endpoint**: `GET /status/{request_id}`

**Parameters**:
- `request_id` (path): UUID of the submitted project

**Response**:
```json
{
  "request_id": "uuid",
  "project_name": "string",
  "status": "submitted|analyzing|planning|designing|coding|testing|completed|failed",
  "progress": {
    "current_stage": "string",
    "completion_percentage": 0-100,
    "stages": {
      "analysis": "pending|in_progress|completed|failed",
      "planning": "pending|in_progress|completed|failed",
      "blueprint": "pending|in_progress|completed|failed",
      "coding": "pending|in_progress|completed|failed",
      "testing": "pending|in_progress|completed|failed"
    }
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "estimated_completion": "2024-12-31T23:59:59Z",
  "deliverables": {
    "analysis_report": "url",
    "project_plan": "url",
    "technical_blueprint": "url",
    "source_code": "url",
    "test_results": "url",
    "documentation": "url"
  },
  "metrics": {
    "processing_time": "PT2H30M",
    "code_quality_score": 0.95,
    "test_coverage": 0.87,
    "complexity_score": "medium"
  }
}
```

#### List Projects

Retrieve a paginated list of all submitted projects.

**Endpoint**: `GET /requests`

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `limit` (optional): Number of items per page (default: 20, max: 100)
- `status` (optional): Filter by status
- `priority` (optional): Filter by priority

**Response**:
```json
{
  "projects": [
    {
      "request_id": "uuid",
      "project_name": "string",
      "status": "string",
      "priority": "string",
      "created_at": "2024-01-01T00:00:00Z",
      "progress": {
        "completion_percentage": 0-100,
        "current_stage": "string"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

#### Cancel Project

Cancel a project that is currently in progress.

**Endpoint**: `DELETE /cancel/{request_id}`

**Parameters**:
- `request_id` (path): UUID of the project to cancel

**Response**:
```json
{
  "request_id": "uuid",
  "status": "cancelled",
  "message": "Project cancelled successfully"
}
```

### System Management

#### Health Check

Check the health status of the API Gateway and connected services.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "api_gateway": "healthy",
    "analysis_agent": "healthy",
    "planning_agent": "healthy",
    "blueprint_agent": "healthy",
    "code_agent": "healthy",
    "test_agent": "healthy",
    "orchestrator": "healthy",
    "message_broker": "healthy",
    "vector_database": "healthy"
  },
  "version": "1.0.0"
}
```

#### System Metrics

Get system-wide metrics and performance data.

**Endpoint**: `GET /metrics`

**Response**:
```json
{
  "system": {
    "uptime": "PT24H30M",
    "total_projects": 150,
    "active_projects": 12,
    "completed_projects": 138,
    "success_rate": 0.92
  },
  "performance": {
    "avg_processing_time": "PT2H15M",
    "queue_depths": {
      "analysis": 3,
      "planning": 2,
      "blueprint": 1,
      "coding": 4,
      "testing": 2
    },
    "throughput": {
      "projects_per_hour": 5.2,
      "requests_per_second": 12.3
    }
  },
  "resources": {
    "cpu_usage": 0.65,
    "memory_usage": 0.78,
    "disk_usage": 0.45
  }
}
```

## Agent-Specific Endpoints

### Analysis Agent

#### Process Requirements

Directly submit requirements for analysis (bypasses API Gateway).

**Endpoint**: `POST /analyze`

**Request Body**:
```json
{
  "requirements": ["string"],
  "context": "string",
  "project_type": "web|mobile|api|desktop|ml"
}
```

**Response**:
```json
{
  "analysis_id": "uuid",
  "intent": {
    "primary_objective": "string",
    "secondary_objectives": ["string"],
    "success_criteria": ["string"]
  },
  "tasks": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "type": "feature|bug|improvement|research",
      "priority": "low|medium|high|critical",
      "estimated_effort": "string",
      "dependencies": ["string"],
      "acceptance_criteria": ["string"]
    }
  ],
  "constraints": {
    "technical": ["string"],
    "business": ["string"],
    "timeline": ["string"]
  },
  "recommendations": ["string"]
}
```

### Planning Agent

#### Generate Project Plan

Create a detailed project plan from analyzed requirements.

**Endpoint**: `POST /plan`

**Request Body**:
```json
{
  "analysis_results": {
    "intent": {},
    "tasks": [],
    "constraints": {}
  },
  "preferences": {
    "methodology": "agile|waterfall|lean",
    "sprint_duration": "1w|2w|3w|4w",
    "team_size": "number"
  }
}
```

**Response**:
```json
{
  "plan_id": "uuid",
  "methodology": "string",
  "phases": [
    {
      "name": "string",
      "duration": "string",
      "tasks": ["string"],
      "deliverables": ["string"],
      "dependencies": ["string"]
    }
  ],
  "timeline": {
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "milestones": [
      {
        "name": "string",
        "date": "2024-06-01",
        "deliverables": ["string"]
      }
    ]
  },
  "resources": {
    "team_requirements": ["string"],
    "technology_stack": ["string"],
    "infrastructure_needs": ["string"]
  },
  "risks": [
    {
      "description": "string",
      "probability": "low|medium|high",
      "impact": "low|medium|high",
      "mitigation": "string"
    }
  ]
}
```

### Blueprint Agent

#### Generate Technical Blueprint

Create technical specifications and architecture designs.

**Endpoint**: `POST /blueprint`

**Request Body**:
```json
{
  "project_plan": {},
  "requirements": {},
  "technology_preferences": ["string"]
}
```

**Response**:
```json
{
  "blueprint_id": "uuid",
  "architecture": {
    "pattern": "microservices|monolith|serverless",
    "components": [
      {
        "name": "string",
        "type": "service|database|gateway|queue",
        "responsibilities": ["string"],
        "interfaces": ["string"]
      }
    ],
    "diagrams": {
      "system_architecture": "url",
      "component_diagram": "url",
      "sequence_diagrams": ["url"]
    }
  },
  "database_design": {
    "type": "relational|nosql|hybrid",
    "entities": [
      {
        "name": "string",
        "attributes": {},
        "relationships": []
      }
    ],
    "schema_diagram": "url"
  },
  "api_specification": {
    "format": "openapi",
    "endpoints": [
      {
        "path": "string",
        "method": "GET|POST|PUT|DELETE",
        "summary": "string",
        "parameters": [],
        "responses": {}
      }
    ],
    "openapi_url": "url"
  },
  "deployment": {
    "strategy": "docker|kubernetes|serverless",
    "environments": ["dev", "staging", "prod"],
    "infrastructure": {},
    "ci_cd_pipeline": {}
  }
}
```

### Code Agent

#### Generate Code

Generate source code from technical blueprints.

**Endpoint**: `POST /generate`

**Request Body**:
```json
{
  "blueprint": {},
  "language": "python|javascript|java|go|rust",
  "framework": "string",
  "coding_standards": {
    "style_guide": "pep8|airbnb|google",
    "test_coverage": "number",
    "documentation": "sphinx|jsdoc|javadoc"
  }
}
```

**Response**:
```json
{
  "generation_id": "uuid",
  "project_structure": {
    "directories": ["string"],
    "files": [
      {
        "path": "string",
        "type": "source|test|config|doc",
        "size": "number",
        "language": "string"
      }
    ]
  },
  "source_code": {
    "repository_url": "string",
    "main_branch": "string",
    "commit_hash": "string"
  },
  "documentation": {
    "readme_url": "string",
    "api_docs_url": "string",
    "developer_guide_url": "string"
  },
  "quality_metrics": {
    "lines_of_code": "number",
    "complexity_score": "number",
    "maintainability_index": "number",
    "technical_debt": "low|medium|high"
  }
}
```

### Test Agent

#### Execute Tests

Run comprehensive tests on generated code.

**Endpoint**: `POST /test`

**Request Body**:
```json
{
  "source_code": {
    "repository_url": "string",
    "branch": "string"
  },
  "test_configuration": {
    "types": ["unit", "integration", "e2e", "performance"],
    "coverage_threshold": "number",
    "performance_benchmarks": {}
  }
}
```

**Response**:
```json
{
  "test_id": "uuid",
  "execution_summary": {
    "total_tests": "number",
    "passed": "number",
    "failed": "number",
    "skipped": "number",
    "execution_time": "string"
  },
  "coverage": {
    "percentage": "number",
    "lines_covered": "number",
    "lines_total": "number",
    "branches_covered": "number",
    "functions_covered": "number"
  },
  "test_results": [
    {
      "suite": "string",
      "test": "string",
      "status": "passed|failed|skipped",
      "duration": "string",
      "error_message": "string"
    }
  ],
  "quality_gates": {
    "coverage_threshold": "passed|failed",
    "performance_benchmarks": "passed|failed",
    "security_scan": "passed|failed"
  },
  "reports": {
    "html_report": "url",
    "junit_xml": "url",
    "coverage_report": "url",
    "performance_report": "url"
  }
}
```

### Orchestrator Agent

#### Get Pipeline Status

Get real-time status of the entire pipeline.

**Endpoint**: `GET /pipeline/status`

**Response**:
```json
{
  "pipeline": {
    "active_projects": "number",
    "queue_status": {
      "analysis": "number",
      "planning": "number",
      "blueprint": "number",
      "coding": "number",
      "testing": "number"
    },
    "agent_status": {
      "analysis_agent": "healthy|busy|error",
      "planning_agent": "healthy|busy|error",
      "blueprint_agent": "healthy|busy|error",
      "code_agent": "healthy|busy|error",
      "test_agent": "healthy|busy|error"
    }
  },
  "performance": {
    "throughput": "number",
    "avg_processing_time": "string",
    "success_rate": "number"
  }
}
```

#### WebSocket Dashboard

Real-time pipeline monitoring via WebSocket connection.

**Endpoint**: `GET /dashboard` (WebSocket upgrade)

**WebSocket Messages**:
```json
{
  "type": "project_update",
  "data": {
    "request_id": "uuid",
    "status": "string",
    "stage": "string",
    "progress": "number",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## Error Responses

All endpoints follow consistent error response formats:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {},
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid"
  }
}
```

### Common Error Codes

- `400` - Bad Request: Invalid request format or parameters
- `401` - Unauthorized: Authentication required or invalid
- `403` - Forbidden: Insufficient permissions
- `404` - Not Found: Resource not found
- `409` - Conflict: Resource already exists or conflicting state
- `422` - Unprocessable Entity: Valid format but semantic errors
- `429` - Too Many Requests: Rate limit exceeded
- `500` - Internal Server Error: Unexpected server error
- `502` - Bad Gateway: Upstream service error
- `503` - Service Unavailable: Service temporarily unavailable

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Default Limit**: 100 requests per minute per IP
- **Authenticated Limit**: 1000 requests per minute per API key
- **Burst Limit**: 10 requests per second

Rate limit information is included in response headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## SDKs and Client Libraries

### Python SDK

```python
from multi_agent_pipeline import PipelineClient

client = PipelineClient(
    base_url="http://localhost:8000",
    api_key="your_api_key"
)

# Submit project
response = client.submit_project({
    "project_name": "My Project",
    "description": "Project description",
    "requirements": ["requirement 1", "requirement 2"]
})

# Check status
status = client.get_status(response.request_id)

# Stream updates
for update in client.stream_updates(response.request_id):
    print(f"Stage: {update.stage}, Progress: {update.progress}%")
```

### JavaScript SDK

```javascript
import { PipelineClient } from '@multi-agent-pipeline/client';

const client = new PipelineClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your_api_key'
});

// Submit project
const response = await client.submitProject({
  projectName: 'My Project',
  description: 'Project description',
  requirements: ['requirement 1', 'requirement 2']
});

// Check status
const status = await client.getStatus(response.requestId);

// WebSocket updates
client.onUpdate(response.requestId, (update) => {
  console.log(`Stage: ${update.stage}, Progress: ${update.progress}%`);
});
```

## Webhooks

Configure webhooks to receive real-time notifications about project status changes.

### Webhook Configuration

**Endpoint**: `POST /webhooks`

**Request Body**:
```json
{
  "url": "https://your-server.com/webhook",
  "events": ["project.submitted", "project.completed", "project.failed"],
  "secret": "your_webhook_secret"
}
```

### Webhook Payload

```json
{
  "event": "project.completed",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "request_id": "uuid",
    "project_name": "string",
    "status": "completed",
    "deliverables": {
      "source_code": "url",
      "documentation": "url",
      "test_results": "url"
    }
  },
  "signature": "sha256=..."
}
``` 