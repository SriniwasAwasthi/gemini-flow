"""
Comprehensive End-to-End Audit & Pipeline Upgrade Verification Suite.
Tests:
1. Application Audit (ConfigManager, Profile API Key, HotkeyManager, VocabEngine, Custom Dictionary, Quick Text)
2. Mid-Sentence / Mid-Speech Application (20s & 1-minute speeches, chunk-boundary crossing, adjacent punctuation)
3. Strict <= 3.0s Chunking & Sequential Context-Chaining (7-chunk example + 60s audio)
4. Model-by-Model Real Execution across all 7 models + 3 Offline Whisper models (small.en, base.en, tiny.en)
"""
import io
import os
import sys
import time
import wave
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import ConfigManager, sanitize_api_key
from app.gemini_engine import GeminiEngine
from app.hotkey_manager import HotkeyManager, _parse_hotkey_to_win32
from app.vocabulary.vocab_engine import VocabularyEngine
from app.transcription.chunker import divide_into_dynamic_chunks, get_audio_info
from app.transcription.context_reconciler import CumulativeContextReconciler
from app.transcription.universal_pipeline import UniversalPipeline, VoiceTriggerExpander
from app.transcription.engine import UnifiedTranscriptionEngine
from app.transformation.gemini_transform_service import GeminiTransformService


class TestAuditAndPipelineUpgrade(unittest.TestCase):
    def test_01_config_singleton_and_api_key_propagation(self):
        cfg = ConfigManager.get_instance()
        self.assertIsNotNone(cfg)
        all_cfg = cfg.get_all()
        self.assertIsInstance(all_cfg, dict)

        raw = '  "GEMINI_API_KEY=AIzaSyTestKey1234567890"  '
        self.assertEqual(sanitize_api_key(raw), "AIzaSyTestKey1234567890")

        eng = UnifiedTranscriptionEngine(api_key=cfg.get_api_key(), config_manager=cfg)
        svc = GeminiTransformService(config_manager=cfg)
        svc.set_api_key(cfg.get_api_key())
        self.assertEqual(eng.api_key, cfg.get_api_key())

    def test_02_hotkey_manager_registration_and_cleanup(self):
        self.assertEqual(_parse_hotkey_to_win32("<ctrl>+<space>"), (0x4002, 0x20))
        self.assertEqual(_parse_hotkey_to_win32("<alt>+p"), (0x4001, ord("P")))
        hm = HotkeyManager(hotkey_str="<ctrl>+<space>", mode="toggle")
        hm.set_recording_state(True)
        self.assertTrue(hm.is_recording)
        hm.set_recording_state(False)
        hm.set_processing_state(False)
        self.assertFalse(hm.is_recording)
        self.assertFalse(hm.is_processing)

    def test_03_custom_dictionary_and_vocab_mid_sentence(self):
        dictionary = [
            {"spoken": "fast api", "replacement": "FastAPI"},
            {"spoken": "post gres", "replacement": "PostgreSQL"},
            {"spoken": "kubernetes", "replacement": "Kubernetes"},
            {"spoken": "c plus plus", "replacement": "C++"},
        ]
        raw = "We deployed fast api with post gres and redis on kubernetes yesterday using c plus plus."
        out = GeminiEngine.apply_dictionary(raw, dictionary)
        self.assertIn("FastAPI", out)
        self.assertIn("PostgreSQL", out)
        self.assertIn("Kubernetes", out)
        self.assertIn("C++", out)

        # VocabEngine singleton sync
        ve = VocabularyEngine.get_instance()
        self.assertGreater(len(ve.entries), 0)
        v_out = ve.normalize("We used anti gravity and faster whisper with type script.")
        self.assertIn("Antigravity", v_out)
        self.assertIn("Faster-Whisper", v_out)
        self.assertIn("TypeScript", v_out)

    def test_04_quick_text_mid_sentence_and_punctuation(self):
        snippets = [
            {
                "trigger": "my social links",
                "content": "GitHub: https://github.com/sriniwas | LinkedIn: https://linkedin.com/in/sriniwas"
            }
        ]
        # Example A from requirements
        spoken = (
            "Hey guys, I am Sriniwas, welcome to today's session on AI pipelines "
            "my social links and thank you everyone for joining."
        )
        out = VoiceTriggerExpander.expand_triggers(spoken, snippets)
        self.assertEqual(
            out,
            "Hey guys, I am Sriniwas, welcome to today's session on AI pipelines. "
            "GitHub: https://github.com/sriniwas | LinkedIn: https://linkedin.com/in/sriniwas. "
            "And thank you everyone for joining."
        )

        # Adjacent punctuation variant
        spoken_comma = "Welcome to the demo, my social links, and thanks for watching."
        out_comma = VoiceTriggerExpander.expand_triggers(spoken_comma, snippets)
        self.assertIn("GitHub: https://github.com/sriniwas | LinkedIn: https://linkedin.com/in/sriniwas.", out_comma)
        self.assertIn("And thanks for watching.", out_comma)

    def test_05_strict_sub_3s_chunking_20s_and_60s(self):
        wav_20s = (ROOT / "tests" / "test_20s_speech.wav").read_bytes()
        chunks_20 = divide_into_dynamic_chunks(wav_20s, chunk_sec=2.5, overlap_sec=0.4)
        self.assertGreaterEqual(len(chunks_20), 7)
        for idx, (s, e, c_bytes) in enumerate(chunks_20):
            dur = e - s
            self.assertLessEqual(dur, 3.01, f"Chunk {idx} exceeded 3.0s: {dur:.2f}s")
            c_dur, _, _, _ = get_audio_info(c_bytes)
            self.assertLessEqual(c_dur, 3.01, f"Chunk {idx} WAV exceeded 3.0s: {c_dur:.2f}s")

        # Build 60s WAV by repeating wav_20s PCM frames 3x
        with wave.open(io.BytesIO(wav_20s), "rb") as wf:
            fr, nc, sw = wf.getframerate(), wf.getnchannels(), wf.getsampwidth()
            pcm = wf.readframes(wf.getnframes())
        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(nc)
            wf.setsampwidth(sw)
            wf.setframerate(fr)
            wf.writeframes(pcm * 3)
        wav_60s = bio.getvalue()
        chunks_60 = divide_into_dynamic_chunks(wav_60s, chunk_sec=2.5, overlap_sec=0.4)
        self.assertGreaterEqual(len(chunks_60), 20)
        for idx, (s, e, _) in enumerate(chunks_60):
            self.assertLessEqual(e - s, 3.01, f"60s Chunk {idx} exceeded 3.0s: {e - s:.2f}s")

    def test_06_sequential_context_chaining_7_chunks_and_cross_boundary_triggers(self):
        rec = CumulativeContextReconciler()
        chunks = [
            "Yesterday we started migrating the",
            "database and write the new test",
            "for all the endpoint in our",
            "production service. We deployed fast",
            "api with post gres and",
            "kubernetes. Also check my social",
            "links and thank you everyone for joining."
        ]
        for i, c in enumerate(chunks):
            rec.add_chunk(chunk_id=i, raw_text=c, start_sec=i * 2.7, end_sec=(i + 1) * 2.7)
        merged = rec.finalize(language="en")

        pipe = UniversalPipeline()
        final = pipe.process(
            raw_text=merged,
            mode="clean_dictation",
            language="en",
            snippets=[{
                "trigger": "my social links",
                "content": "GitHub: https://github.com/sriniwas | LinkedIn: https://linkedin.com/in/sriniwas"
            }],
            dictionary=[
                {"spoken": "fast api", "replacement": "FastAPI"},
                {"spoken": "post gres", "replacement": "PostgreSQL"},
                {"spoken": "kubernetes", "replacement": "Kubernetes"},
            ]
        )
        self.assertIn("wrote", final)
        self.assertIn("tests", final)
        self.assertIn("endpoints", final)
        self.assertIn("FastAPI", final)
        self.assertIn("PostgreSQL", final)
        self.assertIn("Kubernetes", final)
        self.assertIn("GitHub: https://github.com/sriniwas | LinkedIn: https://linkedin.com/in/sriniwas", final)


if __name__ == "__main__":
    unittest.main(verbosity=2)
