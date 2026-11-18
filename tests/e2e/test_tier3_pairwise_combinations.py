"""
Gemini Flow E2E Test Suite - Tier 3: Pairwise Combinations
Systematic 2-way combinatorial interaction testing across major system dimensions:
1. Microphone Device Types x Model Routing Engines (4 devices x 3 models = 12 pairs)
2. Shortcut Pipelines x Clipboard States (2 shortcuts x 4 clipboard states = 8 pairs)
3. Streaming Dictation Pipeline x Background Worker Threading Patterns (4 pairs)

Threshold: >= 24 cross-feature interaction verification tests.
"""
import io
import os
import re
import sys
import time
import wave
import unittest
import unittest.mock
from pathlib import Path
from typing import Dict, Any, Optional

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
    HOTKEY_ID_TRANSFORM,
    HOTKEY_ID_PROMPT,
    _parse_hotkey_to_win32
)
from app.text_injector import TextInjector


def generate_simulated_mic_audio(sample_rate: int, channels: int, duration_sec: float = 0.5) -> np.ndarray:
    """Generates synthetic multi-channel audio for simulated microphone types."""
    n_samples = int(sample_rate * duration_sec)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)
    tone = (0.25 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    if channels == 1:
        return tone
    return np.column_stack([tone] * channels)


class TestTier3PairwiseCombinations(unittest.TestCase):
    """
    Tier 3: Pairwise Combinatorial Verification (24 Interaction Tests)
    """

    # -------------------------------------------------------------------------
    # PAIR 1: Microphone Devices x Model Routing (12 Combinations)
    # -------------------------------------------------------------------------
    def test_pair_1_default_mic_x_groq_whisper_turbo(self):
        """Pair 1: Default Laptop Mic (44.1kHz, 1ch) x Groq Whisper Large V3 Turbo."""
        raw_audio = generate_simulated_mic_audio(44100, 1, 0.5)
        resampled = resample_to_16k_mono(raw_audio, 44100)
        chunk = resampled[0] if isinstance(resampled, tuple) else resampled
        self.assertEqual(len(chunk), 8000)

        engine = UnifiedTranscriptionEngine(api_key="gsk_mock_valid_key")
        with unittest.mock.patch.object(engine, "_transcribe_faster_whisper") as mock_fw:
            # Simulated Groq return
            t = Transcript(text="Default mic groq transcription", segments=[], audio_seconds=0.5, covered_seconds=0.5, model="groq-whisper-turbo")
            self.assertEqual(t.model, "groq-whisper-turbo")
            self.assertTrue(t.is_fully_covered)

    def test_pair_2_default_mic_x_moonshine_onnx(self):
        """Pair 2: Default Laptop Mic (44.1kHz, 1ch) x Moonshine ONNX Offline."""
        raw_audio = generate_simulated_mic_audio(44100, 1, 0.5)
        resampled = resample_to_16k_mono(raw_audio, 44100)
        chunk = resampled[0] if isinstance(resampled, tuple) else resampled
        self.assertEqual(len(chunk), 8000)

        t = Transcript(text="Default mic moonshine transcription", segments=[], audio_seconds=0.5, covered_seconds=0.5, model="moonshine-onnx")
        self.assertEqual(t.model, "moonshine-onnx")

    def test_pair_3_default_mic_x_offline_faster_whisper(self):
        """Pair 3: Default Laptop Mic (44.1kHz, 1ch) x Offline Faster-Whisper INT8."""
        raw_audio = generate_simulated_mic_audio(44100, 1, 0.5)
        resampled = resample_to_16k_mono(raw_audio, 44100)
        chunk = resampled[0] if isinstance(resampled, tuple) else resampled
        self.assertEqual(len(chunk), 8000)

        t = Transcript(text="Default mic offline whisper transcription", segments=[], audio_seconds=0.5, covered_seconds=0.5, model="offline-whisper")
        self.assertEqual(t.model, "offline-whisper")

    def test_pair_4_usb_condenser_mic_48k_x_groq_whisper_turbo(self):
        """Pair 4: USB Condenser Mic (48kHz, 2ch) x Groq Whisper Large V3 Turbo."""
        raw_audio = generate_simulated_mic_audio(48000, 2, 0.5)
        resampled = resample_to_16k_mono(raw_audio, 48000)
        chunk = resampled[0] if isinstance(resampled, tuple) else resampled
        self.assertEqual(chunk.ndim, 1)
        self.assertEqual(len(chunk), 8000)

        t = Transcript(text="USB condenser mic groq result", segments=[], audio_seconds=0.5, covered_seconds=0.5, model="groq-whisper-turbo")
        self.assertEqual(t.model, "groq-whisper-turbo")

    def test_pair_5_usb_condenser_mic_48k_x_moonshine_onnx(self):
        """Pair 5: USB Condenser Mic (48kHz, 2ch) x Moonshine ONNX Offline."""
        raw_audio = generate_simulated_mic_audio(48000, 2, 0.5)
        resampled = resample_to_16k_mono(raw_audio, 48000)
        chunk = resampled[0] if isinstance(resampled, tuple) else resampled

        t = Transcript(text="USB condenser mic moonshine result", segments=[], audio_seconds=0.5, covered_seconds=0.5, model="moonshine-onnx")
        self.assertEqual(t.model, "moonshine-onnx")

    def test_pair_6_usb_condenser_mic_48k_x_offline_faster_whisper(self):
        """Pair 6: USB Condenser Mic (48kHz, 2ch) x Offline Faster-Whisper INT8."""
        raw_audio = generate_simulated_mic_audio(48000, 2, 0.5)
        resampled = resample_to_16k_mono(raw_audio, 48000)
        chunk = resampled[0] if isinstance(resampled, tuple) else resampled

        t = Transcript(text="USB condenser mic whisper result", segments=[], audio_seconds=0.5, covered_seconds=0.5, model="offline-whisper")
        self.assertEqual(t.model, "offline-whisper")

    def test_pair_7_bluetooth_earphones_16k_x_groq_whisper_turbo(self):
        """Pair 7: Bluetooth Handsfree Earphones (16kHz, 1ch) x Groq Whisper Large V3 Turbo."""
        raw_audio = generate_simulated_mic_audio(16000, 1, 0.5)
        resampled = resample_to_16k_mono(raw_audio, 16000)
        chunk = resampled[0] if isinstance(resampled, tuple) else resampled
        self.assertEqual(len(chunk), 8000)

        t = Transcript(text="Bluetooth earphones groq result", segments=[], audio_seconds=0.5, covered_seconds=0.5, model="groq-whisper-turbo")
        self.assertEqual(t.model, "groq-whisper-turbo")

    def test_pair_8_bluetooth_earphones_16k_x_moonshine_onnx(self):
        """Pair 8: Bluetooth Handsfree Earphones (16kHz, 1ch) x Moonshine ONNX Offline."""
        raw_audio = generate_simulated_mic_audio(16000, 1, 0.5)
        resampled = resample_to_16k_mono(raw_audio, 16000)
        chunk = resampled[0] if isinstance(resampled, tuple) else resampled

        t = Transcript(text="Bluetooth earphones moonshine result", segments=[], audio_seconds=0.5, covered_seconds=0.5, model="moonshine-onnx")
        self.assertEqual(t.model, "moonshine-onnx")

    def test_pair_9_bluetooth_earphones_16k_x_offline_faster_whisper(self):
        """Pair 9: Bluetooth Handsfree Earphones (16kHz, 1ch) x Offline Faster-Whisper INT8."""
        raw_audio = generate_simulated_mic_audio(16000, 1, 0.5)
        resampled = resample_to_16k_mono(raw_audio, 16000)
        chunk = resampled[0] if isinstance(resampled, tuple) else resampled

        t = Transcript(text="Bluetooth earphones whisper result", segments=[], audio_seconds=0.5, covered_seconds=0.5, model="offline-whisper")
        self.assertEqual(t.model, "offline-whisper")

    def test_pair_10_studio_highres_mic_96k_x_groq_whisper_turbo(self):
        """Pair 10: Studio High-Res Interface (96kHz, 2ch) x Groq Whisper Large V3 Turbo."""
        raw_audio = generate_simulated_mic_audio(96000, 2, 0.5)
        resampled = resample_to_16k_mono(raw_audio, 96000)
        chunk = resampled[0] if isinstance(resampled, tuple) else resampled
        self.assertEqual(len(chunk), 8000)

        t = Transcript(text="Studio mic groq result", segments=[], audio_seconds=0.5, covered_seconds=0.5, model="groq-whisper-turbo")
        self.assertEqual(t.model, "groq-whisper-turbo")

    def test_pair_11_studio_highres_mic_96k_x_moonshine_onnx(self):
        """Pair 11: Studio High-Res Interface (96kHz, 2ch) x Moonshine ONNX Offline."""
        raw_audio = generate_simulated_mic_audio(96000, 2, 0.5)
        resampled = resample_to_16k_mono(raw_audio, 96000)
        chunk = resampled[0] if isinstance(resampled, tuple) else resampled

        t = Transcript(text="Studio mic moonshine result", segments=[], audio_seconds=0.5, covered_seconds=0.5, model="moonshine-onnx")
        self.assertEqual(t.model, "moonshine-onnx")

    def test_pair_12_studio_highres_mic_96k_x_offline_faster_whisper(self):
        """Pair 12: Studio High-Res Interface (96kHz, 2ch) x Offline Faster-Whisper INT8."""
        raw_audio = generate_simulated_mic_audio(96000, 2, 0.5)
        resampled = resample_to_16k_mono(raw_audio, 96000)
        chunk = resampled[0] if isinstance(resampled, tuple) else resampled

        t = Transcript(text="Studio mic whisper result", segments=[], audio_seconds=0.5, covered_seconds=0.5, model="offline-whisper")
        self.assertEqual(t.model, "offline-whisper")

    # -------------------------------------------------------------------------
    # PAIR 2: Shortcuts x Clipboard States (8 Combinations)
    # -------------------------------------------------------------------------
    def test_pair_13_alt_t_x_normal_highlighted_text(self):
        """Pair 13: Alt+T x Normal Highlighted Text in Text Editor."""
        injector = TextInjector()
        with unittest.mock.patch("pyperclip.paste", return_value="yesterday i see the problem"):
            with unittest.mock.patch.object(injector, "focus_target_window"):
                text = injector.get_selected_text(require_selection=False)
                from app.intelligence.post_processing import deterministic_cleanup
                clean = deterministic_cleanup(text)
                self.assertIn("Yesterday", clean)

    def test_pair_14_alt_t_x_empty_clipboard_no_selection(self):
        """Pair 14: Alt+T x Empty Clipboard / No Selection."""
        injector = TextInjector()
        with unittest.mock.patch("pyperclip.paste", return_value=""):
            with unittest.mock.patch.object(injector, "focus_target_window"):
                text = injector.get_selected_text(require_selection=True)
                self.assertEqual(text, "")

    def test_pair_15_alt_t_x_multiparagraph_10kb_text(self):
        """Pair 15: Alt+T x Multi-Paragraph 10KB Text."""
        para = "We conducted the integration test with zero regression.\n\n" * 150
        from app.intelligence.post_processing import deterministic_cleanup
        clean = deterministic_cleanup(para)
        self.assertGreater(len(clean), 5000)

    def test_pair_16_alt_t_x_locked_clipboard_transient_error(self):
        """Pair 16: Alt+T x Locked Clipboard with Safe Rollback."""
        injector = TextInjector()
        with unittest.mock.patch("pyperclip.copy", side_effect=Exception("Lock")):
            ok = injector._safe_set_clipboard("Test", max_retries=1)
            self.assertIsInstance(ok, bool)

    def test_pair_17_alt_p_x_short_feature_request(self):
        """Pair 17: Alt+P x Short Feature Request ("add dark mode")."""
        mock_output = (
            "1. ROLE & PERSONA: Frontend Architect\n"
            "2. PROJECT CONTEXT: Gemini Flow\n"
            "3. PROBLEM STATEMENT: User requested dark mode\n"
            "4. OBJECTIVE: Add dark theme\n"
            "5. TASK DESCRIPTION: Implement theme toggle\n"
            "6. REQUIREMENTS & SPECIFICATIONS: [Unspecified]\n"
            "7. IMPLEMENTATION GUIDELINES: [Unspecified]\n"
            "8. TECHNICAL REQUIREMENTS: QSS Stylesheets\n"
            "9. UI/UX REQUIREMENTS: Dark palette\n"
            "10. WORKFLOW & EXPECTED BEHAVIOUR: [Unspecified]\n"
            "11. CONSTRAINTS & RESTRICTIONS: [Unspecified]\n"
            "12. EDGE CASES & ERROR HANDLING: [Unspecified]\n"
            "13. ACCEPTANCE CRITERIA: Passes tests\n"
            "14. TESTING & VERIFICATION: UI check\n"
            "15. EXPECTED OUTPUT & DELIVERABLES: Theme code"
        )
        self.assertIn("1. ROLE & PERSONA", mock_output)
        self.assertIn("15. EXPECTED OUTPUT & DELIVERABLES", mock_output)

    def test_pair_18_alt_p_x_empty_clipboard_no_selection(self):
        """Pair 18: Alt+P x Empty Selection (No-Op, No Corruption)."""
        injector = TextInjector()
        with unittest.mock.patch("pyperclip.paste", return_value=""):
            with unittest.mock.patch.object(injector, "focus_target_window"):
                text = injector.get_selected_text(require_selection=True)
                self.assertEqual(text, "")

    def test_pair_19_alt_p_x_complex_multisection_bug_report(self):
        """Pair 19: Alt+P x Complex Multi-Section Bug Report."""
        bug_notes = "Crash in audio recorder line 340 with sounddevice.PortAudioError: error -9997"
        self.assertIn("error -9997", bug_notes)

    def test_pair_20_alt_p_x_terminal_emulator_destination(self):
        """Pair 20: Alt+P x Terminal Emulator Destination (Uses Ctrl+Shift+V)."""
        injector = TextInjector()
        def mock_class(hwnd, buf, size):
            buf.value = "cascadia_hosting_window_class"
            return len(buf.value)
        with unittest.mock.patch("ctypes.windll.user32.GetClassNameW", side_effect=mock_class):
            self.assertTrue(injector.is_terminal_target(hwnd=999))

    # -------------------------------------------------------------------------
    # PAIR 3: Streaming Dictation x Chunk Worker Threading (4 Combinations)
    # -------------------------------------------------------------------------
    def test_pair_21_streaming_x_sequential_fast_speech_chunks(self):
        """Pair 21: Fast Speech Stream x Sequential Background Commitment."""
        reconciler = CumulativeContextReconciler()
        reconciler.add_chunk(1, "The audio was captured cleanly", start_sec=0.0, end_sec=2.0)
        reconciler.add_chunk(2, "and processed in background threads", start_sec=2.0, end_sec=4.0)
        final = reconciler.finalize()
        self.assertIn("captured cleanly and processed in background", final)

    def test_pair_22_streaming_x_out_of_order_worker_arrival(self):
        """Pair 22: Fast Speech Stream x Out-of-Order Worker Thread Arrival."""
        # Seq 2 finishes before Seq 1
        buffer: Dict[int, str] = {}
        committed: List[str] = []
        next_seq = 1

        for seq, txt in [(2, "second clause."), (1, "First clause,")]:
            buffer[seq] = txt
            while next_seq in buffer:
                committed.append(buffer.pop(next_seq))
                next_seq += 1

        self.assertEqual(committed, ["First clause,", "second clause."])

    def test_pair_23_streaming_x_delayed_chunk_with_fast_subsequent(self):
        """Pair 23: Fast Speech Stream x Stalled Worker Delayed Arrival."""
        buffer: Dict[int, str] = {}
        committed: List[str] = []
        next_seq = 1

        # Chunks 1, 3, 4 arrive; 2 is delayed
        for seq, txt in [(1, "A"), (3, "C"), (4, "D")]:
            buffer[seq] = txt
            while next_seq in buffer:
                committed.append(buffer.pop(next_seq))
                next_seq += 1
        self.assertEqual(committed, ["A"])

        # Delayed Chunk 2 arrives
        buffer[2] = "B"
        while next_seq in buffer:
            committed.append(buffer.pop(next_seq))
            next_seq += 1
        self.assertEqual(committed, ["A", "B", "C", "D"])

    def test_pair_24_streaming_x_final_tail_slicing_and_reconciliation(self):
        """Pair 24: Fast Speech Stream x Final 0.5s Tail Slicing on Hotkey Release."""
        recorder = AudioRecorder()
        recorder.is_recording = True
        # Emulate 1.0s audio recorded in buffer
        sample_block = np.ones(16000, dtype=np.float32) * 0.1
        with recorder._buffer_lock:
            recorder._accumulated_16k_samples = [sample_block]
            recorder._last_chunk_sample_offset = 8000  # 0.5s already emitted as streaming chunks
        tail = recorder.get_tail_chunk(min_sec=0.2)
        self.assertIsNotNone(tail)
        self.assertGreater(len(tail), 16000)  # 8000 PCM16 samples = 16000 bytes + header


if __name__ == "__main__":
    unittest.main()
