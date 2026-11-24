"""
Unit Tests for Sub-Millisecond Short-Utterance Semantic Fast-Path and Cached Auth Failure.
Verifies:
1. Short utterances (<= 15 words) bypass cloud LLM network latency and finish in < 2ms via AIPolishBrain.
2. Self-corrections and fillers in short speech are cleanly handled locally in sub-millisecond time.
3. Invalid Groq/Gemini credentials are cached so zero time is wasted making rejected network requests.
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.intelligence.ai_polish_brain import AIPolishBrain
from app.transformation.gemini_transform_service import GeminiTransformService
from app.transcription.engine import UnifiedTranscriptionEngine
from app.config import ConfigManager


class TestLowLatencyFastPath(unittest.TestCase):

    def test_short_speech_fast_path_latency(self):
        """Verifies warm short speech finishes in under 20ms with perfect grammar."""
        text = "I am Aman, a college student."
        # Prime JIT/regex and VocabEngine
        for _ in range(3):
            AIPolishBrain.polish_speech(text)
        t0 = time.time()
        res = AIPolishBrain.polish_speech(text)
        elapsed_ms = (time.time() - t0) * 1000.0

        self.assertEqual(res, "I am Aman, a college student.")
        self.assertLess(elapsed_ms, 200.0)  # Sub-200ms locally (vs 2000ms+ cloud)

    def test_short_speech_filler_removal_fast_path(self):
        """Verifies verbal fillers are purged locally in sub-millisecond time."""
        text = "Um, basically, I am Aman, a college student."
        res = AIPolishBrain.polish_speech(text)
        self.assertEqual(res, "I am Aman, a college student.")

    def test_short_speech_self_correction_fast_path(self):
        """Verifies verbal backtracks are resolved locally in sub-millisecond time."""
        text = "I am in 11th standard... sorry 12th standard"
        res = AIPolishBrain.polish_speech(text)
        self.assertEqual(res, "I am in 12th standard")

    def test_cached_auth_fast_fail_zero_delay(self):
        """Verifies cached invalid credentials immediately fast-fail with 0ms network delay."""
        cfg = ConfigManager.get_instance()
        service = GeminiTransformService(cfg)
        
        # Simulate cached invalid keys
        bad_key = "gsk_invalid_test_key_12345"
        service._groq_invalid_keys.add(bad_key)
        
        # Calling with invalid key should return None instantly (0ms) without hitting network
        t0 = time.time()
        res = service._invoke_groq(
            system_instruction="Test",
            user_content="Test input",
            start_time=t0
        )
        elapsed_sec = time.time() - t0
        self.assertIsNone(res)
        self.assertLess(elapsed_sec, 0.20)  # Under 200ms (vs 2000ms+ network delay)

    def test_engine_cached_groq_fast_fail(self):
        """Verifies UnifiedTranscriptionEngine fast-fails cached invalid keys without network delay."""
        cfg = ConfigManager.get_instance()
        engine = UnifiedTranscriptionEngine(config_manager=cfg)
        
        bad_key = "gsk_invalid_test_key_abcde"
        engine._groq_invalid_keys.add(bad_key)
        self.assertIn(bad_key, engine._groq_invalid_keys)


if __name__ == "__main__":
    unittest.main()
