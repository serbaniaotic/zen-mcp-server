"""
Weaver Tools for qc_workflow (Phase 4 + Phase 5 + Phase 6)

Weaver integration with semantic search and knowledge graph:
- PostgreSQL for metadata storage
- Qdrant for vector search (Phase 5)
- Ollama for embeddings (Phase 5)
- Memgraph for knowledge graph (Phase 6)

This provides the two core prompts:
1. "Did you know..." - Capture curiosity moments
2. "What did I learn today..." - Daily reflection practice
"""

import logging
import psycopg2
import httpx
import uuid
from datetime import datetime
from typing import Any, Optional, Dict, List
from pydantic import Field

from tools.shared.base_models import ToolRequest
from tools.simple.base import SimpleTool

# Phase 5: Import embedding client and Qdrant
try:
    from tools.weaver_embedding import weaver_embedding
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
    PHASE5_AVAILABLE = True
except ImportError as e:
    PHASE5_AVAILABLE = False
    logging.warning(f"Phase 5 features not available: {e}")

# Phase 6: Import Memgraph (Neo4j driver)
try:
    from neo4j import GraphDatabase
    PHASE6_AVAILABLE = True
except ImportError as e:
    PHASE6_AVAILABLE = False
    logging.warning(f"Phase 6 features not available: {e}")

logger = logging.getLogger(__name__)


# ============================================================================
# Field Descriptions
# ============================================================================

CAPTURE_CURIOSITY_FIELD_DESCRIPTIONS = {
    "discovery": "What you discovered or learned (the 'Did you know...' moment)",
    "context": "Optional context where this happened (session, ticket, etc.)",
    "feeling": "How this made you feel (e.g., 'mind_blown', 'excited', 'curious')",
    "user_id": "User identifier (defaults to 'dingo')",
}

CAPTURE_LEARNING_FIELD_DESCRIPTIONS = {
    "reflection": "What you learned today (end-of-day reflection)",
    "depth": "Depth of learning: 'surface', 'medium', or 'deep'",
    "session_context": "Optional context about the session/work",
    "user_id": "User identifier (defaults to 'dingo')",
}

SEARCH_CURIOSITY_FIELD_DESCRIPTIONS = {
    "query": "Search query to find past curiosity moments",
    "limit": "Maximum number of results (default: 5)",
    "user_id": "User identifier (defaults to 'dingo')",
}


# ============================================================================
# Request Models
# ============================================================================

class CaptureCuriosityRequest(ToolRequest):
    """Request model for capturing curiosity moments"""
    discovery: str = Field(..., description=CAPTURE_CURIOSITY_FIELD_DESCRIPTIONS["discovery"])
    context: Optional[str] = Field(None, description=CAPTURE_CURIOSITY_FIELD_DESCRIPTIONS["context"])
    feeling: Optional[str] = Field(None, description=CAPTURE_CURIOSITY_FIELD_DESCRIPTIONS["feeling"])
    user_id: str = Field(default="dingo", description=CAPTURE_CURIOSITY_FIELD_DESCRIPTIONS["user_id"])


class CaptureLearningRequest(ToolRequest):
    """Request model for capturing learning reflections"""
    reflection: str = Field(..., description=CAPTURE_LEARNING_FIELD_DESCRIPTIONS["reflection"])
    depth: Optional[str] = Field(default="medium", description=CAPTURE_LEARNING_FIELD_DESCRIPTIONS["depth"])
    session_context: Optional[str] = Field(None, description=CAPTURE_LEARNING_FIELD_DESCRIPTIONS["session_context"])
    user_id: str = Field(default="dingo", description=CAPTURE_LEARNING_FIELD_DESCRIPTIONS["user_id"])


class SearchCuriosityRequest(ToolRequest):
    """Request model for searching curiosity moments"""
    query: str = Field(..., description=SEARCH_CURIOSITY_FIELD_DESCRIPTIONS["query"])
    limit: int = Field(default=5, ge=1, le=50, description=SEARCH_CURIOSITY_FIELD_DESCRIPTIONS["limit"])
    user_id: str = Field(default="dingo", description=SEARCH_CURIOSITY_FIELD_DESCRIPTIONS["user_id"])


# ============================================================================
# Core Weaver Tools Class
# ============================================================================

class WeaverToolsSimple:
    """
    Simplified Weaver tools for CLI agents

    Direct database access to Phase 3+ infrastructure:
    - PostgreSQL (metadata on zeoin:5433)
    - Qdrant (vectors on zeoin:6333) [Phase 5]
    - Memgraph (graph on zeoin:7687) [Phase 6]
    """

    def __init__(self):
        import os

        # Use environment variables if available, fallback to defaults
        # This allows Docker containers to use container hostnames
        # while local development uses zeoin
        self.postgres_config = {
            "host": os.getenv("POSTGRES_HOST", "zeoin"),
            "port": int(os.getenv("POSTGRES_PORT", "5433")),
            "database": os.getenv("POSTGRES_DB", "weaver_meta"),
            "user": os.getenv("POSTGRES_USER", "weaver"),
            "password": os.getenv("POSTGRES_PASSWORD", "weaver_dev_password")
        }

        qdrant_host = os.getenv("QDRANT_HOST", "zeoin")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        self.qdrant_url = f"http://{qdrant_host}:{qdrant_port}"

        # Memgraph URI - can be overridden entirely or use HOST/PORT
        self.memgraph_uri = os.getenv(
            "MEMGRAPH_URI",
            f"bolt://{os.getenv('MEMGRAPH_HOST', 'zeoin')}:{os.getenv('MEMGRAPH_PORT', '7687')}"
        )

        # Phase 5: Initialize Qdrant client and embedding client
        if PHASE5_AVAILABLE:
            try:
                self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
                self.embedding = weaver_embedding
                logger.info("✅ Phase 5 enabled: Semantic search available")
            except Exception as e:
                logger.warning(f"⚠️  Phase 5 initialization failed: {e}")
                self.qdrant = None
                self.embedding = None
        else:
            self.qdrant = None
            self.embedding = None
            logger.info("ℹ️  Phase 4 mode: Text search only")

        # Phase 6: Initialize Memgraph connection
        if PHASE6_AVAILABLE:
            try:
                self.graph_driver = GraphDatabase.driver(
                    self.memgraph_uri,
                    auth=None  # Memgraph default has no auth in dev
                )
                # Test connection
                with self.graph_driver.session() as session:
                    result = session.run("RETURN 1 as test")
                    result.single()
                logger.info("✅ Phase 6 enabled: Knowledge graph available")
            except Exception as e:
                logger.warning(f"⚠️  Phase 6 initialization failed: {e}")
                self.graph_driver = None
        else:
            self.graph_driver = None
            logger.info("ℹ️  Phase 6 not available: No knowledge graph")

        # Connection will be created per-request (connection pooling in production)
        self._test_connections()

    def _test_connections(self):
        """Test database connections on initialization"""
        try:
            conn = psycopg2.connect(**self.postgres_config)
            conn.close()
            logger.info("✅ PostgreSQL connection verified (zeoin:5433)")
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")

    def _get_connection(self):
        """Get a new PostgreSQL connection"""
        return psycopg2.connect(**self.postgres_config)

    def _create_graph_node(
        self,
        node_id: str,
        node_type: str,
        properties: Dict[str, Any]
    ) -> bool:
        """
        Create a node in Memgraph (Phase 6)

        Args:
            node_id: Unique identifier for the node
            node_type: Type of node (Curiosity, Learning, Concept, etc.)
            properties: Node properties

        Returns:
            bool: True if successful
        """
        if not self.graph_driver:
            logger.debug("Graph driver not available, skipping node creation")
            return False

        try:
            with self.graph_driver.session() as session:
                # Create node with properties
                query = f"""
                MERGE (n:{node_type} {{id: $node_id}})
                SET n += $properties
                RETURN n
                """
                session.run(query, node_id=node_id, properties=properties)
                logger.info(f"📊 Graph node created: {node_type}:{node_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to create graph node: {e}")
            return False

    def _create_graph_relationship(
        self,
        from_id: str,
        from_type: str,
        to_id: str,
        to_type: str,
        relationship: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a relationship between nodes in Memgraph (Phase 6)

        Args:
            from_id: Source node ID
            from_type: Source node type
            to_id: Target node ID
            to_type: Target node type
            relationship: Relationship type (e.g., RELATES_TO, BUILDS_ON)
            properties: Optional relationship properties

        Returns:
            bool: True if successful
        """
        if not self.graph_driver:
            logger.debug("Graph driver not available, skipping relationship creation")
            return False

        try:
            with self.graph_driver.session() as session:
                if properties:
                    query = f"""
                    MATCH (a:{from_type} {{id: $from_id}})
                    MATCH (b:{to_type} {{id: $to_id}})
                    MERGE (a)-[r:{relationship}]->(b)
                    SET r += $properties
                    RETURN r
                    """
                    session.run(query, from_id=from_id, to_id=to_id, properties=properties)
                else:
                    query = f"""
                    MATCH (a:{from_type} {{id: $from_id}})
                    MATCH (b:{to_type} {{id: $to_id}})
                    MERGE (a)-[r:{relationship}]->(b)
                    RETURN r
                    """
                    session.run(query, from_id=from_id, to_id=to_id)

                logger.info(f"🔗 Graph relationship created: {from_type}→{relationship}→{to_type}")
                return True
        except Exception as e:
            logger.error(f"Failed to create graph relationship: {e}")
            return False

    def _create_concept_nodes_and_relationships(
        self,
        node_id: str,
        node_type: str,
        concepts: List[str],
        text: str,
        created_at: str
    ) -> int:
        """
        Create concept nodes and MENTIONS relationships (Phase 6.1)

        Args:
            node_id: Source node ID (Curiosity or Learning)
            node_type: Source node type
            concepts: List of concept strings
            text: Full text for relevance calculation
            created_at: Timestamp

        Returns:
            Number of concepts created
        """
        if not self.graph_driver:
            return 0

        from tools.weaver_graph import weaver_graph

        concepts_created = 0

        try:
            with self.graph_driver.session() as session:
                for concept in concepts:
                    # Format concept name consistently
                    concept_name = weaver_graph.format_concept_name(concept)
                    concept_id = f"concept_{concept_name}"

                    # Calculate relevance score
                    relevance = weaver_graph.calculate_concept_relevance(text, concept)

                    try:
                        # Create or update concept node
                        session.run("""
                            MERGE (c:Concept {id: $concept_id})
                            SET c.name = $concept_name,
                                c.last_seen = $created_at
                            """,
                            concept_id=concept_id,
                            concept_name=concept_name,
                            created_at=created_at
                        )

                        # Create MENTIONS relationship
                        session.run(f"""
                            MATCH (n:{node_type} {{id: $node_id}})
                            MATCH (c:Concept {{id: $concept_id}})
                            MERGE (n)-[r:MENTIONS]->(c)
                            SET r.relevance = $relevance,
                                r.created_at = $created_at
                            """,
                            node_id=node_id,
                            concept_id=concept_id,
                            relevance=relevance,
                            created_at=created_at
                        )

                        concepts_created += 1
                        logger.info(f"🏷️  Concept linked: {concept_name} (relevance: {relevance:.2f})")

                    except Exception as e:
                        logger.warning(f"Failed to create concept {concept_name}: {e}")
                        continue

            logger.info(f"✅ Created {concepts_created} concept nodes and relationships")
            return concepts_created

        except Exception as e:
            logger.error(f"Failed to create concept nodes: {e}")
            return 0

    async def _create_semantic_relationships(
        self,
        node_id: str,
        node_type: str,
        embedding_vector: List[float],
        user_id: str,
        similarity_threshold: float = 0.75,
        max_relationships: int = 3
    ) -> int:
        """
        Create RELATES_TO relationships based on semantic similarity (Phase 6.1)

        Args:
            node_id: Source node ID
            node_type: Source node type (Curiosity or Learning)
            embedding_vector: Embedding vector for similarity search
            user_id: User identifier
            similarity_threshold: Minimum similarity score (0-1)
            max_relationships: Maximum relationships to create

        Returns:
            Number of relationships created
        """
        if not self.graph_driver or not self.qdrant:
            return 0

        relationships_created = 0

        try:
            # Determine collection name based on node type
            collection_name = (
                "curiosity_moments" if node_type == "Curiosity"
                else "learning_reflections"
            )

            # Search for similar nodes in Qdrant
            search_results = self.qdrant.search(
                collection_name=collection_name,
                query_vector=embedding_vector,
                limit=max_relationships + 1,  # +1 because it includes self
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                ),
                score_threshold=similarity_threshold
            )

            # Create relationships to similar nodes
            with self.graph_driver.session() as session:
                for hit in search_results:
                    # Get the related node ID from payload
                    related_id = hit.payload.get(
                        'curiosity_id' if node_type == "Curiosity" else 'learning_id'
                    )

                    # Skip self-reference
                    if related_id == node_id:
                        continue

                    # Skip if we've reached max relationships
                    if relationships_created >= max_relationships:
                        break

                    try:
                        # Create bidirectional RELATES_TO relationship
                        session.run(f"""
                            MATCH (a:{node_type} {{id: $node_id}})
                            MATCH (b:{node_type} {{id: $related_id}})
                            MERGE (a)-[r:RELATES_TO]->(b)
                            SET r.similarity = $similarity,
                                r.created_at = $created_at
                            """,
                            node_id=node_id,
                            related_id=related_id,
                            similarity=float(hit.score),
                            created_at=datetime.now().isoformat()
                        )

                        relationships_created += 1
                        logger.info(f"🔗 Semantic relationship created: {node_id} → {related_id} (similarity: {hit.score:.3f})")

                    except Exception as e:
                        logger.warning(f"Failed to create relationship to {related_id}: {e}")
                        continue

            if relationships_created > 0:
                logger.info(f"✅ Created {relationships_created} semantic relationships")

            return relationships_created

        except Exception as e:
            logger.error(f"Failed to create semantic relationships: {e}")
            return 0

    async def capture_curiosity(
        self,
        discovery: str,
        context: Optional[str] = None,
        feeling: Optional[str] = None,
        user_id: str = "dingo"
    ) -> Dict[str, Any]:
        """
        Capture "Did you know..." moment

        Phase 4: Stores in PostgreSQL for metadata
        Phase 5: Generates embedding and stores in Qdrant for semantic search
        Phase 6: Create graph node in Memgraph for relationships

        Args:
            discovery: What was discovered
            context: Optional context (session, ticket, etc.)
            feeling: How it made you feel
            user_id: User identifier

        Returns:
            Dict with status, id, message, embedding_stored (Phase 5), graph_stored (Phase 6)
        """
        curiosity_id = f"curiosity_{uuid.uuid4().hex[:12]}"

        try:
            # Step 1: Store in PostgreSQL (metadata)
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO curiosity_moments (id, user_id, discovery, context, feeling, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (curiosity_id, user_id, discovery, context, feeling, datetime.now()))

            result = cursor.fetchone()
            conn.commit()

            cursor.close()
            conn.close()

            logger.info(f"✨ Curiosity captured in PostgreSQL: {curiosity_id}")

            # Step 2: Generate embedding and store in Qdrant (Phase 5)
            embedding_stored = False
            embedding_vector = None  # Store for Phase 6.1 semantic relationships
            if self.qdrant and self.embedding:
                try:
                    # Generate embedding
                    embedding_vector = await self.embedding.generate_embedding(
                        text=discovery,
                        prefix="search_document"
                    )

                    if embedding_vector:
                        # Store in Qdrant (use hash of curiosity_id as numeric ID)
                        numeric_id = hash(curiosity_id) & 0x7FFFFFFFFFFFFFFF  # Positive 64-bit integer
                        self.qdrant.upsert(
                            collection_name="curiosity_moments",
                            points=[
                                PointStruct(
                                    id=numeric_id,
                                    vector=embedding_vector,
                                    payload={
                                        "curiosity_id": curiosity_id,  # Store original ID in payload
                                        "user_id": user_id,
                                        "discovery": discovery,
                                        "context": context,
                                        "feeling": feeling,
                                        "created_at": result[1].isoformat()
                                    }
                                )
                            ]
                        )
                        embedding_stored = True
                        logger.info(f"✅ Embedding stored in Qdrant: {curiosity_id} (numeric_id: {numeric_id})")
                    else:
                        logger.warning(f"⚠️  Embedding generation failed for: {curiosity_id}")

                except Exception as e:
                    logger.error(f"❌ Failed to store embedding: {e}")

            # Step 3: Create graph node in Memgraph (Phase 6)
            graph_stored = False
            concepts_created = 0
            relationships_created = 0

            if self.graph_driver:
                # Extract concepts from discovery text
                from tools.weaver_graph import weaver_graph
                concepts = weaver_graph.extract_concepts(discovery)

                graph_properties = {
                    "discovery": discovery,
                    "user_id": user_id,
                    "created_at": result[1].isoformat(),
                }
                if context:
                    graph_properties["context"] = context
                if feeling:
                    graph_properties["feeling"] = feeling
                if concepts:
                    graph_properties["concepts"] = concepts

                graph_stored = self._create_graph_node(
                    node_id=curiosity_id,
                    node_type="Curiosity",
                    properties=graph_properties
                )

                # Phase 6.1: Create concept nodes and MENTIONS relationships
                if graph_stored and concepts:
                    concepts_created = self._create_concept_nodes_and_relationships(
                        node_id=curiosity_id,
                        node_type="Curiosity",
                        concepts=concepts,
                        text=discovery,
                        created_at=result[1].isoformat()
                    )

                # Phase 6.1: Create RELATES_TO relationships based on semantic similarity
                if graph_stored and embedding_stored and embedding_vector:
                    relationships_created = await self._create_semantic_relationships(
                        node_id=curiosity_id,
                        node_type="Curiosity",
                        embedding_vector=embedding_vector,
                        user_id=user_id
                    )

            return {
                'status': 'success',
                'id': result[0],
                'created_at': result[1].isoformat(),
                'embedding_stored': embedding_stored,
                'graph_stored': graph_stored,
                'concepts_created': concepts_created,
                'relationships_created': relationships_created,
                'message': f'Curiosity captured: {discovery[:50]}...'
            }

        except Exception as e:
            logger.error(f"Failed to capture curiosity: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Failed to capture curiosity moment'
            }

    async def capture_learning(
        self,
        reflection: str,
        depth: str = "medium",
        session_context: Optional[str] = None,
        user_id: str = "dingo"
    ) -> Dict[str, Any]:
        """
        Capture "What did I learn today..." reflection

        Phase 4: Stores in PostgreSQL for metadata
        Phase 5: Generate embedding and store in Qdrant for semantic search
        Phase 6: Create graph node in Memgraph and link to related curiosity moments

        Args:
            reflection: What was learned
            depth: Learning depth (surface/medium/deep)
            session_context: Optional session context
            user_id: User identifier

        Returns:
            Dict with status, id, message, embedding_stored, graph_stored
        """
        learning_id = f"learning_{uuid.uuid4().hex[:12]}"

        try:
            # Step 1: Store in PostgreSQL (metadata)
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO learning_reflections (id, user_id, reflection, depth, session_context, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (learning_id, user_id, reflection, depth, session_context, datetime.now()))

            result = cursor.fetchone()
            conn.commit()

            cursor.close()
            conn.close()

            logger.info(f"📚 Learning captured in PostgreSQL: {learning_id}")

            # Step 2: Generate embedding and store in Qdrant (Phase 5)
            embedding_stored = False
            embedding_vector = None  # Store for Phase 6.1 semantic relationships
            if self.qdrant and self.embedding:
                try:
                    embedding_vector = await self.embedding.generate_embedding(
                        text=reflection,
                        prefix="search_document"
                    )

                    if embedding_vector:
                        numeric_id = hash(learning_id) & 0x7FFFFFFFFFFFFFFF
                        self.qdrant.upsert(
                            collection_name="learning_reflections",
                            points=[
                                PointStruct(
                                    id=numeric_id,
                                    vector=embedding_vector,
                                    payload={
                                        "learning_id": learning_id,
                                        "user_id": user_id,
                                        "reflection": reflection,
                                        "depth": depth,
                                        "session_context": session_context,
                                        "created_at": result[1].isoformat()
                                    }
                                )
                            ]
                        )
                        embedding_stored = True
                        logger.info(f"✅ Learning embedding stored in Qdrant: {learning_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to store learning embedding: {e}")

            # Step 3: Create graph node in Memgraph (Phase 6)
            graph_stored = False
            concepts_created = 0
            relationships_created = 0

            if self.graph_driver:
                # Extract concepts from reflection text
                from tools.weaver_graph import weaver_graph
                concepts = weaver_graph.extract_concepts(reflection)

                graph_properties = {
                    "reflection": reflection,
                    "user_id": user_id,
                    "depth": depth,
                    "created_at": result[1].isoformat(),
                }
                if session_context:
                    graph_properties["session_context"] = session_context
                if concepts:
                    graph_properties["concepts"] = concepts

                graph_stored = self._create_graph_node(
                    node_id=learning_id,
                    node_type="Learning",
                    properties=graph_properties
                )

                # Phase 6.1: Create concept nodes and MENTIONS relationships
                if graph_stored and concepts:
                    concepts_created = self._create_concept_nodes_and_relationships(
                        node_id=learning_id,
                        node_type="Learning",
                        concepts=concepts,
                        text=reflection,
                        created_at=result[1].isoformat()
                    )

                # Phase 6.1: Create RELATES_TO relationships based on semantic similarity
                if graph_stored and embedding_stored and embedding_vector:
                    relationships_created = await self._create_semantic_relationships(
                        node_id=learning_id,
                        node_type="Learning",
                        embedding_vector=embedding_vector,
                        user_id=user_id
                    )

            return {
                'status': 'success',
                'id': result[0],
                'created_at': result[1].isoformat(),
                'embedding_stored': embedding_stored,
                'graph_stored': graph_stored,
                'concepts_created': concepts_created,
                'relationships_created': relationships_created,
                'message': f'Learning reflection captured: {reflection[:50]}...'
            }

        except Exception as e:
            logger.error(f"Failed to capture learning: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'message': 'Failed to capture learning reflection'
            }

    async def search_curiosity(
        self,
        query: str,
        limit: int = 5,
        user_id: str = "dingo",
        use_semantic: bool = True
    ) -> Dict[str, Any]:
        """
        Search past curiosity moments

        Phase 4: PostgreSQL text search (ILIKE)
        Phase 5: Qdrant vector search with semantic matching (default)

        Args:
            query: Search query
            limit: Maximum results
            user_id: User identifier
            use_semantic: Use semantic search if True, text search if False

        Returns:
            Dict with status, results, count, search_type
        """
        # Phase 5: Semantic search
        if use_semantic and self.qdrant and self.embedding:
            try:
                # Generate query embedding
                query_embedding = await self.embedding.generate_embedding(
                    text=query,
                    prefix="search_query"
                )

                if not query_embedding:
                    logger.warning("Embedding generation failed, falling back to text search")
                    return await self._search_text(query, limit, user_id)

                # Vector search in Qdrant
                search_results = self.qdrant.search(
                    collection_name="curiosity_moments",
                    query_vector=query_embedding,
                    limit=limit,
                    query_filter=Filter(
                        must=[
                            FieldCondition(
                                key="user_id",
                                match=MatchValue(value=user_id)
                            )
                        ]
                    )
                )

                # Format results
                results = []
                for hit in search_results:
                    results.append({
                        'id': hit.payload.get('curiosity_id', str(hit.id)),  # Use original ID from payload
                        'discovery': hit.payload.get('discovery'),
                        'context': hit.payload.get('context'),
                        'feeling': hit.payload.get('feeling'),
                        'when': hit.payload.get('created_at', '')[:10],
                        'score': round(hit.score, 3)  # Similarity score
                    })

                logger.info(f"🔍 Semantic search found {len(results)} results for: {query}")

                return {
                    'status': 'success',
                    'results': results,
                    'count': len(results),
                    'query': query,
                    'search_type': 'semantic'
                }

            except Exception as e:
                logger.error(f"Qdrant search failed: {e}, falling back to text search")
                return await self._search_text(query, limit, user_id)

        # Phase 4: Text search (fallback or explicit)
        else:
            return await self._search_text(query, limit, user_id)

    async def _search_text(
        self,
        query: str,
        limit: int,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Text-based search using PostgreSQL ILIKE (Phase 4 fallback)

        Args:
            query: Search query
            limit: Maximum results
            user_id: User identifier

        Returns:
            Dict with status, results, count
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, discovery, context, feeling, created_at
                FROM curiosity_moments
                WHERE user_id = %s AND (
                    discovery ILIKE %s OR context ILIKE %s
                )
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, f"%{query}%", f"%{query}%", limit))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'discovery': row[1],
                    'context': row[2],
                    'feeling': row[3],
                    'when': row[4].isoformat()[:10]
                })

            cursor.close()
            conn.close()

            logger.info(f"🔍 Text search found {len(results)} results for: {query}")

            return {
                'status': 'success',
                'results': results,
                'count': len(results),
                'query': query,
                'search_type': 'text'
            }

        except Exception as e:
            logger.error(f"Failed to search curiosity: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'results': [],
                'count': 0
            }

    async def get_timeline(
        self,
        user_id: str = "dingo",
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get recent curiosity and learning timeline

        Args:
            user_id: User identifier
            days: Number of days to look back

        Returns:
            Dict with status, curiosity moments, learning reflections
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get recent curiosity moments
            cursor.execute("""
                SELECT id, discovery, context, feeling, created_at
                FROM curiosity_moments
                WHERE user_id = %s AND created_at > NOW() - INTERVAL '%s days'
                ORDER BY created_at DESC
            """, (user_id, days))

            curiosity = []
            for row in cursor.fetchall():
                curiosity.append({
                    'id': row[0],
                    'discovery': row[1],
                    'context': row[2],
                    'feeling': row[3],
                    'when': row[4].isoformat()
                })

            # Get recent learning reflections
            cursor.execute("""
                SELECT id, reflection, depth, session_context, created_at
                FROM learning_reflections
                WHERE user_id = %s AND created_at > NOW() - INTERVAL '%s days'
                ORDER BY created_at DESC
            """, (user_id, days))

            learning = []
            for row in cursor.fetchall():
                learning.append({
                    'id': row[0],
                    'reflection': row[1],
                    'depth': row[2],
                    'session_context': row[3],
                    'when': row[4].isoformat()
                })

            cursor.close()
            conn.close()

            logger.info(f"📅 Timeline: {len(curiosity)} curiosity, {len(learning)} learning")

            return {
                'status': 'success',
                'curiosity': curiosity,
                'learning': learning,
                'days': days
            }

        except Exception as e:
            logger.error(f"Failed to get timeline: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'curiosity': [],
                'learning': []
            }

    # ========================================================================
    # Phase 6.2: Graph Query Tools
    # ========================================================================

    async def discover_learning_path(
        self,
        start_concept: str,
        end_concept: Optional[str] = None,
        user_id: str = "dingo",
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Discover learning paths between concepts (Phase 6.2)

        Traces how concepts connect through your learning journey.

        Args:
            start_concept: Starting concept
            end_concept: Ending concept (optional - shows all paths if None)
            user_id: User identifier
            max_depth: Maximum path depth

        Returns:
            Dict with status, paths found
        """
        if not self.graph_driver:
            return {
                'status': 'error',
                'error': 'Knowledge graph not available',
                'paths': []
            }

        try:
            with self.graph_driver.session() as session:
                if end_concept:
                    # Find specific path between two concepts
                    query = """
                    MATCH path = (start:Concept {name: $start_concept})<-[:MENTIONS]-(n)-[:MENTIONS]->(end:Concept {name: $end_concept})
                    WHERE n.user_id = $user_id
                    RETURN path, n
                    ORDER BY n.created_at ASC
                    LIMIT 10
                    """
                    result = session.run(query,
                                        start_concept=start_concept,
                                        end_concept=end_concept,
                                        user_id=user_id)
                else:
                    # Find all learning involving this concept
                    query = """
                    MATCH (c:Concept {name: $start_concept})<-[:MENTIONS]-(n)
                    WHERE n.user_id = $user_id
                    RETURN n, labels(n)[0] as type
                    ORDER BY n.created_at ASC
                    """
                    result = session.run(query,
                                        start_concept=start_concept,
                                        user_id=user_id)

                paths = []
                for record in result:
                    node = record['n']
                    node_type = record.get('type', 'Unknown')

                    paths.append({
                        'id': node.get('id'),
                        'type': node_type,
                        'text': node.get('discovery') or node.get('reflection'),
                        'created_at': node.get('created_at'),
                        'concepts': node.get('concepts', [])
                    })

                logger.info(f"🗺️  Found {len(paths)} learning path nodes for: {start_concept}")

                return {
                    'status': 'success',
                    'start_concept': start_concept,
                    'end_concept': end_concept,
                    'paths': paths,
                    'count': len(paths)
                }

        except Exception as e:
            logger.error(f"Failed to discover learning path: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'paths': []
            }

    async def find_concept_clusters(
        self,
        user_id: str = "dingo",
        min_co_occurrence: int = 2,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Find concept clusters (Phase 6.2)

        Discovers concepts that frequently appear together.

        Args:
            user_id: User identifier
            min_co_occurrence: Minimum times concepts must appear together
            limit: Maximum clusters to return

        Returns:
            Dict with status, clusters found
        """
        if not self.graph_driver:
            return {
                'status': 'error',
                'error': 'Knowledge graph not available',
                'clusters': []
            }

        try:
            with self.graph_driver.session() as session:
                query = """
                MATCH (c1:Concept)<-[:MENTIONS]-(n)-[:MENTIONS]->(c2:Concept)
                WHERE c1.id < c2.id AND n.user_id = $user_id
                WITH c1.name as concept1, c2.name as concept2, count(n) as co_occurrences
                WHERE co_occurrences >= $min_co_occurrence
                RETURN concept1, concept2, co_occurrences
                ORDER BY co_occurrences DESC
                LIMIT $limit
                """

                result = session.run(query,
                                    user_id=user_id,
                                    min_co_occurrence=min_co_occurrence,
                                    limit=limit)

                clusters = []
                for record in result:
                    clusters.append({
                        'concept1': record['concept1'],
                        'concept2': record['concept2'],
                        'co_occurrences': record['co_occurrences']
                    })

                logger.info(f"🔍 Found {len(clusters)} concept clusters")

                return {
                    'status': 'success',
                    'clusters': clusters,
                    'count': len(clusters),
                    'min_co_occurrence': min_co_occurrence
                }

        except Exception as e:
            logger.error(f"Failed to find concept clusters: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'clusters': []
            }

    async def find_related_concepts(
        self,
        concept: str,
        user_id: str = "dingo",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Find concepts related to a given concept (Phase 6.2)

        Args:
            concept: Concept to find relations for
            user_id: User identifier
            limit: Maximum related concepts to return

        Returns:
            Dict with status, related concepts
        """
        if not self.graph_driver:
            return {
                'status': 'error',
                'error': 'Knowledge graph not available',
                'related': []
            }

        try:
            with self.graph_driver.session() as session:
                # Find concepts that co-occur with the given concept
                query = """
                MATCH (c1:Concept {name: $concept})<-[:MENTIONS]-(n)-[:MENTIONS]->(c2:Concept)
                WHERE n.user_id = $user_id AND c1.id <> c2.id
                RETURN c2.name as related_concept, count(n) as strength
                ORDER BY strength DESC
                LIMIT $limit
                """

                result = session.run(query,
                                    concept=concept,
                                    user_id=user_id,
                                    limit=limit)

                related = []
                for record in result:
                    related.append({
                        'concept': record['related_concept'],
                        'strength': record['strength']
                    })

                logger.info(f"🔗 Found {len(related)} concepts related to: {concept}")

                return {
                    'status': 'success',
                    'concept': concept,
                    'related': related,
                    'count': len(related)
                }

        except Exception as e:
            logger.error(f"Failed to find related concepts: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'related': []
            }

    async def trace_concept_evolution(
        self,
        concept: str,
        user_id: str = "dingo"
    ) -> Dict[str, Any]:
        """
        Trace how your understanding of a concept evolved over time (Phase 6.2)

        Args:
            concept: Concept to trace
            user_id: User identifier

        Returns:
            Dict with status, timeline of captures mentioning this concept
        """
        if not self.graph_driver:
            return {
                'status': 'error',
                'error': 'Knowledge graph not available',
                'timeline': []
            }

        try:
            with self.graph_driver.session() as session:
                query = """
                MATCH (c:Concept {name: $concept})<-[:MENTIONS]-(n)
                WHERE n.user_id = $user_id
                RETURN n, labels(n)[0] as type
                ORDER BY n.created_at ASC
                """

                result = session.run(query,
                                    concept=concept,
                                    user_id=user_id)

                timeline = []
                for record in result:
                    node = record['n']
                    node_type = record['type']

                    timeline.append({
                        'id': node.get('id'),
                        'type': node_type,
                        'text': node.get('discovery') or node.get('reflection'),
                        'created_at': node.get('created_at'),
                        'context': node.get('context') or node.get('session_context')
                    })

                logger.info(f"📅 Traced {len(timeline)} moments in evolution of: {concept}")

                return {
                    'status': 'success',
                    'concept': concept,
                    'timeline': timeline,
                    'count': len(timeline),
                    'first_seen': timeline[0]['created_at'] if timeline else None,
                    'last_seen': timeline[-1]['created_at'] if timeline else None
                }

        except Exception as e:
            logger.error(f"Failed to trace concept evolution: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timeline': []
            }

    # ========================================================================
    # Phase 6.3: Advanced Graph Algorithms
    # ========================================================================

    async def calculate_concept_importance(
        self,
        user_id: str = "dingo",
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Calculate concept importance using graph algorithms (Phase 6.3)

        Delegates to weaver_graph_algorithms for advanced algorithms.
        """
        from tools.weaver_graph_algorithms import weaver_graph_algorithms
        return await weaver_graph_algorithms.calculate_concept_importance(
            user_id=user_id,
            limit=limit
        )

    async def detect_topic_communities(
        self,
        user_id: str = "dingo",
        min_community_size: int = 2
    ) -> Dict[str, Any]:
        """
        Detect topic communities (Phase 6.3)

        Delegates to weaver_graph_algorithms for community detection.
        """
        from tools.weaver_graph_algorithms import weaver_graph_algorithms
        return await weaver_graph_algorithms.detect_topic_communities(
            user_id=user_id,
            min_community_size=min_community_size
        )

    async def find_shortest_learning_path(
        self,
        start_concept: str,
        end_concept: str,
        user_id: str = "dingo",
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Find shortest learning path between concepts (Phase 6.3)

        Delegates to weaver_graph_algorithms for shortest path algorithm.
        """
        from tools.weaver_graph_algorithms import weaver_graph_algorithms
        return await weaver_graph_algorithms.find_shortest_learning_path(
            start_concept=start_concept,
            end_concept=end_concept,
            user_id=user_id,
            max_depth=max_depth
        )

    async def calculate_concept_centrality(
        self,
        user_id: str = "dingo",
        limit: int = 20,
        metric: str = "betweenness"
    ) -> Dict[str, Any]:
        """
        Calculate concept centrality metrics (Phase 6.3)

        Delegates to weaver_graph_algorithms for centrality calculations.
        """
        from tools.weaver_graph_algorithms import weaver_graph_algorithms
        return await weaver_graph_algorithms.calculate_concept_centrality(
            user_id=user_id,
            limit=limit,
            metric=metric
        )

    # ========================================================================
    # Phase 6.4: Graph Visualization
    # ========================================================================

    async def export_graph_cytoscape(
        self,
        user_id: str = "dingo",
        include_style: bool = True,
        max_nodes: int = 100
    ) -> Dict[str, Any]:
        """
        Export graph to Cytoscape.js JSON format (Phase 6.4)

        Delegates to weaver_visualization for export.
        """
        from tools.weaver_visualization import weaver_visualization
        return await weaver_visualization.export_graph_cytoscape(
            user_id=user_id,
            include_style=include_style,
            max_nodes=max_nodes
        )

    async def export_graph_graphviz(
        self,
        user_id: str = "dingo",
        layout: str = "dot",
        max_nodes: int = 100,
        min_edge_weight: int = 2
    ) -> Dict[str, Any]:
        """
        Export graph to Graphviz DOT format (Phase 6.4)

        Delegates to weaver_visualization for export.
        """
        from tools.weaver_visualization import weaver_visualization
        return await weaver_visualization.export_graph_graphviz(
            user_id=user_id,
            layout=layout,
            max_nodes=max_nodes,
            min_edge_weight=min_edge_weight
        )

    async def export_graph_d3(
        self,
        user_id: str = "dingo",
        max_nodes: int = 100
    ) -> Dict[str, Any]:
        """
        Export graph to D3.js JSON format (Phase 6.4)

        Delegates to weaver_visualization for export.
        """
        from tools.weaver_visualization import weaver_visualization
        return await weaver_visualization.export_graph_d3(
            user_id=user_id,
            max_nodes=max_nodes
        )

    async def generate_graph_stats(
        self,
        user_id: str = "dingo"
    ) -> Dict[str, Any]:
        """
        Generate comprehensive graph statistics (Phase 6.4)

        Delegates to weaver_visualization for statistics generation.
        """
        from tools.weaver_visualization import weaver_visualization
        return await weaver_visualization.generate_graph_stats(
            user_id=user_id
        )

    # ========================================================================
    # Phase 6.5: Learning Insights
    # ========================================================================

    async def identify_knowledge_gaps(
        self,
        user_id: str = "dingo",
        min_mentions: int = 2,
        max_connections: int = 3,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Identify knowledge gaps (Phase 6.5)

        Delegates to weaver_insights for gap identification.
        """
        from tools.weaver_insights import weaver_insights
        return await weaver_insights.identify_knowledge_gaps(
            user_id=user_id,
            min_mentions=min_mentions,
            max_connections=max_connections,
            limit=limit
        )

    async def suggest_learning_topics(
        self,
        user_id: str = "dingo",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Suggest learning topics (Phase 6.5)

        Delegates to weaver_insights for topic suggestions.
        """
        from tools.weaver_insights import weaver_insights
        return await weaver_insights.suggest_learning_topics(
            user_id=user_id,
            limit=limit
        )

    async def track_learning_velocity(
        self,
        user_id: str = "dingo",
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Track learning velocity (Phase 6.5)

        Delegates to weaver_insights for velocity tracking.
        """
        from tools.weaver_insights import weaver_insights
        return await weaver_insights.track_learning_velocity(
            user_id=user_id,
            time_window_days=time_window_days
        )

    async def predict_interests(
        self,
        user_id: str = "dingo",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Predict future interests (Phase 6.5)

        Delegates to weaver_insights for interest predictions.
        """
        from tools.weaver_insights import weaver_insights
        return await weaver_insights.predict_interests(
            user_id=user_id,
            limit=limit
        )


# ============================================================================
# MCP Tool Wrappers
# ============================================================================

class CaptureCuriosityTool(SimpleTool):
    """
    MCP tool for capturing curiosity moments

    Enables CLI agents to capture "Did you know..." moments during sessions.
    """

    def __init__(self):
        super().__init__()
        self.weaver = WeaverToolsSimple()

    def get_name(self) -> str:
        return "capture_curiosity"

    def get_description(self) -> str:
        return (
            "Capture a curiosity moment ('Did you know...'). "
            "Use this when you discover something interesting during a session. "
            "Stores the discovery for future reference and learning."
        )

    def get_request_model(self):
        return CaptureCuriosityRequest

    async def prepare_prompt(self, arguments: Dict[str, Any]) -> tuple[str, list]:
        """Execute curiosity capture and return confirmation"""
        discovery = arguments.get("discovery", "")
        context = arguments.get("context")
        feeling = arguments.get("feeling")
        user_id = arguments.get("user_id", "dingo")

        result = await self.weaver.capture_curiosity(
            discovery=discovery,
            context=context,
            feeling=feeling,
            user_id=user_id
        )

        if result['status'] == 'success':
            storage_status = []
            if result.get('embedding_stored'):
                storage_status.append("✅ Semantic search enabled")
            if result.get('graph_stored'):
                storage_status.append("✅ Knowledge graph node created")

            # Phase 6.1 status
            concepts_count = result.get('concepts_created', 0)
            relationships_count = result.get('relationships_created', 0)
            if concepts_count > 0:
                storage_status.append(f"🏷️  {concepts_count} concept(s) linked")
            if relationships_count > 0:
                storage_status.append(f"🔗 {relationships_count} relationship(s) created")

            status_line = " | ".join(storage_status) if storage_status else "✅ Stored"

            prompt = f"""✨ Curiosity Captured!

**Discovery**: {discovery}
**Context**: {context or 'No context provided'}
**Feeling**: {feeling or 'Not specified'}
**ID**: {result['id']}
**Time**: {result['created_at']}
**Storage**: {status_line}

This moment has been preserved in your Weaver knowledge base.
You can search for it later using the search_curiosity tool.

No further action needed - just confirming the capture."""
        else:
            prompt = f"""❌ Failed to capture curiosity moment

**Error**: {result.get('error', 'Unknown error')}
**Discovery**: {discovery}

Please check the database connection and try again."""

        return prompt, []


class CaptureLearningTool(SimpleTool):
    """
    MCP tool for capturing learning reflections

    Enables CLI agents to capture "What did I learn today..." reflections.
    """

    def __init__(self):
        super().__init__()
        self.weaver = WeaverToolsSimple()

    def get_name(self) -> str:
        return "capture_learning"

    def get_description(self) -> str:
        return (
            "Capture a learning reflection ('What did I learn today...'). "
            "Use this at the end of sessions to reflect on what was learned. "
            "Stores the reflection for future reference and pattern recognition."
        )

    def get_request_model(self):
        return CaptureLearningRequest

    async def prepare_prompt(self, arguments: Dict[str, Any]) -> tuple[str, list]:
        """Execute learning capture and return confirmation"""
        reflection = arguments.get("reflection", "")
        depth = arguments.get("depth", "medium")
        session_context = arguments.get("session_context")
        user_id = arguments.get("user_id", "dingo")

        result = await self.weaver.capture_learning(
            reflection=reflection,
            depth=depth,
            session_context=session_context,
            user_id=user_id
        )

        if result['status'] == 'success':
            storage_status = []
            if result.get('embedding_stored'):
                storage_status.append("✅ Semantic search enabled")
            if result.get('graph_stored'):
                storage_status.append("✅ Knowledge graph node created")

            # Phase 6.1 status
            concepts_count = result.get('concepts_created', 0)
            relationships_count = result.get('relationships_created', 0)
            if concepts_count > 0:
                storage_status.append(f"🏷️  {concepts_count} concept(s) linked")
            if relationships_count > 0:
                storage_status.append(f"🔗 {relationships_count} relationship(s) created")

            status_line = " | ".join(storage_status) if storage_status else "✅ Stored"

            prompt = f"""📚 Learning Reflection Captured!

**Reflection**: {reflection}
**Depth**: {depth}
**Context**: {session_context or 'No context provided'}
**ID**: {result['id']}
**Time**: {result['created_at']}
**Storage**: {status_line}

This learning has been preserved in your Weaver knowledge base.
Over time, patterns will emerge showing your growth and learning journey.

No further action needed - just confirming the capture."""
        else:
            prompt = f"""❌ Failed to capture learning reflection

**Error**: {result.get('error', 'Unknown error')}
**Reflection**: {reflection}

Please check the database connection and try again."""

        return prompt, []


class SearchCuriosityTool(SimpleTool):
    """
    MCP tool for searching past curiosity moments

    Enables CLI agents to search and retrieve past discoveries.
    """

    def __init__(self):
        super().__init__()
        self.weaver = WeaverToolsSimple()

    def get_name(self) -> str:
        return "search_curiosity"

    def get_description(self) -> str:
        return (
            "Search past curiosity moments and learning reflections. "
            "Use this to find related past discoveries when working on similar topics. "
            "Helps connect current work with past learning."
        )

    def get_request_model(self):
        return SearchCuriosityRequest

    async def prepare_prompt(self, arguments: Dict[str, Any]) -> tuple[str, list]:
        """Execute search and return formatted results"""
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        user_id = arguments.get("user_id", "dingo")

        result = await self.weaver.search_curiosity(
            query=query,
            limit=limit,
            user_id=user_id
        )

        if result['status'] == 'success' and result['count'] > 0:
            lines = [f"🔍 Found {result['count']} past curiosity moments for: {query}\n"]

            for i, item in enumerate(result['results'], 1):
                lines.append(f"**{i}. [{item['when']}]** {item['discovery']}")
                if item.get('context'):
                    lines.append(f"   Context: {item['context']}")
                if item.get('feeling'):
                    lines.append(f"   Feeling: {item['feeling']}")
                lines.append("")

            prompt = "\n".join(lines)
            prompt += "\nUse these past insights to inform your current work."

        elif result['status'] == 'success':
            prompt = f"🔍 No curiosity moments found for: {query}\n\nTry a different search term or capture new discoveries as you work."
        else:
            prompt = f"❌ Search failed: {result.get('error', 'Unknown error')}"

        return prompt, []


# ============================================================================
# Exports
# ============================================================================

# Export for direct import in other modules
weaver_tools = WeaverToolsSimple()

# Export MCP tool classes for registration
__all__ = [
    "WeaverToolsSimple",
    "CaptureCuriosityTool",
    "CaptureLearningTool",
    "SearchCuriosityTool",
    "weaver_tools",
]

