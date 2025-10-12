#!/usr/bin/env python3
"""
Demo script for Intelligent Routing in Zen MCP Server.
Shows how the router analyzes queries and suggests optimal tools.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from routing import IntelligentRouter
from utils.analytics import ZenAnalytics


def demo_basic_routing():
    """Demo basic routing without analytics"""
    print("\n" + "=" * 70)
    print("DEMO 1: Basic Routing (No Analytics)")
    print("=" * 70)
    
    router = IntelligentRouter()
    
    queries = [
        "What is Python?",
        "Review my code for security vulnerabilities",
        "Debug a memory leak in our payment processing system",
        "Critical decision: Should we deploy to production now?",
        "Investigate why the distributed database is slow",
        "Plan a new microservices architecture",
    ]
    
    for query in queries:
        print(f"\n{'─' * 70}")
        print(f"Query: {query}")
        print(f"{'─' * 70}")
        
        decision = router.route_request(query)
        
        print(f"🎯 Recommended Tool: {decision.tool}")
        print(f"📋 Strategy: {decision.strategy.value}")
        print(f"📊 Complexity: {decision.complexity}/10")
        print(f"⚠️  Risk: {decision.risk}/10")
        print(f"🎲 Confidence: {decision.confidence:.0%}")
        print(f"💡 Intent: {decision.intent}")
        print(f"📝 Reasoning: {decision.reasoning}")
        
        if decision.alternative_tools:
            print(f"🔄 Alternatives: {', '.join(decision.alternative_tools)}")


def demo_routing_with_analytics():
    """Demo routing with analytics integration"""
    print("\n" + "=" * 70)
    print("DEMO 2: Routing with Analytics")
    print("=" * 70)
    
    # Initialize analytics
    analytics = ZenAnalytics()
    
    # Add some historical data
    print("\n📊 Adding historical data...")
    
    # Simulate successful code review executions
    for _ in range(5):
        analytics.log_tool_execution(
            tool_name="codereview",
            model="gpt-5",
            tokens_used=2000,
            execution_time_ms=3000,
            success=True
        )
    
    # Log routing decisions
    analytics.log_routing_decision(
        user_intent="Review code for issues",
        chosen_tool="codereview",
        chosen_strategy="SOLO",
        detected_complexity=5,
        detected_risk=4,
        outcome="success"
    )
    
    print("   ✅ Historical data added")
    
    # Create router with analytics
    router = IntelligentRouter(analytics=analytics)
    
    # Test routing with historical data
    query = "Review my code for potential bugs"
    print(f"\n{'─' * 70}")
    print(f"Query: {query}")
    print(f"{'─' * 70}")
    
    decision = router.route_request(query)
    
    print(f"🎯 Recommended Tool: {decision.tool}")
    print(f"📋 Strategy: {decision.strategy.value}")
    print(f"📊 Complexity: {decision.complexity}/10")
    print(f"⚠️  Risk: {decision.risk}/10")
    print(f"🎲 Confidence: {decision.confidence:.0%}")
    print(f"💡 Reasoning: {decision.reasoning}")
    
    # Show analytics summary
    print(f"\n📈 Analytics Summary:")
    summary = analytics.get_summary_stats(days=7)
    print(f"   Total executions: {summary['total_executions']}")
    print(f"   Success rate: {summary['success_rate']:.1%}")
    print(f"   Most used tool: {summary['most_used_tool']}")
    
    analytics.close()


def demo_routing_suggestions():
    """Demo human-readable routing suggestions"""
    print("\n" + "=" * 70)
    print("DEMO 3: Routing Suggestions")
    print("=" * 70)
    
    router = IntelligentRouter()
    
    queries = [
        "Help me understand how async/await works in Python",
        "Critical production bug: Payment system is charging customers twice",
        "Design a scalable architecture for real-time analytics",
    ]
    
    for query in queries:
        print(f"\n{'─' * 70}")
        print(f"Query: {query}")
        print(f"{'─' * 70}")
        
        suggestion = router.get_routing_suggestion(query)
        print(suggestion)


def demo_context_and_files():
    """Demo routing with context and files"""
    print("\n" + "=" * 70)
    print("DEMO 4: Routing with Context and Files")
    print("=" * 70)
    
    router = IntelligentRouter()
    
    # Test with files
    query = "Review these files for security issues"
    files = [
        "auth/login.py",
        "auth/middleware.py",
        "api/payments.py",
    ]
    context = {
        "environment": "production",
        "multi_step": True,
    }
    
    print(f"\nQuery: {query}")
    print(f"Files: {files}")
    print(f"Context: {context}")
    print(f"\n{'─' * 70}")
    
    decision = router.route_request(query, context=context, files=files)
    
    print(f"🎯 Recommended Tool: {decision.tool}")
    print(f"📋 Strategy: {decision.strategy.value}")
    print(f"📊 Complexity: {decision.complexity}/10 (files add complexity)")
    print(f"⚠️  Risk: {decision.risk}/10 (production environment increases risk)")
    print(f"💡 Reasoning: {decision.reasoning}")


def demo_manual_overrides():
    """Demo manual tool overrides"""
    print("\n" + "=" * 70)
    print("DEMO 5: Manual Overrides")
    print("=" * 70)
    
    router = IntelligentRouter()
    
    query = "What is Python?"
    
    # Normal routing
    print(f"\nQuery: {query}")
    print(f"\n1️⃣  Normal Routing:")
    decision1 = router.route_request(query)
    print(f"   Tool: {decision1.tool}")
    print(f"   Reasoning: {decision1.reasoning}")
    
    # Override to thinkdeep
    print(f"\n2️⃣  With Override (thinkdeep):")
    decision2 = router.route_request(query, override_tool="thinkdeep")
    print(f"   Tool: {decision2.tool}")
    print(f"   Reasoning: {decision2.reasoning}")


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("INTELLIGENT ROUTING DEMONSTRATION")
    print("Zen MCP Server - Phase 2")
    print("=" * 70)
    
    try:
        demo_basic_routing()
        demo_routing_with_analytics()
        demo_routing_suggestions()
        demo_context_and_files()
        demo_manual_overrides()
        
        print("\n" + "=" * 70)
        print("✅ All demos completed successfully!")
        print("=" * 70)
        
        print("\n💡 Integration Instructions:")
        print("   To integrate with server.py, import RouterIntegration:")
        print("   ")
        print("   from routing import get_router_integration")
        print("   ")
        print("   router = get_router_integration()")
        print("   ")
        print("   # Log tool execution")
        print("   router.log_tool_execution(tool_name, model, tokens, time_ms, success)")
        print("   ")
        print("   # Get routing suggestion")
        print("   suggestion = router.get_routing_suggestion(user_query, context, files)")
        print("")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

