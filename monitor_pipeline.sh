#!/bin/bash

REQUEST_ID="req_716a9f2e_1749101672"
echo "🔄 Real-time Pipeline Monitor for Request: $REQUEST_ID"
echo "Press Ctrl+C to stop monitoring"
echo "=============================================="

while true; do
    clear
    echo "🔄 SMART TODO APP - Pipeline Monitor"
    echo "Request ID: $REQUEST_ID"
    echo "Time: $(date)"
    echo "=============================================="
    
    # Get current status
    STATUS=$(curl -s http://localhost:8000/status/$REQUEST_ID)
    echo "📋 Project Status:"
    echo "$STATUS" | python3 -m json.tool 2>/dev/null || echo "$STATUS"
    echo ""
    
    # Get agent metrics
    echo "📊 Agent Activity (Messages Received):"
    echo "  API Gateway (8000):     $(curl -s http://localhost:8000/metrics | grep 'api_gateway_requests_total' | grep -v '#' | awk '{print $2}' | head -1 || echo '0')"
    echo "  Analysis Agent (8001):  $(curl -s http://localhost:8001/metrics | grep 'analysis_agent_messages_received_total' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Orchestrator (8002):    $(curl -s http://localhost:8002/metrics | grep 'orchestrator_agent_messages_received_total' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Planning Agent (8003):  $(curl -s http://localhost:8003/metrics | grep 'planning_agent_messages_received_total' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Blueprint Agent (8004): $(curl -s http://localhost:8004/metrics | grep 'blueprint_agent_messages_received_total' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Code Agent (8005):      $(curl -s http://localhost:8005/metrics | grep 'code_agent_messages_received_total' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Test Agent (8006):      $(curl -s http://localhost:8006/metrics | grep 'test_agent_messages_received_total' | grep -v '#' | awk '{print $2}' || echo '0')"
    
    echo ""
    echo "🎯 Active Tasks:"
    echo "  Analysis Agent:  $(curl -s http://localhost:8001/metrics | grep 'analysis_agent_active_tasks' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Planning Agent:  $(curl -s http://localhost:8003/metrics | grep 'planning_agent_active_tasks' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Blueprint Agent: $(curl -s http://localhost:8004/metrics | grep 'blueprint_agent_active_tasks' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Code Agent:      $(curl -s http://localhost:8005/metrics | grep 'code_agent_active_tasks' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Test Agent:      $(curl -s http://localhost:8006/metrics | grep 'test_agent_test_passes_total' | grep -v '#' | awk '{print $2}' || echo '0')"
    
    echo ""
    echo "🌐 Dashboard URLs:"
    echo "  Grafana:    http://localhost:3001 (admin/admin)"
    echo "  Prometheus: http://localhost:9090"
    echo "  Jaeger:     http://localhost:16686"
    echo "  Main API:   http://localhost:8000"
    
    sleep 3
done 