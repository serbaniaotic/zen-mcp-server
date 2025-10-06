#!/bin/bash

# Zen MCP Stack Runner
# This script starts the complete MCP stack including zen-mcp, newrelic-mcp, and context7-mcp

set -e

echo "🚀 Starting Zen MCP Stack with New Relic and Context7..."

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
docker-compose -f docker-compose-with-mcp.yml down 2>/dev/null || true

# Build and start the stack
echo "🔨 Building and starting MCP stack..."
docker-compose -f docker-compose-with-mcp.yml up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Checking service status..."
docker-compose -f docker-compose-with-mcp.yml ps

echo ""
echo "🎉 Zen MCP Stack is running!"
echo ""
echo "Services:"
echo "  - zen-mcp-server: Main MCP server with AI tools"
echo "  - newrelic-mcp-server: New Relic monitoring integration"
echo "  - context7-mcp-server: Documentation and code examples"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose-with-mcp.yml logs -f"
echo ""
echo "To stop the stack:"
echo "  docker-compose -f docker-compose-with-mcp.yml down"
echo ""
echo "To test the integration:"
echo "  echo '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}' | docker exec -i zen-mcp-server python server.py"
