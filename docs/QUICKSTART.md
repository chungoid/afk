# Quick Start Guide

## Get Up and Running in 5 Minutes

This guide will get you from zero to a fully functional multi-agent development pipeline in just a few minutes.

## Prerequisites Check

Before starting, ensure you have:
- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- At least 8GB RAM available
- OpenAI API key

**Verify Prerequisites:**
```bash
docker --version          # Should be 20.10+
docker-compose --version  # Should be 2.0+
free -h                   # Check available RAM
```

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd test_swarm

# Create environment configuration
cp env.example .env

# Edit the environment file (REQUIRED)
nano .env
```

**Required Environment Variables:**
```bash
# Minimal required configuration
OPENAI_API_KEY=your_openai_api_key_here
RABBITMQ_DEFAULT_USER=admin
RABBITMQ_DEFAULT_PASS=your_secure_password
```

## Step 2: Deploy the System

```bash
# Build and start all services (this may take 3-5 minutes)
docker-compose up -d

# Wait for all services to become healthy
docker-compose ps
```

**Expected Output:**
```
       Name                   Command                State                 Ports
------------------------------------------------------------------------------------------
analysis-agent       python main.py               Up (healthy)   0.0.0.0:8001->8000/tcp
api-gateway          python main.py               Up (healthy)   0.0.0.0:8000->8000/tcp
blueprint-agent      python main.py               Up (healthy)   0.0.0.0:8004->8000/tcp
code-agent           python main.py               Up (healthy)   0.0.0.0:8005->8000/tcp
orchestrator-agent   python main.py               Up (healthy)   0.0.0.0:8002->8000/tcp
planning-agent       python main.py               Up (healthy)   0.0.0.0:8003->8000/tcp
test-agent           python main.py               Up (healthy)   0.0.0.0:8006->8000/tcp
...
```

## Step 3: Verify Installation

```bash
# Check system health
curl http://localhost:8000/health

# Should return: {"status": "healthy", ...}
```

**Access Web Interfaces:**
- **Main Dashboard**: http://localhost:8000/dashboard
- **Pipeline Monitor**: http://localhost:8002/dashboard
- **RabbitMQ Management**: http://localhost:15672 (admin/your_password)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

## Step 4: Submit Your First Project

### Option A: Web Dashboard
1. Open http://localhost:8000/dashboard
2. Fill out the project form
3. Click "Submit Project"
4. Monitor progress in real-time

### Option B: API Command
```bash
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Todo App",
    "description": "Simple todo application with REST API",
    "requirements": [
      "User authentication",
      "Create and manage todos",
      "REST API endpoints",
      "Database storage"
    ],
    "constraints": [
      "Use Python FastAPI",
      "PostgreSQL database"
    ],
    "priority": "medium",
    "technology_preferences": ["FastAPI", "PostgreSQL", "Docker"]
  }'
```

**Response:**
```json
{
  "request_id": "abc123-def456-ghi789",
  "status": "submitted",
  "message": "Project submitted successfully",
  "tracking_url": "http://localhost:8000/status/abc123-def456-ghi789"
}
```

## Step 5: Monitor Progress

```bash
# Check project status (replace with your request_id)
curl http://localhost:8000/status/abc123-def456-ghi789

# Watch real-time progress
curl http://localhost:8002/dashboard  # Or open in browser
```

**Pipeline Stages:**
1. **Analysis** (1-2 minutes): Requirements analysis and task breakdown
2. **Planning** (2-3 minutes): Project planning and timeline creation
3. **Blueprint** (3-5 minutes): Technical architecture design
4. **Coding** (10-20 minutes): Source code generation
5. **Testing** (5-10 minutes): Test creation and execution

## Quick Reference

### Service Ports
| Service | Port | Purpose |
|---------|------|---------|
| API Gateway | 8000 | Main entry point and dashboard |
| Analysis Agent | 8001 | Requirements analysis |
| Orchestrator | 8002 | Pipeline coordination |
| Planning Agent | 8003 | Project planning |
| Blueprint Agent | 8004 | Architecture design |
| Code Agent | 8005 | Code generation |
| Test Agent | 8006 | Testing and QA |

### Infrastructure Ports
| Service | Port | Purpose |
|---------|------|---------|
| RabbitMQ | 15672 | Message queue management |
| Weaviate | 8080 | Vector database |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3001 | Monitoring dashboards |
| Jaeger | 16686 | Distributed tracing |

### Essential Commands

```bash
# Start the system
docker-compose up -d

# Stop the system
docker-compose down

# Check logs
docker-compose logs -f <service-name>

# Check all service status
docker-compose ps

# Restart a specific service
docker-compose restart <service-name>

# Update and rebuild
docker-compose pull && docker-compose up -d
```

### Health Check URLs

```bash
# Individual service health checks
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # Analysis Agent
curl http://localhost:8002/health  # Orchestrator
curl http://localhost:8003/health  # Planning Agent
curl http://localhost:8004/health  # Blueprint Agent
curl http://localhost:8005/health  # Code Agent
curl http://localhost:8006/health  # Test Agent
```

## Common Issues & Quick Fixes

### Services Won't Start
```bash
# Check Docker resources
docker system prune -f
docker volume prune -f

# Check logs for specific errors
docker-compose logs <service-name>

# Restart with fresh containers
docker-compose down && docker-compose up -d
```

### Out of Memory
```bash
# Check memory usage
docker stats

# Restart services one by one
docker-compose restart api-gateway
docker-compose restart analysis-agent
# etc...
```

### API Key Issues
```bash
# Verify API key is set
grep OPENAI_API_KEY .env

# Test API key manually
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.openai.com/v1/models
```

### Port Conflicts
```bash
# Check what's using ports
netstat -tlnp | grep :8000

# Stop conflicting services
sudo systemctl stop apache2  # Example
```

## Next Steps

Once your system is running:

1. **Explore the Web Dashboard**: http://localhost:8000/dashboard
2. **Monitor Real-time Progress**: http://localhost:8002/dashboard
3. **Check System Metrics**: http://localhost:9090
4. **Review Generated Code**: Check the Git server at http://localhost:3000
5. **Read the Full Documentation**: See [README.md](../README.md) and [docs/](.)

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](DEPLOYMENT.md#troubleshooting)
2. Review service logs: `docker-compose logs <service-name>`
3. Verify system health: `curl http://localhost:8000/health`
4. Check resource usage: `docker stats`

## Sample Projects to Try

### Simple Web API
```json
{
  "project_name": "User Management API",
  "description": "REST API for user management with authentication",
  "requirements": [
    "User registration and login",
    "JWT authentication",
    "CRUD operations for users",
    "Input validation"
  ],
  "technology_preferences": ["FastAPI", "SQLite"]
}
```

### Microservice Application
```json
{
  "project_name": "E-commerce Microservices",
  "description": "Microservices-based e-commerce platform",
  "requirements": [
    "Product catalog service",
    "Shopping cart service", 
    "Order processing service",
    "API Gateway",
    "Service discovery"
  ],
  "technology_preferences": ["FastAPI", "PostgreSQL", "Docker", "Nginx"]
}
```

### Data Processing Pipeline
```json
{
  "project_name": "Data Analytics Pipeline",
  "description": "ETL pipeline for data processing and analytics",
  "requirements": [
    "Data ingestion from APIs",
    "Data transformation and cleaning",
    "Storage in data warehouse",
    "Automated reporting",
    "Monitoring and alerting"
  ],
  "technology_preferences": ["Python", "Apache Airflow", "PostgreSQL", "Redis"]
}
```

You're now ready to start building with the Multi-Agent Software Development Pipeline! 