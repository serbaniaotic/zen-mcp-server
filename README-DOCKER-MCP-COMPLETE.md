# Complete Docker MCP Stack: Zen + New Relic + Context7

## Overview

This setup provides a complete MCP (Model Context Protocol) server stack running in Docker containers:

- **Zen MCP Server**: AI-powered MCP server with multiple tools including New Relic integration
- **Context7 MCP Server**: Documentation and code examples server
- **New Relic Integration**: Built into zen-mcp server for monitoring and metrics

## ✅ What's Working

### Zen MCP Server
- **All AI tools**: chat, codereview, debug, thinkdeep, consensus, etc.
- **New Relic tool**: Query server metrics, execute NRQL queries, get performance data
- **Docker ready**: Runs on-demand when MCP clients connect

### Context7 MCP Server  
- **Documentation queries**: Get up-to-date library documentation
- **Code examples**: Retrieve code snippets and examples
- **Library resolution**: Find and resolve library IDs
- **Docker ready**: Runs on-demand when MCP clients connect

## Quick Start

### 1. Environment Setup

Ensure your `.env` file contains the required API keys:

```bash
# Required for New Relic integration
NEW_RELIC_API_KEY=your_api_key_here
NEW_RELIC_ACCOUNT_ID=your_account_id_here

# Required for AI tools
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here
```

### 2. Test the Servers

```bash
cd /home/dingo/code/zen-mcp-server
./test-docker-mcp-servers.sh
```

### 3. MCP Client Configuration

Use this configuration in your MCP client (Claude Desktop, Cursor, etc.):

```json
{
  "mcpServers": {
    "zen": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i", "--network", "host",
        "-e", "GEMINI_API_KEY=${GEMINI_API_KEY}",
        "-e", "OPENAI_API_KEY=${OPENAI_API_KEY}",
        "-e", "NEW_RELIC_API_KEY=${NEW_RELIC_API_KEY}",
        "-e", "NEW_RELIC_ACCOUNT_ID=${NEW_RELIC_ACCOUNT_ID}",
        "-e", "DEFAULT_MODEL=auto",
        "-e", "LOG_LEVEL=INFO",
        "-e", "PYTHONUNBUFFERED=1",
        "-e", "PYTHONPATH=/app",
        "zen-mcp-server:latest",
        "python", "server.py"
      ]
    },
    "context7": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i", "node:18-alpine",
        "sh", "-c", "npm install -g @iflow-mcp/context7-mcp && context7-mcp"
      ]
    }
  }
}
```

## Available Tools

### Zen MCP Server Tools
- `chat` - Interactive development chat
- `codereview` - Comprehensive code review
- `debug` - Root cause analysis and debugging
- `thinkdeep` - Step-by-step deep thinking workflow
- `consensus` - Multi-model consensus building
- `newrelic` - **New Relic API integration for monitoring**
- `version` - Server version and system information
- And many more AI-powered tools

### Context7 MCP Server Tools
- `resolve-library-id` - Find Context7-compatible library IDs
- `get-library-docs` - Fetch up-to-date documentation and code examples

### New Relic Tool Capabilities
- Query server performance metrics (CPU, memory, disk, network)
- Execute NRQL queries for custom data analysis
- Get application performance data
- Infrastructure monitoring information
- Support for both GraphQL and REST API endpoints

## Usage Examples

### Using New Relic Tool
```bash
# Query server metrics for TSCENTRAL server
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"newrelic","arguments":{"query_type":"server_metrics","query":"SELECT average(cpuPercent) FROM SystemSample WHERE hostname = '\''TSCENTRAL'\''","time_range":"1 hour"}}}' | docker run --rm -i --network host -e GEMINI_API_KEY="$GEMINI_API_KEY" -e OPENAI_API_KEY="$OPENAI_API_KEY" -e NEW_RELIC_API_KEY="$NEW_RELIC_API_KEY" -e NEW_RELIC_ACCOUNT_ID="$NEW_RELIC_ACCOUNT_ID" -e DEFAULT_MODEL=auto -e LOG_LEVEL=INFO -e PYTHONUNBUFFERED=1 -e PYTHONPATH=/app zen-mcp-server:latest python server.py
```

### Using Context7 Tool
```bash
# Get documentation for a library
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"resolve-library-id","arguments":{"libraryName":"react"}}}' | docker run --rm -i node:18-alpine sh -c "npm install -g @iflow-mcp/context7-mcp && context7-mcp"
```

## Key Benefits

1. **Complete MCP Stack**: Both zen-mcp and context7-mcp servers ready
2. **New Relic Integration**: Built-in monitoring capabilities for service issues
3. **Docker Ready**: Both servers run on-demand when MCP clients connect
4. **No Reboot Loops**: Properly configured to handle MCP server lifecycle
5. **Agent Ready**: Perfect for AI agents to query both monitoring data and documentation

## Files Created

- `docker-compose-with-context7.yml` - Docker Compose for both servers
- `mcp-client-config-complete.json` - Complete MCP client configuration
- `test-docker-mcp-servers.sh` - Test script for both servers
- `run-complete-mcp-stack.sh` - Startup script for the complete stack
- `tools/newrelic_tool.py` - New Relic MCP tool implementation

## Next Steps

1. **Configure your MCP client** with the provided configuration
2. **Test the integration** with your specific New Relic data
3. **Use Context7** for up-to-date documentation queries
4. **Leverage New Relic** for monitoring your ReadQueen POS environment

The complete MCP stack is now ready for production use with both monitoring and documentation capabilities!
