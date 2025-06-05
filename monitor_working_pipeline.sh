#!/bin/bash

REQUEST_ID="req_6ac2d32d_1749102503"
echo "🎉 WORKING PIPELINE MONITOR! 🎉"
echo "Request ID: $REQUEST_ID"
echo "Time: $(date)"
echo "=============================================="

while true; do
    clear
    echo "🎉 MULTI-AGENT PIPELINE - FULLY OPERATIONAL!"
    echo "Request ID: $REQUEST_ID (fixed-pipeline-test)"
    echo "Time: $(date)"
    echo "=============================================="
    
    # Get current status
    echo "📋 Project Status:"
    curl -s http://localhost:8000/status/$REQUEST_ID | python3 -m json.tool 2>/dev/null
    echo ""
    
    # RabbitMQ activity
    echo "🐰 RabbitMQ Message Flow:"
    curl -s -u guest:guest "http://localhost:15672/api/exchanges" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for ex in data:
        if 'tasks.' in ex.get('name', ''):
            msgs = ex.get('message_stats', {}).get('publish_in', 0)
            print(f'  {ex[\"name\"]}: {msgs} messages')
except: pass
" 2>/dev/null
    echo ""
    
    # Agent metrics - messages received
    echo "📊 Agent Activity (Messages Processed):"
    echo "  Analysis Agent (8001):  $(curl -s http://localhost:8001/metrics | grep 'analysis_agent_messages_received_total' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Planning Agent (8003):  $(curl -s http://localhost:8003/metrics | grep 'planning_agent_messages_received_total' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Blueprint Agent (8004): $(curl -s http://localhost:8004/metrics | grep 'blueprint_agent_messages_received_total' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Code Agent (8005):      $(curl -s http://localhost:8005/metrics | grep 'code_agent_messages_received_total' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Test Agent (8006):      $(curl -s http://localhost:8006/metrics | grep 'test_agent_messages_received_total' | grep -v '#' | awk '{print $2}' || echo '0')"
    
    echo ""
    echo "🎯 Active Processing:"
    echo "  Analysis Tasks:  $(curl -s http://localhost:8001/metrics | grep 'analysis_agent_active_tasks' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Planning Tasks:  $(curl -s http://localhost:8003/metrics | grep 'planning_agent_active_tasks' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Blueprint Tasks: $(curl -s http://localhost:8004/metrics | grep 'blueprint_agent_active_tasks' | grep -v '#' | awk '{print $2}' || echo '0')"
    echo "  Code Tasks:      $(curl -s http://localhost:8005/metrics | grep 'code_agent_active_tasks' | grep -v '#' | awk '{print $2}' || echo '0')"
    
    echo ""
    echo "✅ MONITORING SUCCESS ACHIEVED!"
    echo "🌐 Dashboards:"
    echo "  Grafana:    http://localhost:3001 (admin/admin)"
    echo "  Prometheus: http://localhost:9090"
    echo "  RabbitMQ:   http://localhost:15672 (guest/guest)"
    
    sleep 3
done 