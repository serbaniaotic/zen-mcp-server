# Docker MCP Setup Guide

## Overview
The zen-mcp-server Docker image is ready. To use it with Claude Code, you need to configure it as an MCP server.

## Quick Setup

### 1. Add to Claude Code MCP Settings

Add this to your Claude Code MCP settings (`.claude/mcp_settings.json` or via Settings UI):

```json
{
  "mcpServers": {
    "zen": {
      "command": "/home/dingo/code/zen-mcp-server/run-docker-mcp.sh",
      "env": {
        "GEMINI_API_KEY": "YOUR_GEMINI_KEY",
        "OPENAI_API_KEY": "YOUR_OPENAI_KEY",
        "DEFAULT_MODEL": "auto",
        "LOG_LEVEL": "INFO",
        "DISABLED_TOOLS": "analyze,refactor,testgen,secaudit,docgen,tracer"
      }
    }
  }
}
```

### 2. Alternative: Use Environment File

Create `.env` in the zen-mcp-server directory:

```bash
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
XAI_API_KEY=your_key_here
DEFAULT_MODEL=auto
LOG_LEVEL=DEBUG
DISABLED_TOOLS=analyze,refactor,testgen,secaudit,docgen,tracer
```

Then use simplified config:

```json
{
  "mcpServers": {
    "zen": {
      "command": "/home/dingo/code/zen-mcp-server/run-docker-mcp.sh"
    }
  }
}
```

## How It Works

1. **Wrapper Script**: `run-docker-mcp.sh` starts a Docker container in interactive mode
2. **stdio Communication**: The container communicates via stdin/stdout with Claude Code
3. **Automatic Cleanup**: Container is removed when the session ends (`--rm` flag)
4. **Unique Names**: Each session gets a unique container name using PID

## Testing

Test the setup manually:

```bash
cd /home/dingo/code/zen-mcp-server
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | ./run-docker-mcp.sh
```

You should see a JSON response with available tools.

## Troubleshooting

### Container Won't Start
- Check if image exists: `docker images | grep zen-mcp`
- Rebuild if needed: `docker build -t zen-mcp-server:latest .`

### Permission Errors
- Ensure script is executable: `chmod +x run-docker-mcp.sh`
- Check Docker socket permissions

### API Key Issues
- Verify keys in `.env` or MCP settings
- Check logs: `docker logs zen-mcp-[PID]` (while running)

## Comparison: Docker vs Native

| Aspect | Docker | Native Python |
|--------|--------|---------------|
| Isolation | ✅ Full isolation | ❌ Shares system Python |
| Dependencies | ✅ Self-contained | ⚠️ Requires venv setup |
| Portability | ✅ Works anywhere | ⚠️ Platform-specific |
| Performance | ⚠️ Slight overhead | ✅ Direct execution |
| Updates | ✅ Rebuild image | ✅ Git pull + pip install |

## Next Steps

1. Add MCP configuration to Claude Code
2. Restart Claude Code
3. Verify zen tools appear in tool list
4. Test with: "Use zen chat to explain what you do"
