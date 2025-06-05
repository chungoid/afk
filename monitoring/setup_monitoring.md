# Multi-Agent Pipeline Monitoring Setup

## 🎯 Your Monitoring Stack is Now Ready!

I've set up comprehensive monitoring for your multi-agent pipeline system. Here's what you need to know:

## 📊 Access Your Dashboards

### Main Dashboard URLs:
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)

### Grafana Dashboards Created:
1. **Multi-Agent Pipeline Monitoring** - Overview of all agents and system health
2. **RabbitMQ Message Queue Monitoring** - Detailed queue and messaging metrics

## 🔍 What to Monitor

### Key Metrics to Watch:

#### 1. Agent Health Status
- Shows UP/DOWN status for all agents
- ✅ Green = Healthy, ❌ Red = Down
- Located in the top-left panel

#### 2. RabbitMQ Queue Sizes
- Monitor message backlogs in each queue
- High numbers indicate processing bottlenecks
- Queues: tasks.analysis, tasks.planning, tasks.blueprint, tasks.coding, tasks.testing

#### 3. Agent Request Rates
- Shows how many requests each agent processes per second
- Helps identify busy vs idle agents

#### 4. Agent Response Times
- 95th and 50th percentile response times
- High values indicate performance issues

#### 5. Error Rates
- HTTP 4xx and 5xx errors by agent
- Should be close to zero in healthy system

#### 6. Memory Usage
- Memory consumption per agent
- Watch for memory leaks or high usage

## 🚨 Alert Conditions to Watch For:

### Critical Issues:
- **Agent Down**: Any agent showing "DOWN" status
- **High Queue Sizes**: >100 messages in any queue for >5 minutes
- **High Error Rates**: >1% error rate for any agent
- **High Response Times**: >5 seconds 95th percentile

### Warning Conditions:
- **Memory Usage**: >500MB per agent
- **Zero Consumers**: RabbitMQ queues with 0 consumers
- **Message Publish/Consume Imbalance**: Publishing much faster than consuming

## 📈 Dashboard Navigation

### Multi-Agent Pipeline Dashboard:
1. **Top Row**: Agent health and queue sizes
2. **Middle Rows**: Performance metrics (request rates, response times)
3. **Bottom Rows**: RabbitMQ message flow and error tracking

### RabbitMQ Dashboard:
1. **Queue Message Counts**: Current messages in each queue
2. **Consumers**: Number of active consumers per queue
3. **Message Rates**: Publish/delivery rates over time
4. **Queue Details Table**: Summary view of all queues

## 🔧 Quick Health Checks

Run these commands to quickly check system health:

```bash
# Check all agent health
curl -s http://localhost:9090/api/v1/query?query=up | jq '.data.result[] | {job: .metric.job, status: .value[1]}'

# Check queue sizes
curl -s http://localhost:9090/api/v1/query?query=rabbitmq_queue_messages | jq '.data.result[] | {queue: .metric.queue, messages: .value[1]}'

# Check for any errors
curl -s http://localhost:9090/api/v1/query?query=rate(http_requests_total{status_code=~"5.."}[5m]) | jq
```

## 📱 Mobile/Quick Access

The dashboards are responsive and work on mobile devices. Bookmark these for quick access:
- Main Dashboard: http://localhost:3001/d/2dfaabac-05bd-4d9d-a770-6b7e7a381b07
- RabbitMQ Dashboard: http://localhost:3001/d/5ff87470-568f-4af5-ae74-17c2b7d647c8

## 🛠 Troubleshooting

### If dashboards show "No Data":
1. Check Prometheus is scraping: http://localhost:9090/targets
2. Verify agents are exposing metrics on their /metrics endpoints
3. Check Grafana data source connection in Settings > Data Sources

### If RabbitMQ metrics are missing:
1. Ensure RabbitMQ management plugin is enabled
2. Check RabbitMQ is accessible at http://localhost:15672
3. Verify prometheus-rabbitmq-exporter is running

## 🎯 Next Steps

1. **Set up Alerting**: Configure alerts for critical conditions
2. **Historical Analysis**: Use longer time ranges to analyze trends
3. **Custom Metrics**: Add application-specific metrics to your agents
4. **Capacity Planning**: Monitor trends to predict scaling needs

Your monitoring stack is now production-ready! 🚀 