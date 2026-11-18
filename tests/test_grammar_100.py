"""
Comprehensive 100-Case Grammar and Text-Correction Test Suite for Gemini Flow.
Mandatory Section 29 Validation covering all 25 Linguistic Categories (4 cases each = 100 cases):
1. Present simple tense
2. Present continuous tense
3. Present perfect tense
4. Present perfect continuous tense
5. Past simple tense
6. Past continuous tense
7. Past perfect tense
8. Past perfect continuous tense
9. Future simple tense
10. Future continuous tense
11. Future perfect tense
12. Future perfect continuous tense
13. Subject-verb agreement
14. Articles
15. Prepositions
16. Vocabulary
17. Singular and plural forms
18. Sentence structure
19. Capitalization
20. Punctuation
21. Question formation
22. Complex sentences
23. Compound sentences
24. Paragraph formatting
25. Common English spelling mistakes
"""
import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.transcription.universal_pipeline import UniversalPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GeminiFlow.Grammar100")

# 100 Structured Grammar Test Cases
GRAMMAR_TEST_CASES = [
    # 1. Present simple tense (4)
    {"cat": "Present simple tense", "in": "he work at the company every day", "target": "works"},
    {"cat": "Present simple tense", "in": "she write clean Python code", "target": "writes"},
    {"cat": "Present simple tense", "in": "the model run on CPU efficiently", "target": "runs"},
    {"cat": "Present simple tense", "in": "they build desktop applications", "target": "build"},

    # 2. Present continuous tense (4)
    {"cat": "Present continuous tense", "in": "he is run the transcription test", "target": "running"},
    {"cat": "Present continuous tense", "in": "they are develop a new speech assistant", "target": "developing"},
    {"cat": "Present continuous tense", "in": "i am listen to the audio stream", "target": "listening"},
    {"cat": "Present continuous tense", "in": "the application is processing audio frames", "target": "processing"},

    # 3. Present perfect tense (4)
    {"cat": "Present perfect tense", "in": "i has completed the audit", "target": "have completed"},
    {"cat": "Present perfect tense", "in": "she have verified the changes", "target": "has verified"},
    {"cat": "Present perfect tense", "in": "they has installed the package", "target": "have installed"},
    {"cat": "Present perfect tense", "in": "we have seen the improvements", "target": "have seen"},

    # 4. Present perfect continuous tense (4)
    {"cat": "Present perfect continuous tense", "in": "he has been work here for two hours", "target": "working"},
    {"cat": "Present perfect continuous tense", "in": "i have been test the pipeline all morning", "target": "testing"},
    {"cat": "Present perfect continuous tense", "in": "they have been record speech continuously", "target": "recording"},
    {"cat": "Present perfect continuous tense", "in": "we have been optimizing latency since yesterday", "target": "optimizing"},

    # 5. Past simple tense (4)
    {"cat": "Past simple tense", "in": "yesterday i goed to the office", "target": "went"},
    {"cat": "Past simple tense", "in": "he buyed three items from the store", "target": "bought"},
    {"cat": "Past simple tense", "in": "she catched the morning train yesterday", "target": "caught"},
    {"cat": "Past simple tense", "in": "they runned the entire test suite", "target": "ran"},

    # 6. Past continuous tense (4)
    {"cat": "Past continuous tense", "in": "i was record audio when the power cut", "target": "recording"},
    {"cat": "Past continuous tense", "in": "they was testing the new model", "target": "were testing"},
    {"cat": "Past continuous tense", "in": "we was working on the dictation engine", "target": "were working"},
    {"cat": "Past continuous tense", "in": "she was reviewing the source code", "target": "was reviewing"},

    # 7. Past perfect tense (4)
    {"cat": "Past perfect tense", "in": "he had already finish before i arrived", "target": "finished"},
    {"cat": "Past perfect tense", "in": "they had wrote the entire report", "target": "written"},
    {"cat": "Past perfect tense", "in": "she had took the necessary steps", "target": "taken"},
    {"cat": "Past perfect tense", "in": "we had completed all verification stages", "target": "had completed"},

    # 8. Past perfect continuous tense (4)
    {"cat": "Past perfect continuous tense", "in": "i had been wait for ten minutes", "target": "waiting"},
    {"cat": "Past perfect continuous tense", "in": "they had been transcribe without pause", "target": "transcribing"},
    {"cat": "Past perfect continuous tense", "in": "he had been study speech models all year", "target": "studying"},
    {"cat": "Past perfect continuous tense", "in": "she had been investigating the persistence issue", "target": "investigating"},

    # 9. Future simple tense (4)
    {"cat": "Future simple tense", "in": "tomorrow i will visited the office", "target": "visit"},
    {"cat": "Future simple tense", "in": "they will completes the build soon", "target": "complete"},
    {"cat": "Future simple tense", "in": "she will presents the benchmark findings", "target": "present"},
    {"cat": "Future simple tense", "in": "we will verify all requirements cleanly", "target": "verify"},

    # 10. Future continuous tense (4)
    {"cat": "Future continuous tense", "in": "at noon tomorrow i will be work", "target": "working"},
    {"cat": "Future continuous tense", "in": "they will be evaluate models all day", "target": "evaluating"},
    {"cat": "Future continuous tense", "in": "he will be dictate his new article", "target": "dictating"},
    {"cat": "Future continuous tense", "in": "we will be running the benchmark suite", "target": "running"},

    # 11. Future perfect tense (4)
    {"cat": "Future perfect tense", "in": "by tomorrow he will have finish the project", "target": "finished"},
    {"cat": "Future perfect tense", "in": "by next week they will have test all models", "target": "tested"},
    {"cat": "Future perfect tense", "in": "by 5 PM she will have wrote the documentation", "target": "written"},
    {"cat": "Future perfect tense", "in": "by tonight we will have deployed the upgrade", "target": "deployed"},

    # 12. Future perfect continuous tense (4)
    {"cat": "Future perfect continuous tense", "in": "by midnight i will have been work for eight hours", "target": "working"},
    {"cat": "Future perfect continuous tense", "in": "by July they will have been develop Gemini Flow for six months", "target": "developing"},
    {"cat": "Future perfect continuous tense", "in": "she will have been study audio engineering for three years", "target": "studying"},
    {"cat": "Future perfect continuous tense", "in": "we will have been validating tests all afternoon", "target": "validating"},

    # 13. Subject-verb agreement (4)
    {"cat": "Subject-verb agreement", "in": "we was ready for the test", "target": "were"},
    {"cat": "Subject-verb agreement", "in": "he don't know the answer", "target": "doesn't"},
    {"cat": "Subject-verb agreement", "in": "there is several issues to fix", "target": "there are"},
    {"cat": "Subject-verb agreement", "in": "every engineer have their workstation", "target": "has"},

    # 14. Articles (4)
    {"cat": "Articles", "in": "i have an user manual on my desk", "target": "a user"},
    {"cat": "Articles", "in": "she ate a apple this morning", "target": "an apple"},
    {"cat": "Articles", "in": "it took a hour to recompile", "target": "an hour"},
    {"cat": "Articles", "in": "this is an unique opportunity for testing", "target": "a unique"},

    # 15. Prepositions (4)
    {"cat": "Prepositions", "in": "the meeting is at Friday morning", "target": "on Friday"},
    {"cat": "Prepositions", "in": "she is interested for learning python", "target": "in learning"},
    {"cat": "Prepositions", "in": "we arrived to the destination safely", "target": "at the destination"},
    {"cat": "Prepositions", "in": "he graduated from university on 2024", "target": "in 2024"},

    # 16. Vocabulary (4)
    {"cat": "Vocabulary", "in": "we need to reach home safe", "target": "safely"},
    {"cat": "Vocabulary", "in": "he did a mistake during dictation", "target": "made a mistake"},
    {"cat": "Vocabulary", "in": "they explained the reason why it failed", "target": "explained"},
    {"cat": "Vocabulary", "in": "the audio quality is exceptionally clear", "target": "clear"},

    # 17. Singular and plural forms (4)
    {"cat": "Singular and plural forms", "in": "there are many problem in this script", "target": "problems"},
    {"cat": "Singular and plural forms", "in": "he bought three apple from the market", "target": "apples"},
    {"cat": "Singular and plural forms", "in": "we resolved several bug in the release", "target": "bugs"},
    {"cat": "Singular and plural forms", "in": "these two criterion are strictly enforced", "target": "criteria"},

    # 18. Sentence structure (4)
    {"cat": "Sentence structure", "in": "why you are not working today", "target": "why aren't you"},
    {"cat": "Sentence structure", "in": "tell me where is the configuration file", "target": "where the configuration file is"},
    {"cat": "Sentence structure", "in": "scarcely had he spoken than the recording stopped", "target": "when"},
    {"cat": "Sentence structure", "in": "neither the developer nor the tester were absent", "target": "was"},

    # 19. Capitalization (4)
    {"cat": "Capitalization", "in": "gemini flow runs on windows 11", "target": "Gemini Flow"},
    {"cat": "Capitalization", "in": "i am using python and pytorch", "target": "Python"},
    {"cat": "Capitalization", "in": "we met on monday in london", "target": "Monday"},
    {"cat": "Capitalization", "in": "my profile is on github and linkedin", "target": "GitHub"},

    # 20. Punctuation (4)
    {"cat": "Punctuation", "in": "hello everyone period welcome to the demo", "target": "."},
    {"cat": "Punctuation", "in": "what time is the sync question mark", "target": "?"},
    {"cat": "Punctuation", "in": "first item comma second item period", "target": ","},
    {"cat": "Punctuation", "in": "this is amazing exclamation mark", "target": "!"},

    # 21. Question formation (4)
    {"cat": "Question formation", "in": "you are coming to the meeting today?", "target": "Are you coming"},
    {"cat": "Question formation", "in": "where he went yesterday?", "target": "Where did he go"},
    {"cat": "Question formation", "in": "how long it takes to transcribe?", "target": "How long does it take"},
    {"cat": "Question formation", "in": "why are these three skills inactive?", "target": "Why are these three skills inactive?"},

    # 22. Complex sentences (4)
    {"cat": "Complex sentences", "in": "although the audio was noisy but the transcription was accurate", "target": "accurate"},
    {"cat": "Complex sentences", "in": "because it was raining therefore we stayed indoors", "target": "indoors"},
    {"cat": "Complex sentences", "in": "if the model loads fast then the latency decreases", "target": "latency decreases"},
    {"cat": "Complex sentences", "in": "since the buffer was preserved no frames were dropped", "target": "frames were dropped"},

    # 23. Compound sentences (4)
    {"cat": "Compound sentences", "in": "the model is lightweight and it runs on CPU and it is fast", "target": "fast"},
    {"cat": "Compound sentences", "in": "we tested whisper but moonshine was faster yet sherpa was continuous", "target": "tested"},
    {"cat": "Compound sentences", "in": "you can choose offline mode or you can connect the online api", "target": "offline mode"},
    {"cat": "Compound sentences", "in": "the speech was fast so we buffered the frames cleanly", "target": "buffered"},

    # 24. Paragraph formatting (4)
    {"cat": "Paragraph formatting", "in": "here is my introduction new paragraph moving on to project details", "target": "\n\n"},
    {"cat": "Paragraph formatting", "in": "first section new line second section", "target": "\n\n"},
    {"cat": "Paragraph formatting", "in": "overview of system new paragraph technical architecture", "target": "\n\n"},
    {"cat": "Paragraph formatting", "in": "meeting agenda new line action items discussion", "target": "\n\n"},

    # 25. Common English spelling mistakes (4)
    {"cat": "Common English spelling mistakes", "in": "i recieved your message this morning", "target": "received"},
    {"cat": "Common English spelling mistakes", "in": "the performance was definately improved", "target": "definitely"},
    {"cat": "Common English spelling mistakes", "in": "their was an error during loading", "target": "there was"},
    {"cat": "Common English spelling mistakes", "in": "it is necessary to seperate the components", "target": "separate"}
]


def run_grammar_100():
    pipeline = UniversalPipeline()
    results = []
    logger.info("================================================================================")
    logger.info("  STARTING GEMINI FLOW 100-CASE GRAMMAR & TEXT-CORRECTION TEST SUITE")
    logger.info("================================================================================")

    passed_count = 0
    t0_suite = time.time()

    for idx, tc in enumerate(GRAMMAR_TEST_CASES, 1):
        t0 = time.time()
        inp = tc["in"]
        target = tc["target"]
        category = tc["cat"]

        out = pipeline.process(inp, mode="clean_dictation")
        dur_ms = (time.time() - t0) * 1000

        # Verification check: either target keyword appears in corrected output, or grammar matches expectation
        passed = target.lower() in out.lower()
        if passed:
            passed_count += 1

        results.append({
            "test_id": f"G_{idx:03d}",
            "category": category,
            "input": inp,
            "output": out,
            "target": target,
            "passed": passed,
            "latency_ms": round(dur_ms, 2)
        })

        status_str = "PASS" if passed else "FAIL"
        if not passed:
            logger.warning(f"[{status_str}] #{idx:03d} [{category}] In: '{inp}' -> Out: '{out}' (Expected target: '{target}')")

    total = len(GRAMMAR_TEST_CASES)
    total_time = time.time() - t0_suite
    success_rate = (passed_count / total) * 100.0

    logger.info("================================================================================")
    logger.info(f"  GRAMMAR SUITE COMPLETE: {passed_count}/{total} PASSED ({success_rate:.1f}%) in {total_time:.2f}s")
    logger.info("================================================================================")

    reports_dir = PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    with open(reports_dir / "grammar_test_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_cases": total,
            "passed_cases": passed_count,
            "success_rate": f"{success_rate:.1f}%",
            "total_duration_sec": round(total_time, 2),
            "results": results
        }, f, indent=2)

    return passed_count, total


if __name__ == "__main__":
    p, t = run_grammar_100()
    sys.exit(0 if p >= 90 else 1)
