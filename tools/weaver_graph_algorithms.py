"""
Weaver Graph Algorithms (Phase 6.3)

Advanced graph algorithms using Memgraph MAGE:
- PageRank for concept importance
- Community detection for topic clustering
- Shortest path between concepts
- Centrality metrics (betweenness, degree, closeness)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import Memgraph driver
try:
    from neo4j import GraphDatabase
    MEMGRAPH_AVAILABLE = True
except ImportError:
    MEMGRAPH_AVAILABLE = False
    logger.warning("Memgraph driver not available for Phase 6.3")


class WeaverGraphAlgorithms:
    """
    Advanced graph algorithms for knowledge graph analysis

    Uses Memgraph's built-in algorithms when available,
    falls back to custom implementations otherwise.
    """

    def __init__(self, memgraph_uri: str = "bolt://zeoin:7687"):
        """Initialize graph algorithms with Memgraph connection"""
        self.memgraph_uri = memgraph_uri
        self.driver = None

        if MEMGRAPH_AVAILABLE:
            try:
                self.driver = GraphDatabase.driver(memgraph_uri, auth=None)
                # Test connection
                with self.driver.session() as session:
                    session.run("RETURN 1 as test")
                logger.info("✅ Graph algorithms enabled (Memgraph connected)")
            except Exception as e:
                logger.warning(f"⚠️  Memgraph connection failed: {e}")
                self.driver = None
        else:
            logger.info("ℹ️  Phase 6.3 disabled: Memgraph not available")

    def __del__(self):
        """Close Memgraph connection on cleanup"""
        if self.driver:
            self.driver.close()

    # ========================================================================
    # 1. PageRank - Concept Importance
    # ========================================================================

    async def calculate_concept_importance(
        self,
        user_id: str = "dingo",
        limit: int = 20,
        damping_factor: float = 0.85,
        iterations: int = 20
    ) -> Dict[str, Any]:
        """
        Calculate concept importance using PageRank algorithm (Phase 6.3)

        PageRank measures the importance of concepts based on:
        - How many other concepts mention them
        - The importance of those mentioning concepts

        Args:
            user_id: User identifier
            limit: Maximum concepts to return
            damping_factor: PageRank damping factor (0.85 standard)
            iterations: Number of PageRank iterations

        Returns:
            Dict with status, ranked concepts by importance
        """
        if not self.driver:
            return {
                'status': 'error',
                'error': 'Graph algorithms not available',
                'concepts': []
            }

        try:
            with self.driver.session() as session:
                # Try using Memgraph's built-in PageRank (MAGE)
                try:
                    # Check if MAGE pagerank is available
                    query = """
                    CALL pagerank.get(
                        {iterations: $iterations, damping: $damping}
                    ) YIELD node, rank
                    WHERE 'Concept' IN labels(node)
                    RETURN node.name as concept, rank as importance
                    ORDER BY importance DESC
                    LIMIT $limit
                    """
                    result = session.run(query,
                                       iterations=iterations,
                                       damping=damping_factor,
                                       limit=limit)

                    concepts = []
                    for record in result:
                        concepts.append({
                            'concept': record['concept'],
                            'importance': float(record['importance']),
                            'algorithm': 'pagerank'
                        })

                    logger.info(f"📊 Calculated importance for {len(concepts)} concepts using PageRank")

                    return {
                        'status': 'success',
                        'concepts': concepts,
                        'count': len(concepts),
                        'algorithm': 'pagerank',
                        'parameters': {
                            'damping_factor': damping_factor,
                            'iterations': iterations
                        }
                    }

                except Exception as mage_error:
                    # MAGE not available, fall back to custom implementation
                    logger.info(f"MAGE PageRank not available ({mage_error}), using custom algorithm")

                    # Custom PageRank: Count incoming MENTIONS relationships
                    query = """
                    MATCH (c:Concept)<-[:MENTIONS]-(n)
                    WHERE n.user_id = $user_id
                    WITH c, count(n) as mention_count
                    MATCH (c)<-[:MENTIONS]-(n1)-[:MENTIONS]->(c2:Concept)
                    WHERE n1.user_id = $user_id
                    WITH c, mention_count, count(DISTINCT c2) as connection_count
                    RETURN c.name as concept,
                           toFloat(mention_count) + (toFloat(connection_count) * 0.5) as importance
                    ORDER BY importance DESC
                    LIMIT $limit
                    """

                    result = session.run(query, user_id=user_id, limit=limit)

                    concepts = []
                    for record in result:
                        concepts.append({
                            'concept': record['concept'],
                            'importance': float(record['importance']),
                            'algorithm': 'custom_weighted'
                        })

                    logger.info(f"📊 Calculated importance for {len(concepts)} concepts using custom algorithm")

                    return {
                        'status': 'success',
                        'concepts': concepts,
                        'count': len(concepts),
                        'algorithm': 'custom_weighted',
                        'note': 'Using mention count + connection strength (MAGE not available)'
                    }

        except Exception as e:
            logger.error(f"Failed to calculate concept importance: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'concepts': []
            }

    # ========================================================================
    # 2. Community Detection - Topic Clustering
    # ========================================================================

    async def detect_topic_communities(
        self,
        user_id: str = "dingo",
        min_community_size: int = 2
    ) -> Dict[str, Any]:
        """
        Detect topic communities using community detection algorithms (Phase 6.3)

        Groups concepts into communities (topics) based on:
        - Co-occurrence patterns
        - Shared connections
        - Semantic relationships

        Args:
            user_id: User identifier
            min_community_size: Minimum concepts per community

        Returns:
            Dict with status, detected communities
        """
        if not self.driver:
            return {
                'status': 'error',
                'error': 'Graph algorithms not available',
                'communities': []
            }

        try:
            with self.driver.session() as session:
                # Try using Memgraph's community detection (MAGE)
                try:
                    # Check if MAGE community detection is available
                    query = """
                    CALL community_detection.detect('louvain')
                    YIELD node, community_id
                    WHERE 'Concept' IN labels(node)
                    RETURN community_id, collect(node.name) as concepts
                    ORDER BY size(concepts) DESC
                    """
                    result = session.run(query)

                    communities = []
                    for record in result:
                        concept_list = record['concepts']
                        if len(concept_list) >= min_community_size:
                            communities.append({
                                'community_id': record['community_id'],
                                'concepts': concept_list,
                                'size': len(concept_list),
                                'algorithm': 'louvain'
                            })

                    logger.info(f"🔍 Detected {len(communities)} communities using Louvain")

                    return {
                        'status': 'success',
                        'communities': communities,
                        'count': len(communities),
                        'algorithm': 'louvain',
                        'total_concepts': sum(c['size'] for c in communities)
                    }

                except Exception as mage_error:
                    # MAGE not available, fall back to custom clustering
                    logger.info(f"MAGE community detection not available ({mage_error}), using custom clustering")

                    # Custom clustering: Group by co-occurrence strength
                    query = """
                    MATCH (c1:Concept)<-[:MENTIONS]-(n)-[:MENTIONS]->(c2:Concept)
                    WHERE n.user_id = $user_id AND c1.id < c2.id
                    WITH c1, c2, count(n) as strength
                    WHERE strength >= 2
                    RETURN c1.name as concept1, c2.name as concept2, strength
                    ORDER BY strength DESC
                    """

                    result = session.run(query, user_id=user_id)

                    # Build communities from strong connections
                    concept_pairs = []
                    for record in result:
                        concept_pairs.append({
                            'concept1': record['concept1'],
                            'concept2': record['concept2'],
                            'strength': record['strength']
                        })

                    # Simple clustering: merge connected concepts
                    communities_dict = {}
                    concept_to_community = {}
                    next_community_id = 0

                    for pair in concept_pairs:
                        c1 = pair['concept1']
                        c2 = pair['concept2']

                        c1_comm = concept_to_community.get(c1)
                        c2_comm = concept_to_community.get(c2)

                        if c1_comm is None and c2_comm is None:
                            # New community
                            community_id = next_community_id
                            next_community_id += 1
                            communities_dict[community_id] = {c1, c2}
                            concept_to_community[c1] = community_id
                            concept_to_community[c2] = community_id
                        elif c1_comm is not None and c2_comm is None:
                            # Add c2 to c1's community
                            communities_dict[c1_comm].add(c2)
                            concept_to_community[c2] = c1_comm
                        elif c1_comm is None and c2_comm is not None:
                            # Add c1 to c2's community
                            communities_dict[c2_comm].add(c1)
                            concept_to_community[c1] = c2_comm
                        elif c1_comm != c2_comm:
                            # Merge communities
                            communities_dict[c1_comm].update(communities_dict[c2_comm])
                            for concept in communities_dict[c2_comm]:
                                concept_to_community[concept] = c1_comm
                            del communities_dict[c2_comm]

                    # Format communities
                    communities = []
                    for comm_id, concepts in communities_dict.items():
                        if len(concepts) >= min_community_size:
                            communities.append({
                                'community_id': comm_id,
                                'concepts': sorted(list(concepts)),
                                'size': len(concepts),
                                'algorithm': 'custom_clustering'
                            })

                    # Sort by size
                    communities.sort(key=lambda x: x['size'], reverse=True)

                    logger.info(f"🔍 Detected {len(communities)} communities using custom clustering")

                    return {
                        'status': 'success',
                        'communities': communities,
                        'count': len(communities),
                        'algorithm': 'custom_clustering',
                        'note': 'Using co-occurrence clustering (MAGE not available)',
                        'total_concepts': sum(c['size'] for c in communities)
                    }

        except Exception as e:
            logger.error(f"Failed to detect topic communities: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'communities': []
            }

    # ========================================================================
    # 3. Shortest Path - Learning Journey
    # ========================================================================

    async def find_shortest_learning_path(
        self,
        start_concept: str,
        end_concept: str,
        user_id: str = "dingo",
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Find shortest learning path between two concepts (Phase 6.3)

        Discovers the most direct route through your learning journey
        connecting two concepts.

        Args:
            start_concept: Starting concept
            end_concept: Ending concept
            user_id: User identifier
            max_depth: Maximum path length

        Returns:
            Dict with status, shortest path information
        """
        if not self.driver:
            return {
                'status': 'error',
                'error': 'Graph algorithms not available',
                'path': []
            }

        try:
            with self.driver.session() as session:
                # Use Cypher's built-in shortestPath function
                query = """
                MATCH path = shortestPath(
                    (start:Concept {name: $start_concept})
                    -[:MENTIONS*..${max_depth}]-
                    (end:Concept {name: $end_concept})
                )
                RETURN path,
                       length(path) as path_length,
                       [node in nodes(path) | node.name] as concepts
                LIMIT 1
                """.replace('${max_depth}', str(max_depth))

                result = session.run(query,
                                   start_concept=start_concept,
                                   end_concept=end_concept)

                record = result.single()

                if not record:
                    return {
                        'status': 'success',
                        'found': False,
                        'start_concept': start_concept,
                        'end_concept': end_concept,
                        'message': f'No path found within {max_depth} hops',
                        'path': []
                    }

                # Extract path details
                path_length = record['path_length']
                concepts = record['concepts']

                # Get the nodes along the path for more details
                path_query = """
                MATCH (c1:Concept {name: $concept1})<-[:MENTIONS]-(n)-[:MENTIONS]->(c2:Concept {name: $concept2})
                WHERE n.user_id = $user_id
                RETURN n.id as node_id,
                       labels(n)[0] as type,
                       coalesce(n.discovery, n.reflection) as text,
                       n.created_at as created_at
                ORDER BY n.created_at ASC
                LIMIT 1
                """

                path_details = []
                for i in range(len(concepts) - 1):
                    c1 = concepts[i]
                    c2 = concepts[i + 1]

                    step_result = session.run(path_query,
                                             concept1=c1,
                                             concept2=c2,
                                             user_id=user_id)

                    step_record = step_result.single()
                    if step_record:
                        path_details.append({
                            'from': c1,
                            'to': c2,
                            'via': {
                                'id': step_record['node_id'],
                                'type': step_record['type'],
                                'text': step_record['text'][:100] + '...' if step_record['text'] else '',
                                'when': step_record['created_at']
                            }
                        })

                logger.info(f"🗺️  Found shortest path ({path_length} hops): {start_concept} → {end_concept}")

                return {
                    'status': 'success',
                    'found': True,
                    'start_concept': start_concept,
                    'end_concept': end_concept,
                    'path_length': path_length,
                    'concepts': concepts,
                    'path_details': path_details,
                    'hops': len(path_details)
                }

        except Exception as e:
            logger.error(f"Failed to find shortest path: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'path': []
            }

    # ========================================================================
    # 4. Centrality Metrics - Concept Influence
    # ========================================================================

    async def calculate_concept_centrality(
        self,
        user_id: str = "dingo",
        limit: int = 20,
        metric: str = "betweenness"
    ) -> Dict[str, Any]:
        """
        Calculate centrality metrics for concepts (Phase 6.3)

        Centrality measures how "central" or influential a concept is
        in the knowledge graph.

        Metrics:
        - betweenness: How often concept appears on shortest paths
        - degree: Number of direct connections
        - closeness: Average distance to all other concepts

        Args:
            user_id: User identifier
            limit: Maximum concepts to return
            metric: Centrality metric to calculate

        Returns:
            Dict with status, concepts ranked by centrality
        """
        if not self.driver:
            return {
                'status': 'error',
                'error': 'Graph algorithms not available',
                'concepts': []
            }

        try:
            with self.driver.session() as session:
                if metric == "degree":
                    # Degree centrality: count of connections
                    query = """
                    MATCH (c:Concept)<-[:MENTIONS]-(n)
                    WHERE n.user_id = $user_id
                    WITH c, count(n) as degree
                    RETURN c.name as concept, degree as centrality
                    ORDER BY centrality DESC
                    LIMIT $limit
                    """

                    result = session.run(query, user_id=user_id, limit=limit)

                elif metric == "betweenness":
                    # Try MAGE betweenness centrality first
                    try:
                        query = """
                        CALL betweenness_centrality.get()
                        YIELD node, betweenness
                        WHERE 'Concept' IN labels(node)
                        RETURN node.name as concept, betweenness as centrality
                        ORDER BY centrality DESC
                        LIMIT $limit
                        """
                        result = session.run(query, limit=limit)

                    except Exception:
                        # Fall back to approximate betweenness
                        logger.info("MAGE betweenness not available, using degree as proxy")
                        query = """
                        MATCH (c:Concept)<-[:MENTIONS]-(n)-[:MENTIONS]->(c2:Concept)
                        WHERE n.user_id = $user_id AND c.id <> c2.id
                        WITH c, count(DISTINCT c2) as connections
                        RETURN c.name as concept, connections as centrality
                        ORDER BY centrality DESC
                        LIMIT $limit
                        """
                        result = session.run(query, user_id=user_id, limit=limit)

                elif metric == "closeness":
                    # Closeness: inverse of average distance
                    # Approximate using connection depth
                    query = """
                    MATCH (c:Concept)<-[:MENTIONS]-(n)-[:MENTIONS]->(c2:Concept)
                    WHERE n.user_id = $user_id AND c.id <> c2.id
                    WITH c, count(DISTINCT c2) as direct_connections
                    MATCH (c)<-[:MENTIONS]-(n1)-[:MENTIONS]->(c3:Concept)
                    <-[:MENTIONS]-(n2)-[:MENTIONS]->(c4:Concept)
                    WHERE n1.user_id = $user_id AND n2.user_id = $user_id
                          AND c.id <> c4.id AND c3.id <> c4.id
                    WITH c, direct_connections, count(DISTINCT c4) as indirect_connections
                    RETURN c.name as concept,
                           toFloat(direct_connections) + (toFloat(indirect_connections) * 0.5) as centrality
                    ORDER BY centrality DESC
                    LIMIT $limit
                    """
                    result = session.run(query, user_id=user_id, limit=limit)

                else:
                    return {
                        'status': 'error',
                        'error': f'Unknown metric: {metric}. Use "degree", "betweenness", or "closeness"',
                        'concepts': []
                    }

                # Format results
                concepts = []
                for record in result:
                    concepts.append({
                        'concept': record['concept'],
                        'centrality': float(record['centrality']),
                        'metric': metric
                    })

                logger.info(f"📊 Calculated {metric} centrality for {len(concepts)} concepts")

                return {
                    'status': 'success',
                    'concepts': concepts,
                    'count': len(concepts),
                    'metric': metric
                }

        except Exception as e:
            logger.error(f"Failed to calculate centrality: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'concepts': []
            }


# ============================================================================
# Export
# ============================================================================

# Global instance
weaver_graph_algorithms = WeaverGraphAlgorithms()

__all__ = [
    "WeaverGraphAlgorithms",
    "weaver_graph_algorithms",
]
