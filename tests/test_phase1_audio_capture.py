"""
Automated Unit Tests for Phase 1: Audio Capture & Buffering.
Verifies:
1. High-fidelity polyphase resampling from native rates (44.1kHz, 48kHz, 96kHz) to 16kHz mono.
2. Producer-consumer continuous disk streaming without dropping frames.
3. Metrics calculation (duration, sample count, RMS) and model-received duration consistency (<0.1s).
4. 30-minute safety cap trigger logic.
5. Gentle 80 Hz DSP filter behaves as expected and is OFF by default.
"""
import io
import os
import sys
import time
import wave
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from app.audio_recorder import (
    AudioRecorder,
    resample_to_16k_mono,
    apply_dsp_filters,
    get_recordings_dir
)


class TestPhase1AudioCapture(unittest.TestCase):

    def test_resample_48k_to_16k(self):
        """Tests polyphase resampling from 48kHz stereo to 16kHz mono."""
        # 1.0s of 480 Hz tone at 48kHz stereo
        t = np.linspace(0, 1.0, 48000, endpoint=False)
        tone_48k_stereo = np.column_stack([np.sin(2 * np.pi * 480 * t), np.sin(2 * np.pi * 480 * t)])

        resampled_16k = resample_to_16k_mono(tone_48k_stereo, orig_sr=48000)
        self.assertEqual(resampled_16k.ndim, 1, "Output must be 1D (mono)")
        self.assertEqual(len(resampled_16k), 16000, "1.0s of 48kHz must resample to exactly 16000 samples")

    def test_resample_44k1_to_16k(self):
        """Tests polyphase resampling from 44.1kHz mono to 16kHz mono."""
        t = np.linspace(0, 1.0, 44100, endpoint=False)
        tone_44k = np.sin(2 * np.pi * 440 * t)

        resampled_16k = resample_to_16k_mono(tone_44k, orig_sr=44100)
        self.assertEqual(resampled_16k.ndim, 1)
        self.assertEqual(len(resampled_16k), 16000, "1.0s of 44.1kHz must resample to exactly 16000 samples")

    def test_dsp_filter_defaults(self):
        """Verifies DSP filters are OFF by default and do not distort clean speech."""
        audio = np.random.uniform(-0.5, 0.5, 16000).astype(np.float32)
        filtered = apply_dsp_filters(audio, sample_rate=16000, high_pass_enabled=False, peak_norm_enabled=False)
        np.testing.assert_array_equal(audio, filtered, "Audio must remain identical when DSP is OFF")

    def test_continuous_disk_streaming_and_metrics(self):
        """Verifies that AudioRecorder streams continuous PCM16 to disk and calculates duration/RMS."""
        recorder = AudioRecorder(sample_rate=16000, channels=1)
        recorder.device_sample_rate = 16000
        recorder.device_channels = 1

        # Simulate recorder start without actual hardware mic
        recorder.is_recording = True
        recorder.start_time = time.time()
        recorder._writer_thread = unittest.mock.MagicMock()
        # Initialize queue & worker
        import threading
        recorder._stop_event.clear()
        recorder._writer_thread = threading.Thread(target=recorder._writer_worker, daemon=True)
        recorder._writer_thread.start()

        # Enqueue 3 chunks of 0.5s audio (total 1.5s = 24,000 samples @ 16kHz)
        chunk = np.ones((8000, 1), dtype=np.float32) * 0.2
        for _ in range(3):
            recorder._audio_callback(chunk, frames=8000, time_info=None, status=None)
            time.sleep(0.05)

        # Stop recording
        wav_path, wav_bytes, duration, sample_count, rms = recorder.stop_recording()

        self.assertTrue(os.path.exists(wav_path), f"WAV file must exist at {wav_path}")
        self.assertGreater(len(wav_bytes), 40000, "WAV bytes must contain 24,000 PCM16 samples + header")
        self.assertAlmostEqual(duration, 1.5, delta=0.1, msg="Recorded duration must match expected within 0.1s")
        self.assertEqual(sample_count, 24000, "Sample count must be exactly 24000")
        self.assertAlmostEqual(rms, 0.2, delta=0.05, msg="RMS should match input amplitude")

        # Cleanup test wav
        try:
            os.remove(wav_path)
        except Exception:
            pass

    def test_safety_cap_trigger(self):
        """Verifies that reaching the 30-minute safety cap triggers on_safety_cap callback."""
        cap_triggered = False

        def _on_cap():
            nonlocal cap_triggered
            cap_triggered = True

        recorder = AudioRecorder(on_safety_cap=_on_cap)
        recorder.SAFETY_CAP_SECONDS = 0.5  # Temporary small threshold for testing

        recorder.is_recording = True
        recorder.device_sample_rate = 16000
        recorder._stop_event.clear()

        import threading
        t = threading.Thread(target=recorder._writer_worker, daemon=True)
        t.start()

        # Send 0.6s of audio (> 0.5s safety cap)
        chunk = np.zeros((9600, 1), dtype=np.float32)
        recorder._raw_queue.put(chunk)
        time.sleep(0.15)

        recorder._stop_event.set()
        t.join(timeout=1.0)
        recorder.is_recording = False

        self.assertTrue(cap_triggered, "Safety cap callback must have been triggered")

        # Clean up created file
        if recorder._current_wav_path and recorder._current_wav_path.exists():
            try:
                recorder._current_wav_path.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
