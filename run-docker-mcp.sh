#!/bin/bash
# Wrapper script to run zen-mcp-server via Docker for MCP clients
# Usage: This script should be configured in Claude Code's MCP settings

set -euo pipefail

# Load environment variables from .env if it exists
if [ -f "$(dirname "$0")/.env" ]; then
    export $(grep -v '^#' "$(dirname "$0")/.env" | xargs)
fi

# Run the container interactively with stdio
exec docker run --rm -i \
    --name "zen-mcp-$$" \
    -e GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
    -e GOOGLE_API_KEY="${GOOGLE_API_KEY:-}" \
    -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
    -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
    -e XAI_API_KEY="${XAI_API_KEY:-}" \
    -e OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}" \
    -e DEFAULT_MODEL="${DEFAULT_MODEL:-auto}" \
    -e LOG_LEVEL="${LOG_LEVEL:-INFO}" \
    -e DEFAULT_THINKING_MODE_THINKDEEP="${DEFAULT_THINKING_MODE_THINKDEEP:-high}" \
    -e DISABLED_TOOLS="${DISABLED_TOOLS:-}" \
    zen-mcp-server:latest
