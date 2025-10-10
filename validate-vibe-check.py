#!/usr/bin/env python3
"""
Quick validation of Vibe-Check integration
Checks imports and code structure without running full tests
"""

import ast
import sys
from pathlib import Path


def check_file_has_import(file_path: Path, import_name: str) -> bool:
    """Check if file imports a specific module"""
    
    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if import_name in str(node.module):
                    return True
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if import_name in alias.name:
                        return True
        
        return False
    except Exception as e:
        print(f"  Error checking {file_path}: {e}")
        return False


def check_has_attribute(file_path: Path, attr_name: str) -> bool:
    """Check if file has a specific attribute/method"""
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        return attr_name in content
    except Exception as e:
        print(f"  Error checking {file_path}: {e}")
        return False


def main():
    """Run validation checks"""
    
    print("\n" + "="*60)
    print("VIBE-CHECK INTEGRATION VALIDATION")
    print("="*60)
    
    root = Path(__file__).parent
    recursive_handler = root / "tools" / "recursive_query_handler.py"
    qc_workflow = root / "tools" / "qc_workflow.py"
    
    checks = []
    
    # Check 1: recursive_query_handler imports vibe_check_tool
    print("\n1. Checking imports in recursive_query_handler.py...")
    has_import = check_file_has_import(recursive_handler, "vibe_check_tool")
    checks.append(("Vibe-Check import", has_import))
    print(f"   {'✅' if has_import else '❌'} vibe_check_tool imported")
    
    # Check 2: recursive_query_handler has _validate_answer method
    print("\n2. Checking _validate_answer method...")
    has_method = check_has_attribute(recursive_handler, "async def _validate_answer")
    checks.append(("_validate_answer method", has_method))
    print(f"   {'✅' if has_method else '❌'} _validate_answer method exists")
    
    # Check 3: recursive_query_handler initializes vibe_check
    print("\n3. Checking vibe_check initialization...")
    has_init = check_has_attribute(recursive_handler, "self.vibe_check = get_vibe_check_tool()")
    checks.append(("Vibe-Check initialization", has_init))
    print(f"   {'✅' if has_init else '❌'} vibe_check initialized in __init__")
    
    # Check 4: Validation is called in _refine_iteration
    print("\n4. Checking validation in _refine_iteration...")
    has_validation_call = check_has_attribute(recursive_handler, "await self._validate_answer")
    checks.append(("Validation call", has_validation_call))
    print(f"   {'✅' if has_validation_call else '❌'} _validate_answer called")
    
    # Check 5: Confidence adjustment logic
    print("\n5. Checking confidence adjustment...")
    has_confidence_adj = check_has_attribute(recursive_handler, "confidence_adjustment")
    checks.append(("Confidence adjustment", has_confidence_adj))
    print(f"   {'✅' if has_confidence_adj else '❌'} confidence_adjustment logic present")
    
    # Check 6: Return includes vibe_check data
    print("\n6. Checking return value includes vibe_check...")
    has_vibe_return = check_has_attribute(recursive_handler, '"vibe_check":')
    checks.append(("Vibe-Check in return", has_vibe_return))
    print(f"   {'✅' if has_vibe_return else '❌'} vibe_check in return dict")
    
    # Check 7: QC workflow displays vibe_check
    print("\n7. Checking QC workflow displays Vibe-Check...")
    has_display = check_has_attribute(qc_workflow, "Vibe-Check Validation")
    checks.append(("QC workflow display", has_display))
    print(f"   {'✅' if has_display else '❌'} Vibe-Check displayed in QC workflow")
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} checks passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 All validation checks passed! Vibe-Check is integrated.")
        print("\nIntegration points:")
        print("  1. ✅ RecursiveQueryHandler imports Vibe-Check")
        print("  2. ✅ Answer validation with risk assessment")
        print("  3. ✅ Confidence adjustment based on risk level")
        print("  4. ✅ Vibe-Check data included in results")
        print("  5. ✅ QC workflow displays Vibe-Check info")
        return 0
    else:
        print(f"\n⚠️  {total - passed} check(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)




