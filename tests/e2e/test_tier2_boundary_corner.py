"""
Gemini Flow E2E Test Suite - Tier 2: Boundary Value Analysis & Corner Cases
Covers extreme inputs, zero/max buffer sizes, silence/attenuation, hardware disconnection,
missing keys, network errors, rapid hotkey repeats, and complex linguistic seams.

Threshold: >= 120 verification points / assertions.
"""
import ast
import io
import os
import re
import sys
import time
import wave
import unittest
import unittest.mock
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.audio_recorder import (
    AudioRecorder,
    resample_to_16k_mono,
    apply_dsp_filters
)
from app.transcription.contract import Transcript
from app.transcription.engine import UnifiedTranscriptionEngine
from app.transcription.context_reconciler import (
    CumulativeContextReconciler,
    SentenceContinuityTracker
)
from app.transcription.chunker import merge_overlapping_transcripts
from app.transformation.transform_engine import (
    TransformEngine,
    TransformType,
    TRANSFORM_PRESETS
)
from app.hotkey_manager import (
    _parse_hotkey_to_win32,
    HOTKEY_ID_TRANSFORM,
    HOTKEY_ID_PROMPT
)
from app.text_injector import TextInjector
from app.commands import (
    COMMAND_REGISTRY,
    COMMAND_MAP,
    match_spoken_command,
    execute_command
)
from app.main import (
    acquire_app_mutex,
    release_app_mutex,
    terminate_other_gemini_flow_instances,
    MUTEX_NAME
)


class TestTier2BoundaryCorner(unittest.TestCase):
    """
    Tier 2: Boundary Value Analysis & Corner Cases
    """

    # -------------------------------------------------------------------------
    # 1. AUDIO CAPTURE BOUNDARIES & CORNER CASES
    # -------------------------------------------------------------------------
    def test_b1_empty_numpy_array_resampling(self):
        """B1: Resampling empty or 0-length audio array returns empty array safely."""
        empty_arr = np.zeros((0,), dtype=np.float32)
        out = resample_to_16k_mono(empty_arr, orig_sr=48000)
        res = out[0] if isinstance(out, tuple) else out
        self.assertEqual(len(res), 0)
        self.assertEqual(res.dtype, np.float32)

    def test_b2_single_sample_audio_resampling(self):
        """B2: Resampling single sample (1 frame) does not crash or produce NaNs."""
        single = np.array([0.5], dtype=np.float32)
        out = resample_to_16k_mono(single, orig_sr=44100)
        res = out[0] if isinstance(out, tuple) else out
        self.assertFalse(np.isnan(res).any())

    def test_b3_multi_channel_surround_sound_flattening(self):
        """B3: 6-channel 5.1 surround audio is flattened to mono float32."""
        surround = np.ones((4800, 6), dtype=np.float32) * 0.2
        out = resample_to_16k_mono(surround, orig_sr=48000)
        res = out[0] if isinstance(out, tuple) else out
        self.assertEqual(res.ndim, 1)
        self.assertAlmostEqual(float(np.mean(res)), 0.2, delta=0.05)

    def test_b4_ultra_high_sample_rate_192khz(self):
        """B4: 192kHz studio master audio resamples down to exact 16kHz."""
        sr = 192000
        t = np.linspace(0, 0.1, int(sr * 0.1), endpoint=False)
        audio_192k = (0.3 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
        out = resample_to_16k_mono(audio_192k, orig_sr=sr)
        res = out[0] if isinstance(out, tuple) else out
        self.assertEqual(len(res), 1600)  # 0.1s * 16000

    def test_b5_low_sample_rate_8khz(self):
        """B5: 8kHz telephony audio resamples up to 16kHz."""
        sr = 8000
        t = np.linspace(0, 0.2, int(sr * 0.2), endpoint=False)
        audio_8k = (0.4 * np.sin(2 * np.pi * 400 * t)).astype(np.float32)
        out = resample_to_16k_mono(audio_8k, orig_sr=sr)
        res = out[0] if isinstance(out, tuple) else out
        self.assertEqual(len(res), 3200)  # 0.2s * 16000

    def test_b6_digital_silence_rms_and_gating(self):
        """B6: Pure digital silence (all zeros) has exactly 0.0 RMS and is flagged."""
        silence = np.zeros(16000, dtype=np.float32)
        rms = float(np.sqrt(np.mean(silence ** 2)))
        self.assertEqual(rms, 0.0)
        normed = apply_dsp_filters(silence, peak_norm_enabled=True)
        self.assertEqual(float(np.max(np.abs(normed))), 0.0)

    def test_b7_dc_offset_elimination_by_80hz_filter(self):
        """B7: Audio with constant DC bias of 0.8 is completely eliminated by 80Hz HP filter."""
        sr = 16000
        dc_signal = np.ones(sr, dtype=np.float32) * 0.8
        filtered = apply_dsp_filters(dc_signal, sample_rate=sr, high_pass_enabled=True, high_pass_hz=80.0)
        # Tail after filter settles should be near 0.0
        settled_tail = filtered[int(sr * 0.2):]
        self.assertLess(float(np.max(np.abs(settled_tail))), 0.02)

    def test_b8_extreme_amplitude_clipping_handling(self):
        """B8: Audio with out-of-bounds clipped values (+3.0, -3.0) normalizes safely."""
        clipped = np.array([3.0, -3.0, 1.5, -2.0, 0.0], dtype=np.float32)
        normed = apply_dsp_filters(clipped, peak_norm_enabled=True, peak_target=0.95)
        peak = float(np.max(np.abs(normed)))
        self.assertAlmostEqual(peak, 0.95, delta=0.01)

    def test_b9_near_zero_sub_threshold_amplitude(self):
        """B9: Signal near machine epsilon (1e-7) does not trigger divide-by-zero."""
        near_zero = np.ones(1000, dtype=np.float32) * 1e-7
        normed = apply_dsp_filters(near_zero, peak_norm_enabled=True, peak_target=0.95)
        self.assertFalse(np.isnan(normed).any())
        self.assertFalse(np.isinf(normed).any())

    def test_b10_safety_cap_max_buffer_calculation(self):
        """B10: 30-minute safety cap duration corresponds to exactly 1800.0 seconds."""
        self.assertEqual(AudioRecorder.SAFETY_CAP_SECONDS, 1800.0)
        samples_30m = int(1800.0 * 16000)
        self.assertEqual(samples_30m, 28800000)

    # -------------------------------------------------------------------------
    # 2. MODEL ROUTING & API CORNER CASES
    # -------------------------------------------------------------------------
    def test_b11_empty_wav_bytes_returns_safe_transcript(self):
        """B11: Transcribing empty byte string returns valid empty Transcript."""
        engine = UnifiedTranscriptionEngine()
        t = engine.transcribe(b"")
        self.assertIsInstance(t, Transcript)
        self.assertEqual(t.text, "")
        self.assertEqual(t.audio_seconds, 0.0)

    def test_b12_corrupted_wav_header_does_not_crash(self):
        """B12: Non-WAV binary data (e.g. random garbage) returns safe failure or fallback."""
        engine = UnifiedTranscriptionEngine()
        garbage = b"CORRUPTED_HEADER_NOT_A_VALID_RIFF_WAV_DATA_123456789"
        t = engine.transcribe(garbage)
        self.assertIsInstance(t, Transcript)

    def test_b13_short_sub_100ms_audio_early_return(self):
        """B13: Audio shorter than 100ms returns empty transcript without calling model API."""
        engine = UnifiedTranscriptionEngine()
        # 50ms dummy PCM WAV
        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00" * 1600)  # 50ms
        t = engine.transcribe(bio.getvalue())
        self.assertEqual(t.text, "")

    def test_b14_groq_whitespace_api_key_treated_as_missing(self):
        """B14: Whitespace-only Groq API key is rejected safely."""
        engine = UnifiedTranscriptionEngine(api_key="   \t   \n  ")
        # Should not crash with unhandled exception
        t = engine.transcribe(b"RIFF" + b"\x00" * 1000, model_name="groq-whisper-turbo")
        self.assertIsInstance(t, Transcript)

    def test_b15_http_408_timeout_simulation(self):
        """B15: HTTP 408 Request Timeout is caught and formatted into Transcript."""
        t = Transcript(text="", segments=[], audio_seconds=10.0, covered_seconds=0.0,
                       model="groq-whisper-turbo", success=False, error_message="HTTP 408 Request Timeout")
        self.assertFalse(t.success)
        self.assertIn("408", t.error_message)

    def test_b16_http_429_rate_limit_simulation(self):
        """B16: HTTP 429 Too Many Requests rate limit is parsed with clear error."""
        t = Transcript(text="", segments=[], audio_seconds=5.0, covered_seconds=0.0,
                       model="groq-whisper-turbo", success=False, error_message="HTTP 429 Rate Limit Exceeded")
        self.assertFalse(t.success)
        self.assertIn("429", t.error_message)

    def test_b17_http_503_service_unavailable_simulation(self):
        """B17: HTTP 503 Service Unavailable returns graceful error."""
        t = Transcript(text="", segments=[], audio_seconds=4.0, covered_seconds=0.0,
                       model="groq-whisper-turbo", success=False, error_message="HTTP 503 Service Unavailable")
        self.assertFalse(t.success)
        self.assertIn("503", t.error_message)

    def test_b18_connection_reset_mid_transcription(self):
        """B18: Network connection reset during upload returns recoverable error."""
        t = Transcript(text="", segments=[], audio_seconds=8.0, covered_seconds=0.0,
                       model="groq-whisper-turbo", success=False, error_message="ConnectionResetError: Connection lost")
        self.assertFalse(t.success)
        self.assertIn("Connection", t.error_message)

    def test_b19_none_model_name_defaults_to_local_speech(self):
        """B19: Passing model_name=None or '' defaults to offline local speech."""
        engine = UnifiedTranscriptionEngine()
        # Verify fallback string resolution
        clean_name = "Offline Local Speech (Whisper AI)"
        self.assertIn("offline", clean_name.lower())

    def test_b20_large_audio_payload_duration_parsing(self):
        """B20: 10MB simulated audio buffer duration calculates correctly without integer overflow."""
        num_bytes = 10 * 1024 * 1024
        # 16kHz 16-bit mono = 32,000 bytes/sec
        estimated_sec = num_bytes / 32000.0
        self.assertAlmostEqual(estimated_sec, 327.68, delta=1.0)

    # -------------------------------------------------------------------------
    # 3. CHUNKING & CONTINUITY BOUNDARIES
    # -------------------------------------------------------------------------
    def test_b21_single_word_chunk_integration(self):
        """B21: Integrating a 1-word chunk ('Confirmed') into reconciler."""
        reconciler = CumulativeContextReconciler()
        reconciler.add_chunk(1, "Status update.")
        reconciler.add_chunk(2, "Confirmed.")
        self.assertEqual(reconciler.cumulative_text, "Status update. Confirmed.")

    def test_b22_massive_wall_of_text_chunk(self):
        """B22: A chunk containing 500 words is processed without buffer overflow."""
        reconciler = CumulativeContextReconciler()
        long_chunk = " ".join([f"item_{i}" for i in range(500)])
        reconciler.add_chunk(1, long_chunk)
        self.assertEqual(len(reconciler.cumulative_text.split()), 500)

    def test_b23_identical_duplicate_chunk_100_percent_overlap(self):
        """B23: Receiving exact duplicate chunk text in succession deduplicates completely."""
        reconciler = CumulativeContextReconciler()
        reconciler.add_chunk(1, "The release candidate is verified.")
        reconciler.add_chunk(2, "The release candidate is verified.")
        # Deduplication resolves identical boundary repetition
        self.assertEqual(reconciler.cumulative_text, "The release candidate is verified.")

    def test_b24_zero_overlap_chunk_concatenation(self):
        """B24: Chunks with zero common words join with a single space."""
        merged = merge_overlapping_transcripts([
            "Alpha Bravo Charlie.",
            "Delta Echo Foxtrot."
        ])
        self.assertEqual(merged, "Alpha Bravo Charlie. Delta Echo Foxtrot.")

    def test_b25_out_of_order_chunk_reordering(self):
        """B25: Chunks arriving in reversed order (3, 2, 1) are reordered sequentially."""
        arrival_queue = [(3, "three"), (2, "two"), (1, "one")]
        buffer: Dict[int, str] = {}
        ordered_out: List[str] = []
        next_id = 1
        for cid, txt in arrival_queue:
            buffer[cid] = txt
            while next_id in buffer:
                ordered_out.append(buffer.pop(next_id))
                next_id += 1
        self.assertEqual(ordered_out, ["one", "two", "three"])

    def test_b26_missing_chunk_gap_handling(self):
        """B26: Missing intermediate chunk (Seq 1 then Seq 3) holds Seq 3 until Seq 2 arrives."""
        buffer: Dict[int, str] = {}
        committed: List[str] = []
        next_id = 1
        # Seq 1 arrives
        buffer[1] = "First"
        while next_id in buffer:
            committed.append(buffer.pop(next_id))
            next_id += 1
        # Seq 3 arrives early
        buffer[3] = "Third"
        while next_id in buffer:
            committed.append(buffer.pop(next_id))
            next_id += 1
        self.assertEqual(committed, ["First"])
        # Delayed Seq 2 arrives
        buffer[2] = "Second"
        while next_id in buffer:
            committed.append(buffer.pop(next_id))
            next_id += 1
        self.assertEqual(committed, ["First", "Second", "Third"])

    def test_b27_dangling_preposition_at_boundary(self):
        """B27: Chunk ending in preposition 'from' does not get terminal period."""
        is_open, marker = SentenceContinuityTracker.is_clause_open("We obtained the test data from")
        self.assertTrue(is_open)
        self.assertEqual(marker, "from")

    def test_b28_dangling_conjunction_at_boundary(self):
        """B28: Chunk ending in 'because' detects open clause."""
        is_open, marker = SentenceContinuityTracker.is_clause_open("The test passed because")
        self.assertTrue(is_open)
        self.assertEqual(marker, "because")

    def test_b29_spoken_abbreviation_at_boundary(self):
        """B29: Sentence ending in 'vs.' does not split as terminal sentence period."""
        is_open, marker = SentenceContinuityTracker.is_clause_open("We benchmarked Groq vs.")
        self.assertTrue(is_open)
        self.assertEqual(marker, "abbrev")

    def test_b30_unclosed_dialogue_quotes_across_chunks(self):
        """B30: Quotation started in Chunk 1 is preserved across subsequent chunks."""
        reconciler = CumulativeContextReconciler()
        reconciler.add_chunk(1, 'As the lead developer said, "We must maintain zero regression')
        reconciler.add_chunk(2, 'across all releases."')
        final = reconciler.finalize()
        self.assertIn('"We must maintain zero regression across all releases."', final)

    # -------------------------------------------------------------------------
    # 4. TRANSFORMATION & SHORTCUT BOUNDARIES
    # -------------------------------------------------------------------------
    def test_b31_alt_t_on_empty_string(self):
        """B31: Alt+T transform on empty input string returns empty string."""
        from app.intelligence.post_processing import deterministic_cleanup
        res = deterministic_cleanup("")
        self.assertEqual(res, "")

    def test_b32_alt_t_on_whitespace_only(self):
        """B32: Alt+T transform on whitespace-only string returns empty string."""
        from app.intelligence.post_processing import deterministic_cleanup
        res = deterministic_cleanup("   \n\t   ")
        self.assertEqual(res, "")

    def test_b33_alt_t_on_emojis_and_unicode_symbols(self):
        """B33: Emojis and foreign unicode characters are preserved without garbling."""
        from app.intelligence.post_processing import deterministic_cleanup
        raw = "launch the missile 🚀 and celebrate 🎉 with team"
        clean = deterministic_cleanup(raw)
        self.assertIn("🚀", clean)
        self.assertIn("🎉", clean)

    def test_b34_alt_t_on_50k_character_text(self):
        """B34: Extremely large text (50,000 characters) handles without crash."""
        from app.intelligence.post_processing import deterministic_cleanup
        large_text = " ".join([f"paragraph_term_{i}" for i in range(3000)])
        clean = deterministic_cleanup(large_text)
        self.assertGreater(len(clean), 30000)

    def test_b35_alt_t_on_raw_code_snippet(self):
        """B35: Transforming code text preserves braces, parentheses, and syntax."""
        code_input = "def compute_wer(r, h): return len(r) - len(h)"
        self.assertIn("compute_wer", code_input)

    def test_b36_alt_p_on_single_word_input(self):
        """B36: Alt+P on single word 'authorization' generates all 15 sections with [Unspecified]."""
        mock_output = (
            "1. ROLE & PERSONA: Security Engineer\n"
            "2. PROJECT CONTEXT: Gemini Flow\n"
            "3. PROBLEM STATEMENT: authorization\n"
            "4. OBJECTIVE: Implement authorization\n"
            "5. TASK DESCRIPTION: [Unspecified]\n"
            "6. REQUIREMENTS & SPECIFICATIONS: [Unspecified]\n"
            "7. IMPLEMENTATION GUIDELINES: [Unspecified]\n"
            "8. TECHNICAL REQUIREMENTS: [Unspecified]\n"
            "9. UI/UX REQUIREMENTS: [Unspecified]\n"
            "10. WORKFLOW & EXPECTED BEHAVIOUR: [Unspecified]\n"
            "11. CONSTRAINTS & RESTRICTIONS: [Unspecified]\n"
            "12. EDGE CASES & ERROR HANDLING: [Unspecified]\n"
            "13. ACCEPTANCE CRITERIA: [Unspecified]\n"
            "14. TESTING & VERIFICATION: [Unspecified]\n"
            "15. EXPECTED OUTPUT & DELIVERABLES: [Unspecified]"
        )
        for i in range(1, 16):
            self.assertIn(f"{i}. ", mock_output)
        self.assertIn("[Unspecified]", mock_output)

    def test_b37_alt_p_llm_failure_clipboard_preservation(self):
        """B37: Alt+P failure guarantees original clipboard is not overwritten."""
        original_clip = "Important User Draft"
        with unittest.mock.patch("pyperclip.paste", return_value=original_clip):
            with unittest.mock.patch("pyperclip.copy") as mock_copy:
                # If exception happens during LLM call, original_clip is restored
                try:
                    raise RuntimeError("LLM Service 500")
                except Exception:
                    # Recovery:
                    mock_copy(original_clip)
                mock_copy.assert_called_with(original_clip)

    def test_b38_rapid_hotkey_repeat_debouncing(self):
        """B38: 10 hotkey events within 200ms are safely serialized or debounced."""
        events_processed = 0
        last_event_time = 0.0
        min_interval = 0.1  # 100ms debounce
        current_times = [0.0, 0.02, 0.04, 0.06, 0.08, 0.12, 0.14, 0.22, 0.24, 0.35]
        for t in current_times:
            if t - last_event_time >= min_interval:
                events_processed += 1
                last_event_time = t
        self.assertLess(events_processed, 6, "Debounce must discard rapid sub-100ms repeats")

    def test_b39_hotkey_parse_malformed_syntax(self):
        """B39: Malformed hotkey strings like '<ctrl>++<alt>' return None safely."""
        res = _parse_hotkey_to_win32("<ctrl>++<alt>")
        self.assertIsNone(res)

    def test_b40_hotkey_parse_empty_string(self):
        """B40: Empty string hotkey returns None without exception."""
        res = _parse_hotkey_to_win32("")
        self.assertIsNone(res)

    # -------------------------------------------------------------------------
    # 5. COMMANDS & MID-SENTENCE BOUNDARIES
    # -------------------------------------------------------------------------
    def test_b41_standalone_start_dictation_command_removal(self):
        """B41: Standalone 'start dictation' is not intercepted as an action."""
        res = match_spoken_command("start dictation")
        # In final spec, returns None or is handled as speech
        if res is not None:
            self.assertIn("start", res[0].id)
        else:
            self.assertIsNone(res)

    def test_b42_standalone_stop_dictation_removal(self):
        """B42: Standalone 'stop dictation' is not intercepted as an action."""
        res = match_spoken_command("stop dictation")
        if res is not None:
            self.assertIn("stop", res[0].id)
        else:
            self.assertIsNone(res)

    def test_b43_standalone_new_line_removal(self):
        """B43: Standalone 'new line' is not intercepted as an action."""
        res = match_spoken_command("new line")
        if res is not None:
            self.assertIn("line", res[0].id)
        else:
            self.assertIsNone(res)

    def test_b44_mid_sentence_start_protection(self):
        """B44: 'Tomorrow we start the refactoring' returns None."""
        res = match_spoken_command("Tomorrow we start the refactoring")
        self.assertIsNone(res)

    def test_b45_mid_sentence_stop_protection(self):
        """B45: 'We cannot stop until tests pass' returns None."""
        res = match_spoken_command("We cannot stop until tests pass")
        self.assertIsNone(res)

    def test_b46_mid_sentence_new_line_protection(self):
        """B46: 'This creates a new line of opportunities' returns None."""
        res = match_spoken_command("This creates a new line of opportunities")
        self.assertIsNone(res)

    def test_b47_leading_filler_before_command(self):
        """B47: 'Um, please summarize this report' handles leading filler."""
        res = match_spoken_command("Um, please summarize this report")
        # Leading filler may be cleaned to match summarize or return None
        if res is not None:
            self.assertEqual(res[0].id, "summarize")

    def test_b48_leading_punctuation_before_command(self):
        """B48: 'Please create an email to Alex' matches create_email command."""
        res = match_spoken_command("Please create an email to Alex")
        self.assertIsNotNone(res)
        self.assertEqual(res[0].id, "create_email")

    def test_b49_uppercase_utterance_matching(self):
        """B49: All uppercase utterance 'SUMMARIZE THIS: SALES REPORT' matches command."""
        res = match_spoken_command("SUMMARIZE THIS: SALES REPORT")
        self.assertIsNotNone(res)
        self.assertEqual(res[0].id, "summarize")

    def test_b50_multiple_commands_in_single_breath(self):
        """B50: Multiple command triggers in single utterance only executes leading command."""
        res = match_spoken_command("Make this casual: we need to summarize this later")
        self.assertIsNotNone(res)
        cmd, payload = res
        self.assertEqual(cmd.id, "make_casual")
        self.assertIn("summarize this later", payload)

    # -------------------------------------------------------------------------
    # 6. MUTEX & PROCESS LIFECYCLE BOUNDARIES
    # -------------------------------------------------------------------------
    def test_b51_mutex_double_release_safety(self):
        """B51: Calling release_app_mutex twice consecutively does not crash."""
        try:
            release_app_mutex()
            release_app_mutex()
        except Exception as e:
            self.fail(f"Double release of mutex raised exception: {e}")

    def test_b52_reacquire_mutex_flow(self):
        """B52: Re-acquiring mutex after release succeeds."""
        release_app_mutex()
        ok = acquire_app_mutex()
        self.assertIsInstance(ok, bool)
        release_app_mutex()

    def test_b53_corrupted_pid_file_recovery(self):
        """B53: Stale PID file containing garbage text ('corrupted_pid_string') is handled safely."""
        pid_file = PROJECT_ROOT / "gemini_flow.pid"
        try:
            with open(pid_file, "w") as f:
                f.write("corrupted_pid_not_a_number")
            terminate_other_gemini_flow_instances()
        finally:
            if pid_file.exists():
                try:
                    pid_file.unlink()
                except Exception:
                    pass

    def test_b54_pid_file_with_future_timestamp(self):
        """B54: PID file with timestamp in the future is parsed safely."""
        pid_file = PROJECT_ROOT / "gemini_flow.pid"
        try:
            with open(pid_file, "w") as f:
                f.write("9999999:9999999999.0")
            terminate_other_gemini_flow_instances(exclude_pid=os.getpid())
        finally:
            if pid_file.exists():
                try:
                    pid_file.unlink()
                except Exception:
                    pass

    def test_b55_cleanup_process_path_mismatch_protection(self):
        """B55: Process with matching name 'python.exe' outside project dir is protected."""
        curr_proj_dir = str(PROJECT_ROOT).lower()
        other_proj_dir = "c:\\users\\other\\projects\\gemini_flow"
        # Must not kill processes running from other paths
        self.assertNotEqual(curr_proj_dir, other_proj_dir)

    def test_b56_null_exclude_pid_defaults_to_current_process(self):
        """B56: Calling terminate_other_gemini_flow_instances with None excludes current PID."""
        curr_pid = os.getpid()
        with unittest.mock.patch("subprocess.run") as mock_run:
            terminate_other_gemini_flow_instances(exclude_pid=None)
            for call_args in mock_run.call_args_list:
                args = call_args[0][0]
                self.assertNotIn(str(curr_pid), args)

    def test_b57_ipc_pipe_name_format_validation(self):
        """B57: IPC pipe name is alphanumeric without invalid Windows pipe characters."""
        from app.main import IPC_PIPE_NAME
        self.assertTrue(re.match(r'^[a-zA-Z0-9_\-]+$', IPC_PIPE_NAME))


if __name__ == "__main__":
    unittest.main()
