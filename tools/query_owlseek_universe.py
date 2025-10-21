"""
Query OwlSeek Universe Tool

Part of QC-081 Phase 3: Agent Query System
Allows AI agents to query the OwlSeek codebase universe for:
- Component flows and dependencies
- API endpoint usage
- MCP tool capabilities
- Code structure and connections

This enables agents to understand the codebase and provide accurate suggestions.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.shared.base_tool import BaseTool
from tools.models import ToolOutput

logger = logging.getLogger(__name__)


class QueryOwlSeekUniverseRequest(ToolRequest):
    """Request model for Query OwlSeek Universe tool"""

    query: str = Field(
        ...,
        description="Natural language query about the codebase (e.g., 'Show voice QC flow', 'Find emotion detection components')"
    )

    query_type: Optional[str] = Field(
        default="semantic",
        description="Query type: 'semantic' (natural language), 'entity' (by ID), 'flow' (trace connections), 'diff' (compare versions)"
    )

    entity_type: Optional[str] = Field(
        default=None,
        description="Filter by entity type: 'persona', 'place', 'object', 'event'"
    )

    domain_filter: Optional[List[str]] = Field(
        default=None,
        description="Filter by domain: ['frontend', 'backend', 'mcp', 'ui', 'api', 'ai-tools']"
    )

    max_results: int = Field(
        default=10,
        description="Maximum number of results to return"
    )

    include_connections: bool = Field(
        default=True,
        description="Include connected entities in results"
    )

    universe_path: Optional[str] = Field(
        default=None,
        description="Optional path to universe JSON (defaults to /opt/dev/owlseek/universe/owlseek-universe.json)"
    )


class QueryOwlSeekUniverseTool(BaseTool):
    """Tool for querying the OwlSeek codebase universe"""

    def get_name(self) -> str:
        return "query_owlseek_universe"

    def get_description(self) -> str:
        return """Query the OwlSeek codebase universe for components, flows, and connections.

Use this tool when you need to:
- Understand code flow: "Show voice QC flow" → traces from UI through API to MCP
- Find components: "Find emotion detection components" → lists all emotion-related entities
- Discover APIs: "List backend endpoints" → shows all API places
- Trace dependencies: "What uses SophiaVoiceChat?" → finds all connections
- Explore MCP tools: "What AI tools are available?" → lists all MCP objects

The universe contains:
- Personas (UI Components): React components with imports and exports
- Places (API Endpoints): Backend routes with HTTP methods
- Objects (MCP Tools): AI tools with capabilities
- Events (Deployments): Version history and changes

Query types:
- semantic: Natural language queries (recommended for exploration)
- entity: Lookup by specific entity ID
- flow: Trace execution flow through connections
- diff: Compare entities across versions (requires events)

Results include entity metadata (file paths, line counts, imports, exports) and can
highlight connections in the Code Graph visualization."""

    def get_input_schema(self) -> Dict[str, Any]:
        return QueryOwlSeekUniverseRequest.model_json_schema()

    def get_system_prompt(self) -> str:
        return """You are a codebase exploration assistant with access to the OwlSeek universe.

When querying the universe:
1. Use natural language for exploration ("Show X flow", "Find Y components")
2. Filter by type and domain to narrow results
3. Include connections to understand relationships
4. Reference file paths and metadata in your explanations

The universe structure:
- Personas = UI components (React)
- Places = API endpoints (Express routes)
- Objects = MCP tools (AI capabilities)
- Events = Deployments (version history)

Always provide:
- Clear explanation of what you found
- Relevant file paths for code navigation
- Connection context (what imports/uses what)
- Suggestions for related entities to explore"""

    def get_request_model(self):
        return QueryOwlSeekUniverseRequest

    def requires_model(self) -> bool:
        """This tool doesn't need AI model access - it's pure data retrieval"""
        return False

    async def prepare_prompt(
        self,
        request,
        files: Optional[List[str]] = None,
        images: Optional[List[str]] = None,
        continuation_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Not used - this tool doesn't use LLM"""
        return ""

    async def execute(self, arguments: Dict[str, Any]) -> ToolOutput:
        """Execute universe query"""
        try:
            # Validate request
            request = QueryOwlSeekUniverseRequest(**arguments)

            # Load universe
            universe_path = request.universe_path or os.getenv(
                "UNIVERSE_PATH",
                "/opt/dev/owlseek/universe/owlseek-universe.json"
            )

            if not os.path.exists(universe_path):
                return ToolOutput(
                    status="error",
                    content=f"Universe not found at {universe_path}. Run universe_generator tool first.",
                    content_type="text"
                )

            with open(universe_path, 'r') as f:
                universe = json.load(f)

            # Execute query based on type
            if request.query_type == "semantic":
                results = self._semantic_query(universe, request)
            elif request.query_type == "entity":
                results = self._entity_query(universe, request)
            elif request.query_type == "flow":
                results = self._flow_query(universe, request)
            elif request.query_type == "diff":
                results = self._diff_query(universe, request)
            else:
                return ToolOutput(
                    status="error",
                    content=f"Unknown query type: {request.query_type}",
                    content_type="text"
                )

            # Format results
            formatted = self._format_results(results, request)

            return ToolOutput(
                status="success",
                content=formatted,
                content_type="markdown",
                metadata={
                    "query": request.query,
                    "query_type": request.query_type,
                    "results_count": len(results.get("entities", [])),
                    "universe_path": universe_path
                }
            )

        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            return ToolOutput(
                status="error",
                content=f"Query failed: {str(e)}",
                content_type="text"
            )

    def _semantic_query(self, universe: Dict, request: QueryOwlSeekUniverseRequest) -> Dict:
        """Natural language semantic search"""
        query_lower = request.query.lower()
        entities = universe.get("entities", [])
        matches = []

        for entity in entities:
            # Check entity type filter
            if request.entity_type and entity["type"] != request.entity_type:
                continue

            # Check domain filter
            if request.domain_filter:
                entity_domains = entity.get("domain", [])
                if not any(d in entity_domains for d in request.domain_filter):
                    continue

            # Semantic matching (simple keyword-based for now)
            score = 0
            text_fields = [
                entity["name"]["en"].lower(),
                entity["description"]["en"].lower(),
                entity["id"].lower(),
                entity.get("subtype", "").lower()
            ]

            # Add metadata text
            if entity.get("metadata"):
                metadata = entity["metadata"]
                if metadata.get("file"):
                    text_fields.append(metadata["file"].lower())
                if metadata.get("componentName"):
                    text_fields.append(metadata["componentName"].lower())
                if metadata.get("endpoint"):
                    text_fields.append(metadata["endpoint"].lower())

            # Score by keyword matches
            for field in text_fields:
                for word in query_lower.split():
                    if word in field:
                        score += 1

            if score > 0:
                matches.append({"entity": entity, "score": score})

        # Sort by score and limit
        matches.sort(key=lambda x: x["score"], reverse=True)
        top_matches = matches[:request.max_results]

        # Build result entities
        result_entities = []
        for match in top_matches:
            entity = match["entity"]
            result_entity = entity.copy()

            # Add connections if requested
            if request.include_connections:
                connected_ids = [c["targetId"] for c in entity.get("connections", [])]
                connected_entities = [
                    e for e in entities if e["id"] in connected_ids
                ]
                result_entity["connected_entities"] = connected_entities[:5]  # Limit connections

            result_entities.append(result_entity)

        return {
            "entities": result_entities,
            "total_matches": len(matches),
            "query": request.query
        }

    def _entity_query(self, universe: Dict, request: QueryOwlSeekUniverseRequest) -> Dict:
        """Lookup by entity ID"""
        entities = universe.get("entities", [])
        entity = next((e for e in entities if e["id"] == request.query), None)

        if not entity:
            return {"entities": [], "total_matches": 0, "query": request.query}

        # Add connections
        if request.include_connections:
            connected_ids = [c["targetId"] for c in entity.get("connections", [])]
            connected_entities = [
                e for e in entities if e["id"] in connected_ids
            ]
            entity["connected_entities"] = connected_entities

        return {
            "entities": [entity],
            "total_matches": 1,
            "query": request.query
        }

    def _flow_query(self, universe: Dict, request: QueryOwlSeekUniverseRequest) -> Dict:
        """Trace flow through connections"""
        # Start with semantic search to find entry point
        initial_results = self._semantic_query(universe, request)

        if not initial_results["entities"]:
            return initial_results

        # Trace connections from first match
        start_entity = initial_results["entities"][0]
        entities = universe.get("entities", [])

        # BFS to trace flow
        visited = set()
        queue = [start_entity["id"]]
        flow_entities = []

        while queue and len(flow_entities) < request.max_results:
            entity_id = queue.pop(0)
            if entity_id in visited:
                continue

            visited.add(entity_id)
            entity = next((e for e in entities if e["id"] == entity_id), None)

            if entity:
                flow_entities.append(entity)
                # Add connected entities to queue
                for conn in entity.get("connections", []):
                    if conn["targetId"] not in visited:
                        queue.append(conn["targetId"])

        return {
            "entities": flow_entities,
            "total_matches": len(flow_entities),
            "query": request.query,
            "flow_type": "breadth_first_search"
        }

    def _diff_query(self, universe: Dict, request: QueryOwlSeekUniverseRequest) -> Dict:
        """Compare entities across versions (placeholder for Phase 4)"""
        return {
            "entities": [],
            "total_matches": 0,
            "query": request.query,
            "error": "Version comparison requires event entities (Phase 4)"
        }

    def _format_results(self, results: Dict, request: QueryOwlSeekUniverseRequest) -> str:
        """Format query results as markdown"""
        entities = results.get("entities", [])
        total = results.get("total_matches", 0)

        if not entities:
            return f"# Query Results\n\n**Query:** {request.query}\n\n**No results found.**\n\nTry:\n- Using different keywords\n- Removing filters\n- Querying by entity type (persona/place/object)"

        lines = [
            f"# Query Results: {request.query}",
            f"",
            f"**Found:** {len(entities)} of {total} matches",
            f"**Query Type:** {request.query_type}",
            f""
        ]

        for i, entity in enumerate(entities, 1):
            entity_type = entity["type"]
            name = entity["name"]["en"]
            desc = entity["description"]["en"]
            metadata = entity.get("metadata", {})

            lines.append(f"## {i}. {name}")
            lines.append(f"**Type:** {entity_type.title()} ({entity.get('subtype', 'N/A')})")
            lines.append(f"**ID:** `{entity['id']}`")
            lines.append(f"**Description:** {desc}")

            # Add type-specific metadata
            if entity_type == "persona" and metadata.get("file"):
                lines.append(f"**File:** `{metadata['file']}`")
                lines.append(f"**Lines:** {metadata.get('lines', 'N/A')}")
                if metadata.get("imports"):
                    lines.append(f"**Imports:** {len(metadata['imports'])} modules")

            elif entity_type == "place" and metadata.get("endpoint"):
                method = metadata.get("method", "?")
                lines.append(f"**Endpoint:** `{method} {metadata['endpoint']}`")
                lines.append(f"**File:** `{metadata.get('file', 'N/A')}`")

            elif entity_type == "object" and metadata.get("toolClass"):
                lines.append(f"**Tool Class:** `{metadata['toolClass']}`")
                capabilities = metadata.get("capabilities", [])
                if capabilities:
                    lines.append(f"**Capabilities:** {', '.join(capabilities)}")

            # Add connections
            if request.include_connections:
                connections = entity.get("connections", [])
                connected_entities = entity.get("connected_entities", [])

                if connected_entities:
                    lines.append(f"**Connected To:**")
                    for conn_entity in connected_entities[:3]:  # Show top 3
                        lines.append(f"  - {conn_entity['name']['en']} ({conn_entity['type']})")
                    if len(connected_entities) > 3:
                        lines.append(f"  - ... and {len(connected_entities) - 3} more")

            lines.append("")

        return "\n".join(lines)
