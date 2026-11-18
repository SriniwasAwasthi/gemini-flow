"""
Automated Tests for Phase 2: Unified Transcription Engine & Zero Truncation.
Verifies:
1. Unified Transcript contract adherence.
2. Full audio coverage verification (covered_seconds within 1.5s of total duration).
3. 30-second speech zero-truncation guarantee (fixes the 13s-of-30s drop).
4. Silence-aligned chunking and suffix-prefix overlap deduplication.
5. Hallucination loop detection and suppression.
"""
import io
import os
import sys
import time
import tempfile
import wave
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from app.transcription.contract import Transcript
from app.transcription.chunker import (
    split_at_silence_boundaries,
    merge_overlapping_transcripts,
    detect_hallucination_loop
)
from app.transcription.engine import UnifiedTranscriptionEngine


def create_test_wav_pcm(duration_sec: float, sample_rate: int = 16000, tone_hz: float = 440.0) -> bytes:
    """Creates synthetic PCM16 WAV audio for testing."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    # Fundamental tone with envelope
    sig = (0.25 * np.sin(2 * np.pi * tone_hz * t)).astype(np.float32)
    pcm16 = (sig * 32767).astype(np.int16)
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())
    return bio.getvalue()


def create_test_speech_sapi(text: str) -> bytes:
    """Creates synthetic English speech WAV using Windows SAPI via PowerShell."""
    import subprocess
    tmp_path = os.path.join(tempfile.gettempdir(), f"sapi_test_{int(time.time()*1000)}.wav").replace("\\", "/")
    escaped_text = text.replace("'", "''")
    script = (
        f"$sp = New-Object -ComObject SAPI.SpVoice; "
        f"$fs = New-Object -ComObject SAPI.SpFileStream; "
        f"$fs.Open('{tmp_path}', 3); "
        f"$sp.AudioOutputStream = $fs; "
        f"$sp.Speak('{escaped_text}'); "
        f"$fs.Close();"
    )
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True)
    if os.path.exists(tmp_path):
        try:
            with open(tmp_path, "rb") as f:
                wav_bytes = f.read()
            return wav_bytes
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    return create_test_wav_pcm(30.0)


class TestPhase2TranscriptionEngine(unittest.TestCase):

    def setUp(self):
        self.engine = UnifiedTranscriptionEngine(api_key="")

    def test_transcript_contract_structure(self):
        """Verifies Transcript dataclass fields and coverage validation property."""
        t = Transcript(
            text="Hello world test.",
            segments=[{"start": 0.0, "end": 4.5, "text": "Hello world test."}],
            audio_seconds=5.0,
            covered_seconds=4.5,
            model="offline-whisper"
        )
        self.assertTrue(t.is_fully_covered, "4.5s out of 5.0s is fully covered (within 1.5s delta)")
        self.assertEqual(t.text, "Hello world test.")
        self.assertEqual(len(t.segments), 1)

    def test_suffix_prefix_merging(self):
        """Verifies merging of overlapping chunk transcripts with duplicate overlap removal."""
        chunk1 = "We have completed the deployment of our service on Friday"
        chunk2 = "our service on Friday and all integration tests have passed successfully."
        merged = merge_overlapping_transcripts([chunk1, chunk2])
        expected = "We have completed the deployment of our service on Friday and all integration tests have passed successfully."
        self.assertEqual(merged, expected, "Duplicated overlap words 'our service on Friday' must be merged seamlessly")

    def test_silence_chunking_boundaries(self):
        """Verifies silence boundary detection for audio longer than 25 seconds."""
        # 32 seconds audio with quiet valleys at 14s and 26s
        sr = 16000
        total_sec = 32.0
        t = np.linspace(0, total_sec, int(sr * total_sec), endpoint=False)
        audio = 0.2 * np.sin(2 * np.pi * 300 * t)
        # Create silence valley at 15s (1s valley)
        audio[int(14.5 * sr) : int(15.5 * sr)] = 0.0001
        pcm16 = (audio * 32767).astype(np.int16)

        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm16.tobytes())

        chunks = split_at_silence_boundaries(bio.getvalue(), max_chunk_sec=20.0, min_chunk_sec=10.0, overlap_sec=1.5)
        self.assertGreaterEqual(len(chunks), 2, "32s audio must be split into at least 2 chunks")
        # Ensure chunks overlap
        first_end = chunks[0][1]
        second_start = chunks[1][0]
        self.assertLess(second_start, first_end, "Successive chunks must have overlap padding")

    def test_hallucination_loop_detection(self):
        """Verifies detection of repeated n-grams and ghost subtitle loops."""
        normal_text = "This is a standard English dictation about software architecture and performance."
        self.assertFalse(detect_hallucination_loop(normal_text))

        # Repeated 3-gram hallucination
        loop_text = "thank you for watching thank you for watching thank you for watching"
        self.assertTrue(detect_hallucination_loop(loop_text), "Must detect repeated ghost phrases")

        ngram_loop = "please subscribe to the channel please subscribe to the channel please subscribe to the channel"
        self.assertTrue(detect_hallucination_loop(ngram_loop), "Must detect repeated n-gram loops")

    def test_zero_truncation_30s_speech(self):
        """
        Directly tests and proves the resolution of the 13s-of-30s truncation bug.
        Runs full faster-whisper transcription on a 30-second speech audio and verifies
        that covered_seconds covers the entire duration within 1.5s delta and the concluding
        phrase is present in the final transcript.
        """
        long_speech = (
            "We are conducting a comprehensive thirty-second verification test for the Gemini Flow speech recognition system. "
            "In earlier versions, there was a risk of speech truncation where audio beyond thirteen seconds could be prematurely cut off. "
            "We have re-architected the entire audio capture, buffering, and transcription pipeline to eliminate all truncation. "
            "Now every single spoken syllable is preserved with zero frame drops, concluding the final thirty seconds successfully."
        )
        wav_bytes = create_test_speech_sapi(long_speech)
        transcript = self.engine.transcribe(wav_bytes, model_name="offline-whisper")

        self.assertTrue(transcript.success)
        self.assertGreater(transcript.audio_seconds, 20.0, "Audio duration must be >20s")
        # Verify coverage does not cut off at 13 seconds!
        self.assertTrue(
            transcript.is_fully_covered,
            f"Coverage failed: covered_seconds ({transcript.covered_seconds:.1f}s) of {transcript.audio_seconds:.1f}s audio!"
        )
        # Verify concluding phrase is intact (accounting for numerical representation 30 vs thirty)
        has_conclusion = ("concluding the final" in transcript.text.lower() and 
                          ("30 seconds" in transcript.text.lower() or "thirty seconds" in transcript.text.lower()))
        self.assertTrue(has_conclusion, f"Concluding words must be present in transcript: '{transcript.text}'")

    def test_groq_routing_precedence(self):
        """Verifies groq-whisper-turbo routes to _transcribe_groq without being hijacked by Faster-Whisper."""
        from unittest.mock import patch
        engine = UnifiedTranscriptionEngine(api_key="gsk_test_mock_routing_key")
        dummy_wav = create_test_wav_pcm(1.0)
        with patch.object(engine, "_transcribe_groq") as mock_groq:
            with patch.object(engine, "_transcribe_faster_whisper") as mock_fw:
                mock_groq.return_value = Transcript(
                    text="Groq routed successfully.",
                    segments=[{"start": 0.0, "end": 1.0, "text": "Groq routed successfully."}],
                    audio_seconds=1.0,
                    covered_seconds=1.0,
                    model="groq-whisper-turbo",
                    success=True
                )
                res = engine.transcribe(dummy_wav, model_name="groq-whisper-turbo")
                mock_groq.assert_called_once()
                mock_fw.assert_not_called()
                self.assertEqual(res.model, "groq-whisper-turbo")
                self.assertEqual(res.text, "Groq routed successfully.")

    def test_groq_request_payload_and_authorization(self):
        """Verifies Groq multipart POST construction, whisper-large-v3-turbo model, and Bearer token."""
        from unittest.mock import patch, MagicMock
        engine = UnifiedTranscriptionEngine(api_key="gsk_live_test_api_key_12345")
        dummy_wav = create_test_wav_pcm(2.0)

        with patch.object(engine.session, "post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "text": "Ultra-low latency dictation on Groq LPU.",
                "segments": [{"start": 0.0, "end": 2.0, "text": "Ultra-low latency dictation on Groq LPU."}],
                "duration": 2.0
            }
            mock_post.return_value = mock_resp

            t = engine.transcribe(dummy_wav, model_name="groq-whisper-turbo", previous_context="Previous context words.")
            self.assertTrue(t.success)
            self.assertEqual(t.model, "groq-whisper-turbo")
            self.assertEqual(t.text, "Ultra-low latency dictation on Groq LPU.")

            # Inspect post call args
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            self.assertEqual(args[0], "https://api.groq.com/openai/v1/audio/transcriptions")
            self.assertEqual(kwargs["headers"]["Authorization"], "Bearer gsk_live_test_api_key_12345")
            self.assertEqual(kwargs["data"]["model"], "whisper-large-v3-turbo")
            self.assertEqual(kwargs["data"]["prompt"], "Previous context words.")
            self.assertIn("file", kwargs["files"])

    def test_groq_response_parsing_and_contract(self):
        """Verifies parsing of standard Groq JSON into complete Transcript contract."""
        from unittest.mock import patch, MagicMock
        engine = UnifiedTranscriptionEngine(api_key="gsk_valid_key_test")
        dummy_wav = create_test_wav_pcm(3.2)

        with patch.object(engine.session, "post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "text": "Quarterly financial summary completed.",
                "segments": [{"start": 0.0, "end": 3.2, "text": "Quarterly financial summary completed."}],
                "duration": 3.2
            }
            mock_post.return_value = mock_resp

            t = engine._transcribe_groq(dummy_wav, audio_seconds=3.2)
            self.assertTrue(t.success)
            self.assertEqual(t.text, "Quarterly financial summary completed.")
            self.assertEqual(t.model, "groq-whisper-turbo")
            self.assertEqual(t.audio_seconds, 3.2)
            self.assertEqual(t.covered_seconds, 3.2)
            self.assertTrue(t.is_fully_covered)

    def test_groq_timeout_and_error_recovery(self):
        """Verifies error handling for HTTP 401 and request timeout with Offline Whisper rescue."""
        from unittest.mock import patch, MagicMock
        import requests
        engine = UnifiedTranscriptionEngine(api_key="gsk_invalid_or_expired_key")
        dummy_wav = create_test_wav_pcm(1.5)

        # 1. Test 401 Unauthorized - rescues via Offline Whisper AI per Directive 1
        with patch.object(engine.session, "post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.text = "Invalid API key"
            mock_post.return_value = mock_resp

            t = engine._transcribe_groq(dummy_wav, audio_seconds=1.5)
            self.assertTrue(t.success, "Groq 401 must be rescued by Offline Whisper AI per Directive 1")
            self.assertTrue(any("rescued by Offline Whisper AI" in w for w in t.warnings))

        # 2. Test Timeout - rescues via Offline Whisper AI per Directive 1
        with patch.object(engine.session, "post", side_effect=requests.exceptions.Timeout("Request timed out")):
            t = engine._transcribe_groq(dummy_wav, audio_seconds=1.5)
            self.assertTrue(t.success, "Groq timeout must be rescued by Offline Whisper AI per Directive 1")
            self.assertTrue(any("rescued by Offline Whisper AI" in w for w in t.warnings))

    def test_groq_missing_key_graceful_fallback(self):
        """Verifies graceful fallback to offline Whisper when GROQ_API_KEY is not configured."""
        from unittest.mock import patch
        engine = UnifiedTranscriptionEngine(api_key="")
        dummy_wav = create_test_wav_pcm(1.0)

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(engine, "_transcribe_faster_whisper") as mock_fw:
                mock_fw.return_value = Transcript(
                    text="Offline fallback text.",
                    segments=[],
                    audio_seconds=1.0,
                    covered_seconds=1.0,
                    model="offline-whisper",
                    success=True
                )
                t = engine.transcribe(dummy_wav, model_name="groq-whisper-turbo")
                mock_fw.assert_called_once()
                self.assertTrue(t.success)
                self.assertTrue(any("GROQ_API_KEY" in w for w in t.warnings))

    def test_moonshine_offline_isolation_without_remote_calls(self):
        """Verifies Moonshine execution strictly operates locally and never calls download.moonshine.ai."""
        import urllib.request
        from unittest.mock import patch

        engine = UnifiedTranscriptionEngine(api_key="")
        dummy_wav = create_test_wav_pcm(1.5)

        # Mock network to detect any outbound attempt to download.moonshine.ai
        with patch("requests.get", side_effect=AssertionError("Network call to download.moonshine.ai is forbidden!")):
            with patch("requests.post", side_effect=AssertionError("Outbound network is forbidden!")):
                t = engine.transcribe(dummy_wav, model_name="moonshine-onnx")
                self.assertIsInstance(t, Transcript)
                self.assertTrue(t.success)

    def test_moonshine_audio_normalization_16khz_mono(self):
        """Verifies _prepare_moonshine_audio downmixes stereo and resamples to 16kHz float32 [-1.0, 1.0]."""
        # Create 44.1kHz stereo audio
        sr_44k = 44100
        duration = 0.5
        t = np.linspace(0, duration, int(sr_44k * duration), endpoint=False)
        ch1 = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        ch2 = (0.2 * np.sin(2 * np.pi * 880 * t)).astype(np.float32)
        stereo_pcm = np.empty((len(t) * 2,), dtype=np.int16)
        stereo_pcm[0::2] = (ch1 * 32767).astype(np.int16)
        stereo_pcm[1::2] = (ch2 * 32767).astype(np.int16)

        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr_44k)
            wf.writeframes(stereo_pcm.tobytes())

        samples, out_sr = UnifiedTranscriptionEngine._prepare_moonshine_audio(bio.getvalue())
        self.assertEqual(out_sr, 16000)
        self.assertEqual(samples.dtype, np.float32)
        self.assertTrue(np.all(samples >= -1.0) and np.all(samples <= 1.0))
        # Expected sample count roughly 16000 * 0.5 = 8000
        self.assertAlmostEqual(len(samples), 8000, delta=20)

    def test_moonshine_missing_model_graceful_handling(self):
        """Verifies graceful fallback rescue to Offline Whisper when local model weights are absent."""
        from unittest.mock import patch
        engine = UnifiedTranscriptionEngine(api_key="")
        dummy_wav = create_test_wav_pcm(1.0)

        with patch.object(engine, "_find_moonshine_model_dir", return_value=None):
            t = engine._transcribe_moonshine_onnx(dummy_wav, audio_seconds=1.0)
            self.assertTrue(t.success, "Missing Moonshine weights must be rescued by Offline Whisper AI")
            self.assertEqual(t.model, "offline-whisper")
            self.assertTrue(any("Moonshine ONNX" in w for w in t.warnings))

    def test_model_router_and_settings_dropdown_sync(self):
        """Verifies groq-whisper-turbo and moonshine-onnx are in MODEL_REGISTRY and selectable."""
        from app.router.model_router import ModelRouter, MODEL_REGISTRY

        self.assertIn("groq-whisper-turbo", MODEL_REGISTRY)
        self.assertIn("moonshine-onnx", MODEL_REGISTRY)

        router = ModelRouter()
        res_groq = router.route(manual_override="groq-whisper-turbo")
        self.assertEqual(res_groq.model_name, "groq-whisper-turbo")

        res_moon = router.route(manual_override="moonshine-onnx")
        self.assertEqual(res_moon.model_name, "moonshine-onnx")


if __name__ == "__main__":
    unittest.main()

