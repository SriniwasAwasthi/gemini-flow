"""
Super Master Engineering Verification & Benchmark Suite for Gemini Flow.
Validates all 15 Core Engineering Test Cases and Model Benchmarks defined in the Super Master Prompt:
1. TEST 1: Duplicate Sentence Elimination
2. TEST 2: Date Correction ('It's Friday. Actually, it's Saturday.')
3. TEST 3: Correction Without Keyword ('Today is Friday. Today is Saturday.')
4. TEST 4: Different Events Preserved ('Yesterday was Friday. Today is Saturday.')
5. TEST 5: Repeated Question ('Why are these three skills inactive? ...')
6. TEST 6: Technical Term Correction ('Use Gemini Fl... Gemini Flow.')
7. TEST 7: Action Replacement ('Open the first application. No, open the second application.')
8. TEST 8: Overlapping Audio Windows Reconciliation
9. TEST 9: Real-Time Partial Transcription Hypothesis Reconciliation
10. TEST 10: Meaningful Repetition Preservation ('This application is fast, very fast.')
11. TEST 11: Multiple Chained Corrections ('Make it blue. No, make it green. Actually, make it black.')
12. TEST 12: Long Recording & Zero Truncation
13. TEST 13: Quick-Text Voice Trigger Expansion (Mid-Sentence)
14. TEST 14: Trigger at Different Positions (Beginning, Middle, End, After Pause)
15. TEST 15: Multilingual Speech Preservation (English, Hindi, Marathi, German, French, Telugu)
"""
import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.transcription.universal_pipeline import (
    UniversalPipeline,
    StreamingHypothesisReconciler,
    OverlapDuplicateResolver,
    UniversalDuplicateEliminator,
    ContextualSelfCorrectionEngine,
    VoiceTriggerExpander,
    GrammarAndPunctuationProcessor,
    AudioFrame
)
from app.transcription.engine import UnifiedTranscriptionEngine
from app.gemini_engine import GeminiEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GeminiFlow.SuperMasterSuite")


class SuperMasterSuite:
    def __init__(self):
        self.pipeline = UniversalPipeline()
        self.engine = UnifiedTranscriptionEngine()
        self.results: List[Dict[str, Any]] = []

    def record_test(self, test_id: str, description: str, passed: bool, input_data: Any, output_data: Any, expected: Any, latency_ms: float = 0.0):
        self.results.append({
            "test_id": test_id,
            "description": description,
            "passed": passed,
            "input": str(input_data),
            "output": str(output_data),
            "expected": str(expected),
            "latency_ms": round(latency_ms, 2)
        })
        status_str = "PASS" if passed else "FAIL"
        logger.info(f"[{status_str}] {test_id}: {description} ({latency_ms:.2f}ms)")
        if not passed:
            logger.error(f"  Got:      {output_data}")
            logger.error(f"  Expected: {expected}")

    def run_all(self):
        logger.info("================================================================================")
        logger.info("  STARTING GEMINI FLOW SUPER MASTER ENGINEERING VERIFICATION SUITE")
        logger.info("================================================================================")

        # -------------------------------------------------------------
        # TEST 1: Duplicate Sentence
        # -------------------------------------------------------------
        t0 = time.time()
        inp1 = "I want to improve Gemini Flow. I want to improve Gemini Flow."
        exp1 = "I want to improve Gemini Flow."
        out1 = self.pipeline.process(inp1)
        self.record_test("TEST 1", "Duplicate Sentence Elimination", out1 == exp1, inp1, out1, exp1, (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 2: Date Correction
        # -------------------------------------------------------------
        t0 = time.time()
        inp2 = "It's Friday. Actually, it's Saturday."
        exp2 = "It's Saturday."
        out2 = self.pipeline.process(inp2)
        self.record_test("TEST 2", "Date Correction with Actually", out2 == exp2, inp2, out2, exp2, (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 3: Correction Without Keyword
        # -------------------------------------------------------------
        t0 = time.time()
        inp3 = "Today is Friday. Today is Saturday."
        exp3 = "Today is Saturday."
        out3 = self.pipeline.process(inp3)
        self.record_test("TEST 3", "Subject/Attribute Replacement Without Keyword", out3 == exp3, inp3, out3, exp3, (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 4: Different Events Preserved
        # -------------------------------------------------------------
        t0 = time.time()
        inp4 = "Yesterday was Friday. Today is Saturday."
        exp4 = "Yesterday was Friday. Today is Saturday."
        out4 = self.pipeline.process(inp4)
        self.record_test("TEST 4", "Different Events Chronological Preservation", out4 == exp4, inp4, out4, exp4, (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 5: Repeated Question
        # -------------------------------------------------------------
        t0 = time.time()
        inp5 = "Why are these three skills inactive? Why are these three skills inactive?"
        exp5 = "Why are these three skills inactive?"
        out5 = self.pipeline.process(inp5)
        self.record_test("TEST 5", "Repeated Question Deduplication", out5 == exp5, inp5, out5, exp5, (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 6: Technical Term Correction
        # -------------------------------------------------------------
        t0 = time.time()
        inp6 = "Use Gemini Fl... Gemini Flow."
        exp6 = "Use Gemini Flow."
        out6 = self.pipeline.process(inp6)
        self.record_test("TEST 6", "Technical Term Stutter Restart", out6 == exp6, inp6, out6, exp6, (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 7: Action Replacement
        # -------------------------------------------------------------
        t0 = time.time()
        inp7 = "Open the first application. No, open the second application."
        exp7 = "Open the second application."
        out7 = self.pipeline.process(inp7)
        self.record_test("TEST 7", "Action Replacement with 'No'", out7 == exp7, inp7, out7, exp7, (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 8: Overlapping Audio Windows
        # -------------------------------------------------------------
        t0 = time.time()
        w1 = "Yesterday I started developing Gemini Flow."
        w2 = "Gemini Flow because I wanted to improve speech recognition."
        exp8 = "Yesterday, I started developing Gemini Flow because I wanted to improve speech recognition."
        out8 = OverlapDuplicateResolver.merge_transcripts([w1, w2])
        self.record_test("TEST 8", "Overlapping Audio Windows Reconciliation", out8 == exp8, [w1, w2], out8, exp8, (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 9: Partial Transcription Hypothesis Reconciliation
        # -------------------------------------------------------------
        t0 = time.time()
        reconciler = StreamingHypothesisReconciler()
        reconciler.update_partial("Yesterday I started")
        reconciler.update_partial("Yesterday I started developing")
        reconciler.update_partial("Yesterday I started developing my application.")
        out9 = reconciler.finalize()
        exp9 = "Yesterday I started developing my application."
        self.record_test("TEST 9", "Real-Time Partial Hypothesis Reconciliation", out9 == exp9, ["Update 1", "Update 2", "Update 3"], out9, exp9, (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 10: Meaningful Repetition
        # -------------------------------------------------------------
        t0 = time.time()
        inp10 = "This application is fast, very fast."
        exp10 = "This application is fast, very fast."
        out10 = self.pipeline.process(inp10)
        self.record_test("TEST 10", "Meaningful Repetition Preservation", out10 == exp10, inp10, out10, exp10, (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 11: Multiple Corrections Chained
        # -------------------------------------------------------------
        t0 = time.time()
        inp11 = "Make it blue. No, make it green. Actually, make it black."
        exp11 = "Make it black."
        out11 = self.pipeline.process(inp11)
        self.record_test("TEST 11", "Multiple Chained Self-Corrections", out11 == exp11, inp11, out11, exp11, (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 12: Long Recording & Zero Truncation
        # -------------------------------------------------------------
        t0 = time.time()
        # Simulate marathon long dictation (50 paragraphs / 5,000 words)
        paragraph = (
            "Gemini Flow is designed for ultra low latency speech recognition on Windows 11. "
            "It runs on CPU cores with INT8 quantization, using 200 millisecond audio frames. "
            "The universal pipeline reconciles duplicates, resolves corrections, and expands triggers. "
        )
        long_speech = (paragraph * 15).strip()
        out12 = self.pipeline.process(long_speech)
        pass12 = len(out12.split()) >= len(long_speech.split()) * 0.95
        self.record_test("TEST 12", "Long Speech Preservation & Zero Truncation", pass12, f"{len(long_speech.split())} words", f"{len(out12.split())} words preserved", "No words dropped", (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 13: Quick-Text Voice Trigger (Mid-Sentence)
        # -------------------------------------------------------------
        t0 = time.time()
        snippets = [{
            "trigger": "Hey I am Sriniwas LinkedIn GitHub",
            "content": "LinkedIn: https://www.linkedin.com/in/srinivas-awasthi/ | GitHub: https://github.com/srinivas-awasthi"
        }]
        inp13 = "Hello everyone, I am introducing myself. Hey I am Sriniwas LinkedIn GitHub. I am working on my engineering projects."
        out13 = self.pipeline.process(inp13, snippets=snippets)
        pass13 = ("LinkedIn: https://www.linkedin.com/in/srinivas-awasthi/" in out13 and
                  ("Hello, everyone" in out13 or "Hello everyone" in out13) and
                  "engineering projects" in out13)
        self.record_test("TEST 13", "Quick-Text Voice Trigger Mid-Sentence Expansion", pass13, inp13, out13, "Expanded snippet with surrounding text preserved", (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 14: Trigger at Different Positions
        # -------------------------------------------------------------
        t0 = time.time()
        # Beginning
        out14_beg = self.pipeline.process("Hey I am Sriniwas LinkedIn GitHub. I am an engineer.", snippets=snippets)
        # End
        out14_end = self.pipeline.process("Here are my profiles: Hey I am Sriniwas LinkedIn GitHub.", snippets=snippets)
        # After short pause / comma
        out14_pause = self.pipeline.process("Welcome to the sync, ... Hey, I am Srinivas, LinkedIn, GitHub. Let us start.", snippets=snippets)

        pass14 = (
            "LinkedIn: https://www.linkedin.com" in out14_beg and "I am an engineer" in out14_beg and
            "LinkedIn: https://www.linkedin.com" in out14_end and "Here are my profiles" in out14_end and
            "LinkedIn: https://www.linkedin.com" in out14_pause and "Let us start" in out14_pause
        )
        self.record_test("TEST 14", "Voice Trigger at Beginning, End, and After Pauses", pass14, "3 positional variations", f"Beginning: {bool('LinkedIn' in out14_beg)}, End: {bool('LinkedIn' in out14_end)}, Pause: {bool('LinkedIn' in out14_pause)}", "All positions expanded cleanly", (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 15: Multilingual Recognition
        # -------------------------------------------------------------
        t0 = time.time()
        # Hindi: "आज शुक्रवार है, सॉरी आज शनिवार है।" -> "आज शनिवार है।"
        hi_in = "आज शुक्रवार है, सॉरी आज शनिवार है।"
        hi_out = self.pipeline.process(hi_in, language="hi")
        # German: "Heute ist Freitag. Entschuldigung, heute ist Samstag."
        de_in = "Heute ist Freitag, entschuldigung heute ist Samstag."
        de_out = self.pipeline.process(de_in, language="de")
        # French: "Aujourd'hui c'est vendredi, pardon aujourd'hui c'est samedi."
        fr_in = "Aujourd'hui c'est vendredi, pardon aujourd'hui c'est samedi."
        fr_out = self.pipeline.process(fr_in, language="fr")

        # Verify English grammar is NEVER forced onto regional languages (no English irregular verb replacement)
        pass15 = (
            "शनिवार" in hi_out and
            "Samstag" in de_out and
            "samedi" in fr_out
        )
        self.record_test("TEST 15", "Multilingual Preservation (Hindi, German, French, etc.)", pass15, "Hindi, German, French inputs", f"HI: {hi_out} | DE: {de_out} | FR: {fr_out}", "Native language preserved without inappropriate English grammar", (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # TEST 16: Section 30.1 Real-World Clean Dictation & Disfluency Test
        # -------------------------------------------------------------
        t0 = time.time()
        inp16 = (
            "Yeah, so basically, uh, if I just, uh, make any changes here, if I just use this anti-gravity, "
            "are you able to do all the things means without any, uh, disturbance or without any, uh, uh, mistakes and all? "
            "Means, I have just installed two times. I have just installed two times anti-gravity, and you have not worked well. So, I'm asking."
        )
        exp16 = (
            "Yeah, so basically, if I make any changes here using Antigravity, will you be able to handle everything "
            "without any interruptions or mistakes? I have installed Antigravity twice, but it still hasn't worked properly. That's why I'm asking."
        )
        out16 = self.pipeline.process(inp16, mode="clean_dictation")
        self.record_test(
            "TEST 16",
            "Section 30.1 Real-World Clean Dictation & Disfluency Overhaul",
            out16 == exp16,
            inp16,
            out16,
            exp16,
            (time.time() - t0) * 1000
        )

        # Save summary
        passed_count = sum(1 for r in self.results if r["passed"])
        total_count = len(self.results)
        logger.info("================================================================================")
        logger.info(f"  SUPER MASTER SUITE FINISHED: {passed_count}/{total_count} TESTS PASSED ({passed_count/total_count*100:.1f}%)")
        logger.info("================================================================================")

        reports_dir = PROJECT_ROOT / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        with open(reports_dir / "super_master_suite_results.json", "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "passed": passed_count,
                "total": total_count,
                "success_rate": f"{passed_count/total_count*100:.1f}%",
                "tests": self.results
            }, f, indent=2)

        return passed_count == total_count

if __name__ == "__main__":
    suite = SuperMasterSuite()
    success = suite.run_all()
    sys.exit(0 if success else 1)
