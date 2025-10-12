#!/usr/bin/env python3
"""
Test script for Phase 1: Database Setup + DuckDB Installation
Tests Postgres connection and DuckDB analytics functionality
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import psycopg2
from utils.analytics import ZenAnalytics


def test_postgres_connection():
    """Test Postgres connection"""
    print("\n" + "=" * 60)
    print("Testing Postgres Connection")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5434,
            database="zendb",
            user="zen",
            password="zenpass"
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        print(f"✅ Postgres connection successful!")
        print(f"   Version: {version[:50]}...")
        
        # Test database info
        cursor.execute("SELECT current_database(), current_user;")
        db, user = cursor.fetchone()
        print(f"   Database: {db}")
        print(f"   User: {user}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Postgres connection failed: {e}")
        return False


def test_duckdb_analytics():
    """Test DuckDB analytics functionality"""
    print("\n" + "=" * 60)
    print("Testing DuckDB Analytics")
    print("=" * 60)
    
    try:
        # Initialize analytics
        analytics = ZenAnalytics()
        print(f"✅ DuckDB analytics initialized")
        print(f"   Database: {analytics.db_path}")
        
        # Test logging tool execution
        print("\n📊 Testing tool execution logging...")
        exec_id = analytics.log_tool_execution(
            tool_name="chat",
            model="gemini-2.5-pro",
            tokens_used=1500,
            execution_time_ms=2500,
            success=True,
            status="completed",
            metadata={"test": "phase1", "type": "verification"}
        )
        print(f"   ✅ Logged execution: {exec_id[:8]}...")
        
        # Test logging routing decision
        print("\n🧭 Testing routing decision logging...")
        decision_id = analytics.log_routing_decision(
            user_intent="Test the analytics system",
            chosen_tool="chat",
            chosen_strategy="SOLO",
            detected_complexity=3,
            detected_risk=2,
            outcome="success",
            metadata={"test": "phase1"}
        )
        print(f"   ✅ Logged routing decision: {decision_id[:8]}...")
        
        # Add more sample data for testing
        print("\n📈 Adding sample data...")
        for i in range(5):
            analytics.log_tool_execution(
                tool_name=["chat", "thinkdeep", "debug", "codereview", "consensus"][i],
                model=["gemini-2.5-pro", "gpt-5", "claude-4", "grok", "gemini-2.5-pro"][i],
                tokens_used=1000 + (i * 500),
                execution_time_ms=1000 + (i * 1000),
                success=True,
                status="completed"
            )
        print(f"   ✅ Added 5 sample executions")
        
        # Test getting tool performance
        print("\n📊 Testing analytics queries...")
        performance = analytics.get_tool_performance(days=7)
        print(f"   ✅ Tool performance records: {len(performance)}")
        
        if performance:
            print(f"\n   Top performing tool:")
            top = performance[0]
            print(f"   - Tool: {top['tool_name']}")
            print(f"   - Model: {top['model']}")
            print(f"   - Executions: {top['total_executions']}")
            print(f"   - Success rate: {top['success_rate']:.1%}")
            if top['avg_tokens']:
                print(f"   - Avg tokens: {top['avg_tokens']:.0f}")
        
        # Test summary statistics
        print("\n📈 Testing summary statistics...")
        summary = analytics.get_summary_stats(days=7)
        print(f"   ✅ Summary generated:")
        print(f"   - Total executions: {summary['total_executions']}")
        print(f"   - Success rate: {summary['success_rate']:.1%}")
        print(f"   - Most used tool: {summary['most_used_tool']}")
        print(f"   - Total tokens: {summary['total_tokens_used']:.0f}")
        
        # Test getting best tool recommendation
        print("\n🎯 Testing tool recommendation...")
        best_tool = analytics.get_best_tool_for(
            intent="test",
            complexity=3,
            risk=2,
            days=7
        )
        if best_tool:
            print(f"   ✅ Recommendation found:")
            print(f"   - Tool: {best_tool['tool']}")
            print(f"   - Strategy: {best_tool['strategy']}")
            print(f"   - Success rate: {best_tool['success_rate']:.1%}")
        else:
            print(f"   ℹ️  No recommendation (need more data)")
        
        # Test model performance update
        print("\n🔄 Testing model performance update...")
        analytics.update_model_performance()
        print(f"   ✅ Model performance aggregations updated")
        
        analytics.close()
        print(f"\n✅ All DuckDB analytics tests passed!")
        
        return True
        
    except Exception as e:
        print(f"❌ DuckDB analytics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_postgres_schema_creation():
    """Test creating task queue schema in Postgres"""
    print("\n" + "=" * 60)
    print("Testing Postgres Schema Creation")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5434,
            database="zendb",
            user="zen",
            password="zenpass"
        )
        
        cursor = conn.cursor()
        
        # Create task_queue table (for Phase 3, but good to test now)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_queue (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                task_type VARCHAR NOT NULL,
                status VARCHAR NOT NULL DEFAULT 'pending',
                assigned_to VARCHAR,
                priority INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP,
                data JSONB NOT NULL,
                result JSONB
            );
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_status ON task_queue(status);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_assigned ON task_queue(assigned_to);
        """)
        
        conn.commit()
        
        print(f"✅ task_queue table created successfully")
        
        # Verify table exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        print(f"   Tables in database: {[t[0] for t in tables]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Postgres schema creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 1 tests"""
    print("\n" + "=" * 60)
    print("PHASE 1 DATABASE SETUP TESTS")
    print("Task 8: Agent-Fusion Integration")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Postgres connection
    results['postgres_connection'] = test_postgres_connection()
    time.sleep(1)
    
    # Test 2: Postgres schema creation
    results['postgres_schema'] = test_postgres_schema_creation()
    time.sleep(1)
    
    # Test 3: DuckDB analytics
    results['duckdb_analytics'] = test_duckdb_analytics()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All Phase 1 tests passed!")
        print("\n✅ Phase 1 Success Criteria Met:")
        print("   ✅ Postgres running and accessible")
        print("   ✅ DuckDB installed in zen venv")
        print("   ✅ Analytics schema created")
        print("   ✅ Basic analytics.py module working")
        print("\nNext step: Phase 2 - Intelligent Router")
        return 0
    else:
        print("\n❌ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

