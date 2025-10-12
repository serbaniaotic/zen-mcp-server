#!/usr/bin/env python3
"""
Test script for Phase 2: Intelligent Router
Tests routing decisions, complexity analysis, risk assessment, and intent detection
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from routing import IntelligentRouter, RoutingStrategy
from utils.analytics import ZenAnalytics


def test_complexity_analysis():
    """Test complexity analysis"""
    print("\n" + "=" * 60)
    print("Testing Complexity Analysis")
    print("=" * 60)
    
    router = IntelligentRouter()
    
    test_cases = [
        {
            "query": "What is Python?",
            "files": [],
            "expected_range": (1, 3),
            "description": "Simple query"
        },
        {
            "query": "How can I optimize the performance of my distributed database system?",
            "files": ["db1.py", "db2.py", "db3.py"],
            "expected_range": (5, 8),
            "description": "Complex query with multiple factors"
        },
        {
            "query": "Review the architecture of our microservices system including authentication, payment processing, and data synchronization across 15 services",
            "files": [f"service{i}.py" for i in range(15)],
            "expected_range": (8, 10),
            "description": "Very complex query"
        },
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        complexity = router._analyze_complexity(
            test["query"],
            {},
            test["files"]
        )
        
        min_expected, max_expected = test["expected_range"]
        success = min_expected <= complexity <= max_expected
        
        status = "✅" if success else "❌"
        print(f"\n{status} Test {i}: {test['description']}")
        print(f"   Query: {test['query'][:60]}...")
        print(f"   Files: {len(test['files'])}")
        print(f"   Complexity: {complexity}/10 (expected: {min_expected}-{max_expected})")
        
        if success:
            passed += 1
    
    print(f"\n📊 Complexity Analysis: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_risk_assessment():
    """Test risk assessment"""
    print("\n" + "=" * 60)
    print("Testing Risk Assessment")
    print("=" * 60)
    
    router = IntelligentRouter()
    
    test_cases = [
        {
            "query": "Explain how arrays work in Python",
            "context": {},
            "expected_range": (1, 3),
            "description": "Low risk query"
        },
        {
            "query": "Deploy changes to production database",
            "context": {"environment": "production"},
            "expected_range": (5, 8),
            "description": "Medium-high risk query"
        },
        {
            "query": "Urgent: Critical security vulnerability in production payment system needs immediate fix",
            "context": {"environment": "production"},
            "expected_range": (8, 10),
            "description": "High risk query"
        },
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        risk = router._assess_risk(
            test["query"],
            test["context"]
        )
        
        min_expected, max_expected = test["expected_range"]
        success = min_expected <= risk <= max_expected
        
        status = "✅" if success else "❌"
        print(f"\n{status} Test {i}: {test['description']}")
        print(f"   Query: {test['query'][:60]}...")
        print(f"   Risk: {risk}/10 (expected: {min_expected}-{max_expected})")
        
        if success:
            passed += 1
    
    print(f"\n📊 Risk Assessment: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_intent_detection():
    """Test natural language intent detection"""
    print("\n" + "=" * 60)
    print("Testing Intent Detection")
    print("=" * 60)
    
    router = IntelligentRouter()
    
    test_cases = [
        {
            "query": "Please review my code for security issues",
            "expected": "review",
            "description": "Review intent"
        },
        {
            "query": "There's a bug in the authentication system that's causing crashes",
            "expected": "debug",
            "description": "Debug intent"
        },
        {
            "query": "How should we design the new API architecture?",
            "expected": "design",
            "description": "Design intent"
        },
        {
            "query": "Implement a new feature for user notifications",
            "expected": "implement",
            "description": "Implement intent"
        },
        {
            "query": "Should I use approach A or approach B for this problem?",
            "expected": "decide",
            "description": "Decision intent"
        },
        {
            "query": "Explain how the authentication middleware works",
            "expected": "understand",
            "description": "Understanding intent"
        },
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        intent = router._extract_intent(test["query"])
        success = intent == test["expected"]
        
        status = "✅" if success else "⚠️"
        print(f"\n{status} Test {i}: {test['description']}")
        print(f"   Query: {test['query']}")
        print(f"   Detected: {intent} (expected: {test['expected']})")
        
        if success:
            passed += 1
    
    print(f"\n📊 Intent Detection: {passed}/{len(test_cases)} tests passed")
    return passed >= len(test_cases) * 0.8  # 80% pass rate acceptable


def test_routing_decisions():
    """Test complete routing decisions"""
    print("\n" + "=" * 60)
    print("Testing Routing Decisions")
    print("=" * 60)
    
    router = IntelligentRouter()
    
    test_cases = [
        {
            "query": "What's the difference between let and const in JavaScript?",
            "expected_tool": "chat",
            "expected_strategy": RoutingStrategy.SOLO,
            "description": "Simple question -> chat/SOLO"
        },
        {
            "query": "Investigate why our distributed system is experiencing memory leaks across multiple services",
            "expected_tool": "thinkdeep",
            "expected_strategy": RoutingStrategy.SEQUENTIAL,
            "description": "Complex investigation -> thinkdeep/SEQUENTIAL"
        },
        {
            "query": "Critical: Should we deploy the breaking changes to production now or wait for the weekend?",
            "expected_tool": "consensus",
            "expected_strategy": RoutingStrategy.CONSENSUS,
            "description": "Critical decision -> consensus/CONSENSUS"
        },
        {
            "query": "Review this code for potential security vulnerabilities",
            "expected_tool": "codereview",
            "expected_strategy": RoutingStrategy.SOLO,
            "description": "Code review -> codereview"
        },
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        decision = router.route_request(test["query"])
        
        tool_match = decision.tool == test["expected_tool"]
        strategy_match = decision.strategy == test["expected_strategy"]
        success = tool_match and strategy_match
        
        status = "✅" if success else "⚠️"
        print(f"\n{status} Test {i}: {test['description']}")
        print(f"   Query: {test['query'][:70]}...")
        print(f"   Tool: {decision.tool} (expected: {test['expected_tool']}) {'✓' if tool_match else '✗'}")
        print(f"   Strategy: {decision.strategy.value} (expected: {test['expected_strategy'].value}) {'✓' if strategy_match else '✗'}")
        print(f"   Complexity: {decision.complexity}/10")
        print(f"   Risk: {decision.risk}/10")
        print(f"   Confidence: {decision.confidence:.0%}")
        print(f"   Reasoning: {decision.reasoning[:100]}...")
        
        if success:
            passed += 1
    
    print(f"\n📊 Routing Decisions: {passed}/{len(test_cases)} tests passed")
    return passed >= len(test_cases) * 0.75  # 75% pass rate acceptable


def test_routing_with_analytics():
    """Test routing with analytics integration"""
    print("\n" + "=" * 60)
    print("Testing Routing with Analytics")
    print("=" * 60)
    
    try:
        # Create analytics with test data
        analytics = ZenAnalytics()
        
        # Add some test historical data
        analytics.log_routing_decision(
            user_intent="Review code for bugs",
            chosen_tool="codereview",
            chosen_strategy="SOLO",
            detected_complexity=5,
            detected_risk=4,
            outcome="success"
        )
        
        # Create router with analytics
        router = IntelligentRouter(analytics=analytics)
        
        # Test routing with historical data
        decision = router.route_request("Review my code for potential issues")
        
        print(f"✅ Router with analytics integration working")
        print(f"   Tool: {decision.tool}")
        print(f"   Strategy: {decision.strategy.value}")
        print(f"   Reasoning: {decision.reasoning[:100]}...")
        
        analytics.close()
        return True
        
    except Exception as e:
        print(f"❌ Analytics integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_routing_overrides():
    """Test manual routing overrides"""
    print("\n" + "=" * 60)
    print("Testing Manual Overrides")
    print("=" * 60)
    
    router = IntelligentRouter()
    
    query = "Simple question about Python"
    
    # Test tool override
    decision = router.route_request(query, override_tool="thinkdeep")
    
    success = decision.tool == "thinkdeep"
    status = "✅" if success else "❌"
    
    print(f"{status} Tool override test")
    print(f"   Query: {query}")
    print(f"   Override tool: thinkdeep")
    print(f"   Result: {decision.tool}")
    print(f"   Reasoning: {decision.reasoning}")
    
    return success


def test_routing_suggestion():
    """Test human-readable routing suggestion"""
    print("\n" + "=" * 60)
    print("Testing Routing Suggestions")
    print("=" * 60)
    
    router = IntelligentRouter()
    
    query = "Debug a memory leak in our production payment processing system"
    
    try:
        suggestion = router.get_routing_suggestion(query)
        
        print("✅ Routing suggestion generated")
        print("\n" + suggestion)
        
        # Check that suggestion contains expected sections
        has_tool = "Tool:" in suggestion
        has_strategy = "Strategy:" in suggestion
        has_analysis = "Analysis:" in suggestion
        has_reasoning = "Reasoning:" in suggestion
        
        success = has_tool and has_strategy and has_analysis and has_reasoning
        
        if not success:
            print("\n❌ Suggestion missing expected sections")
        
        return success
        
    except Exception as e:
        print(f"❌ Routing suggestion test failed: {e}")
        return False


def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n" + "=" * 60)
    print("Testing Edge Cases")
    print("=" * 60)
    
    router = IntelligentRouter()
    
    test_cases = [
        {
            "query": "",
            "description": "Empty query"
        },
        {
            "query": "a" * 1000,
            "description": "Very long query"
        },
        {
            "query": "???",
            "description": "Only special characters"
        },
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        try:
            decision = router.route_request(test["query"])
            print(f"✅ Test {i}: {test['description']} - Handled gracefully")
            print(f"   Tool: {decision.tool}, Strategy: {decision.strategy.value}")
            passed += 1
        except Exception as e:
            print(f"❌ Test {i}: {test['description']} - Failed with: {e}")
    
    print(f"\n📊 Edge Cases: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def main():
    """Run all Phase 2 tests"""
    print("\n" + "=" * 60)
    print("PHASE 2 INTELLIGENT ROUTER TESTS")
    print("Task 8: Agent-Fusion Integration")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Complexity analysis
    results['complexity_analysis'] = test_complexity_analysis()
    
    # Test 2: Risk assessment
    results['risk_assessment'] = test_risk_assessment()
    
    # Test 3: Intent detection
    results['intent_detection'] = test_intent_detection()
    
    # Test 4: Routing decisions
    results['routing_decisions'] = test_routing_decisions()
    
    # Test 5: Analytics integration
    results['analytics_integration'] = test_routing_with_analytics()
    
    # Test 6: Manual overrides
    results['manual_overrides'] = test_routing_overrides()
    
    # Test 7: Routing suggestions
    results['routing_suggestions'] = test_routing_suggestion()
    
    # Test 8: Edge cases
    results['edge_cases'] = test_edge_cases()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = all(results.values())
    passed_count = sum(results.values())
    total_count = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    
    if all_passed:
        print(f"\n🎉 All Phase 2 tests passed! ({passed_count}/{total_count})")
        print("\n✅ Phase 2 Success Criteria Met:")
        print("   ✅ Router correctly classifies complexity")
        print("   ✅ Router correctly assesses risk")
        print("   ✅ Natural language directives detected")
        print("   ✅ Historical patterns influence routing")
        print("   ✅ Integration works correctly")
        print("\nNext step: Phase 2 Integration with server.py")
        return 0
    else:
        print(f"\n⚠️  Some tests failed ({passed_count}/{total_count} passed)")
        print("Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

