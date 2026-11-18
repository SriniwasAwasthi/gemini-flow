"""
Gemini Flow Master E2E Test Suite Runner
Executes all 4 Tiers of requirement-driven opaque-box verification:
- Tier 1: Feature Coverage (F1-F24)
- Tier 2: Boundary Value Analysis & Corner Cases
- Tier 3: Pairwise Combinatorial Interactions
- Tier 4: Real-World Application Scenarios

Aggregates statistics and exits with code 0 on complete pass.
"""
import sys
import time
import unittest
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e.test_tier1_feature_coverage import TestTier1FeatureCoverage
from tests.e2e.test_tier2_boundary_corner import TestTier2BoundaryCorner
from tests.e2e.test_tier3_pairwise_combinations import TestTier3PairwiseCombinations
from tests.e2e.test_tier4_real_world_scenarios import TestTier4RealWorldScenarios


def run_test_tier(name: str, test_case_class) -> dict:
    """Runs a single test tier and returns summary statistics."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(test_case_class)
    
    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=1, stream=sys.stdout)
    print(f"\n{'=' * 80}")
    print(f"  RUNNING {name.upper()}")
    print(f"{'=' * 80}")
    
    result = runner.run(suite)
    duration = time.time() - start_time
    
    passed = result.testsRun - len(result.failures) - len(result.errors)
    return {
        "name": name,
        "total": result.testsRun,
        "passed": passed,
        "failed": len(result.failures),
        "errors": len(result.errors),
        "duration": duration,
        "success": result.wasSuccessful()
    }


def main():
    print("=" * 80)
    print("  GEMINI FLOW E2E MASTER TEST SUITE (TIERS 1-4)")
    print("  Requirement-Driven, Opaque-Box Automated Verification")
    print("=" * 80)

    start_total = time.time()
    tiers = [
        ("Tier 1: Feature Coverage (F1-F24)", TestTier1FeatureCoverage),
        ("Tier 2: Boundary & Corner Cases", TestTier2BoundaryCorner),
        ("Tier 3: Pairwise Combinations", TestTier3PairwiseCombinations),
        ("Tier 4: Real-World Scenarios", TestTier4RealWorldScenarios)
    ]

    tier_results = []
    overall_success = True

    for name, test_class in tiers:
        res = run_test_tier(name, test_class)
        tier_results.append(res)
        if not res["success"]:
            overall_success = False

    total_duration = time.time() - start_total
    total_tests = sum(r["total"] for r in tier_results)
    total_passed = sum(r["passed"] for r in tier_results)
    total_failed = sum(r["failed"] for r in tier_results)
    total_errors = sum(r["errors"] for r in tier_results)

    # Print Summary Table
    print("\n" + "=" * 80)
    print("  E2E TEST EXECUTION SUMMARY TABLE")
    print("=" * 80)
    header = f"{'Tier Name':<42} | {'Total':<6} | {'Passed':<6} | {'Failed':<6} | {'Time (s)':<8} | {'Status'}"
    print(header)
    print("-" * 80)
    for r in tier_results:
        status_str = "[PASS]" if r["success"] else "[FAIL]"
        row = f"{r['name']:<42} | {r['total']:<6} | {r['passed']:<6} | {r['failed']:<6} | {r['duration']:<8.2f} | {status_str}"
        print(row)
    print("-" * 80)
    final_status = "[ALL PASSED]" if overall_success else "[FAILED]"
    summary_row = f"{'TOTAL':<42} | {total_tests:<6} | {total_passed:<6} | {total_failed + total_errors:<6} | {total_duration:<8.2f} | {final_status}"
    print(summary_row)
    print("=" * 80)

    if overall_success:
        print("\nAll End-to-End tests passed successfully with zero errors!")
        sys.exit(0)
    else:
        print(f"\nTest execution finished with {total_failed} failures and {total_errors} errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()
