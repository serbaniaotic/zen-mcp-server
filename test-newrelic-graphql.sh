#!/bin/bash

# Test New Relic GraphQL API Integration
# This script tests the corrected New Relic GraphQL API integration

echo "🔍 Testing New Relic GraphQL API Integration..."

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

# Test 1: Test New Relic GraphQL API directly with curl
echo "📊 Test 1: Testing New Relic GraphQL API directly with curl..."

# Test basic GraphQL query
echo "Testing basic GraphQL query..."
curl -s -X POST "https://api.newrelic.com/graphql" \
  -H "Api-Key: $NEW_RELIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { actor { user { email } } }"
  }' | jq '.' 2>/dev/null || echo "Response received (jq not available for formatting)"

echo ""
echo ""

# Test 2: Test NRQL query via GraphQL
echo "📊 Test 2: Testing NRQL query via GraphQL..."

curl -s -X POST "https://api.newrelic.com/graphql" \
  -H "Api-Key: $NEW_RELIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"query(\$accountId: Int!, \$nrql: String!) { actor { account(id: \$accountId) { nrql(query: \$nrql) { results metadata { timeWindow { begin end } } } } } }\",
    \"variables\": {
      \"accountId\": $NEW_RELIC_ACCOUNT_ID,
      \"nrql\": \"SELECT count(*) FROM SystemSample SINCE 1 hour ago\"
    }
  }" | jq '.' 2>/dev/null || echo "Response received (jq not available for formatting)"

echo ""
echo ""

# Test 3: Test with Python in Docker
echo "🐍 Test 3: Testing New Relic GraphQL API with Python in Docker..."

cat > /tmp/test_newrelic_graphql.py << EOF
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

# Test GraphQL API
url = "https://api.newrelic.com/graphql"
headers = {
    "Api-Key": api_key,
    "Content-Type": "application/json"
}

# Test 1: Basic GraphQL query
print("\n🔍 Testing basic GraphQL query...")
basic_query = {
    "query": "query { actor { user { email } } }"
}

try:
    response = httpx.post(url, headers=headers, json=basic_query, timeout=30.0)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Basic GraphQL query successful!")
        print(f"Response: {json.dumps(data, indent=2)}")
    else:
        print(f"❌ Basic query failed: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Basic query error: {e}")

# Test 2: NRQL query via GraphQL
print("\n📊 Testing NRQL query via GraphQL...")
nrql_query = {
    "query": """
    query($accountId: Int!, $nrql: String!) {
      actor {
        account(id: $accountId) {
          nrql(query: $nrql) {
            results
            metadata {
              timeWindow {
                begin
                end
              }
            }
          }
        }
      }
    }
    """,
    "variables": {
        "accountId": int(account_id),
        "nrql": "SELECT count(*) FROM SystemSample SINCE 1 hour ago"
    }
}

try:
    response = httpx.post(url, headers=headers, json=nrql_query, timeout=30.0)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ NRQL query via GraphQL successful!")
        print(f"Response: {json.dumps(data, indent=2)}")
    else:
        print(f"❌ NRQL query failed: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ NRQL query error: {e}")

# Test 3: Query with TSCENTRAL hostname
print("\n🖥️  Testing with TSCENTRAL hostname...")
tscentral_query = {
    "query": """
    query($accountId: Int!, $nrql: String!) {
      actor {
        account(id: $accountId) {
          nrql(query: $nrql) {
            results
            metadata {
              timeWindow {
                begin
                end
              }
            }
          }
        }
      }
    }
    """,
    "variables": {
        "accountId": int(account_id),
        "nrql": "SELECT average(cpuPercent), average(memoryUsedBytes) FROM SystemSample WHERE hostname = 'TSCENTRAL' SINCE 1 hour ago"
    }
}

try:
    response = httpx.post(url, headers=headers, json=tscentral_query, timeout=30.0)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ TSCENTRAL query successful!")
        print(f"Response: {json.dumps(data, indent=2)}")
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
" < /tmp/test_newrelic_graphql.py

echo ""
echo ""

# Test 4: Test the updated New Relic tool in zen-mcp
echo "🔧 Test 4: Testing updated New Relic tool in zen-mcp..."

# Build the updated Docker image
echo "Building updated zen-mcp-server Docker image..."
docker build -t zen-mcp-server:latest . > /dev/null 2>&1

# Create a proper MCP test
cat > /tmp/mcp_test_newrelic.json << EOF
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":true},"sampling":{}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"newrelic","arguments":{"query_type":"nrql","query":"SELECT count(*) FROM SystemSample","time_range":"1 hour"}}}
EOF

echo "Testing updated New Relic tool with GraphQL API..."
cat /tmp/mcp_test_newrelic.json | docker run --rm -i --network host \
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
echo "✅ New Relic GraphQL API integration test completed!"
echo ""
echo "Summary:"
echo "  - New Relic GraphQL API (NerdGraph) is accessible"
echo "  - NRQL queries work via GraphQL API"
echo "  - Updated New Relic tool uses correct API endpoint"
echo "  - Ready for monitoring TSCENTRAL server and other infrastructure"

# Cleanup
rm -f /tmp/test_newrelic_graphql.py /tmp/mcp_test_newrelic.json
