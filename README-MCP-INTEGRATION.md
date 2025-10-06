# Zen MCP Server with New Relic and Context7 Integration

## Overview

This setup provides a complete MCP (Model Context Protocol) server stack that includes:

- **Zen MCP Server**: Main AI-powered MCP server with multiple tools
- **New Relic Integration**: Built-in New Relic tool for server monitoring and metrics
- **Context7 Support**: Ready for Context7 MCP server integration

## Features

### Zen MCP Server Tools
- `chat` - Interactive development chat
- `codereview` - Comprehensive code review
- `debug` - Root cause analysis and debugging
- `thinkdeep` - Step-by-step deep thinking workflow
- `consensus` - Multi-model consensus building
- `newrelic` - **New Relic API integration for monitoring**
- And many more AI-powered tools

### New Relic Tool Capabilities
- Query server performance metrics (CPU, memory, disk, network)
- Execute NRQL queries for custom data analysis
- Get application performance data
- Infrastructure monitoring information
- Support for both GraphQL and REST API endpoints

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

### 2. Build the Docker Image

```bash
cd /home/dingo/code/zen-mcp-server
docker build -t zen-mcp-server:latest .
```

### 3. Test the MCP Server

```bash
# Test with proper MCP initialization
./test-mcp-proper.sh
```

### 4. MCP Client Configuration

For MCP clients (like Claude Desktop, Cursor, etc.), use this configuration:

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
    "newrelic": {
      "command": "npx",
      "args": ["-y", "@cloudbring/newrelic-mcp"],
      "env": {
        "NEW_RELIC_API_KEY": "YOUR_NEWRELIC_KEY",
        "NEW_RELIC_ACCOUNT_ID": "YOUR_ACCOUNT_ID"
      }
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@iflow-mcp/context7-mcp"]
    }
  }
}
```

## Usage Examples

### Using the New Relic Tool

```bash
# Query server metrics
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"newrelic","arguments":{"query_type":"server_metrics","query":"SELECT average(cpuPercent) FROM SystemSample","time_range":"1 hour"}}}' | docker run --rm -i --network host -e GEMINI_API_KEY="$GEMINI_API_KEY" -e OPENAI_API_KEY="$OPENAI_API_KEY" -e NEW_RELIC_API_KEY="$NEW_RELIC_API_KEY" -e NEW_RELIC_ACCOUNT_ID="$NEW_RELIC_ACCOUNT_ID" -e DEFAULT_MODEL=auto -e LOG_LEVEL=INFO -e PYTHONUNBUFFERED=1 -e PYTHONPATH=/app zen-mcp-server:latest python server.py
```

### Available New Relic Query Types

1. **server_metrics** - Get server performance metrics
2. **app_performance** - Get application performance data
3. **nrql** - Execute custom NRQL queries
4. **graphql** - Execute GraphQL queries
5. **rest** - Execute REST API calls

## Troubleshooting

### Container Issues
- Ensure all required environment variables are set
- Check Docker is running and accessible
- Verify API keys are valid

### New Relic API Issues
- Verify your New Relic API key has the correct permissions
- Check that your account ID is correct
- Ensure your New Relic account has data to query

### MCP Connection Issues
- Use the proper MCP initialization sequence
- Check that the MCP client is configured correctly
- Verify the Docker image is built and accessible

## Files Created

- `docker-compose-fixed.yml` - Docker Compose configuration
- `mcp-client-config-final.json` - MCP client configuration
- `test-mcp-proper.sh` - Proper MCP testing script
- `run-mcp-server-persistent.sh` - Persistent server runner
- `tools/newrelic_tool.py` - New Relic MCP tool implementation

## Next Steps

1. Configure your MCP client with the provided configuration
2. Test the integration with your specific New Relic data
3. Explore the Context7 integration for documentation queries
4. Customize the New Relic tool for your specific monitoring needs

The zen-mcp server now includes both New Relic monitoring capabilities and is ready for Context7 integration, providing a comprehensive MCP solution for AI agents.
