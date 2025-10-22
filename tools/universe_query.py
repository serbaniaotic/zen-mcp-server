"""
Universe Query Tool - QC-083 Phase 3

Provides helper methods for agents to query the OwlSeek Universe:
- Find dependencies for a component
- Find broken/stub implementations
- Trace flows between components
- Generate mermaid diagrams on demand

Part of the Coach Manager system for agent debugging workflows.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.types import TextContent
from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.shared.base_tool import BaseTool
from tools.models import ToolOutput
from tools.mermaid_generator import MermaidGenerator

logger = logging.getLogger(__name__)


class UniverseQueryRequest(ToolRequest):
    """Request model for Universe Query tool"""

    query_type: str = Field(
        ...,
        description="Type of query: 'dependencies', 'broken', 'stubs', 'flow', 'search'"
    )
    component_name: Optional[str] = Field(
        None,
        description="Component name to query (required for 'dependencies' and 'flow')"
    )
    max_depth: int = Field(
        default=3,
        description="Maximum depth for dependency/flow tracing (1-5)"
    )
    universe_path: Optional[str] = Field(
        None,
        description="Optional path to universe JSON (defaults to standard locations)"
    )
    include_mermaid: bool = Field(
        default=True,
        description="Include mermaid diagram in response"
    )


class UniverseQueryTool(BaseTool):
    """
    Query the OwlSeek Universe for debugging and understanding

    Provides pre-built queries for common agent tasks:
    - find_dependencies(component) - Show what a component depends on
    - find_broken() - List all broken/missing connections
    - find_stubs() - List stub implementations
    - trace_flow(component) - Generate flow diagram for component
    """

    def __init__(self):
        super().__init__()
        self.universe_path = None
        self.universe_data = None
        self.mermaid_generator = None

    def get_name(self) -> str:
        """Return tool name for MCP registration"""
        return "universe_query"

    def get_description(self) -> str:
        """Return tool description for MCP clients"""
        return """Query the OwlSeek Universe for debugging and code understanding.

Pre-built queries:
- dependencies: Find what a component depends on
- broken: List all broken/missing connections
- stubs: List stub implementations
- flow: Generate mermaid flow diagram for component
- search: Search for components by name

Helps agents understand codebase structure and identify issues."""

    def get_input_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for tool parameters"""
        return UniverseQueryRequest.model_json_schema()

    def get_system_prompt(self) -> str:
        """Return system prompt for AI model (not used - no LLM)"""
        return ""

    def get_request_model(self):
        """Return Pydantic model for request validation"""
        return UniverseQueryRequest

    async def prepare_prompt(
        self,
        request: UniverseQueryRequest,
        **kwargs
    ) -> str:
        """Not used - this tool doesn't use LLM"""
        return ""

    async def execute_logic(
        self,
        request: UniverseQueryRequest,
        **kwargs
    ) -> ToolOutput:
        """Execute universe query"""
        try:
            # Load universe data
            self._load_universe(request.universe_path)

            if not self.universe_data:
                return ToolOutput(
                    output=[TextContent(
                        type="text",
                        text="❌ Universe data not available. Run universe_generator first."
                    )],
                    metadata={"success": False}
                )

            # Route to appropriate query
            if request.query_type == "dependencies":
                result = self._query_dependencies(request)
            elif request.query_type == "broken":
                result = self._query_broken(request)
            elif request.query_type == "stubs":
                result = self._query_stubs(request)
            elif request.query_type == "flow":
                result = self._query_flow(request)
            elif request.query_type == "search":
                result = self._query_search(request)
            else:
                return ToolOutput(
                    output=[TextContent(
                        type="text",
                        text=f"❌ Unknown query type: {request.query_type}\n\nValid types: dependencies, broken, stubs, flow, search"
                    )],
                    metadata={"success": False}
                )

            return ToolOutput(
                output=[TextContent(type="text", text=result)],
                metadata={"success": True, "query_type": request.query_type}
            )

        except Exception as e:
            logger.error(f"Universe query failed: {e}", exc_info=True)
            return ToolOutput(
                output=[TextContent(
                    type="text",
                    text=f"❌ Query failed: {str(e)}"
                )],
                metadata={"success": False, "error": str(e)}
            )

    def _load_universe(self, custom_path: Optional[str] = None):
        """Load universe JSON data"""
        if custom_path:
            self.universe_path = custom_path
        else:
            # Try common paths
            possible_paths = [
                "/opt/dev/owlseek/universe/owlseek-universe.json",
                "/home/dingo/code/owlseek/universe/owlseek-universe.json",
            ]
            for path in possible_paths:
                if Path(path).exists():
                    self.universe_path = path
                    break

        if not self.universe_path or not Path(self.universe_path).exists():
            logger.warning(f"Universe file not found: {self.universe_path}")
            return

        try:
            with open(self.universe_path, 'r') as f:
                self.universe_data = json.load(f)
            logger.info(f"✅ Loaded universe from {self.universe_path}")

            # Initialize mermaid generator
            self.mermaid_generator = MermaidGenerator(self.universe_path)

        except Exception as e:
            logger.error(f"Failed to load universe: {e}")
            self.universe_data = None

    def _query_dependencies(self, request: UniverseQueryRequest) -> str:
        """Find dependencies for a component"""
        if not request.component_name:
            return "❌ component_name required for dependencies query"

        # Find the entity
        entity = self._find_entity(request.component_name)
        if not entity:
            return f"❌ Component '{request.component_name}' not found in universe"

        # Extract dependencies
        deps = []
        if entity.get("metadata", {}).get("imports"):
            deps.extend(entity["metadata"]["imports"])

        connections = entity.get("connections", [])

        result = [
            f"# Dependencies for {entity['name']['en']}",
            "",
            f"**Type:** {entity['type']} ({entity.get('subtype', 'unknown')})",
            f"**File:** {entity.get('metadata', {}).get('file', 'unknown')}",
            f"**Lines:** {entity.get('metadata', {}).get('lines', 0)}",
            "",
            "## Direct Imports",
            ""
        ]

        if deps:
            for dep in deps:
                result.append(f"- `{dep}`")
        else:
            result.append("- None")

        result.extend(["", "## Connections", ""])

        if connections:
            for conn in connections:
                target = self._find_entity_by_id(conn.get("targetId", ""))
                if target:
                    result.append(f"- {conn.get('type', 'DEPENDS_ON')} → **{target['name']['en']}** ({target.get('subtype', '')})")
        else:
            result.append("- None")

        # Add mermaid diagram
        if request.include_mermaid and self.mermaid_generator:
            result.extend(["", "## Flow Diagram", "", "```mermaid"])
            diagram = self.mermaid_generator.generate_component_flow(
                request.component_name,
                max_depth=request.max_depth
            )
            result.append(diagram)
            result.append("```")

        return "\n".join(result)

    def _query_broken(self, request: UniverseQueryRequest) -> str:
        """Find all broken/missing connections"""
        entities = self.universe_data.get("entities", [])

        broken_items = []

        for entity in entities:
            # Check for broken imports
            resolved_imports = entity.get("metadata", {}).get("resolvedImports", [])
            imports = entity.get("metadata", {}).get("imports", [])

            # Imports that couldn't be resolved
            resolved_paths = {imp.get("import") for imp in resolved_imports}
            for imp in imports:
                if imp not in resolved_paths and not imp.startswith(("react", "lucide-react")):
                    broken_items.append({
                        "component": entity["name"]["en"],
                        "file": entity.get("metadata", {}).get("file", "unknown"),
                        "type": "missing_import",
                        "detail": imp
                    })

        result = [
            "# Broken/Missing Connections",
            "",
            f"**Total broken items:** {len(broken_items)}",
            ""
        ]

        if broken_items:
            result.append("## Issues Found")
            result.append("")
            for item in broken_items:
                result.append(f"### ❌ {item['component']}")
                result.append(f"- **File:** {item['file']}")
                result.append(f"- **Type:** {item['type']}")
                result.append(f"- **Detail:** `{item['detail']}`")
                result.append("")
        else:
            result.append("✅ No broken connections found!")

        return "\n".join(result)

    def _query_stubs(self, request: UniverseQueryRequest) -> str:
        """Find stub implementations"""
        entities = self.universe_data.get("entities", [])

        stubs = []

        for entity in entities:
            # Check for stub markers in metadata
            if entity.get("metadata", {}).get("is_stub"):
                stubs.append(entity)
                continue

            # Check for stub in description
            if "stub" in entity.get("description", {}).get("en", "").lower():
                stubs.append(entity)
                continue

            # Check for minimal line count (likely stub)
            lines = entity.get("metadata", {}).get("lines", 0)
            if lines > 0 and lines < 20 and entity["type"] == "persona":
                stubs.append(entity)

        result = [
            "# Stub Implementations",
            "",
            f"**Total stubs found:** {len(stubs)}",
            ""
        ]

        if stubs:
            result.append("## Stub Components")
            result.append("")
            for stub in stubs:
                result.append(f"### 🚧 {stub['name']['en']}")
                result.append(f"- **Type:** {stub.get('subtype', stub['type'])}")
                result.append(f"- **File:** {stub.get('metadata', {}).get('file', 'unknown')}")
                result.append(f"- **Lines:** {stub.get('metadata', {}).get('lines', 0)}")
                result.append("")
        else:
            result.append("✅ No stubs found!")

        return "\n".join(result)

    def _query_flow(self, request: UniverseQueryRequest) -> str:
        """Generate flow diagram for component"""
        if not request.component_name:
            return "❌ component_name required for flow query"

        if not self.mermaid_generator:
            return "❌ Mermaid generator not available"

        entity = self._find_entity(request.component_name)
        if not entity:
            return f"❌ Component '{request.component_name}' not found"

        result = [
            f"# Flow Diagram: {entity['name']['en']}",
            "",
            f"**Type:** {entity.get('subtype', entity['type'])}",
            f"**File:** {entity.get('metadata', {}).get('file', 'unknown')}",
            "",
            "```mermaid"
        ]

        diagram = self.mermaid_generator.generate_component_flow(
            request.component_name,
            max_depth=request.max_depth,
            include_broken=True
        )
        result.append(diagram)
        result.append("```")

        return "\n".join(result)

    def _query_search(self, request: UniverseQueryRequest) -> str:
        """Search for components by name"""
        if not request.component_name:
            return "❌ component_name required for search query"

        search_term = request.component_name.lower()
        entities = self.universe_data.get("entities", [])

        matches = []
        for entity in entities:
            name = entity["name"]["en"].lower()
            if search_term in name:
                matches.append(entity)

        result = [
            f"# Search Results: '{request.component_name}'",
            "",
            f"**Matches found:** {len(matches)}",
            ""
        ]

        if matches:
            for entity in matches:
                result.append(f"## {entity['name']['en']}")
                result.append(f"- **Type:** {entity.get('subtype', entity['type'])}")
                result.append(f"- **File:** {entity.get('metadata', {}).get('file', 'unknown')}")
                result.append(f"- **Lines:** {entity.get('metadata', {}).get('lines', 0)}")

                # Show description if available
                desc = entity.get("description", {}).get("en", "")
                if desc and desc != f"React component from {entity.get('metadata', {}).get('file', '')}":
                    result.append(f"- **Description:** {desc}")

                result.append("")
        else:
            result.append(f"❌ No components found matching '{request.component_name}'")

        return "\n".join(result)

    def _find_entity(self, name: str) -> Optional[Dict[str, Any]]:
        """Find entity by name (case-insensitive)"""
        search_name = name.lower()
        for entity in self.universe_data.get("entities", []):
            entity_name = entity["name"]["en"].lower()
            if entity_name == search_name or search_name in entity_name:
                return entity
        return None

    def _find_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Find entity by ID"""
        for entity in self.universe_data.get("entities", []):
            if entity["id"] == entity_id:
                return entity
        return None
