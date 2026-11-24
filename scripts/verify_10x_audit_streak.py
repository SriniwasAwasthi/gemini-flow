"""
Gemini Flow 10-Iteration Consecutive Verification Streak Harness.
Executes 10 complete passes across all 6 targeted architectural features:
- Feature 1: Passive Auto-Learning Dictionary
- Feature 2: IDE & Vibe-Coding Awareness (VS Code, Cursor, Windsurf, Cline AI, Continue AI, Zed)
- Feature 3: Rich-Text CF_HTML Formatting & HTML Tag Preservation
- Feature 4: Sub-Second Single-Turn Dictation Pipeline (<25s buffer, VAD 0.45, 12 tenses)
- Feature 5: Offline Fallback & Faster-Whisper INT8 (4-thread CPU cap)
- Feature 6: Vision-Guided Voice & Dynamic Multimodal Routing
"""
import sys
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.test_10cycle_comprehensive_audit import Test10CycleComprehensiveAudit


def run_10_iterations():
    print("=" * 80)
    print("STARTING 10-ITERATION COMPREHENSIVE MULTI-AGENT VERIFICATION AUDIT")
    print("=" * 80)

    loader = unittest.TestLoader()

    streak_results = []
    total_start = time.time()

    for i in range(1, 11):
        t0 = time.time()
        suite = loader.loadTestsFromTestCase(Test10CycleComprehensiveAudit)
        runner = unittest.TextTestRunner(verbosity=0)
        res = runner.run(suite)
        elapsed = time.time() - t0

        passed = res.wasSuccessful() and len(res.failures) == 0 and len(res.errors) == 0
        tests_run = res.testsRun
        status = "PASSED" if passed else "FAILED"
        streak_results.append((i, passed, tests_run, elapsed))

        print(f"Iteration {i:02d}/10: {status} ({tests_run} checks in {elapsed:.3f}s)")
        if not passed:
            print(f"FAILED on iteration {i}: {res.failures} {res.errors}")
            return False

    total_time = time.time() - total_start
    print("=" * 80)
    print(f"10/10 ITERATIONS COMPLETED CLEANLY IN {total_time:.2f}s (100% STREAK SUCCESS)")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_10_iterations()
    sys.exit(0 if success else 1)
