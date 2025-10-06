#!/bin/bash

# Zen MCP Server Runner (Fixed for persistence)
# This script starts the zen-mcp server with proper stdio handling

set -e

echo "🚀 Starting Zen MCP Server with New Relic and Context7 integration..."

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
docker-compose -f docker-compose-fixed.yml down 2>/dev/null || true

# Remove any existing containers
docker rm -f zen-mcp-server 2>/dev/null || true

# Build and start the zen-mcp server
echo "🔨 Building and starting zen-mcp server..."
docker-compose -f docker-compose-fixed.yml up --build -d zen-mcp

# Wait for the service to be ready
echo "⏳ Waiting for zen-mcp server to start..."
sleep 10

# Check if the container is running
if ! docker ps | grep -q zen-mcp-server; then
    echo "❌ Error: zen-mcp-server container failed to start"
    echo "Checking logs..."
    docker logs zen-mcp-server
    exit 1
fi

# Check if the container is healthy (not just running)
echo "🔍 Checking container health..."
for i in {1..30}; do
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "zen-mcp-server.*Up"; then
        echo "✅ Container is running and healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Container failed to become healthy after 30 seconds"
        docker logs zen-mcp-server
        exit 1
    fi
    sleep 1
done

# Check service status
echo "📊 Checking service status..."
docker-compose -f docker-compose-fixed.yml ps

echo ""
echo "🎉 Zen MCP Server is running!"
echo ""
echo "The server includes:"
echo "  - New Relic integration (newrelic tool)"
echo "  - All existing AI tools (chat, codereview, debug, etc.)"
echo ""
echo "To test the server:"
echo "  echo '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}' | docker exec -i zen-mcp-server python server.py"
echo ""
echo "To view logs:"
echo "  docker logs -f zen-mcp-server"
echo ""
echo "To stop the server:"
echo "  docker-compose -f docker-compose-fixed.yml down"
echo ""
echo "For MCP client configuration, use:"
echo "  Command: docker"
echo "  Args: [\"exec\", \"-i\", \"zen-mcp-server\", \"python\", \"server.py\"]"
