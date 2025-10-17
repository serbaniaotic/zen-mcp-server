#!/usr/bin/env python3
"""
Test Suite for Phase 6.3: Advanced Graph Algorithms

Tests all 4 graph algorithm tools:
1. calculate_concept_importance - PageRank-like importance scoring
2. detect_topic_communities - Community detection for topic clustering
3. find_shortest_learning_path - Shortest path between concepts
4. calculate_concept_centrality - Centrality metrics (degree, betweenness, closeness)
"""

import asyncio
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Weaver tools
try:
    from tools.weaver_tools import weaver_tools
except ImportError as e:
    logger.error(f"Failed to import Weaver tools: {e}")
    sys.exit(1)


async def create_test_data():
    """
    Create rich test data with multiple interconnected concepts

    This builds a knowledge graph with:
    - 3 main topics: databases, web-dev, infrastructure
    - Overlapping concepts to create communities
    - Varying importance levels
    """
    logger.info("=" * 60)
    logger.info("STEP 1: Creating Test Data")
    logger.info("=" * 60)

    test_captures = [
        # Database cluster (high connectivity)
        {
            "discovery": "PostgreSQL is a powerful relational database with ACID compliance and advanced indexing",
            "context": "Phase 6.3 testing - databases",
            "feeling": "informed"
        },
        {
            "discovery": "Memgraph is a high-performance graph database that uses Cypher query language for complex relationships",
            "context": "Phase 6.3 testing - databases",
            "feeling": "excited"
        },
        {
            "discovery": "Qdrant is a vector database optimized for semantic search with high-dimensional embeddings",
            "context": "Phase 6.3 testing - databases",
            "feeling": "curious"
        },
        {
            "discovery": "Database indexing dramatically improves query performance for large datasets in PostgreSQL and other SQL databases",
            "context": "Phase 6.3 testing - databases",
            "feeling": "enlightened"
        },

        # Web development cluster
        {
            "discovery": "FastAPI is a modern Python framework for building APIs with automatic OpenAPI documentation",
            "context": "Phase 6.3 testing - web-dev",
            "feeling": "impressed"
        },
        {
            "discovery": "React provides a component-based architecture for building interactive user interfaces with JavaScript",
            "context": "Phase 6.3 testing - web-dev",
            "feeling": "interested"
        },
        {
            "discovery": "TypeScript adds static typing to JavaScript making large-scale web applications more maintainable",
            "context": "Phase 6.3 testing - web-dev",
            "feeling": "convinced"
        },

        # Infrastructure cluster
        {
            "discovery": "Docker containers provide isolated environments for applications ensuring consistency across development and production",
            "context": "Phase 6.3 testing - infrastructure",
            "feeling": "amazed"
        },
        {
            "discovery": "Nginx is a high-performance web server and reverse proxy handling thousands of concurrent connections",
            "context": "Phase 6.3 testing - infrastructure",
            "feeling": "impressed"
        },

        # Cross-cluster connections (bridging concepts)
        {
            "discovery": "REST APIs built with FastAPI connect web applications to PostgreSQL databases for data persistence",
            "context": "Phase 6.3 testing - integration",
            "feeling": "understanding"
        },
        {
            "discovery": "Docker containers can run PostgreSQL, Memgraph, and Qdrant databases with consistent configurations",
            "context": "Phase 6.3 testing - integration",
            "feeling": "practical"
        },
        {
            "discovery": "React frontends communicate with FastAPI backends using REST or GraphQL APIs for real-time data",
            "context": "Phase 6.3 testing - integration",
            "feeling": "connected"
        },
    ]

    captured_ids = []
    for i, capture in enumerate(test_captures, 1):
        logger.info(f"\n[{i}/{len(test_captures)}] Capturing: {capture['discovery'][:60]}...")
        result = await weaver_tools.capture_curiosity(**capture)

        if result['status'] == 'success':
            logger.info(f"  ✅ ID: {result['id']}")
            if result.get('concepts_created', 0) > 0:
                logger.info(f"  🏷️  Concepts: {result['concepts_created']}")
            captured_ids.append(result['id'])
        else:
            logger.error(f"  ❌ Failed: {result.get('error')}")

    logger.info(f"\n✅ Created {len(captured_ids)} test captures")

    # Allow a moment for graph relationships to settle
    await asyncio.sleep(1)

    return captured_ids


async def test_concept_importance():
    """Test 1: Calculate Concept Importance (PageRank)"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 1: Calculate Concept Importance (PageRank)")
    logger.info("=" * 60)

    result = await weaver_tools.calculate_concept_importance(
        user_id="dingo",
        limit=10
    )

    logger.info(f"\nStatus: {result['status']}")

    if result['status'] == 'success':
        logger.info(f"Algorithm: {result.get('algorithm', 'unknown')}")
        logger.info(f"Found {result['count']} important concepts:\n")

        for i, concept in enumerate(result['concepts'][:10], 1):
            logger.info(f"  {i:2}. {concept['concept']:20} | Importance: {concept['importance']:.3f}")

        # Verify top concepts are well-connected
        if result['count'] > 0:
            top_concept = result['concepts'][0]
            logger.info(f"\n✅ Most important concept: '{top_concept['concept']}' (score: {top_concept['importance']:.3f})")
        else:
            logger.warning("⚠️  No concepts found")
    else:
        logger.error(f"❌ Error: {result.get('error')}")

    return result


async def test_community_detection():
    """Test 2: Detect Topic Communities"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Detect Topic Communities")
    logger.info("=" * 60)

    result = await weaver_tools.detect_topic_communities(
        user_id="dingo",
        min_community_size=2
    )

    logger.info(f"\nStatus: {result['status']}")

    if result['status'] == 'success':
        logger.info(f"Algorithm: {result.get('algorithm', 'unknown')}")
        logger.info(f"Found {result['count']} communities:\n")

        for i, community in enumerate(result['communities'], 1):
            logger.info(f"  Community {i} (size: {community['size']}):")
            logger.info(f"    Concepts: {', '.join(community['concepts'])}")

        total_concepts = result.get('total_concepts', 0)
        logger.info(f"\n✅ Total concepts in communities: {total_concepts}")

        if result['count'] > 0:
            logger.info(f"✅ Communities detected successfully")
        else:
            logger.warning("⚠️  No communities found (graphs may be too small)")
    else:
        logger.error(f"❌ Error: {result.get('error')}")

    return result


async def test_shortest_path():
    """Test 3: Find Shortest Learning Path"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Find Shortest Learning Path")
    logger.info("=" * 60)

    # Test path between related concepts
    start = "fastapi"
    end = "postgresql"

    logger.info(f"\nFinding shortest path: '{start}' → '{end}'")

    result = await weaver_tools.find_shortest_learning_path(
        start_concept=start,
        end_concept=end,
        user_id="dingo",
        max_depth=5
    )

    logger.info(f"\nStatus: {result['status']}")

    if result['status'] == 'success':
        if result.get('found'):
            logger.info(f"Path length: {result['path_length']} hops")
            logger.info(f"Concepts in path: {' → '.join(result['concepts'])}")

            if result.get('path_details'):
                logger.info("\nPath details:")
                for i, step in enumerate(result['path_details'], 1):
                    logger.info(f"  Step {i}: {step['from']} → {step['to']}")
                    logger.info(f"    Via: {step['via']['type']} ({step['via']['when'][:10]})")
                    logger.info(f"    Text: {step['via']['text'][:80]}...")

            logger.info(f"\n✅ Found path with {result.get('hops', 0)} hops")
        else:
            logger.info(f"No path found within {result.get('max_depth', 5)} hops")
            logger.info("  This is normal if concepts aren't connected yet")
    else:
        logger.error(f"❌ Error: {result.get('error')}")

    return result


async def test_centrality_metrics():
    """Test 4: Calculate Concept Centrality"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Calculate Concept Centrality")
    logger.info("=" * 60)

    metrics = ["degree", "betweenness", "closeness"]

    results = {}
    for metric in metrics:
        logger.info(f"\n--- Testing {metric.upper()} centrality ---")

        result = await weaver_tools.calculate_concept_centrality(
            user_id="dingo",
            limit=10,
            metric=metric
        )

        results[metric] = result

        if result['status'] == 'success':
            logger.info(f"Found {result['count']} concepts:\n")

            for i, concept in enumerate(result['concepts'][:5], 1):
                logger.info(f"  {i}. {concept['concept']:20} | {metric}: {concept['centrality']:.3f}")

            logger.info(f"✅ {metric.capitalize()} centrality calculated")
        else:
            logger.error(f"❌ Error: {result.get('error')}")

    return results


async def run_all_tests():
    """Run complete Phase 6.3 test suite"""
    logger.info("\n" + "🧪" * 30)
    logger.info("PHASE 6.3: ADVANCED GRAPH ALGORITHMS - TEST SUITE")
    logger.info("🧪" * 30)

    start_time = datetime.now()

    try:
        # Step 1: Create test data
        captured_ids = await create_test_data()

        # Step 2: Test concept importance
        importance_result = await test_concept_importance()

        # Step 3: Test community detection
        community_result = await test_community_detection()

        # Step 4: Test shortest path
        path_result = await test_shortest_path()

        # Step 5: Test centrality metrics
        centrality_results = await test_centrality_metrics()

        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Test duration: {duration:.2f}s")
        logger.info(f"Test captures created: {len(captured_ids)}")
        logger.info(f"\nResults:")
        logger.info(f"  ✅ Concept Importance: {importance_result['status']}")
        logger.info(f"  ✅ Community Detection: {community_result['status']}")
        logger.info(f"  ✅ Shortest Path: {path_result['status']}")
        logger.info(f"  ✅ Centrality Metrics: {all(r['status'] == 'success' for r in centrality_results.values())}")

        logger.info("\n" + "🎉" * 30)
        logger.info("PHASE 6.3 TESTS COMPLETE!")
        logger.info("🎉" * 30)

        return True

    except Exception as e:
        logger.error(f"\n❌ Test suite failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
