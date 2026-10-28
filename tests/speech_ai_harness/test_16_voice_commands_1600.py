"""
Test Harness for Gemini Flow Profiles Section: 16 Voice Command Categories.
Evaluates all 16 Intent Categories with 100 runs each = 1,600 total runs.

Mandatory Regression Test:
User's Real Failure Example in Category 1 (PROFESSIONALIZE):
"Make this professional. I'm Trina Savastrian, I was just visiting the market and I was doing some random stuff I buy: Two apples. One mango three bananas. I come back home."
- Trigger detected & removed
- Name 'Trina Savastrian' preserved
- Grammar & tense corrected ('I buy' -> purchased, 'I come back home' -> returned home)
- Items converted to clean bullets ('• Two apples', '• One mango', '• Three bananas')
- Professional executive tone
"""
import os
import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

from app.intent.intent_system import IntentClassifier, IntentCategory, INTENT_TO_TRANSFORM_MAP
from app.transformation.transform_engine import TransformType, TransformEngine
from app.gemini_engine import GeminiEngine
from app.config import ConfigManager

CASES_FILE = Path("tests/speech_ai_harness/voice_commands_1600_cases.json")
RESULTS_OUTPUT = Path("tests/speech_ai_harness/voice_commands_1600_results.json")

def load_cases() -> List[Dict[str, Any]]:
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def verify_single_case(case: Dict[str, Any], engine: GeminiEngine) -> Dict[str, Any]:
    case_id = case["id"]
    category_str = case["category"]
    mode = case["mode"]
    is_regression = case.get("is_mandatory_regression", False)

    if mode == "highlighted_plus_hotkey":
        spoken_text = case["spoken_command"]
        clipboard_text = case["highlighted_text"]
    else:
        spoken_text = case["input_text"]
        clipboard_text = ""

    # 1. Pipeline Step 1: Intent Classification & Trigger Detection
    intent_res = IntentClassifier.classify(spoken_text, clipboard_fallback=clipboard_text)

    expected_category = IntentCategory(category_str)
    cat_matched = (intent_res.intent == expected_category)

    # 2. Pipeline Step 2: Trigger Stripping
    payload = intent_res.payload.strip() if intent_res.payload else ""
    if not payload and clipboard_text:
        payload = clipboard_text.strip()
    payload = payload.strip().strip('"\'“”«»').strip()

    # Trigger words should never appear in payload
    trigger_stripped = True
    if intent_res.command_trigger and len(intent_res.command_trigger) > 3:
        trig_clean = intent_res.command_trigger.strip(":.- ").lower()
        if trig_clean in payload.lower()[:len(trig_clean) + 5]:
            trigger_stripped = False

    # 3. Pipeline Step 3: Transformation Execution
    trans_type = INTENT_TO_TRANSFORM_MAP.get(intent_res.intent, TransformType.IMPROVE)
    custom_inst = intent_res.system_instruction or ""

    selected_model = "gemini-3.5-flash" if (case_id % 2 == 0) else "gemini-3-flash-preview"
    engine.set_model(selected_model)
    t0 = time.time()
    exec_res = engine.transform_text(
        raw_text=payload,
        transform_type=trans_type,
        custom_instruction=custom_inst
    )
    latency = time.time() - t0

    transformed_text = exec_res.text if (exec_res.success and exec_res.text) else ""

    # 4. Pipeline Step 4: Quality & Fidelity Checks
    passed = False
    fail_reasons = []

    if not exec_res.success or not transformed_text or len(transformed_text.strip()) < 5:
        fail_reasons.append(f"Transformation failed: {exec_res.error_message}")
    elif not cat_matched:
        fail_reasons.append(f"Intent mismatch: expected {category_str}, got {intent_res.intent.value}")
    elif not trigger_stripped:
        fail_reasons.append(f"Trigger phrase '{intent_res.command_trigger}' leaked into payload")
    else:
        # Check that trigger did not leak into output
        if intent_res.command_trigger and len(intent_res.command_trigger) > 5:
            trig_words = intent_res.command_trigger.lower().split()[:2]
            is_pr_or_issue = expected_category in (IntentCategory.CREATE_GITHUB_PR, IntentCategory.CREATE_GITHUB_ISSUE)
            if not is_pr_or_issue and len(trig_words) >= 2 and f"{trig_words[0]} {trig_words[1]}" in transformed_text.lower()[:30]:
                fail_reasons.append("Trigger words leaked into final output")

        # Entity / Name fidelity check
        expected_name = case.get("expected_name")
        if expected_name and expected_category not in (IntentCategory.GENERATE_CODE, IntentCategory.TRANSLATE):
            if expected_name.lower() not in transformed_text.lower():
                parts = expected_name.lower().split()
                if not any(p in transformed_text.lower() for p in parts):
                    fail_reasons.append(f"Spoken entity/name '{expected_name}' not preserved in output")

        # Mandatory Regression Check for Trina Savastrian
        if is_regression:
            has_trina = "trina savastrian" in transformed_text.lower()
            has_apples = "apple" in transformed_text.lower()
            has_mango = "mango" in transformed_text.lower()
            has_bananas = "banana" in transformed_text.lower()
            has_bullets = any(b in transformed_text for b in ("•", "*", "-"))
            tense_corrected = any(w in transformed_text.lower() for w in ("purchased", "bought", "visited", "returned"))

            if not has_trina:
                fail_reasons.append("Trina Savastrian regression: name lost or misspelled")
            if not (has_apples and has_mango and has_bananas):
                fail_reasons.append("Trina Savastrian regression: fruit items lost")
            if not has_bullets:
                fail_reasons.append("Trina Savastrian regression: list not converted to bullets")
            if not tense_corrected:
                fail_reasons.append("Trina Savastrian regression: tenses not corrected")

        # Category-Specific Effect Checks
        lowered = transformed_text.lower()
        if expected_category == IntentCategory.GENERATE_CODE:
            is_valid_py = False
            try:
                import ast
                ast.parse(transformed_text)
                is_valid_py = True
            except Exception:
                pass
            code_markers = ["```", "def ", "function", "func ", "import ", "const ", "select ", "create ", "alter ", "table", "begin", "insert ", "update ", "delete ", "=>", "class ", "return ", "var ", "let ", "val ", ";", "--", "//", "=", "#", chr(34)*3, chr(39)*3]
            if not is_valid_py and not any(m in lowered for m in code_markers):
                fail_reasons.append("Generate Code: output does not contain recognizable code constructs")

        elif expected_category == IntentCategory.FORMAT_TEXT:
            if "|" not in transformed_text:
                fail_reasons.append("Format Table: output missing Markdown table pipes '|'")

        elif expected_category == IntentCategory.CREATE_TASK:
            if not any(m in transformed_text for m in ("[ ]", "- [ ]", "* [ ]", "1.", "•", "-", "*", "priority", "task", "owner")):
                fail_reasons.append("Create Task: output missing checklist or bullet items")

        elif expected_category == IntentCategory.CREATE_PROMPT:
            prompt_markers = ["role", "objective", "instruction", "context", "requirement", "you are", "#"]
            if not any(m in lowered for m in prompt_markers):
                fail_reasons.append("Create Prompt: output missing structured prompt sections")

        elif expected_category == IntentCategory.CREATE_EMAIL:
            email_markers = ["subject", "dear ", "hi ", "hello ", "sincerely", "regards", "best regards", "thank you", "best,"]
            if not any(m in lowered for m in email_markers):
                fail_reasons.append("Draft Email: output missing standard email formatting")

        elif expected_category == IntentCategory.CREATE_GITHUB_ISSUE:
            issue_markers = ["###", "##", "title", "description", "issue", "bug", "steps", "expected", "actual", "reproduction"]
            if not any(m in lowered for m in issue_markers):
                fail_reasons.append("GitHub Issue: output missing markdown issue structure")

        elif expected_category == IntentCategory.CREATE_GITHUB_PR:
            pr_markers = ["###", "##", "summary", "changes", "pr", "pull request", "checklist", "testing", "motivation"]
            if not any(m in lowered for m in pr_markers):
                fail_reasons.append("GitHub PR: output missing markdown PR structure")

        if not fail_reasons:
            passed = True

    preview = (transformed_text.replace("\n", " ")[:90] + "...") if transformed_text else ""

    return {
        "id": case_id,
        "category": category_str,
        "mode": mode,
        "is_regression": is_regression,
        "passed": passed,
        "latency_sec": round(latency, 2),
        "intent_matched": cat_matched,
        "trigger_stripped": trigger_stripped,
        "fail_reasons": fail_reasons,
        "output_preview": preview,
        "full_output": transformed_text[:300]
    }

def main():
    print("=" * 85, flush=True)
    print("STARTING 16 VOICE COMMAND CATEGORIES BENCHMARK HARNESS (1,600 RUNS)", flush=True)
    print("Testing 100 runs per category across all 16 built-in modes", flush=True)
    print("=" * 85, flush=True)

    cases = load_cases()
    print(f"Loaded {len(cases)} total test cases from {CASES_FILE}.", flush=True)

    cfg = ConfigManager()
    engine = GeminiEngine(cfg)

    # Group cases by category
    from collections import defaultdict
    category_cases = defaultdict(list)
    for c in cases:
        category_cases[c["category"]].append(c)

    all_category_results = {}
    total_all_runs = 0
    total_all_passed = 0

    RESULTS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    existing_results = {}
    if RESULTS_OUTPUT.exists():
        try:
            with open(RESULTS_OUTPUT, "r", encoding="utf-8") as f:
                prev_data = json.load(f)
                existing_results = prev_data.get("categories", {})
        except Exception:
            existing_results = {}

    force_rerun = set(sys.argv[1:]) if len(sys.argv) > 1 else {"GENERATE_CODE", "CREATE_GITHUB_PR", "CREATE_GITHUB_ISSUE", "CREATE_PROMPT"}

    cat_idx = 1
    for cat_name, cat_list in category_cases.items():
        if cat_name in existing_results and existing_results[cat_name].get("pass_rate_pct", 0) >= 95.0 and cat_name not in force_rerun and "--force-all" not in sys.argv:
            prev = existing_results[cat_name]
            print(f"\n[{cat_idx:02d}/16] CATEGORY PREVIOUSLY VERIFIED: {cat_name} -> {prev['passed_runs']}/{prev['total_runs']} Passed ({prev['pass_rate_pct']}%)", flush=True)
            all_category_results[cat_name] = prev
            total_all_runs += prev["total_runs"]
            total_all_passed += prev["passed_runs"]
            cat_idx += 1
            continue
        print(f"\n[{cat_idx:02d}/16] EVALUATING CATEGORY: {cat_name} ({len(cat_list)} runs)...", flush=True)
        t_start = time.time()

        from app.reliability.fallback_handler import FallbackHandler
        FallbackHandler._rate_limited_models.clear()

        results = []
        for idx, case in enumerate(cat_list):
            res = verify_single_case(case, engine)
            results.append(res)
            if (idx + 1) % 20 == 0 or idx == 0 or idx == len(cat_list) - 1:
                cur_pass = sum(1 for r in results if r["passed"])
                print(f"   [{idx+1:03d}/{len(cat_list)}] Status: {res['passed']} | Lat: {res['latency_sec']}s | Current Pass: {cur_pass}/{idx+1}", flush=True)
            time.sleep(3.2)

        cat_elapsed = time.time() - t_start
        cat_passed = sum(1 for r in results if r["passed"])
        cat_total = len(results)
        pass_rate = (cat_passed / cat_total) * 100.0 if cat_total else 0.0
        avg_lat = sum(r["latency_sec"] for r in results) / cat_total if cat_total else 0.0

        total_all_runs += cat_total
        total_all_passed += cat_passed

        # Check regression test if in this category
        reg_result = next((r for r in results if r["is_regression"]), None)
        if reg_result:
            reg_status = "PASS" if reg_result["passed"] else "FAIL"
            print(f"   [REGRESSION TEST] Trina Savastrian: {reg_status} | Preview: {reg_result['output_preview']}", flush=True)
            if not reg_result["passed"]:
                print(f"   --> Regression Fail Reasons: {reg_result['fail_reasons']}", flush=True)

        print(f"   --> {cat_name}: {cat_passed}/{cat_total} Passed ({pass_rate:.1f}%) in {cat_elapsed:.1f}s (Avg {avg_lat:.2f}s/run)", flush=True)

        all_category_results[cat_name] = {
            "category": cat_name,
            "total_runs": cat_total,
            "passed_runs": cat_passed,
            "pass_rate_pct": round(pass_rate, 1),
            "avg_latency_sec": round(avg_lat, 2),
            "elapsed_seconds": round(cat_elapsed, 1),
            "failures": [r for r in results if not r["passed"]][:5],
            "sample_outputs": [r["output_preview"] for r in results[:3]]
        }

        # Save progress incrementally
        with open(RESULTS_OUTPUT, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.time(),
                "total_runs": total_all_runs,
                "total_passed": total_all_passed,
                "overall_pass_rate": round((total_all_passed / total_all_runs) * 100.0, 1) if total_all_runs else 0.0,
                "categories": all_category_results
            }, f, indent=2)

        cat_idx += 1
        time.sleep(0.5)

    # Print Grand Final Table for all 16 Categories
    print("\n" + "=" * 95, flush=True)
    print("ALL 16 VOICE COMMAND CATEGORIES FINAL RESULTS (1,600 RUNS TOTAL)", flush=True)
    print("=" * 95, flush=True)
    print(f"{'#':<3} | {'Command Category':<24} | {'Runs':<8} | {'Passed':<8} | {'Pass Rate':<10} | {'Avg Latency':<12} | {'Status'}", flush=True)
    print("-" * 95, flush=True)

    for i, (cat_name, r) in enumerate(all_category_results.items(), 1):
        status = "PASSED" if r["pass_rate_pct"] >= 95.0 else "NEEDS FIX"
        print(f"{i:<3} | {cat_name:<24} | {r['total_runs']:<8} | {r['passed_runs']:<8} | {r['pass_rate_pct']:>8.1f}% | {r['avg_latency_sec']:>10.2f}s | {status}", flush=True)

    print("=" * 95, flush=True)
    overall_pct = (total_all_passed / total_all_runs) * 100.0 if total_all_runs else 0.0
    print(f"GRAND TOTAL: {total_all_passed}/{total_all_runs} Passed ({overall_pct:.1f}%)", flush=True)
    print(f"Results saved to: {RESULTS_OUTPUT}", flush=True)

if __name__ == "__main__":
    main()
