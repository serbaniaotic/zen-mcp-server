#!/bin/bash

# Proper MCP Test Script
# This script tests the MCP server with proper initialization

echo "🧪 Testing MCP Server with Proper Initialization..."

# Load environment variables
source ../tamdac/.env

# Test 1: Initialize and list tools
echo "📋 Testing MCP initialization and tool list..."
{
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true},"sampling":{}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}'
    sleep 1
    echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
    sleep 1
    echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"newrelic","arguments":{"query_type":"server_metrics","query":"SELECT count(*) FROM SystemSample","time_range":"1 hour"}}}'
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
echo "✅ MCP Server test completed!"
