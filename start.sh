#!/bin/bash

# Multi-Agent Pipeline Startup Script

set -e

echo "🚀 Starting Multi-Agent Pipeline..."

# Check if .env exists, if not copy from example
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your actual configuration values!"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "🏗️  Building agent services..."
docker-compose build

echo "📦 Starting infrastructure services..."
docker-compose up -d message-broker weaviate git-server prometheus grafana jaeger

echo "⏳ Waiting for infrastructure to be ready..."
sleep 10

echo "🤖 Starting agent services..."
docker-compose up -d analysis-agent planning-agent blueprint-agent code-agent test-agent orchestrator-agent

echo "🌐 Starting API Gateway..."
docker-compose up -d api-gateway

echo "✅ Multi-Agent Pipeline is starting up!"
echo ""
echo "🔗 Access URLs:"
echo "   • API Gateway Dashboard:  http://localhost:8000/dashboard"
echo "   • Orchestrator Dashboard: http://localhost:8002/dashboard" 
echo "   • RabbitMQ Management:    http://localhost:15672 (guest/guest)"
echo "   • Grafana Monitoring:     http://localhost:3001 (admin/admin)"
echo "   • Prometheus Metrics:     http://localhost:9090"
echo "   • Jaeger Tracing:         http://localhost:16686"
echo "   • Git Server:             http://localhost:3000"
echo ""
echo "📊 Check service status:"
echo "   docker-compose ps"
echo ""
echo "📝 View logs:"
echo "   docker-compose logs -f [service-name]"
echo ""
echo "🛑 Stop everything:"
echo "   docker-compose down"
echo ""
echo "🔥 To submit your first project, visit:"
echo "   http://localhost:8000/dashboard" 