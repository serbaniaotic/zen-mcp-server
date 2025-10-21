"""
Universe Generator Tool - Scan codebase and generate Weaver universe

This tool scans a software project and generates a Weaver-compatible universe
where code elements (components, APIs, tools) become entities with connections.

Design: QC-081 (owlseek-meta-universe-catascape-onboarding.md)
Purpose: Enable OwlSeek to document itself as a queryable knowledge graph

Key Concepts:
- React Components → Persona entities (UI with "behavior")
- API Endpoints → Place entities (locations you visit)
- MCP Tools → Object entities (things you use)
- Deployments → Event entities (moments in time)
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.shared.base_tool import BaseTool
from tools.models import ToolOutput
from mcp.types import TextContent

logger = logging.getLogger(__name__)


class UniverseGeneratorRequest(ToolRequest):
    """Request model for Universe Generator tool"""

    project_path: str = Field(
        ...,
        description="Absolute path to project root (e.g., /home/dingo/code/owlseek)"
    )
    output_path: Optional[str] = Field(
        None,
        description="Where to save universe JSON (default: {project_path}/universe/owlseek-universe.json)"
    )
    include_events: bool = Field(
        default=False,
        description="Include deployment events from changelogs (requires changelogs/*.json)"
    )


class UniverseGeneratorTool(BaseTool):
    """
    Generate Weaver universe from codebase

    Scans a project directory and creates a universe JSON with:
    - Entities (components, APIs, tools, deployments)
    - Connections (imports, API calls, tool invocations)
    - Metadata (file paths, line counts, etc.)
    """

    def __init__(self):
        super().__init__()
        self.entities = []
        self.connections = []
        self.entity_id_map = {}  # name → id mapping

    def get_name(self) -> str:
        """Return tool name for MCP registration"""
        return "universe_generator"

    def get_description(self) -> str:
        """Return tool description for MCP clients"""
        return """Generate Weaver universe from codebase (QC-081 implementation).

Scans a software project and creates a universe JSON with:
- React Components → Persona entities (UI with behavior)
- API Endpoints → Place entities (service locations)
- MCP Tools → Object entities (AI tools)
- Deployments → Event entities (moments in time)

This enables OwlSeek to document itself as a queryable knowledge graph
where code elements become entities with connections."""

    def get_input_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for tool parameters"""
        return UniverseGeneratorRequest.model_json_schema()

    def get_system_prompt(self) -> str:
        """Return system prompt for AI model (not used - this tool doesn't use LLM)"""
        return ""

    def get_request_model(self):
        """Return Pydantic model for request validation"""
        return UniverseGeneratorRequest

    async def prepare_prompt(self, request) -> str:
        """Prepare prompt for AI model (not used - this tool doesn't use LLM)"""
        return ""

    async def execute(self, arguments: Dict[str, Any]) -> ToolOutput:
        """Execute universe generation"""
        try:
            request = UniverseGeneratorRequest(**arguments)

            project_path = Path(request.project_path)
            if not project_path.exists():
                return ToolOutput(
                    content=[TextContent(
                        type="text",
                        text=f"Error: Project path does not exist: {request.project_path}"
                    )],
                    isError=True
                )

            # Generate universe
            logger.info(f"Generating universe for: {project_path}")
            universe = await self.generate_owlseek_universe(
                project_path=str(project_path),
                include_events=request.include_events
            )

            # Save to file
            output_path = request.output_path or str(project_path / "universe" / "owlseek-universe.json")
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(universe, f, indent=2, ensure_ascii=False)

            # Create summary
            stats = universe['statistics']
            summary = f"""✅ Universe Generated Successfully!

**Output:** {output_file}

**Statistics:**
- Total Entities: {stats['totalEntities']}
- Personas (UI Components): {stats['personas']}
- Places (API Endpoints): {stats['places']}
- Objects (MCP Tools): {stats['objects']}
- Events (Deployments): {stats['events']}
- Connections: {stats['connections']}

**Next Steps:**
1. View universe: `cat {output_file} | jq '.statistics'`
2. Load in Catascape (Phase 2)
3. Query via agent (Phase 3)

**QC Reference:** QC-081 Part 2 - Universe Generation
"""

            return ToolOutput(
                content=[TextContent(type="text", text=summary)]
            )

        except Exception as e:
            logger.error(f"Universe generation failed: {e}", exc_info=True)
            return ToolOutput(
                content=[TextContent(
                    type="text",
                    text=f"Error generating universe: {str(e)}"
                )],
                isError=True
            )

    async def generate_owlseek_universe(
        self,
        project_path: str,
        include_events: bool = False
    ) -> Dict[str, Any]:
        """
        Main universe generation logic

        Returns universe JSON with entities, connections, timeline
        """
        project = Path(project_path)

        # Reset state
        self.entities = []
        self.connections = []
        self.entity_id_map = {}

        logger.info("Scanning React components...")
        personas = await self._scan_react_components(project / "ui" / "src" / "components")
        self.entities.extend(personas)

        logger.info("Scanning API routes...")
        places = await self._scan_api_routes(project / "backend" / "src" / "api")
        self.entities.extend(places)

        logger.info("Scanning MCP tools...")
        objects = await self._scan_mcp_tools(project.parent / "zen-mcp-server" / "tools")
        self.entities.extend(objects)

        # Build entity ID map for connection resolution
        for entity in self.entities:
            self.entity_id_map[entity['name']['en']] = entity['id']

        logger.info("Detecting connections...")
        await self._detect_connections(project)

        # Optional: Parse deployment events
        events = []
        if include_events:
            logger.info("Parsing deployment changelogs...")
            events = await self._parse_changelogs(project / "changelogs")
            self.entities.extend(events)

        # Build final universe JSON
        universe = {
            "universeId": "owlseek-codebase",
            "generatedAt": datetime.now().isoformat(),
            "entities": self.entities,
            "timeline": {
                "id": "owlseek-timeline",
                "name": "OwlSeek Development Timeline",
                "startDate": "2024-09-01",
                "endDate": datetime.now().strftime("%Y-%m-%d"),
                "events": [e['id'] for e in events]
            },
            "statistics": {
                "totalEntities": len(self.entities),
                "personas": len(personas),
                "places": len(places),
                "objects": len(objects),
                "events": len(events),
                "connections": len(self.connections)
            }
        }

        return universe

    async def _scan_react_components(self, components_dir: Path) -> List[Dict]:
        """
        Scan UI components and create persona entities

        Returns list of persona entities for React components
        """
        personas = []

        if not components_dir.exists():
            logger.warning(f"Components directory not found: {components_dir}")
            return personas

        # Find all .tsx files
        tsx_files = list(components_dir.rglob("*.tsx"))
        logger.info(f"Found {len(tsx_files)} React components")

        for tsx_file in tsx_files:
            try:
                # Read file content
                with open(tsx_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract component name from filename
                component_name = tsx_file.stem

                # Skip if test file
                if 'test' in component_name.lower() or '__tests__' in str(tsx_file):
                    continue

                # Extract exports
                exports = self._extract_exports(content)

                # Extract imports (for connections later)
                imports = self._extract_imports(content)

                # Count lines
                line_count = len(content.splitlines())

                # Create entity
                entity_id = f"owlseek-{component_name.lower()}"

                entity = {
                    "id": entity_id,
                    "type": "persona",
                    "name": {
                        "en": component_name,
                        "vi": component_name
                    },
                    "description": {
                        "en": f"React component from {tsx_file.relative_to(tsx_file.parents[3])}",
                        "vi": ""
                    },
                    "connections": [],  # Will be populated in _detect_connections
                    "domain": ["frontend", "ui"],
                    "subtype": "React Component",
                    "timelineId": "owlseek-codebase",
                    "metadata": {
                        "file": str(tsx_file.relative_to(tsx_file.parents[3])),
                        "lines": line_count,
                        "exports": exports,
                        "imports": imports
                    }
                }

                personas.append(entity)

            except Exception as e:
                logger.warning(f"Error processing {tsx_file}: {e}")
                continue

        return personas

    async def _scan_api_routes(self, api_dir: Path) -> List[Dict]:
        """
        Scan backend API routes and create place entities

        Returns list of place entities for API endpoints
        """
        places = []

        if not api_dir.exists():
            logger.warning(f"API directory not found: {api_dir}")
            return places

        # Find all *-routes.ts files
        route_files = list(api_dir.glob("*-routes.ts"))
        logger.info(f"Found {len(route_files)} API route files")

        for route_file in route_files:
            try:
                with open(route_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract route definitions
                routes = self._extract_routes(content)

                for route in routes:
                    method = route['method']
                    path = route['path']

                    # Create entity ID from path
                    # e.g., POST /api/voice/emotion → owlseek-api-voice-emotion
                    path_slug = path.replace('/api/', '').replace('/', '-').replace(':', '')
                    entity_id = f"owlseek-api-{path_slug}"

                    entity = {
                        "id": entity_id,
                        "type": "place",
                        "name": {
                            "en": f"{method} {path}",
                            "vi": f"{method} {path}"
                        },
                        "description": {
                            "en": f"API endpoint from {route_file.name}",
                            "vi": ""
                        },
                        "connections": [],
                        "domain": ["backend", "api"],
                        "subtype": method,
                        "timelineId": "owlseek-codebase",
                        "metadata": {
                            "endpoint": path,
                            "method": method,
                            "file": str(route_file.relative_to(route_file.parents[3]))
                        }
                    }

                    places.append(entity)

            except Exception as e:
                logger.warning(f"Error processing {route_file}: {e}")
                continue

        return places

    async def _scan_mcp_tools(self, tools_dir: Path) -> List[Dict]:
        """
        Scan zen-mcp tools and create object entities

        Returns list of object entities for MCP tools
        """
        objects = []

        if not tools_dir.exists():
            logger.warning(f"Tools directory not found: {tools_dir}")
            return objects

        # Find all tool .py files
        tool_files = [
            f for f in tools_dir.glob("*.py")
            if not f.name.startswith('_') and f.name not in ['models.py', 'usage_tracker.py']
        ]
        logger.info(f"Found {len(tool_files)} MCP tool files")

        for tool_file in tool_files:
            try:
                with open(tool_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract tool class name
                tool_class_match = re.search(r'class\s+(\w+Tool)\(', content)
                if not tool_class_match:
                    continue

                tool_name = tool_class_match.group(1)

                # Extract capabilities from docstring
                capabilities = self._extract_capabilities(content)

                entity_id = f"owlseek-tool-{tool_name.lower().replace('tool', '')}"

                entity = {
                    "id": entity_id,
                    "type": "object",
                    "name": {
                        "en": tool_name,
                        "vi": tool_name
                    },
                    "description": {
                        "en": f"Zen-MCP tool from {tool_file.name}",
                        "vi": ""
                    },
                    "connections": [],
                    "domain": ["mcp", "ai-tools"],
                    "subtype": "MCP Tool",
                    "timelineId": "owlseek-codebase",
                    "metadata": {
                        "file": str(tool_file.relative_to(tool_file.parents[1])),
                        "capabilities": capabilities
                    }
                }

                objects.append(entity)

            except Exception as e:
                logger.warning(f"Error processing {tool_file}: {e}")
                continue

        return objects

    async def _parse_changelogs(self, changelogs_dir: Path) -> List[Dict]:
        """
        Parse deployment changelogs and create event entities

        Returns list of event entities for deployments
        """
        events = []

        if not changelogs_dir.exists():
            logger.info("No changelogs directory found, skipping events")
            return events

        # Find all changelog JSON files
        changelog_files = list(changelogs_dir.glob("*.json"))
        logger.info(f"Found {len(changelog_files)} changelog files")

        for changelog_file in changelog_files:
            try:
                with open(changelog_file, 'r', encoding='utf-8') as f:
                    changelog = json.load(f)

                version = changelog.get('version', changelog_file.stem)

                entity_id = f"owlseek-deploy-{version}"

                entity = {
                    "id": entity_id,
                    "type": "event",
                    "name": {
                        "en": f"Deployment {version}",
                        "vi": f"Triển khai {version}"
                    },
                    "description": {
                        "en": changelog.get('summary', f"Deployment on {version}"),
                        "vi": ""
                    },
                    "connections": [],
                    "domain": ["deployment", "ci-cd"],
                    "subtype": "CalVer Release",
                    "timelineId": "owlseek-timeline",
                    "metadata": {
                        "version": version,
                        "git_sha": changelog.get('git_sha', 'unknown'),
                        "breaking_changes": len(changelog.get('breaking_changes', [])),
                        "new_features": len(changelog.get('new_features', [])),
                        "bug_fixes": len(changelog.get('bug_fixes', [])),
                        "known_issues": len(changelog.get('known_issues', [])),
                        "changelog_url": f"/changelogs/{version}.md"
                    }
                }

                events.append(entity)

            except Exception as e:
                logger.warning(f"Error processing {changelog_file}: {e}")
                continue

        return events

    async def _detect_connections(self, project_path: Path):
        """
        Detect connections between entities

        Updates entity['connections'] arrays in-place
        """
        # For each persona (component), find API calls and imports
        for entity in self.entities:
            if entity['type'] == 'persona':
                await self._detect_persona_connections(entity, project_path)
            elif entity['type'] == 'place':
                await self._detect_place_connections(entity, project_path)

    async def _detect_persona_connections(self, entity: Dict, project_path: Path):
        """Detect connections for persona (UI component)"""
        try:
            file_path = project_path / entity['metadata']['file']
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find API calls
            api_calls = self._find_api_calls(content)
            for api_path in api_calls:
                # Try to find matching place entity
                path_slug = api_path.replace('/api/', '').replace('/', '-').replace(':', '')
                target_id = f"owlseek-api-{path_slug}"

                if any(e['id'] == target_id for e in self.entities):
                    entity['connections'].append({
                        "targetId": target_id,
                        "strength": 0.9,
                        "label": "calls"
                    })
                    self.connections.append({
                        "source": entity['id'],
                        "target": target_id,
                        "type": "calls"
                    })

        except Exception as e:
            logger.debug(f"Error detecting connections for {entity['id']}: {e}")

    async def _detect_place_connections(self, entity: Dict, project_path: Path):
        """Detect connections for place (API endpoint)"""
        try:
            file_path = project_path / entity['metadata']['file']
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find MCP tool calls
            tool_calls = self._find_tool_calls(content)
            for tool_name in tool_calls:
                # Try to find matching object entity
                target_id = f"owlseek-tool-{tool_name.lower().replace('tool', '')}"

                if any(e['id'] == target_id for e in self.entities):
                    entity['connections'].append({
                        "targetId": target_id,
                        "strength": 1.0,
                        "label": "uses"
                    })
                    self.connections.append({
                        "source": entity['id'],
                        "target": target_id,
                        "type": "uses"
                    })

        except Exception as e:
            logger.debug(f"Error detecting connections for {entity['id']}: {e}")

    # Helper methods for parsing

    def _extract_exports(self, content: str) -> List[str]:
        """Extract export names from file content"""
        exports = []

        # Match: export function X, export const X, export default X
        patterns = [
            r'export\s+(?:default\s+)?function\s+(\w+)',
            r'export\s+(?:const|let|var)\s+(\w+)',
            r'export\s+default\s+(\w+)',
            r'export\s*\{([^}]+)\}'
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if '{' in match.group(0):
                    # Handle: export { A, B, C }
                    exports.extend([e.strip() for e in match.group(1).split(',')])
                else:
                    exports.append(match.group(1))

        return list(set(exports))  # Deduplicate

    def _extract_imports(self, content: str) -> List[str]:
        """Extract import paths from file content"""
        imports = []

        # Match: import X from 'Y'
        pattern = r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'
        matches = re.finditer(pattern, content)

        for match in matches:
            imports.append(match.group(1))

        return imports

    def _extract_routes(self, content: str) -> List[Dict]:
        """Extract API route definitions from route file"""
        routes = []

        # Match: router.get('/api/...', ...) or router.post('/api/...', ...)
        pattern = r'router\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]'
        matches = re.finditer(pattern, content)

        for match in matches:
            method = match.group(1).upper()
            path = match.group(2)

            routes.append({
                "method": method,
                "path": path
            })

        return routes

    def _extract_capabilities(self, content: str) -> List[str]:
        """Extract tool capabilities from docstring or comments"""
        capabilities = []

        # Simple heuristic: look for common capability keywords
        keywords = [
            'analyze', 'code review', 'debug', 'test', 'chat', 'think',
            'plan', 'refactor', 'documentation', 'emotion', 'voice',
            'tts', 'whisper', 'acoustic'
        ]

        content_lower = content.lower()
        for keyword in keywords:
            if keyword in content_lower:
                capabilities.append(keyword)

        return capabilities[:5]  # Limit to 5

    def _find_api_calls(self, content: str) -> List[str]:
        """Find API calls in component code"""
        api_calls = []

        # Match: fetch('/api/...') or axios.get('/api/...')
        patterns = [
            r'fetch\([\'"]([^\'"]+)[\'"]',
            r'axios\.\w+\([\'"]([^\'"]+)[\'"]'
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                path = match.group(1)
                if path.startswith('/api/'):
                    api_calls.append(path)

        return api_calls

    def _find_tool_calls(self, content: str) -> List[str]:
        """Find MCP tool invocations in backend code"""
        tool_calls = []

        # Match: callTool('XxxTool') or /tools/call with "name": "xxx"
        patterns = [
            r'callTool\([\'"](\w+Tool)[\'"]',
            r'"name":\s*[\'"](\w+)[\'"]'
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                tool_name = match.group(1)
                if tool_name.endswith('Tool') or 'tool' in tool_name.lower():
                    tool_calls.append(tool_name)

        return tool_calls
