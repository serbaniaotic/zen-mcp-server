"""
Weaver Visualization (Phase 6.4)

Graph visualization and export capabilities:
- Cytoscape.js JSON export
- Graphviz DOT export
- D3.js force-directed graph JSON
- Graph statistics and summaries
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import Memgraph driver
try:
    from neo4j import GraphDatabase
    MEMGRAPH_AVAILABLE = True
except ImportError:
    MEMGRAPH_AVAILABLE = False
    logger.warning("Memgraph driver not available for Phase 6.4")


class WeaverVisualization:
    """
    Graph visualization and export tools

    Exports knowledge graph to various formats for visualization:
    - Cytoscape.js (web-based interactive)
    - Graphviz DOT (publication-quality diagrams)
    - D3.js (force-directed layouts)
    - Statistical summaries
    """

    def __init__(self, memgraph_uri: str = "bolt://zeoin:7687"):
        """Initialize visualization with Memgraph connection"""
        self.memgraph_uri = memgraph_uri
        self.driver = None

        if MEMGRAPH_AVAILABLE:
            try:
                self.driver = GraphDatabase.driver(memgraph_uri, auth=None)
                # Test connection
                with self.driver.session() as session:
                    session.run("RETURN 1 as test")
                logger.info("✅ Graph visualization enabled (Memgraph connected)")
            except Exception as e:
                logger.warning(f"⚠️  Memgraph connection failed: {e}")
                self.driver = None
        else:
            logger.info("ℹ️  Phase 6.4 disabled: Memgraph not available")

    def __del__(self):
        """Close Memgraph connection on cleanup"""
        if self.driver:
            self.driver.close()

    # ========================================================================
    # 1. Cytoscape.js Export
    # ========================================================================

    async def export_graph_cytoscape(
        self,
        user_id: str = "dingo",
        include_style: bool = True,
        max_nodes: int = 100
    ) -> Dict[str, Any]:
        """
        Export graph to Cytoscape.js JSON format (Phase 6.4)

        Cytoscape.js is a web-based graph visualization library.
        Output can be loaded directly into Cytoscape.js for interactive visualization.

        Args:
            user_id: User identifier
            include_style: Include basic styling information
            max_nodes: Maximum nodes to include (prevents huge exports)

        Returns:
            Dict with Cytoscape.js-compatible JSON structure
        """
        if not self.driver:
            return {
                'status': 'error',
                'error': 'Graph visualization not available',
                'data': {}
            }

        try:
            with self.driver.session() as session:
                # Fetch nodes (Concepts)
                nodes_query = """
                MATCH (c:Concept)
                OPTIONAL MATCH (c)<-[:MENTIONS]-(n)
                WHERE n.user_id = $user_id
                WITH c, count(n) as mention_count
                RETURN c.name as id,
                       c.name as label,
                       mention_count as weight
                ORDER BY weight DESC
                LIMIT $max_nodes
                """

                nodes_result = session.run(nodes_query, user_id=user_id, max_nodes=max_nodes)

                nodes = []
                concept_ids = set()
                for record in nodes_result:
                    node_id = record['id']
                    concept_ids.add(node_id)
                    nodes.append({
                        'data': {
                            'id': node_id,
                            'label': record['label'],
                            'weight': record['weight'],
                            'type': 'concept'
                        }
                    })

                # Fetch edges (co-occurrence relationships)
                edges_query = """
                MATCH (c1:Concept)<-[:MENTIONS]-(n)-[:MENTIONS]->(c2:Concept)
                WHERE n.user_id = $user_id
                  AND c1.name IN $concept_ids
                  AND c2.name IN $concept_ids
                  AND c1.id < c2.id
                WITH c1.name as source, c2.name as target, count(n) as strength
                RETURN source, target, strength
                ORDER BY strength DESC
                """

                edges_result = session.run(edges_query,
                                          user_id=user_id,
                                          concept_ids=list(concept_ids))

                edges = []
                for record in edges_result:
                    edge_id = f"{record['source']}-{record['target']}"
                    edges.append({
                        'data': {
                            'id': edge_id,
                            'source': record['source'],
                            'target': record['target'],
                            'weight': record['strength']
                        }
                    })

                # Build Cytoscape.js structure
                cytoscape_data = {
                    'elements': {
                        'nodes': nodes,
                        'edges': edges
                    }
                }

                # Add basic styling if requested
                if include_style:
                    cytoscape_data['style'] = [
                        {
                            'selector': 'node',
                            'style': {
                                'label': 'data(label)',
                                'width': 'mapData(weight, 0, 10, 20, 80)',
                                'height': 'mapData(weight, 0, 10, 20, 80)',
                                'background-color': '#4A90E2',
                                'color': '#fff',
                                'text-valign': 'center',
                                'text-halign': 'center',
                                'font-size': '12px'
                            }
                        },
                        {
                            'selector': 'edge',
                            'style': {
                                'width': 'mapData(weight, 1, 5, 1, 5)',
                                'line-color': '#9CA3AF',
                                'target-arrow-shape': 'none',
                                'curve-style': 'bezier',
                                'opacity': 0.6
                            }
                        }
                    ]

                logger.info(f"📊 Exported Cytoscape.js graph: {len(nodes)} nodes, {len(edges)} edges")

                return {
                    'status': 'success',
                    'format': 'cytoscape.js',
                    'nodes_count': len(nodes),
                    'edges_count': len(edges),
                    'data': cytoscape_data,
                    'export_time': datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to export Cytoscape.js graph: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'data': {}
            }

    # ========================================================================
    # 2. Graphviz DOT Export
    # ========================================================================

    async def export_graph_graphviz(
        self,
        user_id: str = "dingo",
        layout: str = "dot",
        max_nodes: int = 100,
        min_edge_weight: int = 2
    ) -> Dict[str, Any]:
        """
        Export graph to Graphviz DOT format (Phase 6.4)

        Graphviz creates publication-quality diagrams.
        Output can be rendered with: dot -Tpng graph.dot -o graph.png

        Args:
            user_id: User identifier
            layout: Layout algorithm (dot, neato, fdp, sfdp, circo, twopi)
            max_nodes: Maximum nodes to include
            min_edge_weight: Minimum edge strength to include

        Returns:
            Dict with DOT format string
        """
        if not self.driver:
            return {
                'status': 'error',
                'error': 'Graph visualization not available',
                'dot': ''
            }

        try:
            with self.driver.session() as session:
                # Fetch nodes
                nodes_query = """
                MATCH (c:Concept)
                OPTIONAL MATCH (c)<-[:MENTIONS]-(n)
                WHERE n.user_id = $user_id
                WITH c, count(n) as mention_count
                RETURN c.name as id, mention_count as weight
                ORDER BY weight DESC
                LIMIT $max_nodes
                """

                nodes_result = session.run(nodes_query, user_id=user_id, max_nodes=max_nodes)

                nodes = []
                concept_ids = set()
                for record in nodes_result:
                    nodes.append({
                        'id': record['id'],
                        'weight': record['weight']
                    })
                    concept_ids.add(record['id'])

                # Fetch edges
                edges_query = """
                MATCH (c1:Concept)<-[:MENTIONS]-(n)-[:MENTIONS]->(c2:Concept)
                WHERE n.user_id = $user_id
                  AND c1.name IN $concept_ids
                  AND c2.name IN $concept_ids
                  AND c1.id < c2.id
                WITH c1.name as source, c2.name as target, count(n) as strength
                WHERE strength >= $min_weight
                RETURN source, target, strength
                ORDER BY strength DESC
                """

                edges_result = session.run(edges_query,
                                          user_id=user_id,
                                          concept_ids=list(concept_ids),
                                          min_weight=min_edge_weight)

                edges = []
                for record in edges_result:
                    edges.append({
                        'source': record['source'],
                        'target': record['target'],
                        'weight': record['strength']
                    })

                # Build DOT format
                dot_lines = []
                dot_lines.append(f'graph knowledge_graph {{')
                dot_lines.append(f'  layout={layout};')
                dot_lines.append(f'  node [shape=circle, style=filled, fillcolor=lightblue];')
                dot_lines.append(f'  edge [color=gray];')
                dot_lines.append('')

                # Add nodes with sizing based on weight
                for node in nodes:
                    # Escape special characters
                    safe_id = node['id'].replace('"', '\\"')
                    size = min(1.0 + (node['weight'] * 0.2), 3.0)  # Size 1.0 to 3.0
                    fontsize = min(10 + (node['weight'] * 2), 24)  # Font 10 to 24
                    dot_lines.append(f'  "{safe_id}" [width={size:.1f}, fontsize={fontsize:.0f}];')

                dot_lines.append('')

                # Add edges with weight-based styling
                for edge in edges:
                    safe_source = edge['source'].replace('"', '\\"')
                    safe_target = edge['target'].replace('"', '\\"')
                    penwidth = min(1 + edge['weight'], 5)  # Line width 1 to 5
                    dot_lines.append(f'  "{safe_source}" -- "{safe_target}" [penwidth={penwidth}];')

                dot_lines.append('}')

                dot_content = '\n'.join(dot_lines)

                logger.info(f"📊 Exported Graphviz DOT: {len(nodes)} nodes, {len(edges)} edges")

                return {
                    'status': 'success',
                    'format': 'graphviz-dot',
                    'layout': layout,
                    'nodes_count': len(nodes),
                    'edges_count': len(edges),
                    'dot': dot_content,
                    'export_time': datetime.utcnow().isoformat(),
                    'usage': f'Save to file.dot and run: {layout} -Tpng file.dot -o graph.png'
                }

        except Exception as e:
            logger.error(f"Failed to export Graphviz DOT: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'dot': ''
            }

    # ========================================================================
    # 3. D3.js Force-Directed Graph Export
    # ========================================================================

    async def export_graph_d3(
        self,
        user_id: str = "dingo",
        max_nodes: int = 100
    ) -> Dict[str, Any]:
        """
        Export graph to D3.js force-directed format (Phase 6.4)

        D3.js is a JavaScript library for data-driven visualizations.
        Output can be used with D3 force simulation layouts.

        Args:
            user_id: User identifier
            max_nodes: Maximum nodes to include

        Returns:
            Dict with D3.js-compatible JSON structure
        """
        if not self.driver:
            return {
                'status': 'error',
                'error': 'Graph visualization not available',
                'data': {}
            }

        try:
            with self.driver.session() as session:
                # Fetch nodes
                nodes_query = """
                MATCH (c:Concept)
                OPTIONAL MATCH (c)<-[:MENTIONS]-(n)
                WHERE n.user_id = $user_id
                WITH c, count(n) as mention_count
                RETURN c.name as id, mention_count as value
                ORDER BY value DESC
                LIMIT $max_nodes
                """

                nodes_result = session.run(nodes_query, user_id=user_id, max_nodes=max_nodes)

                nodes = []
                concept_ids = set()
                id_to_index = {}

                for idx, record in enumerate(nodes_result):
                    node_id = record['id']
                    concept_ids.add(node_id)
                    id_to_index[node_id] = idx

                    nodes.append({
                        'id': node_id,
                        'name': node_id,
                        'value': record['value'],
                        'group': 1  # Can be enhanced with community detection
                    })

                # Fetch edges
                edges_query = """
                MATCH (c1:Concept)<-[:MENTIONS]-(n)-[:MENTIONS]->(c2:Concept)
                WHERE n.user_id = $user_id
                  AND c1.name IN $concept_ids
                  AND c2.name IN $concept_ids
                  AND c1.id < c2.id
                WITH c1.name as source, c2.name as target, count(n) as strength
                RETURN source, target, strength
                """

                edges_result = session.run(edges_query,
                                          user_id=user_id,
                                          concept_ids=list(concept_ids))

                links = []
                for record in edges_result:
                    source_id = record['source']
                    target_id = record['target']

                    # D3 can use either IDs or indices
                    if source_id in id_to_index and target_id in id_to_index:
                        links.append({
                            'source': source_id,
                            'target': target_id,
                            'value': record['strength']
                        })

                # Build D3.js structure
                d3_data = {
                    'nodes': nodes,
                    'links': links
                }

                logger.info(f"📊 Exported D3.js graph: {len(nodes)} nodes, {len(links)} links")

                return {
                    'status': 'success',
                    'format': 'd3-force',
                    'nodes_count': len(nodes),
                    'links_count': len(links),
                    'data': d3_data,
                    'export_time': datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to export D3.js graph: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'data': {}
            }

    # ========================================================================
    # 4. Graph Statistics Summary
    # ========================================================================

    async def generate_graph_stats(
        self,
        user_id: str = "dingo"
    ) -> Dict[str, Any]:
        """
        Generate comprehensive graph statistics (Phase 6.4)

        Provides overview of graph structure and characteristics:
        - Node counts by type
        - Edge counts and density
        - Degree distribution
        - Component analysis
        - Top concepts

        Args:
            user_id: User identifier

        Returns:
            Dict with comprehensive graph statistics
        """
        if not self.driver:
            return {
                'status': 'error',
                'error': 'Graph visualization not available',
                'stats': {}
            }

        try:
            with self.driver.session() as session:
                # Basic counts
                stats = {}

                # 1. Node counts
                node_count_query = """
                MATCH (n)
                RETURN labels(n)[0] as type, count(n) as count
                """
                node_result = session.run(node_count_query)
                stats['node_counts'] = {record['type']: record['count'] for record in node_result}

                # 2. Concept count
                concept_count_query = """
                MATCH (c:Concept)
                RETURN count(c) as count
                """
                concept_result = session.run(concept_count_query)
                stats['total_concepts'] = concept_result.single()['count']

                # 3. Relationship counts
                rel_count_query = """
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(r) as count
                """
                rel_result = session.run(rel_count_query)
                stats['relationship_counts'] = {record['rel_type']: record['count'] for record in rel_result}

                # 4. User-specific concept mentions
                user_mentions_query = """
                MATCH (c:Concept)<-[:MENTIONS]-(n)
                WHERE n.user_id = $user_id
                WITH c, count(n) as mentions
                RETURN count(c) as concepts_with_mentions,
                       sum(mentions) as total_mentions,
                       avg(mentions) as avg_mentions,
                       max(mentions) as max_mentions
                """
                mentions_result = session.run(user_mentions_query, user_id=user_id)
                mentions_record = mentions_result.single()
                if mentions_record:
                    stats['user_concepts'] = {
                        'concepts_mentioned': mentions_record['concepts_with_mentions'],
                        'total_mentions': mentions_record['total_mentions'],
                        'avg_mentions_per_concept': round(float(mentions_record['avg_mentions'] or 0), 2),
                        'max_mentions': mentions_record['max_mentions']
                    }

                # 5. Top concepts by mentions
                top_concepts_query = """
                MATCH (c:Concept)<-[:MENTIONS]-(n)
                WHERE n.user_id = $user_id
                WITH c.name as concept, count(n) as mentions
                RETURN concept, mentions
                ORDER BY mentions DESC
                LIMIT 10
                """
                top_result = session.run(top_concepts_query, user_id=user_id)
                stats['top_concepts'] = [
                    {'concept': record['concept'], 'mentions': record['mentions']}
                    for record in top_result
                ]

                # 6. Concept co-occurrence statistics
                cooccurrence_query = """
                MATCH (c1:Concept)<-[:MENTIONS]-(n)-[:MENTIONS]->(c2:Concept)
                WHERE n.user_id = $user_id AND c1.id < c2.id
                WITH count(*) as total_pairs
                RETURN total_pairs
                """
                cooccur_result = session.run(cooccurrence_query, user_id=user_id)
                stats['concept_pairs'] = cooccur_result.single()['total_pairs']

                # 7. Graph density (for concepts)
                if stats['total_concepts'] > 1:
                    max_possible_edges = (stats['total_concepts'] * (stats['total_concepts'] - 1)) / 2
                    actual_edges = stats.get('concept_pairs', 0)
                    stats['graph_density'] = round(actual_edges / max_possible_edges, 4) if max_possible_edges > 0 else 0
                else:
                    stats['graph_density'] = 0

                logger.info(f"📊 Generated graph statistics: {stats['total_concepts']} concepts")

                return {
                    'status': 'success',
                    'user_id': user_id,
                    'stats': stats,
                    'generated_at': datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to generate graph stats: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'stats': {}
            }


# ============================================================================
# Export
# ============================================================================

# Global instance
weaver_visualization = WeaverVisualization()

__all__ = [
    "WeaverVisualization",
    "weaver_visualization",
]
