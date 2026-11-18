"""
50x Per-Section Deep Stress Verification Suite for Gemini Flow.
Executes 50 independent iterations for each individual section and category:
1. Section 1: Vocabulary Engine (50 iterations)
2. Section 2: Custom Dictionary (50 iterations)
3. Section 3: Quick Text / Snippets (50 iterations)
4. Section 4: Developer Productivity Profiles (50 iterations)
5. Section 5: All 16 Command Categories (50 iterations each = 800 evaluations)
6. Section 6: Hotkeys AI Prompt (Alt+P) & Universal Transform (50 iterations)
7. Section 7: AI Dictation Pipeline & Verbal Self-Corrections (50 iterations)
8. Section 8: Cost Productivity & Dynamic Pricing Analytics (50 iterations)
9. Section 9: Speech Model Engine Latency & Audio Processing (50 iterations)
"""
import sys
import time
import io
import wave
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.vocabulary.vocab_engine import VocabularyEngine
from app.transcription.universal_pipeline import UniversalPipeline, VoiceTriggerExpander
from app.commands import COMMAND_REGISTRY, match_spoken_command, CommandDefinition
from app.profiles.profile_manager import ProfileManager, BUILTIN_PROFILES
from app.cost_awareness import calculate_entry_cost, get_milestone_info, MODEL_PRICING
from app.transformation.transform_engine import TransformEngine, TransformType, TRANSFORM_PRESETS
from app.transcription.engine import UnifiedTranscriptionEngine
from app.gemini_engine import GeminiEngine

logging.basicConfig(level=logging.WARNING)

def run_section_audit_50x():
    print("=" * 85)
    print("   GEMINI FLOW: 50x PER-SECTION & PER-CATEGORY EXHAUSTIVE AUDIT SUITE")
    print("=" * 85)

    vocab = VocabularyEngine.get_instance()
    pipeline = UniversalPipeline()
    prof_mgr = ProfileManager()
    trans_engine = UnifiedTranscriptionEngine()

    total_checks = 0
    total_passed = 0
    section_reports = {}

    # -------------------------------------------------------------------------
    # SECTION 1: VOCABULARY ENGINE (50 ITERATIONS)
    # -------------------------------------------------------------------------
    t0 = time.time()
    s1_pass = 0
    test_vocab_cases = [
        ("I am testing anti gravity on olama with fast whisper", ["Antigravity", "Ollama", "Faster-Whisper"]),
        ("Check my github repository for typescript in camel case", ["GitHub", "TypeScript", "camelCase"]),
        ("Train pytorch models on leetcode with snake case", ["PyTorch", "LeetCode", "snake_case"]),
        ("Enter the api key into gemini-flow settings", ["API key", "Gemini Flow"])
    ]
    for i in range(50):
        inp, expected = test_vocab_cases[i % len(test_vocab_cases)]
        out = vocab.normalize(inp)
        if all(term.lower() in out.lower() for term in expected):
            s1_pass += 1
    s1_time = time.time() - t0
    section_reports["1. Vocabulary Engine"] = (s1_pass, 50, s1_time)
    print(f"[{'PASS' if s1_pass == 50 else 'FAIL'}] Section 1: Vocabulary Engine -> {s1_pass}/50 Passed ({s1_time*1000:.1f}ms total, {s1_time/50*1000:.2f}ms/op)")

    # -------------------------------------------------------------------------
    # SECTION 2: CUSTOM DICTIONARY (50 ITERATIONS)
    # -------------------------------------------------------------------------
    t0 = time.time()
    s2_pass = 0
    custom_dict = [
        {"spoken": "local host", "replacement": "localhost"},
        {"spoken": "fast whisper", "replacement": "Faster-Whisper"},
        {"spoken": "anti gravity", "replacement": "Antigravity"},
        {"spoken": "gemini flow", "replacement": "Gemini Flow"}
    ]
    test_dict_cases = [
        ("Deploy on local host", "localhost"),
        ("Use fast whisper for transcription", "Faster-Whisper"),
        ("Integrate anti gravity agent", "Antigravity"),
        ("Launch gemini flow desktop", "Gemini Flow")
    ]
    for i in range(50):
        inp, exp = test_dict_cases[i % len(test_dict_cases)]
        out = GeminiEngine.apply_dictionary(inp, custom_dict)
        if exp in out:
            s2_pass += 1
    s2_time = time.time() - t0
    section_reports["2. Custom Dictionary"] = (s2_pass, 50, s2_time)
    print(f"[{'PASS' if s2_pass == 50 else 'FAIL'}] Section 2: Custom Dictionary -> {s2_pass}/50 Passed ({s2_time*1000:.1f}ms total, {s2_time/50*1000:.2f}ms/op)")

    # -------------------------------------------------------------------------
    # SECTION 3: QUICK TEXT / SNIPPETS (50 ITERATIONS)
    # -------------------------------------------------------------------------
    t0 = time.time()
    s3_pass = 0
    snippets = [
        {"trigger": "my social links", "content": "LinkedIn: https://linkedin.com/in/srinivas | GitHub: https://github.com/srinivas"},
        {"trigger": "meeting intro", "content": "Hi everyone, thank you for joining today's session."}
    ]
    test_snippet_cases = [
        ("my social links please review", "LinkedIn: https://linkedin.com/in/srinivas"),
        ("before we start meeting intro today", "Hi everyone, thank you for joining"),
        ("check this out my social links and share", "GitHub: https://github.com/srinivas"),
        ("lets begin with meeting intro right now", "thank you for joining today's session")
    ]
    for i in range(50):
        inp, exp = test_snippet_cases[i % len(test_snippet_cases)]
        out = VoiceTriggerExpander.expand_triggers(inp, snippets)
        if exp in out:
            s3_pass += 1
    s3_time = time.time() - t0
    section_reports["3. Quick Text (Snippets)"] = (s3_pass, 50, s3_time)
    print(f"[{'PASS' if s3_pass == 50 else 'FAIL'}] Section 3: Quick Text (Snippets) -> {s3_pass}/50 Passed ({s3_time*1000:.1f}ms total, {s3_time/50*1000:.2f}ms/op)")

    # -------------------------------------------------------------------------
    # SECTION 4: DEVELOPER PROFILES (50 ITERATIONS)
    # -------------------------------------------------------------------------
    t0 = time.time()
    s4_pass = 0
    profile_ids = list(BUILTIN_PROFILES.keys())
    for i in range(50):
        target_pid = profile_ids[i % len(profile_ids)]
        prof_mgr.set_active_profile(target_pid)
        act = prof_mgr.get_active_profile()
        if act.id == target_pid and len(act.system_prompt_addition) > 10 and act.name:
            s4_pass += 1
    s4_time = time.time() - t0
    section_reports["4. Developer Profiles"] = (s4_pass, 50, s4_time)
    print(f"[{'PASS' if s4_pass == 50 else 'FAIL'}] Section 4: Developer Profiles -> {s4_pass}/50 Passed ({s4_time*1000:.1f}ms total, {s4_time/50*1000:.2f}ms/op)")

    # -------------------------------------------------------------------------
    # SECTION 5: ALL 16 COMMAND CATEGORIES (50 ITERATIONS EACH = 800 RUNS)
    # -------------------------------------------------------------------------
    t0 = time.time()
    s5_pass = 0
    cmd_count = len(COMMAND_REGISTRY)
    for cmd_idx, cmd in enumerate(COMMAND_REGISTRY, 1):
        cmd_p = 0
        for i in range(50):
            trig = cmd.trigger_phrases[i % len(cmd.trigger_phrases)]
            sample_inp = cmd.sample_input
            test_utterance = f"{trig}: {sample_inp}"
            matched = match_spoken_command(test_utterance)
            if matched and matched[0].id == cmd.id and len(matched[1]) > 0:
                # Test validator contract on empty (must reject) and sample
                bad_val, _ = cmd.validator(sample_inp, "")
                if not bad_val:
                    cmd_p += 1
        s5_pass += cmd_p
        assert cmd_p == 50, f"Command {cmd.id} failed some of 50 iterations ({cmd_p}/50)"
    s5_time = time.time() - t0
    section_reports["5. All 16 Command Categories (800 checks)"] = (s5_pass, 800, s5_time)
    print(f"[{'PASS' if s5_pass == 800 else 'FAIL'}] Section 5: All 16 Command Categories -> {s5_pass}/800 Passed ({s5_time*1000:.1f}ms total, {s5_time/800*1000:.2f}ms/op)")

    # -------------------------------------------------------------------------
    # SECTION 6: HOTKEYS AI PROMPT (ALT+P) & UNIVERSAL TRANSFORMATION (50 ITERATIONS)
    # -------------------------------------------------------------------------
    t0 = time.time()
    s6_pass = 0
    for i in range(50):
        # Verify TransformEngine builds prompt instruction cleanly with zero empty fields
        prompt_instruction = TransformEngine.build_system_instruction(TransformType.CONVERT_PROMPT)
        preset = TransformEngine.get_preset(TransformType.CONVERT_PROMPT)
        # Test universal preset retrieval
        alt_preset = TransformEngine.get_preset(TransformType.PROFESSIONAL)
        if "AI Prompt Architect" in prompt_instruction and preset.recommended_model and alt_preset.temperature > 0.0:
            s6_pass += 1
    s6_time = time.time() - t0
    section_reports["6. Hotkeys Transformation Engine"] = (s6_pass, 50, s6_time)
    print(f"[{'PASS' if s6_pass == 50 else 'FAIL'}] Section 6: Hotkeys Transformation Engine -> {s6_pass}/50 Passed ({s6_time*1000:.1f}ms total, {s6_time/50*1000:.2f}ms/op)")

    # -------------------------------------------------------------------------
    # SECTION 7: AI DICTATION & VERBAL SELF-CORRECTIONS (50 ITERATIONS)
    # -------------------------------------------------------------------------
    t0 = time.time()
    s7_pass = 0
    dictation_cases = [
        ("I want to improve Gemini Flow. I want to improve Gemini Flow.", "I want to improve Gemini Flow."),
        ("It's Friday. Actually, it's Saturday.", "It's Saturday."),
        ("Today is Friday. Today is Saturday.", "Today is Saturday."),
        ("Where is the configuration file? Where is the configuration file?", "Where is the configuration file?"),
        ("Open the first window. No, open the second window.", "Open the second window.")
    ]
    for i in range(50):
        inp, exp = dictation_cases[i % len(dictation_cases)]
        out = pipeline.process(inp)
        if out == exp:
            s7_pass += 1
    s7_time = time.time() - t0
    section_reports["7. AI Dictation & Self-Correction Pipeline"] = (s7_pass, 50, s7_time)
    print(f"[{'PASS' if s7_pass == 50 else 'FAIL'}] Section 7: AI Dictation Pipeline -> {s7_pass}/50 Passed ({s7_time*1000:.1f}ms total, {s7_time/50*1000:.2f}ms/op)")

    # -------------------------------------------------------------------------
    # SECTION 8: COST PRODUCTIVITY & PRICING ANALYTICS (50 ITERATIONS)
    # -------------------------------------------------------------------------
    t0 = time.time()
    s8_pass = 0
    for i in range(50):
        model_name = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"][i % 3]
        cost = calculate_entry_cost(model_name, duration_sec=float(i + 5), input_chars=100 * (i + 1), output_chars=50 * (i + 1))
        m_info = get_milestone_info(50 * (i + 1))
        if cost > 0.0 and m_info.rank_title and m_info.words_remaining >= 0:
            s8_pass += 1
    s8_time = time.time() - t0
    section_reports["8. Cost Productivity & Analytics"] = (s8_pass, 50, s8_time)
    print(f"[{'PASS' if s8_pass == 50 else 'FAIL'}] Section 8: Cost Productivity & Analytics -> {s8_pass}/50 Passed ({s8_time*1000:.1f}ms total, {s8_time/50*1000:.2f}ms/op)")

    # -------------------------------------------------------------------------
    # SECTION 9: SPEECH RECOGNITION ENGINE CONTRACT (50 ITERATIONS)
    # -------------------------------------------------------------------------
    t0 = time.time()
    s9_pass = 0
    # Create valid 0.5s 16kHz silence WAV
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b'\x00' * 16000)
    silence_wav = buf.getvalue()

    for i in range(50):
        transcript = trans_engine.transcribe(silence_wav, model_name="Offline Local Speech (Whisper AI)")
        if transcript.success and transcript.text == "" and any("silence" in str(w).lower() or "short" in str(w).lower() for w in transcript.warnings):
            s9_pass += 1
    s9_time = time.time() - t0
    section_reports["9. Speech Engine Contract & Silence VAD"] = (s9_pass, 50, s9_time)
    print(f"[{'PASS' if s9_pass == 50 else 'FAIL'}] Section 9: Speech Engine Contract & Silence VAD -> {s9_pass}/50 Passed ({s9_time*1000:.1f}ms total, {s9_time/50*1000:.2f}ms/op)")

    # -------------------------------------------------------------------------
    # GRAND TOTAL SUMMARY
    # -------------------------------------------------------------------------
    total_checks = sum(total for _, total, _ in section_reports.values())
    total_passed = sum(p for p, _, _ in section_reports.values())
    grand_time = sum(t for _, _, t in section_reports.values())

    print("\n" + "=" * 85)
    print("   GRAND MULTI-AGENT STRESS AUDIT SUMMARY (50x PER SECTION)")
    print("=" * 85)
    for section, (p, total, duration) in section_reports.items():
        status = "FLAWLESS PASS" if p == total else "FAILED"
        print(f"  • {section:<50} : {p:>4}/{total:<4} ({p/total*100:>5.1f}%) | {duration*1000:>6.1f}ms | {status}")
    print("-" * 85)
    print(f"  TOTAL CHECKS EXECUTED : {total_checks}")
    print(f"  TOTAL CHECKS PASSED   : {total_passed} ({total_passed/total_checks*100:.1f}%)")
    print(f"  TOTAL DURATION        : {grand_time:.2f}s (Average {grand_time/total_checks*1000:.2f}ms per operation)")
    print("=" * 85)

    if total_passed == total_checks:
        print("\n>>> ALL 1,200 CHECKS PASSED CONSECUTIVELY WITH ZERO FAILURES! <<<")
    else:
        print(f"\n>>> AUDIT ENCOUNTERED {total_checks - total_passed} FAILURES <<<")
        sys.exit(1)

if __name__ == "__main__":
    run_section_audit_50x()
