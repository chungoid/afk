# Dashboard Guide

This guide provides comprehensive information about all the monitoring, management, and observability dashboards available in the Multi-Agent Software Development Pipeline.

## Overview

The system includes 8 main dashboards and 7 MCP server endpoints that provide complete visibility into the pipeline's operation, from project submission to deployment. Each dashboard serves a specific purpose in monitoring different aspects of the system.

## Main Dashboards

### 1. Pipeline Dashboard
**URL:** `http://localhost:8000/dashboard`  
**Credentials:** None required  
**Primary Purpose:** Project submission and real-time pipeline monitoring

#### What It's For
The main entry point for users to interact with the development pipeline. This dashboard provides:
- Project submission interface with web forms
- Real-time project status tracking
- Pipeline stage visualization
- Progress monitoring across all active projects

#### How to Use
1. **Submit New Projects:** Use the project submission form to input project requirements, constraints, and preferences
2. **Monitor Progress:** View active projects and their current stage in the pipeline
3. **Track Completion:** See completed projects and access generated artifacts
4. **View Logs:** Access real-time logs and status updates for ongoing projects

#### Key Features
- Intuitive web interface for non-technical users
- Real-time WebSocket updates for live progress tracking
- Project history and artifact access
- Integration with all pipeline stages

### 2. API Documentation
**URL:** `http://localhost:8000/docs`  
**Credentials:** None required  
**Primary Purpose:** Interactive API exploration and testing

#### What It's For
FastAPI's automatic interactive documentation provides:
- Complete API endpoint documentation
- Request/response schema definitions
- Interactive testing capabilities
- Authentication and authorization details

#### How to Use
1. **Explore Endpoints:** Browse all available API endpoints organized by service
2. **Test Requests:** Use the "Try it out" feature to send test requests
3. **View Schemas:** Examine request and response data models
4. **Authentication:** Test authenticated endpoints with proper credentials

#### Key Features
- Swagger UI with complete OpenAPI specification
- Interactive request testing
- Schema validation and examples
- Real-time API testing without external tools

### 3. Grafana Monitoring
**URL:** `http://localhost:3001`  
**Credentials:** admin/admin  
**Primary Purpose:** Service metrics visualization and alerting

#### What It's For
Grafana provides comprehensive system monitoring through:
- Pre-configured dashboards for each service
- Custom metrics visualization
- Alert configuration and notification
- Historical performance analysis

#### How to Use
1. **Login:** Use admin/admin credentials to access the interface
2. **Navigate Dashboards:** Select from pre-configured dashboards in the left panel
3. **Create Custom Views:** Build custom dashboards for specific monitoring needs
4. **Set Alerts:** Configure alerts for critical metrics and thresholds
5. **Analyze Trends:** Use time range selectors to analyze historical data

#### Available Dashboards
- **System Overview:** High-level system health and performance
- **Agent Performance:** Individual agent metrics and throughput
- **Infrastructure Health:** RabbitMQ, Weaviate, and other service metrics
- **Pipeline Analytics:** Project completion rates and processing times
- **Resource Utilization:** CPU, memory, and network usage

#### Key Metrics to Monitor
- Service uptime and availability
- Request latency and throughput
- Queue depths and message processing rates
- Error rates and failure patterns
- Resource consumption trends

### 4. Prometheus Metrics
**URL:** `http://localhost:9090`  
**Credentials:** None required  
**Primary Purpose:** Raw metrics collection and querying

#### What It's For
Prometheus serves as the metrics database providing:
- Time-series data collection from all services
- PromQL query language for custom metrics analysis
- Target discovery and health monitoring
- Data source for Grafana dashboards

#### How to Use
1. **Query Metrics:** Use the Expression Browser to run PromQL queries
2. **Explore Targets:** Check the Status > Targets page to verify data collection
3. **View Service Discovery:** Monitor which services are being scraped
4. **Create Alerts:** Configure alerting rules for specific conditions

#### Common Queries
```promql
# Service availability
up{job="api-gateway"}

# Request rate by service
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"4.."}[5m]) / rate(http_requests_total[5m])

# Memory usage
process_resident_memory_bytes / 1024 / 1024

# Queue depth
rabbitmq_queue_messages{queue="tasks.analysis"}
```

#### Key Features
- Real-time metrics querying
- Target health monitoring
- Service discovery integration
- Alert rule configuration

### 5. Jaeger Tracing
**URL:** `http://localhost:16686`  
**Credentials:** None required  
**Primary Purpose:** Distributed request tracing and performance analysis

#### What It's For
Jaeger provides distributed tracing capabilities for:
- Request flow visualization across services
- Performance bottleneck identification
- Service dependency mapping
- Error propagation analysis

#### How to Use
1. **Search Traces:** Use the search interface to find specific traces by service, operation, or tags
2. **Analyze Performance:** Examine trace timelines to identify slow operations
3. **Debug Issues:** Follow request paths to locate error sources
4. **Monitor Dependencies:** View service interaction patterns

#### Trace Analysis Features
- **Timeline View:** Visualize request flow and timing across services
- **Service Map:** Understand service dependencies and call patterns
- **Error Tracking:** Identify and trace error propagation
- **Performance Profiling:** Find bottlenecks and optimization opportunities

#### Key Use Cases
- Debugging cross-service communication issues
- Performance optimization and bottleneck identification
- Understanding request flow through the pipeline
- Monitoring service health and interaction patterns

### 6. RabbitMQ Management
**URL:** `http://localhost:15672`  
**Credentials:** guest/guest  
**Primary Purpose:** Message queue monitoring and management

#### What It's For
RabbitMQ Management provides message broker oversight including:
- Queue monitoring and management
- Message flow visualization
- Connection and channel monitoring
- Exchange and binding configuration

#### How to Use
1. **Login:** Use guest/guest credentials to access the management interface
2. **Monitor Queues:** View queue depths, message rates, and consumer activity
3. **Manage Connections:** Monitor client connections and channels
4. **Configure Routing:** Set up exchanges, queues, and bindings
5. **Debug Messages:** Inspect individual messages and routing patterns

#### Key Monitoring Areas
- **Queues:** Message counts, processing rates, and consumer activity
- **Exchanges:** Message routing and binding configurations
- **Connections:** Client connections and channel usage
- **Nodes:** Cluster health and resource usage

#### Critical Metrics
- Queue depth and message accumulation
- Message processing rates and consumer lag
- Connection stability and client health
- Memory and disk usage

### 7. Weaviate Console
**URL:** `http://localhost:8080`  
**Credentials:** None required  
**Primary Purpose:** Vector database management and querying

#### What It's For
Weaviate Console provides vector database management for:
- Schema configuration and management
- Data exploration and querying
- Vector similarity searches
- GraphQL query interface

#### How to Use
1. **Explore Schema:** View configured classes and properties
2. **Query Data:** Use GraphQL to search and retrieve vectors
3. **Monitor Performance:** Check query performance and indexing status
4. **Manage Data:** Import, export, and manage vector collections

#### Key Features
- GraphQL query interface for vector searches
- Schema visualization and management
- Data import/export capabilities
- Performance monitoring and optimization

### 8. Git Server
**URL:** `http://localhost:3000`  
**Credentials:** None required  
**Primary Purpose:** Code repository hosting and version control

#### What It's For
The integrated Git server provides:
- Repository hosting for generated projects
- Version control for code artifacts
- Collaboration and code review capabilities
- Integration with the deployment pipeline

#### How to Use
1. **Browse Repositories:** View all generated project repositories
2. **Examine Code:** Review generated code and project structures
3. **Track Changes:** Monitor code evolution and version history
4. **Access Artifacts:** Download or clone completed projects

## MCP Server Endpoints

### Sequential Thinking (Port 8101)
**Purpose:** Advanced reasoning and problem-solving capabilities for complex development tasks  
**Usage:** Provides multi-step reasoning for architectural decisions and complex problem solving

### Memory Management (Port 8102)
**Purpose:** Persistent storage and retrieval of context information across pipeline stages  
**Usage:** Maintains context between agent interactions and stores learning from previous projects

### Filesystem Operations (Port 8103)
**Purpose:** File system operations for code generation and project structure creation  
**Usage:** Handles file creation, modification, and project scaffolding operations

### Git Integration (Port 8104)
**Purpose:** Version control operations and repository management  
**Usage:** Manages code commits, branching, and integration with the Git server

### Web Fetch (Port 8105)
**Purpose:** Web scraping and external resource fetching capabilities  
**Usage:** Retrieves documentation, examples, and external resources during development

### Time Services (Port 8106)
**Purpose:** Scheduling, timing, and temporal operations  
**Usage:** Manages time-based operations, scheduling, and temporal context

### Context Management (Port 8107)
**Purpose:** Context preservation and sharing across agent interactions  
**Usage:** Maintains conversation context and shared state between different agents

## Dashboard Access Patterns

### For System Administrators
1. **Start with Grafana** for overall system health monitoring
2. **Check Prometheus** for detailed metrics and alerting configuration
3. **Use RabbitMQ Management** for message flow monitoring and queue health
4. **Access Jaeger** for performance troubleshooting and trace analysis

### For Developers
1. **Use API Documentation** for integration development and testing
2. **Monitor Jaeger traces** for debugging cross-service communication
3. **Check Git Server** for code artifacts and version control
4. **Use Pipeline Dashboard** for testing complete workflows

### For End Users
1. **Primary interface:** Pipeline Dashboard for project submission and monitoring
2. **Monitor progress** through real-time status updates and notifications
3. **Access results** via Git Server links and download capabilities
4. **Review logs** through dashboard interface for transparency

## Troubleshooting Dashboard Issues

### Dashboard Not Loading
```bash
# Check service status
docker-compose ps

# Verify specific service
curl http://localhost:[PORT]/health

# Check logs for errors
docker-compose logs [service-name]

# Restart specific service if needed
docker-compose restart [service-name]
```

### Authentication Issues
- **Grafana:** Default admin/admin, check environment variables if changed
- **RabbitMQ:** Default guest/guest, verify RABBITMQ_DEFAULT_USER/PASS settings
- **Other services:** Most require no authentication for local development

### Performance Issues
1. **Check system resources:** `docker stats` to monitor container resource usage
2. **Monitor metrics:** Use Prometheus to identify bottlenecks and performance issues
3. **Trace analysis:** Use Jaeger to identify slow operations and service dependencies
4. **Queue monitoring:** Review RabbitMQ queue depths for message backlog issues

### Data Not Appearing
1. **Verify data collection:** Check Prometheus targets to ensure metrics are being scraped
2. **Check service logs:** Look for errors in individual service logs
3. **Validate configuration:** Ensure proper configuration in docker-compose.yml
4. **Network connectivity:** Verify services can communicate with each other

## Best Practices

### Regular Monitoring
- Check Grafana dashboards daily for system health trends
- Monitor RabbitMQ queue depths to prevent message backlog
- Review Jaeger traces weekly for performance degradation patterns
- Use Prometheus alerts for proactive issue detection and response

### Performance Optimization
- Monitor resource usage trends in Grafana to predict scaling needs
- Use Jaeger to identify and eliminate performance bottlenecks
- Optimize queue configurations based on RabbitMQ metrics analysis
- Scale services based on utilization patterns and demand

### Security Considerations
- Change default passwords for production deployments
- Implement proper authentication for sensitive dashboards
- Monitor access logs and unusual activity patterns
- Regular security updates and patches for all components

### Maintenance Tasks
- Regular backup of dashboard configurations and historical data
- Periodic cleanup of old traces and metrics to manage storage
- Update dashboard queries and alerts based on system evolution
- Documentation updates when adding new services or metrics

## Integration Examples

### Custom Monitoring Setup
```bash
# Add custom metrics endpoint to Prometheus
curl -X POST http://localhost:9090/api/v1/admin/tsdb/snapshot

# Query specific agent performance metrics
curl 'http://localhost:9090/api/v1/query?query=rate(agent_requests_total[5m])'

# Check service health across all components
curl 'http://localhost:9090/api/v1/query?query=up'
```

### Automated Alerting Configuration
Configure Grafana alerts to notify on:
- Service downtime or health check failures
- High queue depths indicating processing bottlenecks
- Error rate spikes across services indicating system issues
- Resource utilization approaching limits requiring scaling

### Dashboard Customization
- Create custom Grafana dashboards for specific business metrics
- Implement custom metrics in services for domain-specific monitoring
- Set up automated reporting and dashboard snapshots for stakeholders
- Integrate external monitoring tools via Prometheus metrics export

### API Integration Examples
```bash
# Submit project via API and monitor through dashboards
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{"project_name": "Test Project", "description": "Dashboard test"}'

# Check project status
curl http://localhost:8000/status/{request_id}

# Monitor processing through Grafana metrics
# Navigate to http://localhost:3001 and check project processing dashboard
```

This comprehensive dashboard ecosystem provides complete visibility into the Multi-Agent Software Development Pipeline, enabling effective monitoring, troubleshooting, and optimization of the entire system from development through deployment. 