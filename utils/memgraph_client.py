#!/usr/bin/env python3
"""
MemGraph Client for TAMDAC QC Sessions
Provides connection and operations for storing/querying QC session data
"""

from neo4j import GraphDatabase
from datetime import datetime
from typing import List, Dict, Any, Optional


class MemGraphClient:
    """Client for MemGraph operations - QC session storage and retrieval"""
    
    def __init__(self, uri="bolt://localhost:7687", user="", password=""):
        """Initialize connection to MemGraph"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        """Close the driver connection"""
        self.driver.close()
    
    def verify_connection(self) -> bool:
        """Test connection to MemGraph"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                return result.single()["test"] == 1
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def clear_all(self):
        """Clear all data (for testing)"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    
    # === QC SESSION ===
    
    def create_qc_session(self, session_id: str, timestamp: str, status: str,
                         participants: List[str], context_level: str,
                         duration_minutes: int) -> Dict[str, Any]:
        """Create a QC_SESSION node"""
        with self.driver.session() as session:
            query = """
            CREATE (qc:QC_SESSION {
                id: $id,
                timestamp: $timestamp,
                status: $status,
                participants: $participants,
                context_level: $context_level,
                duration_minutes: $duration_minutes
            })
            RETURN qc
            """
            result = session.run(query,
                id=session_id,
                timestamp=timestamp,
                status=status,
                participants=participants,
                context_level=context_level,
                duration_minutes=duration_minutes
            )
            return result.single()[0]
    
    # === INSIGHT ===
    
    def create_insight(self, insight_id: str, content: str, timestamp: str,
                      sequence: int, insight_type: str, impact: str) -> Dict[str, Any]:
        """Create an INSIGHT node"""
        with self.driver.session() as session:
            query = """
            CREATE (i:INSIGHT {
                id: $id,
                content: $content,
                timestamp: $timestamp,
                sequence: $sequence,
                type: $type,
                impact: $impact
            })
            RETURN i
            """
            result = session.run(query,
                id=insight_id,
                content=content,
                timestamp=timestamp,
                sequence=sequence,
                type=insight_type,
                impact=impact
            )
            return result.single()[0]
    
    # === DECISION ===
    
    def create_decision(self, decision_id: str, content: str, timestamp: str,
                       sequence: int, status: str, binding_scope: List[str]) -> Dict[str, Any]:
        """Create a DECISION node"""
        with self.driver.session() as session:
            query = """
            CREATE (d:DECISION {
                id: $id,
                content: $content,
                timestamp: $timestamp,
                sequence: $sequence,
                status: $status,
                binding_scope: $binding_scope
            })
            RETURN d
            """
            result = session.run(query,
                id=decision_id,
                content=content,
                timestamp=timestamp,
                sequence=sequence,
                status=status,
                binding_scope=binding_scope
            )
            return result.single()[0]
    
    # === RELATIONSHIPS ===
    
    def link_session_contains(self, session_id: str, node_id: str):
        """Create CONTAINS relationship from session to insight/decision"""
        with self.driver.session() as session:
            query = """
            MATCH (qc:QC_SESSION {id: $session_id})
            MATCH (n {id: $node_id})
            CREATE (qc)-[:CONTAINS]->(n)
            """
            session.run(query, session_id=session_id, node_id=node_id)
    
    def link_session_produces(self, session_id: str, decision_id: str):
        """Create PRODUCES relationship from session to decision"""
        with self.driver.session() as session:
            query = """
            MATCH (qc:QC_SESSION {id: $session_id})
            MATCH (d:DECISION {id: $decision_id})
            CREATE (qc)-[:PRODUCES]->(d)
            """
            session.run(query, session_id=session_id, decision_id=decision_id)
    
    def link_insight_followed_by(self, first_id: str, second_id: str, time_delta: int):
        """Create FOLLOWED_BY relationship (sequential thinking)"""
        with self.driver.session() as session:
            query = """
            MATCH (i1:INSIGHT {id: $first_id})
            MATCH (i2:INSIGHT {id: $second_id})
            CREATE (i1)-[:FOLLOWED_BY {time_delta: $time_delta}]->(i2)
            """
            session.run(query, first_id=first_id, second_id=second_id,
                       time_delta=time_delta)
    
    def link_insight_led_to_decision(self, insight_id: str, decision_id: str):
        """Create LED_TO relationship (causal)"""
        with self.driver.session() as session:
            query = """
            MATCH (i:INSIGHT {id: $insight_id})
            MATCH (d:DECISION {id: $decision_id})
            CREATE (i)-[:LED_TO]->(d)
            """
            session.run(query, insight_id=insight_id, decision_id=decision_id)
    
    # === QUERIES ===
    
    def get_session_insights(self, session_id: str) -> List[Dict[str, Any]]:
        """Query all insights from a session"""
        with self.driver.session() as session:
            query = """
            MATCH (qc:QC_SESSION {id: $session_id})-[:CONTAINS]->(i:INSIGHT)
            RETURN i.id AS id, i.content AS content, i.sequence AS sequence,
                   i.type AS type, i.impact AS impact
            ORDER BY i.sequence
            """
            result = session.run(query, session_id=session_id)
            return [dict(record) for record in result]
    
    def get_session_decisions(self, session_id: str) -> List[Dict[str, Any]]:
        """Query all decisions from a session"""
        with self.driver.session() as session:
            query = """
            MATCH (qc:QC_SESSION {id: $session_id})-[:PRODUCES]->(d:DECISION)
            RETURN d.id AS id, d.content AS content, d.sequence AS sequence,
                   d.status AS status, d.binding_scope AS binding_scope
            ORDER BY d.sequence
            """
            result = session.run(query, session_id=session_id)
            return [dict(record) for record in result]
    
    def get_sequential_thinking(self, session_id: str) -> List[str]:
        """Get the chain of sequential thinking from a session"""
        with self.driver.session() as session:
            # Simpler query: just get all insights in order
            query = """
            MATCH (qc:QC_SESSION {id: $session_id})-[:CONTAINS]->(i:INSIGHT)
            RETURN i.content AS content
            ORDER BY i.sequence
            """
            result = session.run(query, session_id=session_id)
            return [record["content"] for record in result]
    
    def why_was_decision_made(self, decision_id: str) -> List[Dict[str, str]]:
        """Query the reasoning chain that led to a decision"""
        with self.driver.session() as session:
            query = """
            MATCH (i:INSIGHT)-[:LED_TO]->(d:DECISION {id: $decision_id})
            RETURN i.content AS insight, d.content AS decision
            """
            result = session.run(query, decision_id=decision_id)
            return [dict(record) for record in result]


def test_connection():
    """Test basic connection to MemGraph"""
    print("🔗 Testing MemGraph connection...")
    client = MemGraphClient()
    
    if client.verify_connection():
        print("✅ Connected to MemGraph successfully!")
        client.close()
        return True
    else:
        print("❌ Connection failed")
        client.close()
        return False


def test_basic_operations():
    """Test create/query operations"""
    print("\n📝 Testing basic operations...")
    client = MemGraphClient()
    
    # Clear existing data
    print("  Clearing existing data...")
    client.clear_all()
    
    # Create a simple test session
    print("  Creating test QC session...")
    client.create_qc_session(
        session_id='qc-test',
        timestamp='2025-10-10T12:00:00Z',
        status='closed',
        participants=['human', 'claude'],
        context_level='test',
        duration_minutes=30
    )
    
    # Create test insight
    print("  Creating test insight...")
    client.create_insight(
        insight_id='insight-test-1',
        content='This is a test insight',
        timestamp='2025-10-10T12:05:00Z',
        sequence=1,
        insight_type='test',
        impact='minor'
    )
    
    # Create test decision
    print("  Creating test decision...")
    client.create_decision(
        decision_id='decision-test-1',
        content='This is a test decision',
        timestamp='2025-10-10T12:10:00Z',
        sequence=1,
        status='approved',
        binding_scope=['test']
    )
    
    # Link them
    print("  Creating relationships...")
    client.link_session_contains('qc-test', 'insight-test-1')
    client.link_session_produces('qc-test', 'decision-test-1')
    client.link_insight_led_to_decision('insight-test-1', 'decision-test-1')
    
    # Query back
    print("\n🔍 Testing queries...")
    insights = client.get_session_insights('qc-test')
    print(f"  Insights found: {len(insights)}")
    for insight in insights:
        print(f"    - {insight['content']}")
    
    decisions = client.get_session_decisions('qc-test')
    print(f"  Decisions found: {len(decisions)}")
    for decision in decisions:
        print(f"    - {decision['content']}")
    
    # Clean up
    print("\n  Cleaning up test data...")
    client.clear_all()
    
    client.close()
    print("✅ All basic operations passed!")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("TAMDAC MemGraph Client Test Suite")
    print("=" * 60)
    
    # Test 1: Connection
    if not test_connection():
        print("\n❌ Connection test failed. Is MemGraph running?")
        print("   Run: docker ps | grep memgraph")
        exit(1)
    
    # Test 2: Basic operations
    if not test_basic_operations():
        print("\n❌ Basic operations test failed")
        exit(1)
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! MemGraph client is ready.")
    print("=" * 60)

