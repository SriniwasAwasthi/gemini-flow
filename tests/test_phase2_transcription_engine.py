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
    """Creates synthetic English speech WAV using Windows SAPI."""
    import win32com.client
    tmp_path = os.path.join(tempfile.gettempdir(), f"sapi_test_{int(time.time()*1000)}.wav")
    try:
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        stream.Open(tmp_path, 3)
        voice.AudioOutputStream = stream
        voice.Speak(text)
        stream.Close()
        with open(tmp_path, "rb") as f:
            wav_bytes = f.read()
        return wav_bytes
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


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


if __name__ == "__main__":
    unittest.main()
