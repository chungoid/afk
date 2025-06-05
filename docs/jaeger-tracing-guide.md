# Jaeger Distributed Tracing Guide

## What is Jaeger?

**Jaeger** is an open-source distributed tracing system originally developed by Uber. It helps you monitor and troubleshoot transactions in complex distributed systems by tracking requests as they flow through multiple services.

### Why Jaeger is Crucial for Your Multi-Agent Pipeline

Your system has multiple services communicating via RabbitMQ:
```
API Gateway → Analysis Agent → Planning Agent → Blueprint Agent → Code Agent → Test Agent
```

Without distributed tracing, when something goes wrong, you have to check logs across multiple services. With Jaeger, you can see the **entire request journey** in one place.

## What You'll See in Jaeger

### 1. **Request Flow Visualization**
- Complete journey from API Gateway through all agents
- See which agent received/processed each message
- Understand the exact sequence of operations

### 2. **Performance Analysis**
- **Latency:** How long each agent takes to process
- **Bottlenecks:** Which agent is slowing down the pipeline
- **Concurrency:** How many requests are being processed simultaneously

### 3. **Error Tracking**
- **Error Propagation:** See where failures start and how they cascade
- **Root Cause:** Identify the exact operation that failed
- **Context:** See the request data that caused the error

### 4. **Service Dependencies**
- Visual map of how your services interact
- MCP server calls and their performance
- Database/external API calls

## How to Use Jaeger

### 1. **Access the UI**
```bash
# Open Jaeger UI in your browser
http://localhost:16686
```

### 2. **Find Traces**
1. **Select Service:** Choose `mcp-agent-swarm.api-gateway` (or any other service)
2. **Time Range:** Adjust the time range (default: last hour)
3. **Operation:** Filter by specific operations like `submit_project_request`
4. **Click "Find Traces"**

### 3. **Analyze a Trace**
Click on any trace to see:
- **Timeline:** Visual representation of the request flow
- **Spans:** Individual operations within the trace
- **Tags:** Metadata like `request_id`, `project_name`, etc.
- **Logs:** Structured log events within each span

### 4. **Key Metrics to Monitor**

#### **Latency Analysis**
- **P95/P99 Latency:** 95th/99th percentile response times
- **Average Duration:** Mean processing time per agent
- **Slowest Requests:** Identify performance outliers

#### **Error Rates**
- **Error Percentage:** Failed requests vs total requests
- **Error Patterns:** Common failure points
- **Error Details:** Exception stack traces and context

#### **Throughput**
- **Requests per Second:** Pipeline processing capacity
- **Queue Depths:** Message backlog in RabbitMQ
- **Resource Utilization:** CPU/Memory usage correlation

## Practical Use Cases

### 1. **Debugging a Slow Pipeline**
```
Problem: User complains their project is taking too long
Solution:
1. Search for traces by request_id
2. Look at the timeline to see which agent is slow
3. Drill down into that agent's spans
4. Identify the specific operation causing delay
```

### 2. **Finding Error Root Causes**
```
Problem: Projects are failing randomly
Solution:
1. Filter traces by "error" tag
2. Look at error patterns - which agent fails most?
3. Examine error span details and logs
4. Check if errors correlate with specific input types
```

### 3. **Capacity Planning**
```
Problem: Need to scale the system
Solution:
1. Look at service dependencies graph
2. Identify bottleneck services (highest latency)
3. Analyze request volume patterns
4. Scale the slowest/most utilized services first
```

### 4. **Monitoring MCP Server Performance**
```
Problem: MCP servers might be slow
Solution:
1. Filter traces containing MCP calls
2. Compare latency of different MCP servers
3. Identify which MCP operations are slowest
4. Optimize or replace slow MCP servers
```

## What Your Traces Will Show

### Example Trace Structure:
```
📊 Trace: req_a1b2c3d4_1234567890 (Total: 2.5s)
├── 🚪 api-gateway: submit_project_request (50ms)
│   ├── 📝 Parse request data (5ms)
│   ├── 🔍 Validate project requirements (10ms)
│   └── 📤 Publish to analysis queue (35ms)
│
├── 🧠 analysis-agent: process_analysis (800ms)
│   ├── 🤖 MCP Sequential Thinking call (400ms)
│   ├── 💾 MCP Memory store analysis (100ms)
│   └── 📤 Publish to planning queue (300ms)
│
├── 📋 planning-agent: create_plan (600ms)
│   ├── 🧠 Generate project plan (450ms)
│   └── 📤 Publish to blueprint queue (150ms)
│
├── 🏗️ blueprint-agent: design_architecture (1000ms)
│   ├── 🎨 Create system design (700ms)
│   └── 📤 Publish to coding queue (300ms)
│
└── 💻 code-agent: generate_code (400ms)
    ├── 🔨 Generate source files (350ms)
    └── 📤 Publish to testing queue (50ms)
```

### Custom Tags You'll See:
- `request_id`: Unique identifier for the request
- `project_name`: Name of the project being processed
- `project_type`: Type (new, existing_git, existing_local)
- `agent_stage`: Current pipeline stage
- `mcp_server`: Which MCP server was called
- `operation_name`: Specific operation being performed
- `error`: Error flag and details if operation failed

## Advanced Jaeger Features

### 1. **Service Dependency Graph**
- Visual representation of service interactions
- Shows call volume and error rates between services
- Helps identify critical service dependencies

### 2. **Trace Comparison**
- Compare successful vs failed traces
- Identify patterns in slow vs fast requests
- Spot configuration differences

### 3. **Alerts and Monitoring**
- Set up alerts for high error rates
- Monitor SLA compliance (e.g., 95% of requests < 5s)
- Track performance trends over time

### 4. **Integration with Metrics**
- Correlate traces with Prometheus metrics
- Link Grafana dashboards to Jaeger traces
- Create comprehensive observability

## Troubleshooting Common Issues

### No Traces Appearing
1. **Check services are instrumented:**
   ```bash
   # Look for tracing initialization logs
   docker logs api-gateway | grep -i "tracing"
   ```

2. **Verify Jaeger connectivity:**
   ```bash
   # Check if services can reach Jaeger
   docker exec api-gateway curl -f http://jaeger:14268/api/traces
   ```

3. **Check environment variables:**
   ```bash
   # Ensure tracing is enabled
   docker exec api-gateway env | grep TRACING
   ```

### Incomplete Traces
- Missing spans usually indicate instrumentation gaps
- Check if all inter-service calls are instrumented
- Verify MCP server calls include trace context

### Performance Impact
- Tracing overhead is typically <1% with sampling
- Adjust `TRACING_SAMPLE_RATE` if needed (default: 1.0 = 100%)
- Use async exporters to minimize latency impact

## Testing Your Tracing Setup

### 1. **Run the Test Script**
```bash
# Generate sample traces
python test_jaeger_tracing.py
```

### 2. **Submit a Real Project**
```bash
# Use the API Gateway to submit a project
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Tracing Test",
    "description": "Test project for Jaeger tracing",
    "requirements": ["Simple web API"],
    "project_type": "new"
  }'
```

### 3. **Verify in Jaeger UI**
1. Open http://localhost:16686
2. Select service: `mcp-agent-swarm.api-gateway`
3. Click "Find Traces"
4. You should see your test traces!

## Best Practices

### 1. **Meaningful Span Names**
- Use descriptive operation names
- Include business context in span tags
- Add relevant logs and events to spans

### 2. **Proper Error Handling**
- Mark spans as errors when operations fail
- Include exception details in span tags
- Log error context for debugging

### 3. **Performance Considerations**
- Use sampling in production (typically 1-10%)
- Batch span exports for efficiency
- Monitor tracing system resource usage

### 4. **Security**
- Don't include sensitive data in span tags
- Sanitize user input before adding to traces
- Consider data retention policies

## Integration with Your Workflow

### Development
- Use traces to understand request flow
- Debug integration issues between agents
- Validate performance improvements

### Testing
- Trace end-to-end test scenarios
- Verify system behavior under load
- Catch performance regressions early

### Production
- Monitor system health and performance
- Quick incident response and debugging
- Capacity planning and optimization

## Next Steps

1. **Start the services** with tracing enabled
2. **Run the test script** to generate sample traces
3. **Explore the Jaeger UI** to understand your system
4. **Integrate tracing** into your monitoring workflow
5. **Set up alerts** for performance and error thresholds

Remember: **Distributed tracing is most valuable when you use it proactively**, not just when things break. Regular trace analysis helps you understand your system's normal behavior and catch issues before they become problems! 