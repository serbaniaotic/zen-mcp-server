"""
Context7 Integration Tool for Zen MCP Server

Provides agents with access to Context7 for schema and endpoint discovery.
Context7 specializes in providing up-to-date API documentation, type definitions,
and endpoint schemas from popular libraries and services.
"""

import json
import os
import subprocess
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Context7Tool:
    """
    Tool for querying Context7 MCP server for API schemas and documentation.

    Use cases:
    - Discover API endpoints for a library (e.g., Notion API, Stripe API)
    - Get type definitions and schemas
    - Find function signatures and parameter documentation
    - Look up authentication patterns
    """

    name = "context7"
    description = (
        "Query Context7 MCP for API schemas, endpoints, and documentation. "
        "IMPORTANT: Use this tool FIRST when you need to discover API endpoints, "
        "request/response schemas, type definitions, function signatures, or "
        "authentication patterns for popular libraries and services (Notion, Stripe, "
        "GitHub, OpenAI, React, etc.). Context7 provides real-time schema discovery "
        "without web searching. Combine with 'apilookup' for version-specific changes."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["resolve-library", "search-docs", "get-schema"],
                "description": (
                    "Action to perform: "
                    "'resolve-library' to get library ID from name, "
                    "'search-docs' to search documentation, "
                    "'get-schema' to get API schema"
                ),
            },
            "library_name": {
                "type": "string",
                "description": "Library or service name (e.g., 'notion', 'stripe', 'react')",
            },
            "library_id": {
                "type": "string",
                "description": "Library ID (use resolve-library first if unknown)",
            },
            "query": {
                "type": "string",
                "description": "Search query for documentation or schema lookup",
            },
            "continuation_id": {
                "type": "string",
                "description": "Thread continuation ID for multi-turn conversations",
            },
        },
        "required": ["action"],
    }

    def __init__(self):
        self.context7_url = os.getenv(
            "CONTEXT7_MCP_URL", "http://context7-mcp-server:3001"
        )
        self.container_name = "context7-mcp-server"
        logger.info(f"Context7Tool initialized with URL: {self.context7_url}")

    async def run(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute Context7 query based on action.

        Args:
            arguments: Tool arguments including action, library_name, query, etc.

        Returns:
            List of response content blocks
        """
        action = arguments.get("action")
        logger.info(f"Context7Tool.run called with action: {action}")

        try:
            if action == "resolve-library":
                return await self._resolve_library(arguments)
            elif action == "search-docs":
                return await self._search_docs(arguments)
            elif action == "get-schema":
                return await self._get_schema(arguments)
            else:
                return [
                    {
                        "type": "text",
                        "text": f"Unknown action: {action}. Use 'resolve-library', 'search-docs', or 'get-schema'",
                    }
                ]

        except Exception as e:
            logger.error(f"Error in Context7Tool: {e}", exc_info=True)
            return [
                {
                    "type": "text",
                    "text": f"Error querying Context7: {str(e)}\n\n"
                    f"Make sure context7-mcp-server is running: "
                    f"docker ps | grep context7",
                }
            ]

    async def _resolve_library(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Resolve library name to library ID."""
        library_name = arguments.get("library_name")
        if not library_name:
            return [{"type": "text", "text": "Error: library_name is required"}]

        logger.info(f"Resolving library: {library_name}")

        # Build MCP JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "resolve-library-id",
                "arguments": {"libraryName": library_name},
            },
        }

        result = await self._exec_context7_request(request)
        return [{"type": "text", "text": json.dumps(result, indent=2)}]

    async def _search_docs(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search documentation for a library."""
        library_id = arguments.get("library_id")
        query = arguments.get("query", "")

        if not library_id:
            return [
                {
                    "type": "text",
                    "text": "Error: library_id is required. Use resolve-library action first.",
                }
            ]

        logger.info(f"Searching docs for library: {library_id}, query: {query}")

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search-docs",
                "arguments": {"libraryId": library_id, "query": query},
            },
        }

        result = await self._exec_context7_request(request)
        return [{"type": "text", "text": json.dumps(result, indent=2)}]

    async def _get_schema(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get API schema for a library or endpoint."""
        library_id = arguments.get("library_id")
        query = arguments.get("query", "")

        if not library_id:
            return [
                {
                    "type": "text",
                    "text": "Error: library_id is required. Use resolve-library action first.",
                }
            ]

        logger.info(f"Getting schema for library: {library_id}, query: {query}")

        # Context7 may provide schema through search-docs
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search-docs",
                "arguments": {"libraryId": library_id, "query": f"schema {query}"},
            },
        }

        result = await self._exec_context7_request(request)
        return [{"type": "text", "text": json.dumps(result, indent=2)}]

    async def _exec_context7_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute MCP JSON-RPC request to Context7 via docker exec.

        Args:
            request: JSON-RPC request object

        Returns:
            JSON-RPC response
        """
        request_json = json.dumps(request)

        # Use docker exec to send request to context7-mcp-server
        cmd = [
            "docker",
            "exec",
            "-i",
            self.container_name,
            "context7-mcp",
        ]

        logger.debug(f"Executing: {' '.join(cmd)}")
        logger.debug(f"Request: {request_json}")

        try:
            result = subprocess.run(
                cmd,
                input=request_json.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                error_msg = result.stderr.decode("utf-8")
                logger.error(f"Context7 command failed: {error_msg}")
                return {
                    "error": f"Context7 command failed: {error_msg}",
                    "suggestion": "Check if context7-mcp-server is running: docker ps | grep context7",
                }

            output = result.stdout.decode("utf-8")
            logger.debug(f"Response: {output}")

            try:
                return json.loads(output)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Context7 response: {e}")
                return {"error": f"Invalid JSON response: {output[:200]}"}

        except subprocess.TimeoutExpired:
            logger.error("Context7 request timed out")
            return {"error": "Request timed out after 30 seconds"}
        except Exception as e:
            logger.error(f"Error executing Context7 request: {e}", exc_info=True)
            return {"error": str(e)}


# Export tool instance
context7_tool = Context7Tool()
