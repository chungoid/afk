#!/bin/bash

echo "Starting MCP-Enhanced Agent Swarm"
echo "===================================="

echo "Pulling MCP server images..."
docker pull ghcr.io/chungoid/fetch:latest
docker pull ghcr.io/chungoid/filesystem:latest
docker pull ghcr.io/chungoid/git:latest
docker pull ghcr.io/chungoid/memory:latest
docker pull ghcr.io/chungoid/sequentialthinking:latest
docker pull ghcr.io/chungoid/time:latest
docker pull ghcr.io/chungoid/context7:latest

echo "Starting infrastructure and MCP servers..."
docker-compose up -d message-broker weaviate git-server
docker-compose up -d mcp-fetch mcp-filesystem mcp-git mcp-memory mcp-sequentialthinking mcp-time mcp-context7

echo "Waiting for MCP servers to be ready..."
sleep 10

echo "Checking MCP server health..."
for port in 8100 8101 8102 8103 8104 8105 8106; do
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        echo "MCP server on port $port is healthy"
    else
        echo "MCP server on port $port not responding"
    fi
done

echo "Starting agent services..."
docker-compose up -d analysis-agent planning-agent blueprint-agent code-agent test-agent orchestrator-agent api-gateway

echo "Starting monitoring..."
docker-compose up -d prometheus grafana jaeger

echo ""
echo "MCP-Enhanced Agent Swarm is now running!"
echo "=================================="
echo "Dashboard:     http://localhost:8000"
echo "Grafana:       http://localhost:3001 (admin/admin)"
echo "Prometheus:    http://localhost:9090"
echo "Jaeger:        http://localhost:16686"
echo ""
echo "MCP Servers:"
echo "   Fetch:         http://localhost:8100"
echo "   Filesystem:    http://localhost:8101"
echo "   Git:           http://localhost:8102"
echo "   Memory:        http://localhost:8103"
echo "   SeqThinking:   http://localhost:8104"
echo "   Time:          http://localhost:8105"
echo "   Context7:      http://localhost:8106"
echo ""
echo "To test MCP integration: python test_mcp_enhanced_analysis.py" 