"""
New Relic MCP Tool

This tool provides integration with New Relic APIs to query server metrics,
application performance data, and infrastructure monitoring information.

Key Features:
- Query server performance metrics (CPU, memory, disk, network)
- Retrieve application performance data
- Get infrastructure monitoring information
- Execute NRQL queries for custom data analysis
- Support for both GraphQL and REST API endpoints

The tool is designed to help with service issue diagnosis and performance analysis,
particularly useful for the ReadQueen POS environment described in ticket 002.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from mcp.types import TextContent

from .shared.base_tool import BaseTool
from .shared.base_models import ToolRequest
from .models import ToolModelCategory, ToolOutput

logger = logging.getLogger(__name__)


class NewRelicTool(BaseTool):
    """New Relic API integration tool for server monitoring and metrics querying."""

    def get_name(self) -> str:
        return "newrelic"

    def get_description(self) -> str:
        return "Query New Relic APIs for server metrics, application performance, and infrastructure monitoring data"

    def get_input_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the tool's input"""
        return {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["nrql", "graphql", "rest", "server_metrics", "app_performance"],
                    "description": "Type of query to execute"
                },
                "query": {
                    "type": "string",
                    "description": "The query to execute (NRQL, GraphQL, or REST endpoint)"
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range for the query (e.g., '1 hour', '24 hours', '7 days')",
                    "default": "1 hour"
                },
                "hostname": {
                    "type": "string",
                    "description": "Specific hostname to filter results (optional)"
                },
                "application_name": {
                    "type": "string",
                    "description": "Application name to filter results (optional)"
                }
            },
            "required": ["query_type", "query"]
        }

    def get_request_model(self):
        """Return the Pydantic model for request validation."""
        return ToolRequest

    def get_system_prompt(self) -> str:
        """No AI model needed for this tool - it directly queries APIs."""
        return ""

    def requires_model(self) -> bool:
        """This tool doesn't require an AI model - it directly queries APIs."""
        return False

    def get_model_category(self):
        """Not applicable for this tool."""
        return ToolModelCategory.ANALYTICAL

    async def prepare_prompt(self, request: ToolRequest) -> str:
        """Not used for this utility tool"""
        return ""

    def format_response(self, response: str, request: ToolRequest, model_info: dict = None) -> str:
        """Format the response for display."""
        return response

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Execute New Relic API queries based on the provided arguments.

        Args:
            arguments: Dictionary containing:
                - query_type: Type of query (nrql, graphql, rest, server_metrics, app_performance)
                - query: The actual query to execute
                - time_range: Time range for the query (optional)
                - hostname: Hostname filter (optional)
                - application_name: Application name filter (optional)

        Returns:
            List of TextContent objects with query results
        """
        try:
            query_type = arguments.get("query_type")
            query = arguments.get("query")
            time_range = arguments.get("time_range", "1 hour")
            hostname = arguments.get("hostname")
            application_name = arguments.get("application_name")

            if not query_type or not query:
                return [TextContent(
                    type="text",
                    text=ToolOutput(
                        status="error",
                        content="Both 'query_type' and 'query' are required parameters",
                        content_type="text"
                    ).model_dump_json()
                )]

            # Get API credentials from environment
            api_key = self._get_api_key()
            account_id = self._get_account_id()

            if not api_key or not account_id:
                return [TextContent(
                    type="text",
                    text=ToolOutput(
                        status="error",
                        content="New Relic API key and account ID must be configured in environment variables",
                        content_type="text"
                    ).model_dump_json()
                )]

            # Execute the appropriate query type
            if query_type == "nrql":
                result = await self._execute_nrql_query(api_key, account_id, query, time_range)
            elif query_type == "graphql":
                result = await self._execute_graphql_query(api_key, query)
            elif query_type == "rest":
                result = await self._execute_rest_query(api_key, query)
            elif query_type == "server_metrics":
                result = await self._get_server_metrics(api_key, account_id, time_range, hostname)
            elif query_type == "app_performance":
                result = await self._get_app_performance(api_key, account_id, time_range, application_name)
            else:
                return [TextContent(
                    type="text",
                    text=ToolOutput(
                        status="error",
                        content=f"Unknown query type: {query_type}",
                        content_type="text"
                    ).model_dump_json()
                )]

            return [TextContent(
                type="text",
                text=ToolOutput(
                    status="success",
                    content=result,
                    content_type="json",
                    metadata={
                        "query_type": query_type,
                        "time_range": time_range,
                        "hostname": hostname,
                        "application_name": application_name
                    }
                ).model_dump_json()
            )]

        except Exception as e:
            logger.error(f"New Relic query execution failed: {e}")
            return [TextContent(
                type="text",
                text=ToolOutput(
                    status="error",
                    content=f"New Relic query execution failed: {str(e)}",
                    content_type="text"
                ).model_dump_json()
            )]

    def _get_api_key(self) -> Optional[str]:
        """Get New Relic API key from environment variables."""
        import os
        return os.getenv("NEW_RELIC_API_KEY") or os.getenv("NEWRELIC_API_KEY")

    def _get_account_id(self) -> Optional[str]:
        """Get New Relic account ID from environment variables."""
        import os
        return os.getenv("NEW_RELIC_ACCOUNT_ID") or os.getenv("NEWRELIC_ACCOUNT_ID")

    async def _execute_nrql_query(self, api_key: str, account_id: str, query: str, time_range: str) -> str:
        """Execute an NRQL query against New Relic's GraphQL API."""
        # Use New Relic's GraphQL API (NerdGraph) for NRQL queries
        url = "https://api.newrelic.com/graphql"

        headers = {
            "Api-Key": api_key,
            "Content-Type": "application/json"
        }

        # Convert time range to NRQL format
        nrql_time_range = self._convert_time_range(time_range)
        full_query = f"{query} {nrql_time_range}"

        # GraphQL query for NRQL
        graphql_query = """
        query($accountId: Int!, $nrql: Nrql!) {
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
        """

        payload = {
            "query": graphql_query,
            "variables": {
                "accountId": int(account_id),
                "nrql": full_query
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)

    async def _execute_graphql_query(self, api_key: str, query: str) -> str:
        """Execute a GraphQL query against New Relic's API."""
        url = "https://api.newrelic.com/graphql"
        
        headers = {
            "API-Key": api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "query": query
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)

    async def _execute_rest_query(self, api_key: str, endpoint: str) -> str:
        """Execute a REST API query against New Relic's API."""
        # Ensure the endpoint starts with the base URL if it's a relative path
        if not endpoint.startswith("http"):
            endpoint = f"https://api.newrelic.com/v2/{endpoint.lstrip('/')}"
        
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(endpoint, headers=headers)
            response.raise_for_status()
            return json.dumps(response.json(), indent=2)

    async def _get_server_metrics(self, api_key: str, account_id: str, time_range: str, hostname: Optional[str] = None) -> str:
        """Get server performance metrics."""
        # Build NRQL query for server metrics
        base_query = """
        SELECT average(cpuPercent), average(memoryUsedBytes), average(diskUsedPercent), 
               average(networkInBytes), average(networkOutBytes)
        FROM SystemSample
        """
        
        if hostname:
            base_query += f" WHERE hostname = '{hostname}'"
        
        return await self._execute_nrql_query(api_key, account_id, base_query, time_range)

    async def _get_app_performance(self, api_key: str, account_id: str, time_range: str, application_name: Optional[str] = None) -> str:
        """Get application performance metrics."""
        # Build NRQL query for application performance
        base_query = """
        SELECT average(responseTime), average(throughput), average(errorRate)
        FROM Transaction
        """
        
        if application_name:
            base_query += f" WHERE appName = '{application_name}'"
        
        return await self._execute_nrql_query(api_key, account_id, base_query, time_range)

    def _convert_time_range(self, time_range: str) -> str:
        """Convert human-readable time range to NRQL format."""
        time_range = time_range.lower().strip()
        
        if "hour" in time_range:
            if "1" in time_range:
                return "SINCE 1 hour ago"
            elif "24" in time_range:
                return "SINCE 24 hours ago"
            else:
                return "SINCE 1 hour ago"
        elif "day" in time_range:
            if "1" in time_range:
                return "SINCE 1 day ago"
            elif "7" in time_range:
                return "SINCE 7 days ago"
            elif "30" in time_range:
                return "SINCE 30 days ago"
            else:
                return "SINCE 1 day ago"
        elif "week" in time_range:
            return "SINCE 1 week ago"
        elif "month" in time_range:
            return "SINCE 1 month ago"
        else:
            return "SINCE 1 hour ago"

    def get_annotations(self) -> Dict[str, Any]:
        """Return tool annotations for MCP."""
        return {
            "category": "monitoring",
            "provider": "newrelic",
            "capabilities": [
                "server_metrics",
                "application_performance",
                "infrastructure_monitoring",
                "custom_nrql_queries",
                "graphql_queries",
                "rest_api_access"
            ]
        }