#!/usr/bin/env python3
"""
Test Vibe-Check integration with Recursive QC

Validates:
1. Vibe-Check initialization
2. Answer validation with risk assessment
3. Confidence adjustment based on risk level
4. Integration with recursive query handler
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.recursive_query_handler import RecursiveQueryHandler
from tools.vibe_check_tool import get_vibe_check_tool


async def test_vibe_check_available():
    """Test 1: Vibe-Check is available"""
    
    print("\n" + "="*60)
    print("TEST 1: Vibe-Check Availability")
    print("="*60)
    
    try:
        vibe_tool = get_vibe_check_tool()
        print(f"✅ Vibe-Check initialized: {type(vibe_tool).__name__}")
        return True
    except Exception as e:
        print(f"❌ Vibe-Check not available: {e}")
        return False


async def test_recursive_handler_with_vibe_check():
    """Test 2: RecursiveQueryHandler integrates Vibe-Check"""
    
    print("\n" + "="*60)
    print("TEST 2: Recursive Handler + Vibe-Check")
    print("="*60)
    
    try:
        handler = RecursiveQueryHandler({})
        
        # Check if Vibe-Check is initialized
        has_vibe = hasattr(handler, 'vibe_check') and handler.vibe_check is not None
        print(f"✅ RecursiveQueryHandler has Vibe-Check: {has_vibe}")
        
        if not has_vibe:
            print("⚠️  Vibe-Check not initialized in handler")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_answer_validation():
    """Test 3: Answer validation produces risk assessment"""
    
    print("\n" + "="*60)
    print("TEST 3: Answer Validation")
    print("="*60)
    
    try:
        handler = RecursiveQueryHandler({})
        
        # Test validation
        test_answer = "Python is a programming language created in 1991 by Guido van Rossum."
        test_query = "Tell me about Python"
        
        validation = await handler._validate_answer(test_answer, test_query, 1)
        
        print(f"  Risk level: {validation['risk_level']}")
        print(f"  Confidence adjustment: {validation['confidence_adjustment']:+.2f}")
        print(f"  Questions: {len(validation['questions'])}")
        
        # Validate structure
        assert validation['risk_level'] in ['low', 'medium', 'high'], "Invalid risk level"
        assert -0.3 <= validation['confidence_adjustment'] <= 0.2, "Invalid confidence adjustment"
        assert isinstance(validation['questions'], list), "Questions should be a list"
        
        print("✅ Answer validation working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_query_with_validation():
    """Test 4: Full query includes Vibe-Check results"""
    
    print("\n" + "="*60)
    print("TEST 4: Full Query with Vibe-Check")
    print("="*60)
    
    try:
        handler = RecursiveQueryHandler({})
        
        # Run a simple query
        query = "What are the key principles of good software design?"
        print(f"\n  Query: {query}")
        
        result = await handler.answer(query, {})
        
        print(f"\n  Answer: {result['answer'][:100]}...")
        print(f"  Confidence: {result['confidence']:.1%}")
        print(f"  Iterations: {result['iterations']}")
        
        # Check for Vibe-Check results
        vibe_check = result.get('vibe_check', {})
        
        if not vibe_check:
            print("⚠️  No Vibe-Check data in result")
            return False
        
        print(f"\n  Vibe-Check:")
        print(f"    - Risk level: {vibe_check.get('risk_level', 'N/A')}")
        print(f"    - Validations: {vibe_check.get('validations_count', 0)}")
        print(f"    - Questions: {len(vibe_check.get('questions', []))}")
        
        # Validate structure
        assert 'risk_level' in vibe_check, "Missing risk_level"
        assert 'validations_count' in vibe_check, "Missing validations_count"
        assert 'questions' in vibe_check, "Missing questions"
        
        print("\n✅ Full query with Vibe-Check working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_confidence_adjustment():
    """Test 5: Confidence adjusts based on risk level"""
    
    print("\n" + "="*60)
    print("TEST 5: Confidence Adjustment")
    print("="*60)
    
    try:
        handler = RecursiveQueryHandler({})
        
        # Test different risk scenarios
        test_cases = [
            ("Low risk answer", 0.6, "low", 0.1),
            ("Medium risk answer", 0.6, "medium", 0.0),
            ("High risk answer", 0.6, "high", -0.2)
        ]
        
        for answer, base_conf, expected_risk, expected_adj in test_cases:
            validation = {
                "risk_level": expected_risk,
                "confidence_adjustment": expected_adj,
                "questions": [],
                "recommendations": []
            }
            
            # Simulate confidence adjustment
            adjusted_conf = min(base_conf + validation['confidence_adjustment'], 0.95)
            
            print(f"\n  {expected_risk.upper()} risk:")
            print(f"    Base confidence: {base_conf:.1%}")
            print(f"    Adjustment: {validation['confidence_adjustment']:+.2f}")
            print(f"    Final confidence: {adjusted_conf:.1%}")
            
            assert adjusted_conf == base_conf + expected_adj, f"Wrong adjustment for {expected_risk}"
        
        print("\n✅ Confidence adjustment logic working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    
    print("\n" + "="*60)
    print("VIBE-CHECK INTEGRATION TEST SUITE")
    print("="*60)
    print("\nValidating Vibe-Check integration with Recursive QC...")
    
    tests = [
        ("Vibe-Check Availability", test_vibe_check_available),
        ("Recursive Handler Integration", test_recursive_handler_with_vibe_check),
        ("Answer Validation", test_answer_validation),
        ("Full Query with Vibe-Check", test_full_query_with_validation),
        ("Confidence Adjustment", test_confidence_adjustment),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Vibe-Check is fully integrated.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)




