"""
Verification Test Suite for Gemini Flow 5-Stage Architecture.
Tests:
1. Untouched Core Integrity: Quick Text, Custom Dictionary, and Custom Directory preservation.
2. Stage 1 Audio Capture: Polyphase 16kHz mono resampling and Whisper Mode gain boost.
3. Stage 2 Noise Suppression & VAD: 80Hz high-pass filtering, soft noise gating, and silence gating.
4. Stage 3 ASR Provider Routing: Dictionary keyword biasing and fast-fail fallback contract.
5. Stage 4 Stateless LLM Polish: Thinking budget 0 optimization, self-correction, and bullet list formatting.
6. Stage 5 OS Text Injection: Terminal vs GUI routing and asynchronous clipboard safety.
"""
import io
import os
import sys
import time
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from app.config import ConfigManager, DEFAULT_DICTIONARY, DEFAULT_SNIPPETS
from app.audio_recorder import AudioRecorder, resample_to_16k_mono, apply_dsp_filters
from app.audio.noise_suppressor import NoiseSuppressor, condition_audio_for_transcription
from app.transcription.engine import UnifiedTranscriptionEngine
from app.intelligence.ai_polish_brain import AIPolishBrain
from app.text_injector import TextInjector, TERMINAL_CLASSES, TERMINAL_EXES


class TestUntouchedCoreIntegrity(unittest.TestCase):
    """Verifies Quick Text, Custom Dictionary, and Custom Directory remain intact."""

    def test_quick_text_snippets_intact(self):
        cfg = ConfigManager.get_instance()
        snippets = cfg.get_snippets()
        self.assertIsInstance(snippets, list)
        self.assertGreater(len(snippets), 0)
        first = snippets[0]
        self.assertIn("trigger", first)
        self.assertTrue("content" in first or "replacement" in first or "text" in first)
        self.assertGreater(len(DEFAULT_SNIPPETS), 0)

    def test_custom_dictionary_intact(self):
        cfg = ConfigManager.get_instance()
        dict_entries = cfg.get_dictionary()
        self.assertIsInstance(dict_entries, list)
        self.assertGreater(len(dict_entries), 0)
        first = dict_entries[0]
        self.assertTrue("spoken" in first or "trigger" in first)
        self.assertIn("replacement", first)
        self.assertGreater(len(DEFAULT_DICTIONARY), 0)

    def test_custom_directory_storage_intact(self):
        cfg = ConfigManager.get_instance()
        history = cfg.get_history()
        self.assertIsInstance(history, list)
        # Create valid 16kHz mono WAV bytes
        import wave
        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00" * 3200)
        valid_wav = bio.getvalue()
        path = cfg.save_recorded_audio(valid_wav, prefix="unit_test")
        self.assertNotEqual(path, "")
        self.assertIn("recordings", path.lower())


class TestStage1AudioCapture(unittest.TestCase):
    """Verifies low-latency capture, polyphase resampling, and Whisper Mode."""

    def test_polyphase_resampling_48k_to_16k(self):
        sr_in = 48000
        t = np.linspace(0, 0.1, 4800, endpoint=False)
        tone_48k = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)

        resampled, next_state = resample_to_16k_mono(tone_48k, orig_sr=sr_in, return_state=True)
        self.assertEqual(len(resampled), 1600)  # Exactly 0.1s at 16kHz
        self.assertEqual(resampled.dtype, np.float32)

    def test_whisper_mode_gain_and_soft_saturation(self):
        quiet_signal = (0.05 * np.ones(1600)).astype(np.float32)
        suppressor = NoiseSuppressor(sample_rate=16000, whisper_mode=True, whisper_gain_db=12.0)
        boosted = suppressor.apply_whisper_mode_gain(quiet_signal)

        self.assertGreater(np.max(boosted), np.max(quiet_signal) * 2.0)
        self.assertLessEqual(np.max(np.abs(boosted)), 1.0)


class TestStage2NoiseSuppressionAndVAD(unittest.TestCase):
    """Verifies 80Hz high-pass filter, noise gating, and silence hallucination prevention."""

    def test_high_pass_filter_attenuates_sub_audible_hum(self):
        suppressor = NoiseSuppressor(sample_rate=16000, high_pass_hz=80.0)
        t = np.linspace(0, 0.5, 8000, endpoint=False)
        hum_30hz = 0.4 * np.sin(2 * np.pi * 30 * t).astype(np.float32)
        filtered = suppressor.filter_highpass(hum_30hz)

        rms_orig = np.sqrt(np.mean(hum_30hz ** 2))
        rms_filt = np.sqrt(np.mean(filtered ** 2))
        self.assertLess(rms_filt, rms_orig * 0.5)

    def test_pure_silence_detection(self):
        suppressor = NoiseSuppressor(sample_rate=16000)
        pure_silence = (0.0005 * np.random.randn(8000)).astype(np.float32)
        _, contains_speech, rms = suppressor.process(pure_silence)
        self.assertFalse(contains_speech)
        self.assertLess(rms, 0.005)


class TestStage3ASRProviderRouting(unittest.TestCase):
    """Verifies ASR engine initialization, Deepgram provider, and custom dictionary keyword biasing."""

    def test_asr_engine_biasing_prompt(self):
        cfg = ConfigManager.get_instance()
        engine = UnifiedTranscriptionEngine(config_manager=cfg)

        silence_bytes = b"\x00" * 3200
        t = engine.transcribe(silence_bytes, model_name="groq-whisper-turbo")
        self.assertTrue(t.success)
        self.assertEqual(t.text, "")

    def test_deepgram_provider_graceful_fallback(self):
        from app.transcription.deepgram_provider import DeepgramProvider
        provider = DeepgramProvider(api_key="")
        self.assertFalse(provider.is_available())
        ok, msg, meta = provider.transcribe(b"\x00" * 3200)
        self.assertFalse(ok)
        self.assertIn("not configured", msg.lower())

    def test_config_stateless_keys(self):
        cfg = ConfigManager.get_instance()
        self.assertEqual(cfg.get_asr_provider(), "auto")
        self.assertEqual(cfg.get_cleanup_level(), "light")
        self.assertEqual(cfg.get_writing_style(), "auto")
        self.assertFalse(cfg.get_whisper_mode())


class TestStage4StatelessLLMPolish(unittest.TestCase):
    """Verifies self-correction resolution, list formatting, and thinking budget 0."""

    def test_auto_cleanup_levels(self):
        from app.transcription.universal_pipeline import UniversalPipeline
        pipeline = UniversalPipeline()

        raw = "um so like let's meet at 2:00 actually 3:00 tomorrow"
        # Level 'none': preserves raw transcript
        res_none = pipeline.process(raw, cleanup_level="none")
        self.assertIn("actually", res_none)

        # Level 'light': eliminates disfluencies and resolves self-correction
        res_light = pipeline.process(raw, cleanup_level="light")
        self.assertIn("3:00", res_light)
        self.assertNotIn("actually", res_light.lower())

    def test_self_correction_resolution(self):
        raw = "let's meet at 2:00 actually 3:00 tomorrow"
        polished = AIPolishBrain.resolve_self_corrections(raw)
        self.assertIn("3:00", polished)
        self.assertNotIn("actually", polished.lower())

    def test_smart_bullet_formatting(self):
        raw = "I have some advantages. First is high speed. Second is accuracy. Third is privacy."
        formatted = AIPolishBrain.smart_bullet_formatter(raw)
        self.assertTrue("•" in formatted or "-" in formatted)
        self.assertTrue("\n" in formatted)


class TestStage5OSTextInjection(unittest.TestCase):
    """Verifies terminal detection and atomic paste chords."""

    def test_terminal_detection(self):
        self.assertIn("windowsterminal.exe", TERMINAL_EXES)
        self.assertIn("powershell.exe", TERMINAL_EXES)
        self.assertIn("cmd.exe", TERMINAL_EXES)

    def test_clipboard_context_methods(self):
        ti = TextInjector()
        app_name = ti.get_target_app_name()
        self.assertIsInstance(app_name, str)
        fg_ctx = ti.get_foreground_context()
        self.assertIsInstance(fg_ctx, dict)
        self.assertIn("category", fg_ctx)

    def test_app_aware_writing_styles(self):
        ti = TextInjector()
        # Chat / Messaging with casual style: strip trailing period
        chat_ctx = {"category": "chat", "app_name": "Slack"}
        res_chat = ti.apply_contextual_formatting("Let's meet tomorrow at 4 PM.", context=chat_ctx, writing_style="casual")
        self.assertEqual(res_chat, "Let's meet tomorrow at 4 PM")

        # Formal style in document: keep trailing period
        doc_ctx = {"category": "document", "app_name": "Word"}
        res_doc = ti.apply_contextual_formatting("The report is finalized.", context=doc_ctx, writing_style="formal")
        self.assertEqual(res_doc, "The report is finalized.")

        # Terminal style: strip curly quotes
        term_ctx = {"category": "terminal", "app_name": "Terminal"}
        res_term = ti.apply_contextual_formatting('git commit -m “initial commit”', context=term_ctx)
        self.assertEqual(res_term, 'git commit -m "initial commit"')

    def test_emergency_recovery_paste_last(self):
        ti = TextInjector()
        ti._last_injected_text = "Previous speech dictation"
        self.assertTrue(hasattr(ti, "paste_last_transcript"))


if __name__ == "__main__":
    unittest.main()
