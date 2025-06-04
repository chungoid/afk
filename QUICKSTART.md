# Quick Start Guide: Multi-Agent Swarm Pipeline

This guide will help you get the multi-agent swarm pipeline running quickly.

## Prerequisites

Before starting, ensure you have:

- **Docker & Docker Compose** (for infrastructure)
- **Node.js 16+** (for TypeScript components)
- **Python 3.9+** (for orchestrator and agents)
- **API Keys** for:
  - OpenAI (required)
  - Pinecone or Weaviate (for vector storage)

## Setup Options

### Option 1: Automated Setup (Recommended)

```bash
# Run the setup script
./setup.sh

# Follow the prompts to configure your .env file
```

### Option 2: Manual Setup

```bash
# 1. Create environment file
cp env.example .env
# Edit .env with your API keys

# 2. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Setup Node.js
npm install
npm run build
```

## Configuration

Edit your `.env` file with the required API keys:

```bash
# REQUIRED
OPENAI_API_KEY=sk-your-openai-key
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=your-environment

# OPTIONAL (for enhanced features)
AZURE_OPENAI_ENDPOINT=your-azure-endpoint
WEAVIATE_URL=http://localhost:8080
```

## Running the System

### 1. Start Infrastructure Services

```bash
# Start all supporting services (RabbitMQ, Weaviate, Git server, etc.)
docker-compose up -d

# Check services are running
docker-compose ps
```

### 2. Run Individual Components

#### Analysis Agent (TypeScript)
```bash
# Activate environment and run
source venv/bin/activate
npm start "Create a web API for user management"
```

#### Python Orchestrator
```bash
# Run the full pipeline
source venv/bin/activate
python -m orchestrator run_pipeline --input requirements.txt --verbose

# Or pipe input directly
echo "Build a React todo app" | python -m orchestrator run_pipeline
```

### 3. Full Multi-Agent Pipeline

Once infrastructure is running, the agents will communicate through message queues:

1. **Analysis Agent** → Breaks requirements into tasks
2. **Planning Agent** → Prioritizes and sequences tasks  
3. **Blueprint Agent** → Creates architecture plans
4. **Code Agent** → Generates code artifacts
5. **Test Agent** → Runs tests and validation
6. **Orchestrator** → Coordinates the entire workflow

## Monitoring & Observability

Access the following dashboards:

- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **Grafana Dashboard**: http://localhost:3001 (admin/admin)
- **Prometheus Metrics**: http://localhost:9090
- **Jaeger Tracing**: http://localhost:16686
- **Git Server**: http://localhost:3000

## Testing the System

### Quick Test - Analysis Only
```bash
# Test the analysis agent with a simple requirement
source venv/bin/activate
echo "Create a Python calculator" | python -m orchestrator run_pipeline --debug
```

### Full Pipeline Test
```bash
# Create a test requirement file
echo "Build a REST API with authentication and user management" > test_requirement.txt

# Run the full pipeline
python -m orchestrator run_pipeline --input test_requirement.txt --verbose
```

## Understanding the Output

The system will output:
- **JSON task definitions** with structured requirements
- **Message queue events** showing inter-agent communication
- **Generated artifacts** (code, tests, documentation)
- **Metrics and logs** for monitoring pipeline health

## Example Workflow

```bash
# 1. Start services
docker-compose up -d

# 2. Activate Python environment  
source venv/bin/activate

# 3. Run analysis on a requirement
echo "Create a microservice for order processing with PostgreSQL" | \
python -m orchestrator run_pipeline --debug

# 4. Monitor the message queues and agent interactions
# 5. Check generated outputs in the respective agent containers
```

## Troubleshooting

### Common Issues:

1. **API Key Errors**: Ensure your `.env` file has valid API keys
2. **Docker Issues**: Check `docker-compose logs` for service errors
3. **Python Import Errors**: Ensure virtual environment is activated
4. **TypeScript Build Errors**: Run `npm run build` to compile TS code

### Debug Commands:
```bash
# Check service health
docker-compose ps
docker-compose logs [service-name]

# Test Python imports
python -c "import orchestrator; print('OK')"

# Test Node.js build
npm run lint
npm test
```

## Next Steps

Once the system is running:

1. **Explore the Architecture**: Check `/docs` for detailed documentation
2. **Customize Agents**: Modify prompts in `/prompts` directory
3. **Add New Agents**: Create new services following the existing patterns
4. **Monitor Performance**: Use Grafana dashboards for system metrics
5. **Scale the System**: Deploy to Kubernetes using `/k8s` manifests

## Getting Help

- Check `README.md` for detailed documentation
- Review `/docs` directory for architecture details
- Monitor logs: `docker-compose logs -f`
- Test individual components using the test suite: `npm test` or `pytest` 