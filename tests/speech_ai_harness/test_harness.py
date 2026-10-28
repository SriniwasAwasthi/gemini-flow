"""
Test Harness for Gemini Flow Speech-to-Text Verification (Phase A & Phase B).
Evaluates all 4 models:
1. gemini-3.5-flash (Gemini Model #1)
2. gemini-3.5-flash-lite (Gemini Model #2)
3. offline-whisper (faster-whisper)
4. ollama-gemma2 (Ollama Gemma 2B)

Measures:
- Accuracy / WER
- Formatting & Bullet Correctness
- Word Order Consistency
- Latency (Speed)
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

from app.gemini_engine import GeminiEngine
from app.config import ConfigManager
from tests.speech_ai_harness.wer_evaluator import (
    compute_wer,
    check_formatting_correctness,
    check_order_consistency
)

DATASET_METADATA = Path("scratch/dataset_400/metadata.json")
RESULTS_OUTPUT = Path("tests/speech_ai_harness/benchmark_results.json")

def load_dataset() -> List[Dict[str, Any]]:
    with open(DATASET_METADATA, "r", encoding="utf-8") as f:
        return json.load(f)

def run_model_evaluation(
    engine: GeminiEngine,
    model_id: str,
    model_name_label: str,
    samples: List[Dict[str, Any]],
    phase_label: str = "Phase A"
) -> Dict[str, Any]:
    print(f"\n{'='*75}", flush=True)
    print(f"[{phase_label}] EVALUATING: {model_name_label} ({model_id}) — {len(samples)} Audio Runs", flush=True)
    print(f"{'='*75}", flush=True)

    engine.set_model(model_id)

    total_runs = len(samples)
    passed_runs = 0
    total_wer = 0.0
    total_latency = 0.0
    total_formatting_ok = 0
    total_order_ok = 0

    runs_detail = []

    for idx, sample in enumerate(samples):
        wav_path = sample["path"]
        if not os.path.exists(wav_path):
            print(f"File not found: {wav_path}", flush=True)
            continue

        with open(wav_path, "rb") as f:
            wav_bytes = f.read()

        t0 = time.time()
        ok, hypothesis = engine.transcribe_audio(
            wav_bytes=wav_bytes,
            system_instruction="You are Gemini Flow, an elite speech-to-text transcriber.",
            task="dictate"
        )
        lat = time.time() - t0
        total_latency += lat

        ref_gt = sample["ground_truth"]
        is_list = sample["is_list"]

        if ok and hypothesis and hypothesis.strip():
            wer = compute_wer(ref_gt, hypothesis)
            fmt_ok = check_formatting_correctness(hypothesis, is_list)
            ord_ok = check_order_consistency(ref_gt, hypothesis)

            # Pass criteria: valid text produced, reasonable WER or list items captured
            is_pass = wer < 0.45 or (is_list and fmt_ok)
            if is_pass:
                passed_runs += 1
            if fmt_ok:
                total_formatting_ok += 1
            if ord_ok:
                total_order_ok += 1
            total_wer += wer
        else:
            wer = 1.0
            fmt_ok = False
            ord_ok = False
            is_pass = False

        status = "PASS" if is_pass else "FAIL"

        runs_detail.append({
            "sample_id": sample["id"],
            "category": sample["category"],
            "status": status,
            "latency_sec": round(lat, 2),
            "wer": round(wer, 4),
            "accuracy_pct": round(max(0.0, 1.0 - wer) * 100.0, 1),
            "formatting_ok": fmt_ok,
            "order_ok": ord_ok,
            "output_preview": (hypothesis.replace('\n', ' ')[:80] + '...') if hypothesis else ""
        })

        # Progress reporting every 15 runs
        if (idx + 1) % 15 == 0 or idx == 0 or idx == len(samples) - 1:
            print(f"[{idx+1:03d}/{len(samples)}] {status} | Latency: {lat:.2f}s | WER: {wer:.2f} | Hyp: {runs_detail[-1]['output_preview']}", flush=True)

        # Gentle pacing for online API to prevent burst limits
        if model_id.startswith("gemini"):
            time.sleep(0.3)

    avg_lat = total_latency / total_runs if total_runs else 0.0
    avg_wer = total_wer / total_runs if total_runs else 1.0
    avg_acc = max(0.0, 1.0 - avg_wer) * 100.0
    pass_rate = (passed_runs / total_runs) * 100.0 if total_runs else 0.0
    fmt_rate = (total_formatting_ok / total_runs) * 100.0 if total_runs else 0.0
    ord_rate = (total_order_ok / total_runs) * 100.0 if total_runs else 0.0

    print(f"\n>> {model_name_label} Summary [{phase_label}]:", flush=True)
    print(f"   Runs: {passed_runs}/{total_runs} Passed ({pass_rate:.1f}%)", flush=True)
    print(f"   Accuracy: {avg_acc:.1f}% (Avg WER: {avg_wer:.3f})", flush=True)
    print(f"   Formatting Correctness: {fmt_rate:.1f}%", flush=True)
    print(f"   Order Consistency: {ord_rate:.1f}%", flush=True)
    print(f"   Average Latency: {avg_lat:.2f}s", flush=True)

    return {
        "model_id": model_id,
        "label": model_name_label,
        "phase": phase_label,
        "total_runs": total_runs,
        "passed_runs": passed_runs,
        "pass_rate": round(pass_rate, 1),
        "avg_wer": round(avg_wer, 4),
        "accuracy_pct": round(avg_acc, 1),
        "formatting_rate_pct": round(fmt_rate, 1),
        "order_consistency_pct": round(ord_rate, 1),
        "avg_latency_sec": round(avg_lat, 2),
        "runs_sample": runs_detail[:5]
    }

def main():
    print("=" * 80, flush=True)
    print("STARTING FULL SPEECH-AI MULTI-MODEL TEST HARNESS", flush=True)
    print("Testing 4 Models across Phase A (100 runs each) & Phase B (50 runs each)", flush=True)
    print("=" * 80, flush=True)

    dataset = load_dataset()
    print(f"Loaded {len(dataset)} verified audio samples from dataset.", flush=True)

    cfg = ConfigManager()
    engine = GeminiEngine(cfg)

    # 4 Target Models
    MODELS = [
        ("gemini-2.5-flash", "Gemini 2.5 Flash (Model #1)"),
        ("gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite (Model #2)"),
        ("offline-whisper", "Faster-Whisper Flow (Model #3)"),
        ("ollama-gemma2", "Ollama Gemma 2B (Model #4)")
    ]

    RESULTS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    all_results = {
        "timestamp": time.time(),
        "phase_a": {},
        "phase_b": {}
    }

    # =========================================================================
    # PHASE A: 100 Runs per model (400 runs total)
    # =========================================================================
    print("\n" + "#" * 80, flush=True)
    print("PHASE A: VERIFICATION (100 Distinct Audio Runs per Model = 400 Runs Total)", flush=True)
    print("#" * 80, flush=True)

    for i, (m_id, m_label) in enumerate(MODELS):
        start_idx = i * 100
        end_idx = start_idx + 100
        model_samples = dataset[start_idx:end_idx]

        res = run_model_evaluation(
            engine=engine,
            model_id=m_id,
            model_name_label=m_label,
            samples=model_samples,
            phase_label="Phase A"
        )
        all_results["phase_a"][m_id] = res

        # Incremental save
        with open(RESULTS_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)

    # =========================================================================
    # PHASE B: 50 Confirmation Runs per model (200 runs total)
    # =========================================================================
    print("\n" + "#" * 80, flush=True)
    print("PHASE B: CONFIRMATION (50 Distinct Audio Runs per Model = 200 Runs Total)", flush=True)
    print("#" * 80, flush=True)

    for i, (m_id, m_label) in enumerate(MODELS):
        start_idx = (i * 100 + 50) % len(dataset)
        end_idx = start_idx + 50
        if end_idx <= len(dataset):
            conf_samples = dataset[start_idx:end_idx]
        else:
            conf_samples = dataset[start_idx:] + dataset[:end_idx % len(dataset)]

        res = run_model_evaluation(
            engine=engine,
            model_id=m_id,
            model_name_label=m_label,
            samples=conf_samples,
            phase_label="Phase B"
        )
        all_results["phase_b"][m_id] = res

        # Incremental save
        with open(RESULTS_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)

    # Print Grand Final Tables
    print("\n" + "=" * 90, flush=True)
    print("PHASE A RESULTS TABLE (100 RUNS PER MODEL — 400 TOTAL)", flush=True)
    print("=" * 90, flush=True)
    print(f"{'Model':<35} | {'Passed':<10} | {'Accuracy':<10} | {'Formatting':<12} | {'Avg Speed':<10}", flush=True)
    print("-" * 90, flush=True)
    for m_id, r in all_results["phase_a"].items():
        print(f"{r['label']:<35} | {r['passed_runs']}/{r['total_runs']:<6} | {r['accuracy_pct']:>8.1f}% | {r['formatting_rate_pct']:>10.1f}% | {r['avg_latency_sec']:>8.2f}s", flush=True)

    print("\n" + "=" * 90, flush=True)
    print("PHASE B CONFIRMATION TABLE (50 RUNS PER MODEL — 200 TOTAL)", flush=True)
    print("=" * 90, flush=True)
    print(f"{'Model':<35} | {'Passed':<10} | {'Accuracy':<10} | {'Formatting':<12} | {'Avg Speed':<10}", flush=True)
    print("-" * 90, flush=True)
    for m_id, r in all_results["phase_b"].items():
        print(f"{r['label']:<35} | {r['passed_runs']}/{r['total_runs']:<6} | {r['accuracy_pct']:>8.1f}% | {r['formatting_rate_pct']:>10.1f}% | {r['avg_latency_sec']:>8.2f}s", flush=True)
    print("=" * 90, flush=True)
    print(f"\nAll test harness runs finished. Detailed JSON report saved to: {RESULTS_OUTPUT}", flush=True)

if __name__ == "__main__":
    main()
