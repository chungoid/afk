#!/bin/bash

echo "Setting up Multi-Agent Swarm Pipeline..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install Node.js 16+ first."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3.9+ is not installed. Please install Python first."
    exit 1
fi

echo "Prerequisites check passed"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp env.example .env
    echo "Please edit .env file with your API keys before proceeding"
    echo "Required: OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_ENVIRONMENT"
    read -p "Press Enter after configuring .env file..."
fi

# Setup Python virtual environment
echo "Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Setup Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

# Build TypeScript
echo "Building TypeScript code..."
npm run build

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p logs
mkdir -p data/vector-store
mkdir -p data/git-server
mkdir -p data/rabbitmq

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Start infrastructure: docker-compose up -d"
echo "3. Run the pipeline: npm start 'Your requirement here'"
echo "   OR: python -m orchestrator run_pipeline --input requirements.txt"
echo ""
echo "See README.md for detailed usage instructions" 