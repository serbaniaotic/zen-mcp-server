#!/bin/bash

# Zen MCP Server Persistent Runner
# This script runs the zen-mcp server in a way that keeps it running for MCP connections

set -e

echo "🚀 Starting Zen MCP Server (Persistent Mode)..."

# Check if .env file exists
if [ ! -f "../tamdac/.env" ]; then
    echo "❌ Error: .env file not found at ../tamdac/.env"
    exit 1
fi

# Load environment variables
export $(cat ../tamdac/.env | grep -v '^#' | xargs)

echo "✅ Environment variables loaded"

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker rm -f zen-mcp-server 2>/dev/null || true

# Build the image
echo "🔨 Building zen-mcp server image..."
docker build -t zen-mcp-server:latest .

# Run the container in interactive mode with a keep-alive mechanism
echo "🚀 Starting zen-mcp server container..."
docker run -d \
  --name zen-mcp-server \
  --network host \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e NEW_RELIC_API_KEY="$NEW_RELIC_API_KEY" \
  -e NEW_RELIC_ACCOUNT_ID="$NEW_RELIC_ACCOUNT_ID" \
  -e DEFAULT_MODEL="auto" \
  -e LOG_LEVEL="INFO" \
  -e PYTHONUNBUFFERED=1 \
  -e PYTHONPATH=/app \
  -v zen-mcp-logs:/app/logs \
  zen-mcp-server:latest \
  sh -c "while true; do echo 'MCP Server Ready' && python server.py; sleep 1; done"

# Wait for the container to start
echo "⏳ Waiting for container to start..."
sleep 5

# Check if the container is running
if ! docker ps | grep -q zen-mcp-server; then
    echo "❌ Error: Container failed to start"
    docker logs zen-mcp-server
    exit 1
fi

echo "✅ Zen MCP Server is running!"
echo ""
echo "Container: zen-mcp-server"
echo "Status: $(docker ps --format 'table {{.Names}}\t{{.Status}}' | grep zen-mcp-server)"
echo ""
echo "To test the server:"
echo "  echo '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}' | docker exec -i zen-mcp-server python server.py"
echo ""
echo "To view logs:"
echo "  docker logs -f zen-mcp-server"
echo ""
echo "To stop the server:"
echo "  docker stop zen-mcp-server && docker rm zen-mcp-server"
echo ""
echo "For MCP client configuration:"
echo "  Command: docker"
echo "  Args: [\"exec\", \"-i\", \"zen-mcp-server\", \"python\", \"server.py\"]"
