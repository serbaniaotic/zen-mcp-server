"""
Weaver Learning Insights (Phase 6.5)

Intelligent learning recommendations and analysis:
- Knowledge gap identification
- Learning topic suggestions
- Learning velocity tracking
- Interest pattern predictions
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

# Try to import Memgraph driver and database modules
try:
    from neo4j import GraphDatabase
    MEMGRAPH_AVAILABLE = True
except ImportError:
    MEMGRAPH_AVAILABLE = False
    logger.warning("Memgraph driver not available for Phase 6.5")

try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("PostgreSQL driver not available for Phase 6.5")


class WeaverInsights:
    """
    Learning insights and recommendations

    Analyzes knowledge graph and learning history to provide:
    - Knowledge gaps (under-explored concepts)
    - Topic recommendations
    - Learning velocity metrics
    - Interest predictions
    """

    def __init__(
        self,
        memgraph_uri: str = "bolt://zeoin:7687",
        postgres_host: str = "zeoin",
        postgres_port: int = 5433,
        postgres_db: str = "weaver",
        postgres_user: str = "weaver",
        postgres_password: str = "weaver"
    ):
        """Initialize insights with database connections"""
        self.memgraph_uri = memgraph_uri
        self.memgraph_driver = None
        self.postgres_config = {
            'host': postgres_host,
            'port': postgres_port,
            'database': postgres_db,
            'user': postgres_user,
            'password': postgres_password
        }

        # Initialize Memgraph
        if MEMGRAPH_AVAILABLE:
            try:
                self.memgraph_driver = GraphDatabase.driver(memgraph_uri, auth=None)
                with self.memgraph_driver.session() as session:
                    session.run("RETURN 1 as test")
                logger.info("✅ Learning insights enabled (Memgraph connected)")
            except Exception as e:
                logger.warning(f"⚠️  Memgraph connection failed: {e}")
                self.memgraph_driver = None
        else:
            logger.info("ℹ️  Phase 6.5 disabled: Memgraph not available")

    def __del__(self):
        """Close database connections"""
        if self.memgraph_driver:
            self.memgraph_driver.close()

    # ========================================================================
    # 1. Knowledge Gap Identification
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

        Finds concepts that are:
        - Mentioned multiple times (showing interest)
        - But have few connections to other concepts (under-explored)

        These are topics you've touched on but haven't fully integrated
        into your knowledge graph.

        Args:
            user_id: User identifier
            min_mentions: Minimum mentions to consider
            max_connections: Maximum connections to qualify as "gap"
            limit: Maximum gaps to return

        Returns:
            Dict with identified knowledge gaps
        """
        if not self.memgraph_driver:
            return {
                'status': 'error',
                'error': 'Learning insights not available',
                'gaps': []
            }

        try:
            with self.memgraph_driver.session() as session:
                # Find concepts with mentions but few connections
                query = """
                MATCH (c:Concept)<-[:MENTIONS]-(n)
                WHERE n.user_id = $user_id
                WITH c, count(n) as mention_count
                WHERE mention_count >= $min_mentions

                OPTIONAL MATCH (c)<-[:MENTIONS]-(n1)-[:MENTIONS]->(c2:Concept)
                WHERE n1.user_id = $user_id AND c.id <> c2.id
                WITH c, mention_count, count(DISTINCT c2) as connection_count
                WHERE connection_count <= $max_connections

                RETURN c.name as concept,
                       mention_count,
                       connection_count,
                       toFloat(mention_count) / (toFloat(connection_count) + 1) as gap_score
                ORDER BY gap_score DESC
                LIMIT $limit
                """

                result = session.run(query,
                                   user_id=user_id,
                                   min_mentions=min_mentions,
                                   max_connections=max_connections,
                                   limit=limit)

                gaps = []
                for record in result:
                    gaps.append({
                        'concept': record['concept'],
                        'mentions': record['mention_count'],
                        'connections': record['connection_count'],
                        'gap_score': round(float(record['gap_score']), 2),
                        'recommendation': 'Explore connections to related topics'
                    })

                logger.info(f"🔍 Identified {len(gaps)} knowledge gaps")

                return {
                    'status': 'success',
                    'gaps': gaps,
                    'count': len(gaps),
                    'criteria': {
                        'min_mentions': min_mentions,
                        'max_connections': max_connections
                    }
                }

        except Exception as e:
            logger.error(f"Failed to identify knowledge gaps: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'gaps': []
            }

    # ========================================================================
    # 2. Learning Topic Suggestions
    # ========================================================================

    async def suggest_learning_topics(
        self,
        user_id: str = "dingo",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Suggest learning topics based on your current knowledge (Phase 6.5)

        Finds concepts that:
        - Are connected to what you already know
        - But you haven't explored yet
        - Are frequently co-mentioned in the graph

        Args:
            user_id: User identifier
            limit: Maximum suggestions to return

        Returns:
            Dict with topic suggestions and rationale
        """
        if not self.memgraph_driver:
            return {
                'status': 'error',
                'error': 'Learning insights not available',
                'suggestions': []
            }

        try:
            with self.memgraph_driver.session() as session:
                # Find concepts you know
                known_query = """
                MATCH (c:Concept)<-[:MENTIONS]-(n)
                WHERE n.user_id = $user_id
                RETURN collect(DISTINCT c.name) as known_concepts
                """
                known_result = session.run(known_query, user_id=user_id)
                known_concepts = known_result.single()['known_concepts']

                if not known_concepts:
                    return {
                        'status': 'success',
                        'suggestions': [],
                        'message': 'No learning history yet to base suggestions on'
                    }

                # Find concepts connected to what you know, but you haven't explored
                suggestions_query = """
                // Find concepts you already know
                MATCH (known:Concept)<-[:MENTIONS]-(n1)
                WHERE n1.user_id = $user_id AND known.name IN $known_concepts

                // Find concepts connected to what you know
                MATCH (known)<-[:MENTIONS]-(bridge)-[:MENTIONS]->(suggested:Concept)
                WHERE NOT suggested.name IN $known_concepts

                // Count how many of your known concepts connect to this suggestion
                WITH suggested, count(DISTINCT known) as relevance_score, collect(DISTINCT known.name) as related_to

                RETURN suggested.name as concept,
                       relevance_score,
                       related_to[..3] as sample_related_concepts
                ORDER BY relevance_score DESC
                LIMIT $limit
                """

                result = session.run(suggestions_query,
                                   user_id=user_id,
                                   known_concepts=known_concepts,
                                   limit=limit)

                suggestions = []
                for record in result:
                    suggestions.append({
                        'concept': record['concept'],
                        'relevance': record['relevance_score'],
                        'related_to': record['sample_related_concepts'],
                        'rationale': f"Connects to {record['relevance_score']} concepts you know"
                    })

                logger.info(f"💡 Generated {len(suggestions)} learning suggestions")

                return {
                    'status': 'success',
                    'suggestions': suggestions,
                    'count': len(suggestions),
                    'known_concepts_count': len(known_concepts)
                }

        except Exception as e:
            logger.error(f"Failed to suggest learning topics: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'suggestions': []
            }

    # ========================================================================
    # 3. Learning Velocity Tracking
    # ========================================================================

    async def track_learning_velocity(
        self,
        user_id: str = "dingo",
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Track learning velocity over time (Phase 6.5)

        Measures:
        - Captures per day/week
        - New concepts per week
        - Learning streak
        - Acceleration trends

        Args:
            user_id: User identifier
            time_window_days: Days to analyze (default 30)

        Returns:
            Dict with velocity metrics and trends
        """
        if not POSTGRES_AVAILABLE:
            return {
                'status': 'error',
                'error': 'PostgreSQL not available for velocity tracking',
                'metrics': {}
            }

        try:
            conn = await asyncpg.connect(**self.postgres_config)

            try:
                # Get captures in time window
                cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)

                captures_query = """
                SELECT
                    DATE(created_at) as capture_date,
                    COUNT(*) as captures_count
                FROM curiosity_moments
                WHERE user_id = $1 AND created_at >= $2
                GROUP BY DATE(created_at)
                ORDER BY capture_date ASC
                """
                captures = await conn.fetch(captures_query, user_id, cutoff_date)

                # Calculate metrics
                total_captures = sum(row['captures_count'] for row in captures)
                capture_days = len(captures)

                if capture_days == 0:
                    return {
                        'status': 'success',
                        'metrics': {
                            'message': 'No activity in the specified time window'
                        }
                    }

                avg_per_day = total_captures / max(time_window_days, 1)

                # Find streak (consecutive days)
                if captures:
                    streak = 1
                    for i in range(1, len(captures)):
                        prev_date = captures[i-1]['capture_date']
                        curr_date = captures[i]['capture_date']
                        diff = (curr_date - prev_date).days
                        if diff == 1:
                            streak += 1
                        else:
                            break
                else:
                    streak = 0

                # Calculate weekly trends
                weeks = defaultdict(int)
                for row in captures:
                    week = row['capture_date'].isocalendar()[1]
                    weeks[week] += row['captures_count']

                week_counts = list(weeks.values())

                # Velocity trend (comparing first half to second half)
                if len(week_counts) >= 2:
                    mid = len(week_counts) // 2
                    first_half_avg = sum(week_counts[:mid]) / mid
                    second_half_avg = sum(week_counts[mid:]) / (len(week_counts) - mid)
                    velocity_change = ((second_half_avg - first_half_avg) / max(first_half_avg, 1)) * 100

                    if velocity_change > 10:
                        trend = "accelerating"
                    elif velocity_change < -10:
                        trend = "slowing"
                    else:
                        trend = "steady"
                else:
                    velocity_change = 0
                    trend = "insufficient_data"

                logger.info(f"📈 Learning velocity: {avg_per_day:.1f} captures/day")

                return {
                    'status': 'success',
                    'metrics': {
                        'time_window_days': time_window_days,
                        'total_captures': total_captures,
                        'active_days': capture_days,
                        'avg_captures_per_day': round(avg_per_day, 2),
                        'current_streak_days': streak,
                        'velocity_trend': trend,
                        'velocity_change_percent': round(velocity_change, 1),
                        'weekly_breakdown': {
                            f'week_{k}': v for k, v in weeks.items()
                        }
                    }
                }

            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"Failed to track learning velocity: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'metrics': {}
            }

    # ========================================================================
    # 4. Interest Pattern Predictions
    # ========================================================================

    async def predict_interests(
        self,
        user_id: str = "dingo",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Predict future interests based on learning patterns (Phase 6.5)

        Analyzes:
        - Concept progression patterns
        - Community expansion trends
        - Related topic discovery

        Args:
            user_id: User identifier
            limit: Maximum predictions to return

        Returns:
            Dict with predicted interests and confidence scores
        """
        if not self.memgraph_driver:
            return {
                'status': 'error',
                'error': 'Learning insights not available',
                'predictions': []
            }

        try:
            with self.memgraph_driver.session() as session:
                # Find concepts you've recently explored
                recent_query = """
                MATCH (c:Concept)<-[:MENTIONS]-(n)
                WHERE n.user_id = $user_id
                WITH c, max(n.created_at) as last_mentioned
                ORDER BY last_mentioned DESC
                LIMIT 10
                RETURN collect(c.name) as recent_concepts
                """
                recent_result = session.run(recent_query, user_id=user_id)
                recent_concepts = recent_result.single()['recent_concepts']

                if not recent_concepts:
                    return {
                        'status': 'success',
                        'predictions': [],
                        'message': 'Insufficient learning history for predictions'
                    }

                # Find concepts that frequently co-occur with recent interests
                # but you haven't explored yet
                predictions_query = """
                // Your recent interests
                MATCH (recent:Concept)<-[:MENTIONS]-(n1)
                WHERE n1.user_id = $user_id AND recent.name IN $recent_concepts

                // Find what others explore alongside your recent interests
                MATCH (recent)<-[:MENTIONS]-(shared_moment)-[:MENTIONS]->(predicted:Concept)
                WHERE NOT predicted.name IN $recent_concepts

                // Count co-occurrence strength
                WITH predicted, count(DISTINCT recent) as overlap_score

                // Calculate prediction confidence
                RETURN predicted.name as concept,
                       overlap_score,
                       toFloat(overlap_score) / toFloat($recent_count) as confidence
                ORDER BY confidence DESC, overlap_score DESC
                LIMIT $limit
                """

                result = session.run(predictions_query,
                                   user_id=user_id,
                                   recent_concepts=recent_concepts,
                                   recent_count=len(recent_concepts),
                                   limit=limit)

                predictions = []
                for record in result:
                    confidence = float(record['confidence'])
                    predictions.append({
                        'concept': record['concept'],
                        'confidence': round(confidence, 2),
                        'overlap_score': record['overlap_score'],
                        'rationale': f"Strongly related to {record['overlap_score']} of your recent interests"
                    })

                logger.info(f"🔮 Generated {len(predictions)} interest predictions")

                return {
                    'status': 'success',
                    'predictions': predictions,
                    'count': len(predictions),
                    'based_on_recent': len(recent_concepts)
                }

        except Exception as e:
            logger.error(f"Failed to predict interests: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'predictions': []
            }


# ============================================================================
# Export
# ============================================================================

# Global instance
weaver_insights = WeaverInsights()

__all__ = [
    "WeaverInsights",
    "weaver_insights",
]
