"""
Live 18 x 10 = 180 Consecutive Streak Verification Suite for Gemini Flow.

Verifies:
1. Persistent API key & config reload across cold ConfigManager instantiation.
2. Section 1: AI Prompt Transformation Shortcut (Alt + P) -> 10 consecutive passes.
3. Section 2: Universal Text Transformation Shortcut (Alt + T) -> 10 consecutive passes.
4. Section 3: All 16 Profiles Command Categories via Spoken Trigger Matching +
   GeminiTransformService.execute_command_category + Contract Validator -> 10 consecutive passes each.
5. Zero regression across all 7 existing core dictation/transcription models.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.commands import COMMAND_MAP, COMMAND_REGISTRY, match_spoken_command
from app.config import CONFIG_FILE, ConfigManager
from app.router.model_router import MODEL_REGISTRY
from app.transcription.engine import UnifiedTranscriptionEngine
from app.transformation.gemini_transform_service import GeminiTransformService

TARGET_API_KEY = os.environ.get("GEMINI_API_KEY", "")
STREAK_TARGET = 10


def _no_error_leak(text: str) -> bool:
    low = (text or "").lower()
    bad_markers = (
        "unavalable",
        "unavailable (http",
        "http 404",
        "http 401",
        "http 403",
        "invalid or unauthorized gemini api key",
        "traceback (most recent call last)",
    )
    return not any(m in low for m in bad_markers)


def _check_no_chatty_preamble(text: str) -> bool:
    low = (text or "").strip().lower()
    bad_starts = (
        "sure, here",
        "here is the",
        "here's the",
        "certainly!",
        "of course!",
    )
    return not any(low.startswith(s) for s in bad_starts)


def verify_alt_p(svc: GeminiTransformService, idx: int) -> Tuple[bool, str, str, float]:
    coffee_prompt = (
        "Create a beginner-friendly e-commerce website for a coffee shop. "
        "Home page, Product Listing, Product Details, Shopping Cart, Login/Register, Checkout. "
        "Tech Stack: React.js, Tailwind CSS, Node.js, Express.js, MongoDB, JWT, Stripe."
    )
    ml_prompt = (
        "Build a Python tabular churn prediction pipeline using scikit-learn, XGBoost, "
        "StratifiedKFold cross-validation, Optuna tuning, and SHAP feature importance."
    )
    inp = coffee_prompt if idx % 2 == 0 else ml_prompt
    res = svc.transform_to_ai_prompt(inp)
    if not res.success or not res.text:
        return False, res.error_message or "Empty response", res.model_used, res.latency_seconds
    out = res.text
    required_tags = ("<role>", "</role>", "<context>", "</context>", "<task>", "</task>", "<constraints>", "</constraints>", "<output_format>", "</output_format>")
    if not all(t in out for t in required_tags):
        return False, "Missing required 5-part XML tags", res.model_used, res.latency_seconds
    if "..." in out:
        return False, "Detected '...' truncation in output", res.model_used, res.latency_seconds
    if not _no_error_leak(out):
        return False, "Error marker leaked into output", res.model_used, res.latency_seconds
    if idx % 2 == 0:
        for tech in ("react", "tailwind", "node", "express", "mongodb", "jwt", "stripe"):
            if tech not in out.lower():
                return False, f"Missing required stack item '{tech}'", res.model_used, res.latency_seconds
        role_block = out.split("</role>")[0].lower()
        if "next.js" in role_block:
            return False, "Hardcoded Next.js persona leaked into MERN role", res.model_used, res.latency_seconds
    else:
        for kw in ("xgboost", "scikit-learn", "optuna", "shap"):
            if kw not in out.lower():
                return False, f"Missing ML requirement '{kw}'", res.model_used, res.latency_seconds
    return True, out, res.model_used, res.latency_seconds


def verify_universal_transform(svc: GeminiTransformService, idx: int) -> Tuple[bool, str, str, float]:
    samples = [
        (
            "hey team sorry im late sending this but the api server kept crashing yesterday bc "
            "memory spiked on the export job. i restarted it and bumped limit to 4gb, looks fine now, "
            "gonna add proper streaming next week",
            lambda o: ("4" in o and "gb" in o.lower() and "export" in o.lower() and "streaming" in o.lower()),
        ),
        (
            "hi sarah i checked the q3 invoice and total was 1250 dollars instead of 1500 dollars, "
            "can you please resend updated pdf before 5 pm friday",
            lambda o: ("1,250" in o or "1250" in o) and ("1,500" in o or "1500" in o) and ("friday" in o.lower()),
        ),
    ]
    inp, fn = samples[idx % len(samples)]
    res = svc.transform_universal_text(inp, app_context={"app_name": "Slack", "tone": "professional"})
    if not res.success or not res.text:
        return False, res.error_message or "Empty response", res.model_used, res.latency_seconds
    out = res.text
    if not _no_error_leak(out) or not _check_no_chatty_preamble(out):
        return False, "Preamble or error leak detected", res.model_used, res.latency_seconds
    if not fn(out):
        return False, f"Factual preservation failed: {out[:120]}", res.model_used, res.latency_seconds
    return True, out, res.model_used, res.latency_seconds


SPOKEN_TEST_CASES: Dict[str, Tuple[str, Callable[[str], bool]]] = {
    "professionalize": (
        "Make this professional: hey boss we finished the v2 update yesterday budget was 1500 dollars and all 12 tests passed",
        lambda o: ("1,500" in o or "1500" in o) and "12" in o,
    ),
    "grammar_fix": (
        "Fix the grammar: yesterday i go to office and seen three problem with the database server",
        lambda o: "went" in o.lower() and "saw" in o.lower() and "problems" in o.lower(),
    ),
    "generate_code": (
        "Generate code python async function to retry httpx get 3 times with backoff",
        lambda o: "async def" in o and "httpx" in o and "TODO" not in o,
    ),
    "summarize": (
        "Summarize this: We held our Q4 engineering review today. API latency dropped by 35 percent after deploying Redis caching. Mobile app crashes fell from 4 percent to 0.5 percent, and user signups grew by 12,000 this month. However, webhook retries spiked on Tuesdays, so Elena will ship a dead-letter queue patch by Friday.",
        lambda o: ("35%" in o or "35 percent" in o.lower()) and len(o.split()) < 65,
    ),
    "create_prompt": (
        "Turn this into a prompt: Build a FastAPI service with PostgreSQL, SQLAlchemy, JWT auth, and Redis rate limiting",
        lambda o: all(t in o for t in ("<role>", "<context>", "<task>", "<constraints>", "<output_format>")) and "fastapi" in o.lower() and "redis" in o.lower(),
    ),
    "make_casual": (
        "Make it friendly: Please be advised that the quarterly projection has been revised upwards by 12 percent.",
        lambda o: ("12%" in o or "12 percent" in o.lower()),
    ),
    "shorten": (
        "Make it concise: In order to properly ensure that the primary database server continues operating without running into unexpected memory errors, it is absolutely essential that we perform a scheduled reboot at 10 PM.",
        lambda o: ("10" in o and len(o.split()) < 34),
    ),
    "expand": (
        "Expand this: We need to adopt Redis caching to reduce database load.",
        lambda o: ("redis" in o.lower() and len(o.split()) > 20),
    ),
    "explain": (
        "Explain concept: How does HTTP keep-alive connection pooling reduce API latency?",
        lambda o: ("connection" in o.lower() and len(o.split()) >= 15),
    ),
    "translate": (
        "Translate this to Spanish: Good morning team, our deployment starts at 10:30 AM.",
        lambda o: ("10:30" in o and ("buenos" in o.lower() or "equipo" in o.lower() or "despliegue" in o.lower())),
    ),
    "create_email": (
        "Draft an email: tell Alex the Q3 demo is ready for review and ask if we can meet Thursday at 2 PM",
        lambda o: ("subject" in o.lower() and "alex" in o.lower() and "2" in o),
    ),
    "create_github_issue": (
        "Create a GitHub issue: Export button freezes UI thread when CSV has over 50000 rows on Windows 11",
        lambda o: ("##" in o and "50" in o and ("- [ ]" in o or "reproduce" in o.lower())),
    ),
    "create_github_pr": (
        "Create PR: added exponential backoff and ListModels auto-discovery for Gemini transformation service",
        lambda o: ("summary" in o.lower() and "- [ ]" in o),
    ),
    "create_task": (
        "Create task list: deploy the v2 build, verify postgres migrations, notify QA team, and publish release notes",
        lambda o: ("- [ ]" in o and o.count("- [ ]") >= 3),
    ),
    "format_text": (
        "Format this into a table: Apples 5 dollars in stock, Bananas 3 dollars low stock, Oranges 4 dollars in stock",
        lambda o: ("|" in o and bool(re.search(r"\|[-:\s|]+\|", o)) and "apples" in o.lower()),
    ),
    "rewrite": (
        "Polish this: I think the migration plan is good but we might hit 2 downtime risks if we dont test backups first.",
        lambda o: (("2" in o or "two" in o.lower()) and "backup" in o.lower()),
    ),
}


def verify_command_category(svc: GeminiTransformService, cmd_id: str) -> Tuple[bool, str, str, float]:
    spoken, extra_check = SPOKEN_TEST_CASES[cmd_id]
    matched = match_spoken_command(spoken)
    if matched is None:
        return False, f"Spoken trigger did not match: {spoken}", "", 0.0
    cmd, payload = matched
    if cmd.id != cmd_id:
        return False, f"Matched wrong command '{cmd.id}' instead of '{cmd_id}'", "", 0.0

    res = svc.execute_command_category(cmd=cmd, payload=payload)
    if not res.success or not res.text:
        return False, res.error_message or "Command returned empty output", res.model_used, res.latency_seconds

    is_valid, reason = cmd.validator(payload, res.text)
    if not is_valid:
        return False, f"Validator failed ({reason}): {res.text[:160]}", res.model_used, res.latency_seconds
    if not _no_error_leak(res.text):
        return False, f"Error leaked into output: {res.text[:160]}", res.model_used, res.latency_seconds
    if not extra_check(res.text):
        return False, f"Quality/fact check failed: {res.text[:160]}", res.model_used, res.latency_seconds
    return True, res.text, res.model_used, res.latency_seconds


def main() -> int:
    # 1. Persist key & transform model and verify cold reload
    cm = ConfigManager()
    cm.set_api_key(TARGET_API_KEY)
    cm.set("gemini_transform_model", "gemini-2.5-flash")
    cm.save_config()

    cm_reloaded = ConfigManager()
    persisted_key = cm_reloaded.get_api_key()
    assert persisted_key == TARGET_API_KEY, f"Persisted key mismatch: {persisted_key[:8]}..."
    assert cm_reloaded.get("gemini_transform_model") == "gemini-2.5-flash"
    print(f"[PERSISTENCE] Verified key & config persisted at: {CONFIG_FILE}", flush=True)

    # 2. Verify zero regression on the 7 existing core models
    expected_7 = {
        "offline-whisper",
        "groq-whisper-turbo",
        "moonshine-onnx",
        "sherpa-onnx",
        "gemini-2.5-flash",
        "gemini-3.5-flash-lite",
        "ollama-qwen2.5",
    }
    engine = UnifiedTranscriptionEngine(api_key=persisted_key)
    diag = engine.get_all_models_diagnostics()
    missing_models = expected_7 - set(diag.keys())
    assert not missing_models, f"Missing existing core models: {missing_models}"
    assert (expected_7 - {"sherpa-onnx"}).issubset(set(MODEL_REGISTRY.keys()))
    print(f"[CORE MODELS] All 7 existing models verified intact: {sorted(expected_7)}", flush=True)

    svc = GeminiTransformService(config_manager=cm_reloaded)

    sections: List[Tuple[str, str, Callable[[int], Tuple[bool, str, str, float]]]] = [
        ("Section 1: Alt+P AI Prompt Shortcut", "alt_p", lambda i: verify_alt_p(svc, i)),
        ("Section 2: Universal Text Shortcut", "alt_t", lambda i: verify_universal_transform(svc, i)),
    ]
    for idx, cmd in enumerate(COMMAND_REGISTRY, start=1):
        cid = cmd.id
        sections.append((f"Section 3.{idx:02d}: {cmd.name}", cid, lambda _i, c=cid: verify_command_category(svc, c)))

    assert len(sections) == 18, f"Expected 18 sections, got {len(sections)}"

    report: List[Dict[str, Any]] = []
    total_passes = 0
    total_runs = 0
    all_passed = True

    for label, sec_id, runner in sections:
        streak = 0
        models_used: List[str] = []
        latencies: List[float] = []
        sample_out = ""
        failures: List[str] = []

        for run_idx in range(STREAK_TARGET):
            total_runs += 1
            ok, out_or_err, model_used, lat = runner(run_idx)
            if ok:
                streak += 1
                total_passes += 1
                if model_used:
                    models_used.append(model_used)
                latencies.append(lat)
                if not sample_out:
                    sample_out = out_or_err
                print(f"  [PASS {streak:02d}/{STREAK_TARGET}] {label} ({model_used}, {lat:.2f}s)", flush=True)
            else:
                all_passed = False
                failures.append(f"Run {run_idx + 1}: {out_or_err}")
                print(f"  [FAIL] {label} run {run_idx + 1}: {out_or_err}", flush=True)
                break
            time.sleep(2.2)

        avg_lat = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        report.append({
            "label": label,
            "id": sec_id,
            "streak": streak,
            "target": STREAK_TARGET,
            "avg_latency_s": avg_lat,
            "models_used": sorted(set(models_used)),
            "sample_output": sample_out[:240].replace("\n", " "),
            "failures": failures,
        })

    out_dir = ROOT / "scratch"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "streak_180_report.json"
    report_path.write_text(json.dumps({
        "total_passes": total_passes,
        "total_runs": total_runs,
        "all_passed": all_passed,
        "sections": report,
    }, indent=2), encoding="utf-8")

    print("\n" + "=" * 88, flush=True)
    print(f"18 x 10 STREAK SUMMARY: {total_passes}/{total_runs} PASSES | ALL_PASSED={all_passed}", flush=True)
    print("=" * 88, flush=True)
    for row in report:
        print(f"{row['label']:36s} | {row['streak']:2d}/{row['target']} | avg={row['avg_latency_s']:4.2f}s | models={','.join(row['models_used'])}", flush=True)

    return 0 if (all_passed and total_passes == 180) else 1


if __name__ == "__main__":
    raise SystemExit(main())
