#!/bin/bash

# Test MCP Connection Script
# This script tests the MCP server connection and lists available tools

echo "🧪 Testing MCP Server Connection..."

# Check if container is running
if ! docker ps | grep -q zen-mcp-server; then
    echo "❌ Error: zen-mcp-server container is not running"
    echo "Please start it first with: ./run-zen-mcp-fixed.sh"
    exit 1
fi

echo "✅ Container is running"

# Test 1: List tools
echo ""
echo "📋 Testing tool list..."
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | docker exec -i zen-mcp-server python server.py

echo ""
echo ""

# Test 2: Test New Relic tool specifically
echo "🔍 Testing New Relic tool..."
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"newrelic","arguments":{"query_type":"server_metrics","query":"SELECT count(*) FROM SystemSample","time_range":"1 hour"}}}' | docker exec -i zen-mcp-server python server.py

echo ""
echo ""

# Test 3: Test version tool
echo "ℹ️  Testing version tool..."
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"version","arguments":{}}}' | docker exec -i zen-mcp-server python server.py

echo ""
echo "✅ MCP Server tests completed!"
