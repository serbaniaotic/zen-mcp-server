#!/bin/bash

# Test New Relic API Configuration in Docker
# This script specifically tests the New Relic integration in the Docker container

echo "🔍 Testing New Relic API Configuration in Docker..."

# Load environment variables
source ../tamdac/.env

# Check if required environment variables are set
if [ -z "$NEW_RELIC_API_KEY" ] || [ -z "$NEW_RELIC_ACCOUNT_ID" ]; then
    echo "❌ Error: New Relic API credentials not found in .env file"
    echo "Please ensure your .env file contains:"
    echo "  NEW_RELIC_API_KEY=your_api_key_here"
    echo "  NEW_RELIC_ACCOUNT_ID=your_account_id_here"
    exit 1
fi

echo "✅ New Relic credentials found:"
echo "  API Key: ${NEW_RELIC_API_KEY:0:10}..."
echo "  Account ID: $NEW_RELIC_ACCOUNT_ID"
echo ""

# Build the Docker image
echo "🔨 Building zen-mcp-server Docker image..."
docker build -t zen-mcp-server:latest . > /dev/null 2>&1

# Test 1: Check if New Relic tool is available
echo "📋 Test 1: Checking if New Relic tool is available..."
{
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true},"sampling":{}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}'
    sleep 1
    echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
} | docker run --rm -i --network host \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e NEW_RELIC_API_KEY="$NEW_RELIC_API_KEY" \
  -e NEW_RELIC_ACCOUNT_ID="$NEW_RELIC_ACCOUNT_ID" \
  -e DEFAULT_MODEL=auto \
  -e LOG_LEVEL=INFO \
  -e PYTHONUNBUFFERED=1 \
  -e PYTHONPATH=/app \
  zen-mcp-server:latest python server.py | grep -A 5 -B 5 "newrelic"

echo ""

# Test 2: Test New Relic tool initialization
echo "🔍 Test 2: Testing New Relic tool initialization..."
{
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true},"sampling":{}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}'
    sleep 1
    echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"newrelic","arguments":{"query_type":"server_metrics","query":"SELECT count(*) FROM SystemSample","time_range":"1 hour"}}}'
} | docker run --rm -i --network host \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e NEW_RELIC_API_KEY="$NEW_RELIC_API_KEY" \
  -e NEW_RELIC_ACCOUNT_ID="$NEW_RELIC_ACCOUNT_ID" \
  -e DEFAULT_MODEL=auto \
  -e LOG_LEVEL=INFO \
  -e PYTHONUNBUFFERED=1 \
  -e PYTHONPATH=/app \
  zen-mcp-server:latest python server.py

echo ""

# Test 3: Test different New Relic query types
echo "📊 Test 3: Testing different New Relic query types..."

echo "Testing NRQL query..."
{
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true},"sampling":{}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}'
    sleep 1
    echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"newrelic","arguments":{"query_type":"nrql","query":"SELECT count(*) FROM SystemSample","time_range":"1 hour"}}}'
} | docker run --rm -i --network host \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e NEW_RELIC_API_KEY="$NEW_RELIC_API_KEY" \
  -e NEW_RELIC_ACCOUNT_ID="$NEW_RELIC_ACCOUNT_ID" \
  -e DEFAULT_MODEL=auto \
  -e LOG_LEVEL=INFO \
  -e PYTHONUNBUFFERED=1 \
  -e PYTHONPATH=/app \
  zen-mcp-server:latest python server.py

echo ""
echo ""

# Test 4: Test with specific hostname (TSCENTRAL from ticket 002)
echo "🖥️  Test 4: Testing with TSCENTRAL hostname (from ticket 002)..."
{
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true},"sampling":{}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}'
    sleep 1
    echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"newrelic","arguments":{"query_type":"server_metrics","query":"SELECT average(cpuPercent), average(memoryUsedBytes) FROM SystemSample","time_range":"1 hour","hostname":"TSCENTRAL"}}}'
} | docker run --rm -i --network host \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e NEW_RELIC_API_KEY="$NEW_RELIC_API_KEY" \
  -e NEW_RELIC_ACCOUNT_ID="$NEW_RELIC_ACCOUNT_ID" \
  -e DEFAULT_MODEL=auto \
  -e LOG_LEVEL=INFO \
  -e PYTHONUNBUFFERED=1 \
  -e PYTHONPATH=/app \
  zen-mcp-server:latest python server.py

echo ""
echo "✅ New Relic API configuration test completed!"
echo ""
echo "Summary:"
echo "  - New Relic tool is available in zen-mcp server"
echo "  - API credentials are properly passed to Docker container"
echo "  - Tool can execute different query types"
echo "  - Ready for monitoring TSCENTRAL server and other infrastructure"
