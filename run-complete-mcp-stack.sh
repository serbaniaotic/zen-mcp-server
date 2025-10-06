#!/bin/bash

# Complete MCP Stack Runner
# This script starts zen-mcp and context7-mcp servers together

set -e

echo "🚀 Starting Complete MCP Stack (Zen + Context7)..."

# Check if .env file exists
if [ ! -f "../tamdac/.env" ]; then
    echo "❌ Error: .env file not found at ../tamdac/.env"
    echo "Please ensure your .env file contains the required API keys:"
    echo "  - NEW_RELIC_API_KEY"
    echo "  - NEW_RELIC_ACCOUNT_ID"
    echo "  - GEMINI_API_KEY"
    echo "  - OPENAI_API_KEY"
    exit 1
fi

# Load environment variables
export $(cat ../tamdac/.env | grep -v '^#' | xargs)

# Check required environment variables
if [ -z "$NEW_RELIC_API_KEY" ] || [ -z "$NEW_RELIC_ACCOUNT_ID" ]; then
    echo "❌ Error: New Relic API credentials not found in .env file"
    echo "Please add the following to your .env file:"
    echo "  NEW_RELIC_API_KEY=your_api_key_here"
    echo "  NEW_RELIC_ACCOUNT_ID=your_account_id_here"
    exit 1
fi

echo "✅ Environment variables loaded"

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose-with-context7.yml down 2>/dev/null || true

# Remove any existing containers
docker rm -f zen-mcp-server context7-mcp-server 2>/dev/null || true

# Build and start the complete stack
echo "🔨 Building and starting complete MCP stack..."
docker-compose -f docker-compose-with-context7.yml up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 15

# Check if containers are running
echo "🔍 Checking container status..."
if ! docker ps | grep -q zen-mcp-server; then
    echo "❌ Error: zen-mcp-server container failed to start"
    echo "Checking logs..."
    docker logs zen-mcp-server
    exit 1
fi

if ! docker ps | grep -q context7-mcp-server; then
    echo "❌ Error: context7-mcp-server container failed to start"
    echo "Checking logs..."
    docker logs context7-mcp-server
    exit 1
fi

# Check service status
echo "📊 Checking service status..."
docker-compose -f docker-compose-with-context7.yml ps

echo ""
echo "🎉 Complete MCP Stack is running!"
echo ""
echo "Services:"
echo "  - zen-mcp-server: Main MCP server with AI tools + New Relic integration"
echo "  - context7-mcp-server: Documentation and code examples"
echo ""
echo "To test the services:"
echo "  ./test-complete-stack.sh"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose-with-context7.yml logs -f"
echo ""
echo "To stop the stack:"
echo "  docker-compose -f docker-compose-with-context7.yml down"
echo ""
echo "MCP Client Configuration:"
echo "  Use the configuration in mcp-client-config-complete.json"
