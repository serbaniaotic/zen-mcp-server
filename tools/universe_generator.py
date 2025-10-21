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
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.types import TextContent
from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.shared.base_tool import BaseTool
from tools.models import ToolOutput

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
        self.entities: List[Dict[str, Any]] = []
        self.connections: List[Dict[str, Any]] = []
        self.entity_lookup: Dict[str, Dict[str, Any]] = {}
        self.entity_alias_map: Dict[str, str] = {}
        self.file_lookup: Dict[str, str] = {}
        self.api_path_index: Dict[str, str] = {}

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

    async def prepare_prompt(
        self,
        request,
        files: Optional[list[str]] = None,
        images: Optional[list[str]] = None,
        continuation_id: Optional[str] = None,
        **kwargs
    ) -> str:
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
                status="success",
                content=summary,
                content_type="markdown",
                metadata={
                    "output_path": str(output_file),
                    "statistics": stats,
                },
            )

        except Exception as e:
            logger.error(f"Universe generation failed: {e}", exc_info=True)
            return ToolOutput(
                status="error",
                content=f"Error generating universe: {str(e)}",
                content_type="text",
                metadata={"exception": repr(e)},
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
        self.entity_lookup = {}
        self.entity_alias_map = {}
        self.file_lookup = {}
        self.api_path_index = {}

        logger.info("Scanning React components...")
        personas = await self._scan_react_components(project / "ui" / "src" / "components")
        self.entities.extend(personas)

        logger.info("Scanning API routes...")
        places = await self._scan_api_routes(project / "backend" / "src" / "api")
        self.entities.extend(places)

        logger.info("Scanning MCP tools...")
        objects = await self._scan_mcp_tools(project.parent / "zen-mcp-server" / "tools")
        self.entities.extend(objects)

        # Build lookup tables for connection resolution
        self._build_entity_indexes()

        logger.info("Detecting connections...")
        await self._detect_connections(project)
        self._link_deployment_connections()

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

                # Extract metadata
                component_name = tsx_file.stem
                relative_path = tsx_file.relative_to(tsx_file.parents[3])
                stat = tsx_file.stat()
                last_modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
                description_text = self._extract_jsdoc_description(content)

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
                        "en": description_text or f"React component from {relative_path}",
                        "vi": ""
                    },
                    "connections": [],  # Will be populated in _detect_connections
                    "domain": ["frontend", "ui"],
                    "subtype": "React Component",
                    "timelineId": "owlseek-codebase",
                    "metadata": {
                        "file": str(relative_path),
                        "componentName": component_name,
                        "lines": line_count,
                        "exports": exports,
                        "imports": imports,
                        "lastModified": last_modified,
                        "jsdoc": description_text or ""
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

                stat = route_file.stat()
                last_modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
                line_count = len(content.splitlines())

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
                            "file": str(route_file.relative_to(route_file.parents[3])),
                            "lines": line_count,
                            "lastModified": last_modified
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

                stat = tool_file.stat()
                last_modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")

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
                        "toolClass": tool_name,
                        "capabilities": capabilities,
                        "lastModified": last_modified
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
                changed_files = self._extract_changed_files(changelog)
                event_date = changelog.get('date')

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
                        "changelog_url": f"/changelogs/{version}.md",
                        "changedFiles": changed_files,
                        "eventDate": event_date
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
            if not file_path.exists():
                logger.debug(f"Persona file not found for {entity['id']}: {file_path}")
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find API calls (fetch/axios)
            api_calls = [
                call for call in self._find_api_calls(content)
                if call.get('path') and call['path'].startswith('/api/')
            ]

            if api_calls:
                entity['metadata']['apiCalls'] = api_calls

            for call in api_calls:
                path = call.get('path')
                method = call.get('method')

                target_id = self._resolve_api_target(path, method)
                if not target_id:
                    continue

                self._add_connection(
                    source_id=entity['id'],
                    target_id=target_id,
                    label="calls",
                    strength=0.9,
                    connection_type="calls",
                    reciprocal_label="called-by",
                    reciprocal_strength=0.6,
                )

                entity['metadata'].setdefault('apiConnections', []).append({
                    "path": path,
                    "method": method,
                    "targetId": target_id,
                })

            # Resolve component imports → component connections
            self._detect_import_links(entity)

        except Exception as e:
            logger.debug(f"Error detecting connections for {entity['id']}: {e}")

    async def _detect_place_connections(self, entity: Dict, project_path: Path):
        """Detect connections for place (API endpoint)"""
        try:
            file_path = project_path / entity['metadata']['file']
            if not file_path.exists():
                logger.debug(f"Route file not found for {entity['id']}: {file_path}")
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find MCP tool calls
            tool_calls = self._find_tool_calls(content)
            if tool_calls:
                entity['metadata']['toolCalls'] = tool_calls

            for tool_name in tool_calls:
                target_id = self._find_entity_id(tool_name)
                if not target_id:
                    # Try without "Tool" suffix
                    target_id = self._find_entity_id(tool_name.replace("Tool", ""))

                if not target_id:
                    continue

                self._add_connection(
                    source_id=entity['id'],
                    target_id=target_id,
                    label="uses",
                    strength=1.0,
                    connection_type="uses",
                    reciprocal_label="used-by",
                    reciprocal_strength=0.5,
                )

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

    def _find_api_calls(self, content: str) -> List[Dict[str, Optional[str]]]:
        """Find API calls in component code"""
        api_calls: List[Dict[str, Optional[str]]] = []

        fetch_pattern = re.compile(
            r"fetch\(\s*['\"]([^'\"]+)['\"]\s*(?:,\s*\{([^}]*)\})?",
            re.MULTILINE,
        )
        for match in fetch_pattern.finditer(content):
            path = match.group(1)
            options = match.group(2) or ""
            method_match = re.search(r"method\s*:\s*['\"]([A-Z]+)['\"]", options, re.IGNORECASE)
            method = method_match.group(1).upper() if method_match else None
            api_calls.append({
                "path": path,
                "method": method,
                "via": "fetch",
            })

        axios_pattern = re.compile(
            r"axios\.(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]",
            re.IGNORECASE,
        )
        for match in axios_pattern.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            api_calls.append({
                "path": path,
                "method": method,
                "via": "axios",
            })

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

    def _detect_import_links(self, entity: Dict):
        """Create connections based on import statements between personas."""
        imports = entity.get('metadata', {}).get('imports') or []
        if not imports:
            return

        resolved_imports: List[Dict[str, str]] = []

        for import_path in imports:
            target_id = self._resolve_import_target(import_path)
            if not target_id or target_id == entity['id']:
                continue

            self._add_connection(
                source_id=entity['id'],
                target_id=target_id,
                label="imports",
                strength=0.6,
                connection_type="imports",
                reciprocal_label="imported-by",
                reciprocal_strength=0.4,
            )
            resolved_imports.append({"import": import_path, "targetId": target_id})

        if resolved_imports:
            entity['metadata']['resolvedImports'] = resolved_imports

    def _resolve_import_target(self, import_path: str) -> Optional[str]:
        """Resolve an import path to a known entity id if possible."""
        if not import_path:
            return None

        cleaned = import_path.split('?', 1)[0]
        parts = [
            part for part in re.split(r'[\\/]', cleaned)
            if part and part not in {'.', '..'}
        ]
        if not parts:
            return None

        candidate = parts[-1]
        if candidate.lower().startswith('index') and len(parts) > 1:
            candidate = parts[-2]

        candidate = re.sub(r'\.(tsx|ts|jsx|js)$', '', candidate, flags=re.IGNORECASE)

        target_id = self._find_entity_id(candidate)
        if target_id:
            return target_id

        # Fallback: try previous path segment (handles nested folders)
        if len(parts) > 1:
            candidate = parts[-2]
            candidate = re.sub(r'\.(tsx|ts|jsx|js)$', '', candidate, flags=re.IGNORECASE)
            return self._find_entity_id(candidate)

        return None

    def _resolve_api_target(self, path: str, method: Optional[str]) -> Optional[str]:
        """Resolve API path + method to a place entity id."""
        if not path:
            return None

        normalized_path = self._normalize_api_path(path)
        if method:
            key = f"{method.lower()} {normalized_path}"
            target = self.api_path_index.get(key)
            if target:
                return target

        return self.api_path_index.get(normalized_path)

    def _find_entity_id(self, token: str) -> Optional[str]:
        """Lookup entity id by alias token."""
        if not token:
            return None

        key = self._normalize_key(token)
        if not key:
            return None

        return self.entity_alias_map.get(key)

    def _add_connection(
        self,
        source_id: str,
        target_id: str,
        label: str,
        strength: float,
        connection_type: str,
        reciprocal_label: Optional[str] = None,
        reciprocal_strength: Optional[float] = None,
    ):
        """Add a connection between two entities with duplicate protection."""

        source = self.entity_lookup.get(source_id)
        target = self.entity_lookup.get(target_id)
        if not source or not target:
            return

        if not any(conn.get('targetId') == target_id and conn.get('label') == label for conn in source['connections']):
            source['connections'].append({
                "targetId": target_id,
                "strength": strength,
                "label": label,
            })

        if reciprocal_label:
            reciprocal_strength = reciprocal_strength if reciprocal_strength is not None else strength
            if not any(conn.get('targetId') == source_id and conn.get('label') == reciprocal_label for conn in target['connections']):
                target['connections'].append({
                    "targetId": source_id,
                    "strength": reciprocal_strength,
                    "label": reciprocal_label,
                })

        if not any(
            conn.get('source') == source_id and conn.get('target') == target_id and conn.get('type') == connection_type
            for conn in self.connections
        ):
            self.connections.append({
                "source": source_id,
                "target": target_id,
                "type": connection_type,
            })

    def _build_entity_indexes(self):
        """Build lookup tables for entities, aliases, files, and API paths."""
        self.entity_lookup = {}
        self.entity_alias_map = {}
        self.file_lookup = {}
        self.api_path_index = {}

        for entity in self.entities:
            entity_id = entity['id']
            metadata = entity.get('metadata', {}) or {}

            self.entity_lookup[entity_id] = entity

            # Register aliases
            self._register_alias(entity_id, entity_id)
            if entity_id.startswith('owlseek-'):
                self._register_alias(entity_id[len('owlseek-'):], entity_id)

            name_en = entity.get('name', {}).get('en')
            if name_en:
                self._register_alias(name_en, entity_id)

            if entity['type'] == 'persona':
                component_name = metadata.get('componentName')
                if component_name:
                    self._register_alias(component_name, entity_id)
                for export in metadata.get('exports', []) or []:
                    self._register_alias(export, entity_id)

            if entity['type'] == 'object':
                tool_class = metadata.get('toolClass')
                if tool_class:
                    self._register_alias(tool_class, entity_id)
                    self._register_alias(tool_class.replace('Tool', ''), entity_id)

            if entity['type'] == 'place':
                endpoint = metadata.get('endpoint')
                if endpoint:
                    normalized = self._normalize_api_path(endpoint)
                    self.api_path_index.setdefault(normalized, entity_id)
                    method = metadata.get('method')
                    if method:
                        key = f"{method.lower()} {normalized}"
                        self.api_path_index.setdefault(key, entity_id)

            file_path = metadata.get('file')
            if file_path:
                normalized_path = self._normalize_path(file_path)
                if normalized_path:
                    self.file_lookup.setdefault(normalized_path, entity_id)
                    if normalized_path.startswith('owlseek/'):
                        trimmed = normalized_path.split('owlseek/', 1)[1]
                        self.file_lookup.setdefault(trimmed, entity_id)

    def _register_alias(self, value: str, entity_id: str):
        """Register a normalized alias for an entity."""
        key = self._normalize_key(value)
        if not key:
            return

        self.entity_alias_map.setdefault(key, entity_id)

    @staticmethod
    def _normalize_key(value: str) -> str:
        if not value:
            return ""
        return re.sub(r'[^a-z0-9]+', '', value.lower())

    @staticmethod
    def _normalize_path(value: str) -> str:
        if not value:
            return ""
        normalized = value.replace('\\', '/').lstrip('./')
        normalized = re.sub(r'^owlseek/', '', normalized)
        return normalized.lower()

    @staticmethod
    def _normalize_api_path(value: str) -> str:
        return value.strip().lower()

    def _match_entity_by_file(self, file_path: str) -> Optional[str]:
        normalized = self._normalize_path(file_path)
        if not normalized:
            return None

        target = self.file_lookup.get(normalized)
        if target:
            return target

        parts = normalized.split('/', 1)
        if len(parts) > 1:
            return self.file_lookup.get(parts[1])

        return None

    def _link_deployment_connections(self):
        """Link deployment events to affected entities based on changed files."""
        for event in self.entities:
            if event.get('type') != 'event':
                continue

            metadata = event.get('metadata', {}) or {}
            changed_files = metadata.get('changedFiles') or []
            if not changed_files:
                continue

            impacted: List[str] = []
            for file_entry in changed_files:
                target_id = self._match_entity_by_file(file_entry)
                if not target_id:
                    continue

                impacted.append(target_id)
                self._add_connection(
                    source_id=event['id'],
                    target_id=target_id,
                    label="affects",
                    strength=0.7,
                    connection_type="affects",
                    reciprocal_label="affected-by",
                    reciprocal_strength=0.5,
                )

            if impacted:
                metadata['affectedEntities'] = sorted(set(impacted))
                event['metadata'] = metadata

    def _extract_jsdoc_description(self, content: str) -> Optional[str]:
        """Extract the first JSDoc block description from a file."""
        match = re.search(r"/\*\*([\s\S]*?)\*/", content)
        if not match:
            return None

        description_lines = []
        for line in match.group(1).splitlines():
            cleaned = line.strip(" *\t")
            if not cleaned or cleaned.startswith('@'):
                continue
            description_lines.append(cleaned)

        description = " ".join(description_lines).strip()
        return description or None

    def _extract_changed_files(self, changelog: Dict[str, Any]) -> List[str]:
        """Extract changed file paths from a changelog JSON structure."""
        candidates: List[str] = []

        direct_keys = ['changed_files', 'changedFiles', 'files', 'impacted_files', 'impactedFiles']
        for key in direct_keys:
            value = changelog.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        candidates.append(item)
                    elif isinstance(item, dict):
                        for field in ('file', 'path', 'name'):
                            field_value = item.get(field)
                            if isinstance(field_value, str):
                                candidates.append(field_value)

        section_keys = ['breaking_changes', 'new_features', 'bug_fixes', 'known_issues', 'changes']
        for key in section_keys:
            entries = changelog.get(key)
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        for field in ('file', 'path', 'component', 'endpoint'):
                            field_value = entry.get(field)
                            if isinstance(field_value, str):
                                candidates.append(field_value)

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for item in candidates:
            if item not in seen:
                seen.add(item)
                deduped.append(item)

        return deduped
