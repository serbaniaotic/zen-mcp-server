"""
Mermaid Generator Tool - QC-083 Phase 1 & 3

Generates mermaid diagrams from the OwlSeek Universe for:
- Component flows and dependencies
- Deployment reports with health status
- Debug mode visualization

Part of the Coach Manager Universe Integration system.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class MermaidGenerator:
    """
    Generate mermaid diagrams from universe data

    Supports:
    - Component flow diagrams
    - Dependency graphs
    - Health status visualization
    - Broken connection highlighting
    """

    def __init__(self, universe_path: Optional[str] = None, memgraph_uri: Optional[str] = None):
        """
        Initialize mermaid generator

        Args:
            universe_path: Path to universe JSON file
            memgraph_uri: URI for Memgraph connection (for advanced queries)
        """
        # Try multiple common paths for universe file
        if universe_path:
            self.universe_path = universe_path
        else:
            possible_paths = [
                "/opt/dev/owlseek/universe/owlseek-universe.json",
                "/home/dingo/code/owlseek/universe/owlseek-universe.json",
                os.path.expanduser("~/code/owlseek/universe/owlseek-universe.json"),
            ]
            self.universe_path = None
            for path in possible_paths:
                if Path(path).exists():
                    self.universe_path = path
                    break
            if not self.universe_path:
                self.universe_path = possible_paths[0]  # Default to first if none found

        self.memgraph_uri = memgraph_uri or "bolt://zeoin:7687"
        self.universe_data = None
        self.graph_driver = None

        # Try to load universe data
        self._load_universe()

        # Try to connect to Memgraph
        self._connect_memgraph()

    def _load_universe(self):
        """Load universe JSON data"""
        try:
            universe_file = Path(self.universe_path)
            if universe_file.exists():
                with open(universe_file, 'r') as f:
                    self.universe_data = json.load(f)
                logger.info(f"✅ Loaded universe from {self.universe_path}")
            else:
                logger.warning(f"⚠️  Universe file not found: {self.universe_path}")
        except Exception as e:
            logger.error(f"❌ Failed to load universe: {e}")

    def _connect_memgraph(self):
        """Connect to Memgraph for advanced queries"""
        try:
            self.graph_driver = GraphDatabase.driver(self.memgraph_uri, auth=None)
            # Test connection
            with self.graph_driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            logger.info("✅ Connected to Memgraph")
        except Exception as e:
            logger.warning(f"⚠️  Memgraph not available: {e}")
            self.graph_driver = None

    def generate_component_flow(
        self,
        component_name: str,
        max_depth: int = 3,
        include_broken: bool = True
    ) -> str:
        """
        Generate mermaid flow diagram for a component

        Args:
            component_name: Name of the component to trace
            max_depth: Maximum depth of dependency tree
            include_broken: Highlight broken/missing connections

        Returns:
            Mermaid diagram as string
        """
        if not self.universe_data:
            return "graph TD\n    Error[Universe data not available]"

        # Find the entity
        entity = self._find_entity(component_name)
        if not entity:
            return f"graph TD\n    Error[Component '{component_name}' not found]"

        # Build flow graph
        nodes = []
        edges = []
        visited = set()

        self._trace_dependencies(entity, nodes, edges, visited, depth=0, max_depth=max_depth)

        # Generate mermaid syntax
        mermaid = ["graph TD"]

        # Add nodes
        for node_id, node_label, node_type, is_broken in nodes:
            if is_broken and include_broken:
                mermaid.append(f"    {node_id}[{node_label}]")
                mermaid.append(f"    style {node_id} fill:#ef4444")
            else:
                mermaid.append(f"    {node_id}[{node_label}]")

        # Add edges
        for from_id, to_id, label, is_broken in edges:
            if is_broken and include_broken:
                mermaid.append(f"    {from_id} -.->|❌ {label}| {to_id}")
            else:
                mermaid.append(f"    {from_id} -->|{label}| {to_id}")

        return "\n".join(mermaid)

    def generate_deployment_report(
        self,
        changed_files: List[str],
        project_path: str
    ) -> str:
        """
        Generate deployment report with mermaid diagrams

        Args:
            changed_files: List of changed file paths
            project_path: Root project path

        Returns:
            Markdown report with mermaid diagrams
        """
        if not self.universe_data:
            return "# Deployment Report\n\n❌ Universe data not available"

        # Load latest changelog
        changelog_data = self._load_latest_changelog(project_path)

        # Find entities for changed files
        changed_entities = []
        for file_path in changed_files:
            entity = self._find_entity_by_file(file_path)
            if entity:
                changed_entities.append(entity)

        # Build report
        report = ["# Deployment Report (CalVer)", ""]
        report.append(f"**Version**: {changelog_data.get('version', 'Unknown')}")
        report.append(f"**Generated**: {self.universe_data.get('generatedAt', 'Unknown')}")
        report.append(f"**Git SHA**: {changelog_data.get('git_sha', 'Unknown')}")
        report.append(f"**Branch**: {changelog_data.get('branch', 'Unknown')}")
        report.append("")

        # Add changelog summary
        if changelog_data:
            stats = changelog_data.get('stats', {})
            report.append("## Deployment Summary")
            report.append("")
            report.append(f"- **Description**: {changelog_data.get('description', 'N/A')}")
            report.append(f"- **Previous Version**: {changelog_data.get('previousVersion', 'none')}")
            report.append(f"- **Files Changed**: {stats.get('files_changed', 0)}")
            report.append(f"- **New Features**: {stats.get('features_count', 0)}")
            report.append(f"- **Bug Fixes**: {stats.get('fixes_count', 0)}")
            report.append(f"- **Breaking Changes**: {stats.get('breaking_count', 0)}")
            report.append("")

        report.append(f"**Changed Components**: {len(changed_entities)}")
        report.append("")

        # List changed components
        report.append("## Changed Components")
        report.append("")
        for entity in changed_entities:
            name = entity.get('name', {}).get('en', 'Unknown')
            entity_type = entity.get('type', 'unknown')
            file_path = entity.get('metadata', {}).get('file', 'Unknown')

            # Check health status
            is_broken = self._check_entity_health(entity)
            status = "❌ BROKEN" if is_broken else "✅ WORKING"

            report.append(f"- **{name}** ({entity_type}) - {status}")
            report.append(f"  - File: `{file_path}`")

            # Get QC session if available
            qc_session = entity.get('metadata', {}).get('qc_session')
            if qc_session:
                report.append(f"  - QC Session: {qc_session}")

            report.append("")

        # Generate mermaid diagrams for each changed component
        report.append("## Component Flows")
        report.append("")

        for entity in changed_entities:
            name = entity.get('name', {}).get('en', 'Unknown')
            report.append(f"### {name}")
            report.append("")
            report.append("```mermaid")
            report.append(self.generate_component_flow(name, max_depth=2))
            report.append("```")
            report.append("")

        return "\n".join(report)

    def generate_broken_flow(self, component_name: str) -> str:
        """
        Generate mermaid diagram highlighting broken connections

        Args:
            component_name: Component to analyze

        Returns:
            Mermaid diagram with broken connections highlighted
        """
        return self.generate_component_flow(component_name, include_broken=True)

    def generate_module_architecture(self, module_name: str) -> str:
        """
        Generate cluster view of a module

        Args:
            module_name: Module name (e.g., 'teachme', 'voice-qc')

        Returns:
            Mermaid diagram with clustered view
        """
        if not self.universe_data:
            return "graph TD\n    Error[Universe data not available]"

        # Find all entities in this module
        module_entities = [
            e for e in self.universe_data.get('entities', [])
            if module_name.lower() in e.get('name', {}).get('en', '').lower()
        ]

        if not module_entities:
            return f"graph TD\n    Error[No entities found for module '{module_name}']"

        mermaid = ["graph TD"]

        # Group by type
        personas = [e for e in module_entities if e.get('type') == 'persona']
        places = [e for e in module_entities if e.get('type') == 'place']
        objects = [e for e in module_entities if e.get('type') == 'object']

        # Add subgraphs
        if personas:
            mermaid.append(f"    subgraph UI[UI Components]")
            for entity in personas:
                entity_id = self._make_node_id(entity.get('id', ''))
                name = entity.get('name', {}).get('en', 'Unknown')
                mermaid.append(f"        {entity_id}[{name}]")
            mermaid.append("    end")

        if places:
            mermaid.append(f"    subgraph API[API Endpoints]")
            for entity in places:
                entity_id = self._make_node_id(entity.get('id', ''))
                name = entity.get('name', {}).get('en', 'Unknown')
                mermaid.append(f"        {entity_id}[{name}]")
            mermaid.append("    end")

        if objects:
            mermaid.append(f"    subgraph MCP[MCP Tools]")
            for entity in objects:
                entity_id = self._make_node_id(entity.get('id', ''))
                name = entity.get('name', {}).get('en', 'Unknown')
                mermaid.append(f"        {entity_id}[{name}]")
            mermaid.append("    end")

        return "\n".join(mermaid)

    def _find_entity(self, name: str) -> Optional[Dict[str, Any]]:
        """Find entity by name"""
        if not self.universe_data:
            return None

        for entity in self.universe_data.get('entities', []):
            entity_name = entity.get('name', {}).get('en', '')
            if entity_name.lower() == name.lower():
                return entity

        return None

    def _find_entity_by_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Find entity by file path"""
        if not self.universe_data:
            return None

        # Normalize file path
        normalized_path = file_path.replace('\\', '/').lower()

        for entity in self.universe_data.get('entities', []):
            entity_file = entity.get('metadata', {}).get('file', '')
            if entity_file and normalized_path in entity_file.lower():
                return entity

        return None

    def _check_entity_health(self, entity: Dict[str, Any]) -> bool:
        """
        Check if entity has broken connections

        Returns:
            True if entity is broken, False if healthy
        """
        # Check metadata for broken flag
        if entity.get('metadata', {}).get('is_broken'):
            return True

        # Check connections for missing targets
        for conn in entity.get('connections', []):
            target_id = conn.get('targetId')
            if target_id and not self._find_entity_by_id(target_id):
                return True

        return False

    def _find_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Find entity by ID"""
        if not self.universe_data:
            return None

        for entity in self.universe_data.get('entities', []):
            if entity.get('id') == entity_id:
                return entity

        return None

    def _trace_dependencies(
        self,
        entity: Dict[str, Any],
        nodes: List[tuple],
        edges: List[tuple],
        visited: Set[str],
        depth: int,
        max_depth: int
    ):
        """
        Recursively trace dependencies

        Args:
            entity: Current entity
            nodes: List of (node_id, label, type, is_broken) tuples
            edges: List of (from_id, to_id, label, is_broken) tuples
            visited: Set of visited entity IDs
            depth: Current depth
            max_depth: Maximum depth to trace
        """
        entity_id = entity.get('id', '')
        if entity_id in visited or depth > max_depth:
            return

        visited.add(entity_id)

        # Add current node
        name = entity.get('name', {}).get('en', 'Unknown')
        entity_type = entity.get('type', 'unknown')
        is_broken = self._check_entity_health(entity)
        node_id = self._make_node_id(entity_id)

        nodes.append((node_id, name, entity_type, is_broken))

        # Trace connections
        for conn in entity.get('connections', []):
            target_id = conn.get('targetId')
            conn_type = conn.get('type', 'depends_on')

            if target_id:
                target_entity = self._find_entity_by_id(target_id)

                if target_entity:
                    target_node_id = self._make_node_id(target_id)
                    edges.append((node_id, target_node_id, conn_type, False))

                    # Recursively trace
                    if depth < max_depth:
                        self._trace_dependencies(
                            target_entity, nodes, edges, visited, depth + 1, max_depth
                        )
                else:
                    # Broken connection
                    target_node_id = self._make_node_id(f"{target_id}_missing")
                    nodes.append((target_node_id, f"Missing: {target_id}", "missing", True))
                    edges.append((node_id, target_node_id, conn_type, True))

    def _make_node_id(self, entity_id: str) -> str:
        """Convert entity ID to valid mermaid node ID"""
        # Remove special characters and make uppercase for mermaid
        return entity_id.replace('-', '_').replace('/', '_').upper()[:20]

    def _load_latest_changelog(self, project_path: str) -> dict:
        """Load the latest changelog JSON file"""
        from datetime import datetime

        changelog_dir = Path(project_path) / "changelogs"
        if not changelog_dir.exists():
            return {}

        # Find latest changelog by date
        changelog_files = sorted(changelog_dir.glob("*.json"), reverse=True)
        if not changelog_files:
            return {}

        try:
            with open(changelog_files[0], 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load changelog: {e}")
            return {}


# Singleton instance
mermaid_generator = MermaidGenerator()


class DeploymentCoach:
    """
    Deployment Coach - Auto-generate deployment reports

    Detects changed files and generates comprehensive reports with:
    - Changed components list
    - Mermaid flow diagrams
    - Health status indicators
    """

    def __init__(self):
        self.generator = mermaid_generator

    def generate_report(self, project_path: str, output_path: Optional[str] = None) -> str:
        """
        Generate deployment report

        Args:
            project_path: Root path of the project
            output_path: Optional output path for report (defaults to project_path/DEPLOYMENT-REPORT.md)

        Returns:
            Path to generated report
        """
        import subprocess

        # Get changed files from git
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD~1'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            changed_files = result.stdout.strip().split('\n') if result.stdout else []
        except Exception as e:
            logger.error(f"Failed to get git diff: {e}")
            changed_files = []

        # Generate report
        report_content = self.generator.generate_deployment_report(changed_files, project_path)

        # Write report
        if not output_path:
            output_path = Path(project_path) / "DEPLOYMENT-REPORT.md"

        with open(output_path, 'w') as f:
            f.write(report_content)

        logger.info(f"✅ Deployment report generated: {output_path}")
        return str(output_path)


# Export singleton
deployment_coach = DeploymentCoach()
