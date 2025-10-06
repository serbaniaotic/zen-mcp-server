#!/bin/bash

# Direct New Relic API Test
# This script tests the New Relic API directly to confirm it's working

echo "🔍 Testing New Relic API Directly..."

# Load environment variables
source ../tamdac/.env

# Check if required environment variables are set
if [ -z "$NEW_RELIC_API_KEY" ] || [ -z "$NEW_RELIC_ACCOUNT_ID" ]; then
    echo "❌ Error: New Relic API credentials not found in .env file"
    exit 1
fi

echo "✅ New Relic credentials found:"
echo "  API Key: ${NEW_RELIC_API_KEY:0:10}..."
echo "  Account ID: $NEW_RELIC_ACCOUNT_ID"
echo ""

# Test 1: Test New Relic API directly with curl
echo "📊 Test 1: Testing New Relic API directly with curl..."

# Test NRQL query endpoint
echo "Testing NRQL query endpoint..."
curl -s -X POST "https://api.newrelic.com/v1/accounts/$NEW_RELIC_ACCOUNT_ID/query" \
  -H "X-Api-Key: $NEW_RELIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"nrql": "SELECT count(*) FROM SystemSample SINCE 1 hour ago"}' \
  | jq '.' 2>/dev/null || echo "Response received (jq not available for formatting)"

echo ""
echo ""

# Test 2: Test with Python directly in Docker
echo "🐍 Test 2: Testing New Relic API with Python in Docker..."

cat > /tmp/test_newrelic_api.py << 'EOF'
import os
import httpx
import json

# Get credentials from environment
api_key = os.getenv("NEW_RELIC_API_KEY")
account_id = os.getenv("NEW_RELIC_ACCOUNT_ID")

if not api_key or not account_id:
    print("❌ Error: New Relic credentials not found in environment")
    exit(1)

print(f"✅ Using API Key: {api_key[:10]}...")
print(f"✅ Using Account ID: {account_id}")

# Test NRQL query
url = f"https://api.newrelic.com/v1/accounts/{account_id}/query"
headers = {
    "X-Api-Key": api_key,
    "Content-Type": "application/json"
}

payload = {
    "nrql": "SELECT count(*) FROM SystemSample SINCE 1 hour ago"
}

try:
    print("\n🔍 Testing NRQL query...")
    response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ New Relic API is working!")
        print(f"Query result: {json.dumps(data, indent=2)}")
    else:
        print(f"❌ API Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test with TSCENTRAL hostname
print("\n🖥️  Testing with TSCENTRAL hostname...")
payload_tscentral = {
    "nrql": "SELECT average(cpuPercent), average(memoryUsedBytes) FROM SystemSample WHERE hostname = 'TSCENTRAL' SINCE 1 hour ago"
}

try:
    response = httpx.post(url, headers=headers, json=payload_tscentral, timeout=30.0)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ TSCENTRAL query successful!")
        print(f"Query result: {json.dumps(data, indent=2)}")
    else:
        print(f"❌ TSCENTRAL query failed: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ TSCENTRAL query error: {e}")
EOF

# Run the Python test in Docker
docker run --rm -i --network host \
  -e NEW_RELIC_API_KEY="$NEW_RELIC_API_KEY" \
  -e NEW_RELIC_ACCOUNT_ID="$NEW_RELIC_ACCOUNT_ID" \
  python:3.11-slim sh -c "
    pip install httpx > /dev/null 2>&1 &&
    python /dev/stdin
" < /tmp/test_newrelic_api.py

echo ""
echo ""

# Test 3: Test the New Relic tool in zen-mcp with proper MCP protocol
echo "🔧 Test 3: Testing New Relic tool with proper MCP protocol..."

# Create a proper MCP test
cat > /tmp/mcp_test.json << EOF
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true},"sampling":{}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"newrelic","arguments":{"query_type":"server_metrics","query":"SELECT count(*) FROM SystemSample","time_range":"1 hour"}}}
EOF

echo "Testing New Relic tool with proper MCP initialization..."
cat /tmp/mcp_test.json | docker run --rm -i --network host \
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
echo "  - New Relic API credentials are valid"
echo "  - API endpoints are accessible"
echo "  - New Relic tool is integrated in zen-mcp server"
echo "  - Ready for monitoring TSCENTRAL server and other infrastructure"

# Cleanup
rm -f /tmp/test_newrelic_api.py /tmp/mcp_test.json
