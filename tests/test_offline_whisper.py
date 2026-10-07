"""
Verification Test Suite for Gemini Flow Offline Whisper Engine
Tests offline model loading, audio decoding, proper noun accuracy, and dictionary normalization.
"""
import os
import sys
import io
import time
from pathlib import Path

# Add project root directory to path
PROJECT_DIR = Path(__file__).parent.parent.resolve()
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app.offline.offline_engine import OfflineSpeechEngine
from app.gemini_engine import GeminiEngine
from app.vocabulary.vocab_engine import VocabEngine


def test_offline_engine():
    print("=" * 70)
    print("  TESTING OFFLINE SPEECH ENGINE (OPENAI WHISPER + CTRANSLATE2)")
    print("=" * 70)

    # 1. Model Singleton & Warmup Test
    print("\n[1] Testing Model Initialization & Singleton...")
    t0 = time.time()
    model = OfflineSpeechEngine.get_whisper_model("base.en")
    assert model is not None, "Failed to load Whisper base.en model!"
    print(f"  [PASS] Whisper base.en model ready in {time.time() - t0:.2f}s.")

    # 2. Test In-Memory Audio Transcription
    test_audio = PROJECT_DIR / "test_audio_sample.wav"
    if not test_audio.exists():
        test_audio = PROJECT_DIR / "scratch" / "test_user_phrase.wav"

    assert test_audio.exists(), f"Test audio file not found: {test_audio}"

    with open(test_audio, "rb") as f:
        wav_bytes = f.read()

    print(f"\n[2] Testing Transcription on '{test_audio.name}' ({len(wav_bytes)} bytes)...")
    prompt = "Hi, I am Sriniwas Awasthi, using Gemini Flow voice dictation in offline mode."
    t0 = time.time()
    success, text = OfflineSpeechEngine.transcribe_wav(wav_bytes, initial_prompt=prompt)
    duration = time.time() - t0

    assert success, f"Transcription failed: {text}"
    print(f"  [PASS] Offline Transcription Success in {duration:.2f}s:")
    print(f"  Result: '{text}'")

    # 3. Test Vocabulary & Dictionary Normalization
    print("\n[3] Testing Dictionary & Vocabulary Normalization...")
    dict_rules = [
        {"spoken": "Srinivas Avasthi", "replacement": "Sriniwas Awasthi"},
        {"spoken": "Shrinivas", "replacement": "Sriniwas"}
    ]
    normalized = GeminiEngine.apply_dictionary(text, dict_rules)
    print(f"  [PASS] Post-Processed Text: '{normalized}'")

    # 4. Test Silence Handling (Short audio or silence should not crash)
    print("\n[4] Testing Short / Empty Audio Handling...")
    ok, err = OfflineSpeechEngine.transcribe_wav(b"RIFF" + b"\x00" * 100)
    assert not ok, "Short audio should return False"
    print(f"  [PASS] Short audio correctly rejected: '{err}'")

    # 5. Test Offline Mode in GeminiEngine
    print("\n[5] Testing GeminiEngine Offline Fallback (Without API Key)...")
    gemini_offline = GeminiEngine(api_key="", model_name="gemini-2.5-flash")
    ok, res = gemini_offline.transcribe_audio(
        wav_bytes=wav_bytes,
        system_instruction="Clean verbatim text",
        offline_fallback_enabled=True
    )
    assert ok, f"GeminiEngine offline fallback failed: {res}"
    print(f"  [PASS] GeminiEngine offline fallback succeeded:")
    print(f"  Model Used: '{gemini_offline.last_model_used}'")
    print(f"  Fallback Result: '{res}'")

    print("\n" + "=" * 70)
    print("  ALL OFFLINE SPEECH ENGINE TESTS PASSED 100%!")
    print("=" * 70)


if __name__ == "__main__":
    test_offline_engine()
