"""
200 Consecutive Iteration Stress & Reliability Benchmark Suite for Gemini Flow.
Executes 200 uninterrupted passes across all core subsystems:
- Vocabulary Engine
- Custom Dictionary
- Quick Text (Snippets)
- All 16 Command Categories
- AI Dictation Pipeline & Verbal Self-Correction
- Profiles & Cost Productivity
"""
import sys
import time
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.vocabulary.vocab_engine import VocabularyEngine
from app.transcription.universal_pipeline import UniversalPipeline, VoiceTriggerExpander
from app.commands import COMMAND_REGISTRY, match_spoken_command
from app.profiles.profile_manager import ProfileManager
from app.cost_awareness import calculate_entry_cost, get_milestone_info
from app.gemini_engine import GeminiEngine

logging.basicConfig(level=logging.WARNING)

def run_200_iterations():
    print("=" * 80)
    print("  STARTING 200 CONSECUTIVE ITERATIONS VERIFICATION & STRESS AUDIT")
    print("=" * 80)

    vocab = VocabularyEngine.get_instance()
    pipeline = UniversalPipeline()
    prof_mgr = ProfileManager()

    custom_dict = [
        {"spoken": "local host", "replacement": "localhost"},
        {"spoken": "fast whisper", "replacement": "Faster-Whisper"},
        {"spoken": "anti gravity", "replacement": "Antigravity"}
    ]

    snippets = [
        {
            "trigger": "my social links",
            "content": "LinkedIn: https://www.linkedin.com/in/srinivas-awasthi/ | GitHub: https://github.com/srinivas-awasthi"
        },
        {
            "trigger": "meeting intro",
            "content": "Hi everyone, thank you for joining today's session."
        }
    ]

    total_iterations = 200
    failed_iterations = []
    t_global_start = time.time()

    # We run Round 1 (1 to 100) and Round 2 (101 to 200)
    for iteration in range(1, total_iterations + 1):
        t_iter_start = time.time()
        round_num = 1 if iteration <= 100 else 2
        
        try:
            # 1. Vocabulary Engine Test
            v_in = "Using anti gravity, fast whisper on olama with type script and camel case"
            v_out = vocab.normalize(v_in)
            assert "Antigravity" in v_out, f"Vocab Antigravity missing: {v_out}"
            assert "Faster-Whisper" in v_out, f"Vocab Faster-Whisper missing: {v_out}"
            assert "Ollama" in v_out, f"Vocab Ollama missing: {v_out}"
            assert "TypeScript" in v_out, f"Vocab TypeScript missing: {v_out}"
            assert "camelCase" in v_out, f"Vocab camelCase missing: {v_out}"

            # 2. Custom Dictionary Test
            d_in = "Deploy to local host using fast whisper"
            d_out = GeminiEngine.apply_dictionary(d_in, custom_dict)
            assert "localhost" in d_out, f"Dictionary localhost failed: {d_out}"
            assert "Faster-Whisper" in d_out, f"Dictionary Faster-Whisper failed: {d_out}"

            # 3. Quick Text (Snippets) Test
            s_in = "Please check my social links before meeting intro starts"
            s_out = VoiceTriggerExpander.expand_triggers(s_in, snippets)
            assert "https://www.linkedin.com/in/srinivas-awasthi/" in s_out, f"Snippet link missing: {s_out}"
            assert "Hi everyone, thank you for joining" in s_out, f"Snippet intro missing: {s_out}"

            # 4. All 16 Command Categories Trigger & Validator Tests
            for cmd in COMMAND_REGISTRY:
                trig = cmd.trigger_phrases[0]
                sample_utterance = f"{trig}: {cmd.sample_input}"
                matched = match_spoken_command(sample_utterance)
                assert matched is not None, f"Command {cmd.id} failed trigger match on iter {iteration}"
                m_cmd, payload = matched
                assert m_cmd.id == cmd.id, f"Command mismatch: expected {cmd.id}, got {m_cmd.id}"
                ok_empty, _ = cmd.validator(cmd.sample_input, "")
                assert not ok_empty, f"Validator {cmd.id} accepted empty output"

            # 5. AI Dictation & Universal Pipeline Core Speech Transformations
            # 5a. Duplicate Sentence Deduplication
            p1_in = "I want to improve Gemini Flow. I want to improve Gemini Flow."
            p1_out = pipeline.process(p1_in)
            assert p1_out == "I want to improve Gemini Flow.", f"Dedup failed: {p1_out}"

            # 5b. Verbal Self-Correction with 'Actually'
            p2_in = "It's Friday. Actually, it's Saturday."
            p2_out = pipeline.process(p2_in)
            assert p2_out == "It's Saturday.", f"Correction with actually failed: {p2_out}"

            # 5c. Attribute Replacement without Keyword
            p3_in = "Today is Friday. Today is Saturday."
            p3_out = pipeline.process(p3_in)
            assert p3_out == "Today is Saturday.", f"Correction without keyword failed: {p3_out}"

            # 5d. Direct Question Deduplication & Preservation
            p4_in = "Where is the configuration file? Where is the configuration file?"
            p4_out = pipeline.process(p4_in)
            assert p4_out == "Where is the configuration file?", f"Direct question deduplication failed: {p4_out}"

            # 5e. Action Replacement with 'No'
            p5_in = "Open the first application. No, open the second application."
            p5_out = pipeline.process(p5_in)
            assert p5_out == "Open the second application.", f"Action replacement failed: {p5_out}"

            # 6. Cost Productivity Test
            cost = calculate_entry_cost("gemini-3.5-flash-lite", duration_sec=10.0, input_chars=150, output_chars=150)
            assert cost > 0.0, f"Cost calculation returned <= 0: {cost}"
            m_info = get_milestone_info(1200)
            assert m_info.rank_title, "Milestone rank title missing"

            # 7. Profiles Switch & Prompt Retrieval
            active_p = prof_mgr.get_active_profile()
            assert active_p.name, "Active profile name missing"

            iter_duration_ms = (time.time() - t_iter_start) * 1000

            if iteration % 25 == 0 or iteration in (1, 50, 100, 150, 200):
                print(f"[Round {round_num}] Iteration {iteration:03d}/200: PASS (All Subsystems OK | Latency: {iter_duration_ms:.1f}ms)")

        except AssertionError as ae:
            print(f"[FAIL] Iteration {iteration}: {ae}")
            failed_iterations.append((iteration, str(ae)))
        except Exception as ex:
            print(f"[ERROR] Iteration {iteration}: Unexpected exception {ex}")
            failed_iterations.append((iteration, str(ex)))

    total_time = time.time() - t_global_start
    print("=" * 80)
    print(f"200-ITERATION STRESS AUDIT COMPLETE in {total_time:.2f}s (Avg {total_time/total_iterations*1000:.1f}ms per full-stack iteration)")
    print(f"Total Iterations: {total_iterations}")
    print(f"Passed:           {total_iterations - len(failed_iterations)}/{total_iterations} ({(total_iterations - len(failed_iterations))/total_iterations*100:.1f}%)")
    print(f"Failed:           {len(failed_iterations)}")
    print("=" * 80)

    if failed_iterations:
        print("\nSummary of Failures:")
        for it, err in failed_iterations:
            print(f"  - Iteration {it}: {err}")
        sys.exit(1)
    else:
        print("ALL 200 ITERATIONS PASSED WITH 100.0% SUCCESS AND ZERO FAILURES!")

if __name__ == "__main__":
    run_200_iterations()
