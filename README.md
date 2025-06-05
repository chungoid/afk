# Multi-Agent Software Development Pipeline

A production-ready, microservices-based multi-agent system that automates the complete software development lifecycle from requirements analysis to code generation and testing.

## Overview

This system implements a sophisticated 6-stage AI-powered development pipeline that transforms project requirements into fully tested, deployable code. The pipeline consists of specialized agents that communicate via message queues to collaboratively analyze, plan, design, implement, and test software projects.

## Architecture

### Core Components

The system is built as a distributed microservices architecture with the following components:

#### Agent Services
- **API Gateway** (Port 8000): Entry point and web dashboard for project submissions
- **Analysis Agent** (Port 8001): Requirements analysis and task decomposition  
- **Orchestrator Agent** (Port 8002): Pipeline coordination and real-time monitoring
- **Planning Agent** (Port 8003): Project planning and task sequencing
- **Blueprint Agent** (Port 8004): Architecture design and technical specifications
- **Code Agent** (Port 8005): Code generation and implementation
- **Test & Deploy Agent** (Port 8006): Automated testing, quality assurance, artifact persistence, and deployment

#### Infrastructure Services
- **RabbitMQ** (Port 5672/15672): Message broker for inter-agent communication
- **Weaviate** (Port 8080): Vector database for semantic search and RAG
- **Prometheus** (Port 9090): Metrics collection and monitoring
- **Grafana** (Port 3001): Visualization and dashboards
- **Jaeger** (Port 16686): Distributed tracing
- **Git Server** (Port 3000): Version control and code storage

### Pipeline Flow

1. **Analysis Stage**: Requirements are analyzed and decomposed into structured tasks
2. **Planning Stage**: Tasks are prioritized, sequenced, and organized into a project plan
3. **Blueprint Stage**: Technical architecture, database schemas, and API specifications are designed
4. **Coding Stage**: Code is generated based on blueprints and requirements
5. **Testing & Deployment Stage**: Automated tests are executed, artifacts are persisted to Git, and successful projects are deployed
6. **Orchestration**: Cross-stage coordination, monitoring, and pipeline management

## Prerequisites

### System Requirements
- Docker 20.10+ and Docker Compose
- 8GB+ RAM (recommended for all services)
- 10GB+ available disk space
- Linux, macOS, or Windows with WSL2

### Required API Keys
- OpenAI API key for LLM services
- Optional: Other LLM provider API keys (Anthropic, etc.)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd test_swarm
```

### 2. Environment Configuration
Create a `.env` file in the project root:

```bash
# LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2000

# Message Broker Configuration
RABBITMQ_DEFAULT_USER=admin
RABBITMQ_DEFAULT_PASS=secure_password
BROKER_URL=amqp://admin:secure_password@mcp-use:5672/

# Database Configuration
WEAVIATE_URL=http://weaviate:8080
VECTOR_STORE_CLASS=ProjectDocuments

# Monitoring Configuration
PROMETHEUS_URL=http://prometheus:9090
JAEGER_ENDPOINT=http://jaeger:14268/api/traces

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Service-specific Configuration
ANALYSIS_SUBSCRIBE_TOPIC=tasks.analysis
PLANNING_SUBSCRIBE_TOPIC=tasks.planning
BLUEPRINT_SUBSCRIBE_TOPIC=tasks.blueprint
CODING_SUBSCRIBE_TOPIC=tasks.coding
TESTING_SUBSCRIBE_TOPIC=tasks.testing
ORCHESTRATION_TOPIC=orchestration.events
```

### 3. Build and Start Services
```bash
# Build all services
docker-compose build

# Start the complete pipeline
docker-compose up -d

# Verify all services are healthy
docker-compose ps
```

### 4. Initial Setup Verification
```bash
# Check service health
curl http://localhost:8000/health

# Verify message broker
curl http://localhost:15672 (admin/secure_password)

# Check monitoring
curl http://localhost:9090/targets
```

## Usage

### Web Dashboard Interface

Access the main project dashboard at `http://localhost:8000/dashboard` to:
- Submit new projects via web form
- Monitor project status and progress
- View pipeline stages and completion

### API Interface

#### Submit a Project
```bash
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Todo Application",
    "description": "A web-based todo application with user authentication and task management",
    "requirements": [
      "User registration and authentication",
      "Create, read, update, delete tasks",
      "Task categorization and filtering",
      "REST API endpoints"
    ],
    "constraints": [
      "Use Python FastAPI",
      "PostgreSQL database",
      "Deploy on Docker"
    ],
    "priority": "medium",
    "technology_preferences": ["FastAPI", "PostgreSQL", "React"]
  }'
```

#### Check Project Status
```bash
curl http://localhost:8000/status/{request_id}
```

#### List All Projects
```bash
curl http://localhost:8000/requests
```

### Individual Agent APIs

Each agent exposes standard endpoints:
- `GET /health` - Health check
- `GET /status` - Agent status and metrics
- `GET /metrics` - Prometheus metrics
- Agent-specific endpoints for direct interaction

### Monitoring and Observability

The system provides comprehensive monitoring, tracing, and management dashboards. For detailed dashboard usage instructions, see [docs/dashboards.md](docs/dashboards.md).

#### Available Dashboards

| Dashboard | URL | Credentials | Purpose |
|-----------|-----|-------------|---------|
| **Main Pipeline Dashboard** | `http://localhost:8000/dashboard` | None | Primary interface for project submission and monitoring |
| **API Documentation** | `http://localhost:8000/docs` | None | Interactive API documentation and testing |
| **Grafana Monitoring** | `http://localhost:3001` | admin/admin | Service metrics visualization and alerting |
| **Prometheus Metrics** | `http://localhost:9090` | None | Raw metrics collection and querying |
| **Jaeger Tracing** | `http://localhost:16686` | None | Distributed request tracing and performance analysis |
| **RabbitMQ Management** | `http://localhost:15672` | guest/guest | Message queue monitoring and management |
| **Weaviate Console** | `http://localhost:8080` | None | Vector database management and querying |
| **Git Server** | `http://localhost:3000` | None | Code repository hosting and version control |

#### MCP Server Endpoints
- **Sequential Thinking**: `http://localhost:8101`
- **Memory Management**: `http://localhost:8102`
- **Filesystem Operations**: `http://localhost:8103`
- **Git Integration**: `http://localhost:8104`
- **Web Fetch**: `http://localhost:8105`
- **Time Services**: `http://localhost:8106`
- **Context Management**: `http://localhost:8107`

#### Quick Health Check
```bash
# Verify all services are running
curl http://localhost:8000/health

# Check dashboard availability
curl -s http://localhost:8000/dashboard | head -n 10

# Verify monitoring stack
curl -s http://localhost:9090/api/v1/query?query=up | jq '.data.result | length'
```

## Development

### Local Development Setup

1. **Install Python Dependencies**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Install Node.js Dependencies**
```bash
npm install
```

3. **Development with Hot Reload**
```bash
# Start infrastructure services only
docker-compose up -d mcp-use weaviate prometheus grafana jaeger git-server

# Run agents locally with hot reload
python services/analysis-agent/main.py
python services/planning-agent/main.py
# ... etc
```

### Adding New Agents

1. Create service directory: `services/new-agent/`
2. Implement FastAPI service with standard endpoints
3. Add Dockerfile and requirements.txt
4. Update docker-compose.yml
5. Configure message topics and routing

### Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# End-to-end pipeline tests
pytest tests/e2e/

# Performance tests
pytest tests/performance/
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM services | Required |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO |
| `BROKER_URL` | RabbitMQ connection URL | amqp://guest:guest@localhost:5672/ |
| `WEAVIATE_URL` | Weaviate vector database URL | http://localhost:8080 |
| `PROMETHEUS_URL` | Prometheus metrics endpoint | http://localhost:9090 |

### Service Configuration

Each agent can be configured via environment variables or configuration files:
- Message topics and routing
- LLM model selection and parameters
- Database connections
- Monitoring and logging settings

## Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check container logs
docker-compose logs <service-name>

# Restart specific service
docker-compose restart <service-name>

# Rebuild if needed
docker-compose build <service-name>
```

#### API Connection Issues
```bash
# Verify service health
curl http://localhost:8000/health

# Check service status
docker-compose ps

# Verify network connectivity
docker-compose exec api-gateway ping analysis-agent
```

#### Message Queue Issues
```bash
# Check RabbitMQ status
curl http://localhost:15672/api/overview

# Monitor message queues
docker-compose exec mcp-use rabbitmqctl list_queues
```

#### Performance Issues
```bash
# Check resource usage
docker stats

# Monitor service metrics
curl http://localhost:9090/api/v1/query?query=up

# View detailed traces
# Navigate to http://localhost:16686
```

### Debug Mode
Enable debug logging by setting:
```bash
export LOG_LEVEL=DEBUG
docker-compose restart
```

## Production Deployment

### Security Considerations
- Change default passwords in `.env`
- Use secure API keys and credentials
- Configure TLS/SSL certificates
- Implement proper authentication and authorization
- Network security and firewall configuration

### Scaling
- Configure service replicas in docker-compose.yml
- Use container orchestration (Kubernetes, Docker Swarm)
- Implement load balancing for high availability
- Monitor and scale based on metrics

### Backup and Recovery
- Regular backup of vector database and project data
- Database backup strategies
- Configuration backup and version control
- Disaster recovery procedures

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow Python PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Ensure all services maintain health check endpoints
- Follow semantic versioning for releases

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:
- Check the [troubleshooting section](#troubleshooting)
- Review service logs: `docker-compose logs <service-name>`
- Monitor service health: `http://localhost:8000/health`
- Create an issue in the repository

## Acknowledgments

Built with modern microservices architecture patterns and industry-standard observability tools.