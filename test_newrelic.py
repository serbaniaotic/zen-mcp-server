#!/usr/bin/env python3
"""
Test script for New Relic MCP tool integration.

This script tests the New Relic tool functionality without requiring the full MCP server.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root.parent / "tamdac" / ".env")

from tools.newrelic_tool import NewRelicTool


async def test_newrelic_tool():
    """Test the New Relic tool with various query types."""
    print("Testing New Relic MCP Tool Integration")
    print("=" * 50)
    
    # Check environment variables
    api_key = os.getenv("NEW_RELIC_API_KEY") or os.getenv("NEWRELIC_API_KEY")
    account_id = os.getenv("NEW_RELIC_ACCOUNT_ID") or os.getenv("NEWRELIC_ACCOUNT_ID")
    
    if not api_key or not account_id:
        print("❌ Error: New Relic API credentials not found in environment")
        print("Please ensure NEW_RELIC_API_KEY and NEW_RELIC_ACCOUNT_ID are set")
        return False
    
    print(f"✅ API Key: {api_key[:10]}...")
    print(f"✅ Account ID: {account_id}")
    print()
    
    # Initialize the tool
    tool = NewRelicTool()
    
    # Test 1: Server metrics query
    print("Test 1: Server Metrics Query")
    print("-" * 30)
    try:
        result = await tool.execute({
            "query_type": "server_metrics",
            "query": "SELECT average(cpuPercent), average(memoryUsedBytes) FROM SystemSample",
            "time_range": "1 hour",
            "hostname": "TSCENTRAL"  # From ticket 002 context
        })
        
        print("✅ Server metrics query executed successfully")
        print(f"Result: {result[0].text[:200]}...")
    except Exception as e:
        print(f"❌ Server metrics query failed: {e}")
    
    print()
    
    # Test 2: NRQL query
    print("Test 2: NRQL Query")
    print("-" * 20)
    try:
        result = await tool.execute({
            "query_type": "nrql",
            "query": "SELECT count(*) FROM SystemSample",
            "time_range": "1 hour"
        })
        
        print("✅ NRQL query executed successfully")
        print(f"Result: {result[0].text[:200]}...")
    except Exception as e:
        print(f"❌ NRQL query failed: {e}")
    
    print()
    
    # Test 3: Application performance query
    print("Test 3: Application Performance Query")
    print("-" * 40)
    try:
        result = await tool.execute({
            "query_type": "app_performance",
            "query": "SELECT average(responseTime) FROM Transaction",
            "time_range": "1 hour"
        })
        
        print("✅ Application performance query executed successfully")
        print(f"Result: {result[0].text[:200]}...")
    except Exception as e:
        print(f"❌ Application performance query failed: {e}")
    
    print()
    print("New Relic MCP Tool Integration Test Complete!")
    return True


if __name__ == "__main__":
    asyncio.run(test_newrelic_tool())
