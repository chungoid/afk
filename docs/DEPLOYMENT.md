# Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Multi-Agent Software Development Pipeline in various environments, from local development to production-scale deployments.

## Prerequisites

### System Requirements

#### Minimum Requirements
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 20GB available space
- **Network**: Stable internet connection for LLM API calls

#### Recommended Production Requirements
- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Storage**: 100GB+ SSD
- **Network**: High-bandwidth connection with low latency

### Software Dependencies

#### Required
- Docker 20.10+
- Docker Compose 2.0+
- Git 2.30+

#### Optional (for Kubernetes deployment)
- kubectl 1.20+
- Helm 3.0+
- Kubernetes cluster 1.20+

### Environment Variables

Before deployment, ensure you have the following environment variables configured:

```bash
# Required - LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Optional - LLM Settings
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2000

# Message Broker Configuration
RABBITMQ_DEFAULT_USER=admin
RABBITMQ_DEFAULT_PASS=secure_random_password

# Database Configuration
WEAVIATE_URL=http://weaviate:8080

# Monitoring Configuration (Production)
PROMETHEUS_URL=http://prometheus:9090
GRAFANA_ADMIN_PASSWORD=secure_admin_password

# Security Configuration (Production)
JWT_SECRET_KEY=your_jwt_secret_key
API_KEY_SALT=your_api_key_salt
```

## Development Deployment

### Quick Start

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd test_swarm
   ```

2. **Environment Setup**
   ```bash
   cp env.example .env
   # Edit .env file with your configuration
   nano .env
   ```

3. **Deploy Services**
   ```bash
   # Build and start all services
   docker-compose up -d
   
   # Verify deployment
   docker-compose ps
   ```

4. **Health Check**
   ```bash
   # Check all services are healthy
   curl http://localhost:8000/health
   
   # Check individual services
   curl http://localhost:8001/health  # Analysis Agent
   curl http://localhost:8002/health  # Orchestrator Agent
   # ... etc for other agents
   ```

### Development Configuration

For development, you may want to:

1. **Enable Debug Logging**
   ```bash
   export LOG_LEVEL=DEBUG
   docker-compose restart
   ```

2. **Mount Source Code Volumes** (for hot reload)
   ```yaml
   # Add to docker-compose.override.yml
   version: '3.8'
   services:
     analysis-agent:
       volumes:
         - ./services/analysis-agent:/app
         - ./src:/app/src
   ```

3. **Expose Additional Ports** (for debugging)
   ```yaml
   # Add to docker-compose.override.yml
   services:
     analysis-agent:
       ports:
         - "8001:8000"
         - "5678:5678"  # For debugpy
   ```

## Staging Deployment

### Environment Setup

1. **Staging Configuration**
   ```bash
   # Create staging environment file
   cp .env .env.staging
   
   # Update staging-specific values
   sed -i 's/LOG_LEVEL=DEBUG/LOG_LEVEL=INFO/' .env.staging
   sed -i 's/localhost/staging-host/' .env.staging
   ```

2. **Deploy with Staging Configuration**
   ```bash
   docker-compose --env-file .env.staging up -d
   ```

3. **Load Testing Configuration**
   ```yaml
   # docker-compose.staging.yml
   version: '3.8'
   services:
     analysis-agent:
       deploy:
         replicas: 2
         resources:
           limits:
             memory: 2G
             cpus: '1.0'
   ```

### Staging Validation

1. **Automated Health Checks**
   ```bash
   # Create health check script
   cat > staging_health_check.sh << 'EOF'
   #!/bin/bash
   
   services=("8000" "8001" "8002" "8003" "8004" "8005" "8006")
   
   for port in "${services[@]}"; do
       if curl -f http://staging-host:$port/health > /dev/null 2>&1; then
           echo "✓ Service on port $port is healthy"
       else
           echo "✗ Service on port $port is unhealthy"
           exit 1
       fi
   done
   
   echo "All services are healthy"
   EOF
   
   chmod +x staging_health_check.sh
   ./staging_health_check.sh
   ```

2. **End-to-End Testing**
   ```bash
   # Run E2E tests against staging
   pytest tests/e2e/ --base-url=http://staging-host:8000
   ```

## Production Deployment

### Security Hardening

1. **Environment Security**
   ```bash
   # Generate secure passwords
   export RABBITMQ_DEFAULT_PASS=$(openssl rand -base64 32)
   export GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 32)
   export JWT_SECRET_KEY=$(openssl rand -base64 64)
   
   # Create production environment file
   cat > .env.production << EOF
   # Production Configuration
   LOG_LEVEL=INFO
   LOG_FORMAT=json
   
   # Security
   RABBITMQ_DEFAULT_USER=admin
   RABBITMQ_DEFAULT_PASS=$RABBITMQ_DEFAULT_PASS
   JWT_SECRET_KEY=$JWT_SECRET_KEY
   
   # LLM Configuration
   OPENAI_API_KEY=$OPENAI_API_KEY
   LLM_MODEL=gpt-4
   LLM_TEMPERATURE=0.1
   
   # Monitoring
   GRAFANA_ADMIN_PASSWORD=$GRAFANA_ADMIN_PASSWORD
   EOF
   ```

2. **Network Security**
   ```yaml
   # docker-compose.production.yml
   version: '3.8'
   services:
     api-gateway:
       ports:
         - "443:8000"  # HTTPS only
       environment:
         - TLS_CERT_PATH=/certs/server.crt
         - TLS_KEY_PATH=/certs/server.key
       volumes:
         - ./certs:/certs:ro
   
     # Remove external ports for internal services
     analysis-agent:
       ports: []
   ```

3. **Resource Limits**
   ```yaml
   # Production resource configuration
   services:
     analysis-agent:
       deploy:
         resources:
           limits:
             memory: 4G
             cpus: '2.0'
           reservations:
             memory: 2G
             cpus: '1.0'
         restart_policy:
           condition: on-failure
           max_attempts: 3
   ```

### Production Deployment Steps

1. **Prepare Production Environment**
   ```bash
   # Create production directory
   mkdir -p /opt/multi-agent-pipeline
   cd /opt/multi-agent-pipeline
   
   # Clone repository
   git clone <repository-url> .
   git checkout production
   
   # Set up environment
   cp .env.production .env
   chmod 600 .env
   ```

2. **SSL/TLS Configuration**
   ```bash
   # Create certificates directory
   mkdir -p certs
   
   # Generate self-signed certificate (for testing)
   openssl req -x509 -newkey rsa:4096 -keyout certs/server.key \
     -out certs/server.crt -days 365 -nodes \
     -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"
   
   # Or copy your SSL certificates
   cp /path/to/your/cert.crt certs/server.crt
   cp /path/to/your/key.key certs/server.key
   ```

3. **Deploy Production Services**
   ```bash
   # Pull latest images
   docker-compose -f docker-compose.yml -f docker-compose.production.yml pull
   
   # Deploy with production configuration
   docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d
   
   # Verify deployment
   docker-compose ps
   ```

4. **Database Initialization**
   ```bash
   # Wait for Weaviate to be ready
   while ! curl -f http://localhost:8080/v1/meta > /dev/null 2>&1; do
       echo "Waiting for Weaviate..."
       sleep 5
   done
   
   # Initialize vector database schema
   curl -X POST http://localhost:8080/v1/schema \
     -H "Content-Type: application/json" \
     -d @schemas/weaviate_schema.json
   ```

5. **Monitoring Setup**
   ```bash
   # Import Grafana dashboards
   for dashboard in monitoring/grafana/dashboards/*.json; do
       curl -X POST http://admin:$GRAFANA_ADMIN_PASSWORD@localhost:3001/api/dashboards/db \
         -H "Content-Type: application/json" \
         -d @$dashboard
   done
   
   # Configure Prometheus alerts
   docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
   ```

### High Availability Setup

1. **Load Balancer Configuration**
   ```nginx
   # nginx.conf for load balancing
   upstream api_gateway {
       server api-gateway-1:8000;
       server api-gateway-2:8000;
       server api-gateway-3:8000;
   }
   
   upstream analysis_agents {
       server analysis-agent-1:8000;
       server analysis-agent-2:8000;
   }
   
   server {
       listen 443 ssl;
       server_name your-domain.com;
       
       ssl_certificate /etc/ssl/certs/server.crt;
       ssl_certificate_key /etc/ssl/private/server.key;
       
       location / {
           proxy_pass http://api_gateway;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

2. **Service Scaling**
   ```yaml
   # docker-compose.ha.yml
   version: '3.8'
   services:
     api-gateway:
       deploy:
         replicas: 3
         update_config:
           parallelism: 1
           delay: 10s
       
     analysis-agent:
       deploy:
         replicas: 2
       
     planning-agent:
       deploy:
         replicas: 2
   ```

## Kubernetes Deployment

### Helm Chart

1. **Install Helm Chart**
   ```bash
   # Add Helm repository
   helm repo add multi-agent-pipeline ./k8s/helm
   
   # Install with custom values
   helm install multi-agent-pipeline ./k8s/helm/multi-agent-pipeline \
     --namespace multi-agent-pipeline \
     --create-namespace \
     --values values.production.yaml
   ```

2. **Custom Values File**
   ```yaml
   # values.production.yaml
   global:
     imageRegistry: your-registry.com
     imagePullSecrets:
       - name: registry-secret
   
   apiGateway:
     replicaCount: 3
     service:
       type: LoadBalancer
     ingress:
       enabled: true
       hosts:
         - host: api.your-domain.com
           paths: ["/"]
   
   analysisAgent:
     replicaCount: 2
     resources:
       limits:
         memory: 4Gi
         cpu: 2000m
   
   monitoring:
     prometheus:
       enabled: true
     grafana:
       enabled: true
       adminPassword: "secure-password"
   ```

### Kubernetes Manifests

1. **Namespace and RBAC**
   ```yaml
   # k8s/namespace.yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: multi-agent-pipeline
   ---
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: multi-agent-pipeline-sa
     namespace: multi-agent-pipeline
   ```

2. **ConfigMap and Secrets**
   ```yaml
   # k8s/configmap.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: multi-agent-config
     namespace: multi-agent-pipeline
   data:
     LOG_LEVEL: "INFO"
     LLM_MODEL: "gpt-4"
     BROKER_URL: "amqp://admin:password@rabbitmq:5672/"
   ---
   apiVersion: v1
   kind: Secret
   metadata:
     name: multi-agent-secrets
     namespace: multi-agent-pipeline
   type: Opaque
   stringData:
     OPENAI_API_KEY: "your-api-key"
     JWT_SECRET_KEY: "your-jwt-secret"
   ```

3. **Deployment Example**
   ```yaml
   # k8s/api-gateway-deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: api-gateway
     namespace: multi-agent-pipeline
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: api-gateway
     template:
       metadata:
         labels:
           app: api-gateway
       spec:
         containers:
         - name: api-gateway
           image: multi-agent-pipeline/api-gateway:latest
           ports:
           - containerPort: 8000
           envFrom:
           - configMapRef:
               name: multi-agent-config
           - secretRef:
               name: multi-agent-secrets
           livenessProbe:
             httpGet:
               path: /health
               port: 8000
             initialDelaySeconds: 30
             periodSeconds: 10
           readinessProbe:
             httpGet:
               path: /ready
               port: 8000
             initialDelaySeconds: 5
             periodSeconds: 5
   ```

## Monitoring and Observability

### Prometheus Configuration

```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alerts/*.yml"

scrape_configs:
  - job_name: 'multi-agent-pipeline'
    static_configs:
      - targets: 
        - 'api-gateway:8000'
        - 'analysis-agent:8000'
        - 'planning-agent:8000'
        - 'blueprint-agent:8000'
        - 'code-agent:8000'
        - 'test-agent:8000'
        - 'orchestrator-agent:8000'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboards

```json
{
  "dashboard": {
    "title": "Multi-Agent Pipeline Overview",
    "panels": [
      {
        "title": "Service Health",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"multi-agent-pipeline\"}",
            "legendFormat": "{{instance}}"
          }
        ]
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{service}}"
          }
        ]
      }
    ]
  }
}
```

## Backup and Recovery

### Database Backup

```bash
#!/bin/bash
# backup_weaviate.sh

BACKUP_DIR="/opt/backups/weaviate/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Export Weaviate data
curl -X POST http://localhost:8080/v1/backups/filesystem \
  -H "Content-Type: application/json" \
  -d '{
    "id": "backup-'$(date +%Y%m%d_%H%M%S)'",
    "include": ["ProjectDocuments", "CodePatterns"],
    "config": {
      "path": "'$BACKUP_DIR'"
    }
  }'

# Backup configuration
cp -r config/ $BACKUP_DIR/
cp .env.production $BACKUP_DIR/

echo "Backup completed: $BACKUP_DIR"
```

### Service Recovery

```bash
#!/bin/bash
# recovery.sh

# Stop services
docker-compose down

# Restore from backup
BACKUP_DIR=$1
if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

# Restore configuration
cp $BACKUP_DIR/.env.production .env
cp -r $BACKUP_DIR/config/ .

# Restore database
docker-compose up -d weaviate
sleep 30

curl -X POST http://localhost:8080/v1/backups/filesystem/restore \
  -H "Content-Type: application/json" \
  -d '{
    "id": "backup-restore",
    "config": {
      "path": "'$BACKUP_DIR'"
    }
  }'

# Start all services
docker-compose up -d

echo "Recovery completed"
```

## Performance Tuning

### Resource Optimization

1. **Memory Tuning**
   ```yaml
   services:
     analysis-agent:
       environment:
         - JAVA_OPTS=-Xmx2g -Xms1g
         - PYTHON_MEMORY_LIMIT=2048m
       deploy:
         resources:
           limits:
             memory: 4G
   ```

2. **CPU Optimization**
   ```yaml
   services:
     code-agent:
       environment:
         - WORKER_PROCESSES=4
         - WORKER_THREADS=8
       deploy:
         resources:
           limits:
             cpus: '4.0'
   ```

### Database Optimization

```bash
# Weaviate performance tuning
cat > weaviate.env << EOF
QUERY_DEFAULTS_LIMIT=100
QUERY_MAXIMUM_RESULTS=10000
PERSISTENCE_DATA_PATH=/var/lib/weaviate
ENABLE_MODULES=text2vec-openai,generative-openai
CLUSTER_HOSTNAME=weaviate
CLUSTER_GOSSIP_BIND_PORT=7000
CLUSTER_DATA_BIND_PORT=7001
EOF
```

## Troubleshooting

### Common Issues

1. **Service Startup Failures**
   ```bash
   # Check logs
   docker-compose logs -f <service-name>
   
   # Check resource usage
   docker stats
   
   # Check configuration
   docker-compose config
   ```

2. **Memory Issues**
   ```bash
   # Monitor memory usage
   docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
   
   # Adjust memory limits
   docker-compose -f docker-compose.yml -f docker-compose.memory-optimized.yml up -d
   ```

3. **Network Connectivity**
   ```bash
   # Test inter-service communication
   docker-compose exec api-gateway ping analysis-agent
   
   # Check port bindings
   docker-compose ps
   netstat -tlnp
   ```

### Health Check Scripts

```bash
#!/bin/bash
# health_check.sh

services=(
    "api-gateway:8000"
    "analysis-agent:8001"
    "orchestrator-agent:8002"
    "planning-agent:8003"
    "blueprint-agent:8004"
    "code-agent:8005"
    "test-agent:8006"
)

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if curl -f http://localhost:$port/health > /dev/null 2>&1; then
        echo "✓ $name is healthy"
    else
        echo "✗ $name is unhealthy"
        docker-compose logs --tail=20 $name
    fi
done
```

## Maintenance

### Regular Maintenance Tasks

1. **Log Rotation**
   ```bash
   # Configure logrotate
   cat > /etc/logrotate.d/multi-agent-pipeline << EOF
   /var/log/multi-agent-pipeline/*.log {
       daily
       rotate 30
       compress
       delaycompress
       missingok
       notifempty
       postrotate
           docker-compose restart
       endscript
   }
   EOF
   ```

2. **Security Updates**
   ```bash
   # Update base images
   docker-compose pull
   docker-compose up -d
   
   # Update system packages
   sudo apt update && sudo apt upgrade -y
   ```

3. **Performance Monitoring**
   ```bash
   # Weekly performance report
   cat > weekly_report.sh << 'EOF'
   #!/bin/bash
   echo "Weekly Performance Report - $(date)"
   echo "=================================="
   
   # Service uptime
   docker-compose ps
   
   # Resource usage
   docker stats --no-stream
   
   # Request metrics
   curl -s http://localhost:9090/api/v1/query?query=rate(http_requests_total[1w])
   EOF
   ```

This deployment guide provides comprehensive instructions for deploying the Multi-Agent Software Development Pipeline across different environments with proper security, monitoring, and maintenance procedures. 