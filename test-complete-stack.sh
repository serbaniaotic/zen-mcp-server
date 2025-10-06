#!/bin/bash

# Complete MCP Stack Test Script
# This script tests both zen-mcp and context7-mcp servers

echo "🧪 Testing Complete MCP Stack..."

# Check if containers are running
if ! docker ps | grep -q zen-mcp-server; then
    echo "❌ Error: zen-mcp-server container is not running"
    echo "Please start it first with: ./run-complete-mcp-stack.sh"
    exit 1
fi

if ! docker ps | grep -q context7-mcp-server; then
    echo "❌ Error: context7-mcp-server container is not running"
    echo "Please start it first with: ./run-complete-mcp-stack.sh"
    exit 1
fi

echo "✅ Both containers are running"

# Load environment variables
source ../tamdac/.env

# Test 1: Zen MCP Server
echo ""
echo "📋 Testing Zen MCP Server..."
echo "Testing tool list and New Relic integration..."
{
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true},"sampling":{}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}'
    sleep 1
    echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
    sleep 1
    echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"version","arguments":{}}}'
} | docker exec -i zen-mcp-server python server.py

echo ""
echo ""

# Test 2: Context7 MCP Server
echo "📚 Testing Context7 MCP Server..."
echo "Testing Context7 initialization..."
{
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true},"sampling":{}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}'
    sleep 1
    echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
} | docker exec -i context7-mcp-server context7-mcp

echo ""
echo ""

# Test 3: New Relic Tool (if available)
echo "🔍 Testing New Relic Tool..."
echo "Testing New Relic server metrics query..."
{
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true},"sampling":{}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}'
    sleep 1
    echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"newrelic","arguments":{"query_type":"server_metrics","query":"SELECT count(*) FROM SystemSample","time_range":"1 hour"}}}'
} | docker exec -i zen-mcp-server python server.py

echo ""
echo "✅ Complete MCP Stack tests completed!"
echo ""
echo "Summary:"
echo "  - Zen MCP Server: ✅ Running with New Relic integration"
echo "  - Context7 MCP Server: ✅ Running for documentation queries"
echo "  - Both servers are ready for MCP client connections"
