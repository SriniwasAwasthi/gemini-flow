"""
Unit test for AudioRecorder simulating a 3-second dictation recording.
Verifies zero AttributeError exceptions, in-memory processing, rolling chunk methods,
audio capture diagnostics, and safe disconnection handling.
"""
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from app.audio_recorder import AudioRecorder, resample_to_16k_mono, apply_dsp_filters


class TestAudioRecorderSimulated(unittest.TestCase):
    def test_simulated_3s_recording(self):
        amplitude_events = []
        silence_cut_events = []

        recorder = AudioRecorder(
            sample_rate=16000,
            channels=1,
            on_amplitude=lambda a: amplitude_events.append(a),
            on_speech_silence_cut=lambda: silence_cut_events.append(True)
        )

        # 1. Verify attributes exist and do not raise AttributeError
        self.assertTrue(hasattr(recorder, "get_rolling_chunk"))
        self.assertTrue(hasattr(recorder, "rolling_chunks_were_emitted"))
        self.assertTrue(hasattr(recorder, "get_diagnostics"))
        self.assertFalse(recorder.rolling_chunks_were_emitted())
        self.assertIsNone(recorder.get_rolling_chunk(min_sec=30.0, max_sec=45.0))

        # Check initial diagnostics
        diag_init = recorder.get_diagnostics()
        self.assertIsInstance(diag_init, dict)
        self.assertIn("device_index", diag_init)
        self.assertIn("device_name", diag_init)
        self.assertIn("sample_rate", diag_init)
        self.assertIn("buffer_rms", diag_init)
        self.assertIn("buffers_delivered", diag_init)
        self.assertIn("is_recording", diag_init)
        self.assertIn("device_disconnected", diag_init)
        self.assertFalse(diag_init["is_recording"])
        self.assertFalse(diag_init["device_disconnected"])

        # 2. Start recording
        started = recorder.start_recording()
        self.assertTrue(started, "Recorder should start successfully")
        self.assertTrue(recorder.is_recording)

        # 3. Feed simulated 3 seconds of audio into raw_queue
        sr = recorder.device_sample_rate
        total_samples = int(3.0 * sr)
        t = np.linspace(0, 3.0, total_samples, endpoint=False)
        synthetic_speech = (0.2 * np.sin(2 * np.pi * 440 * t) + 0.01 * np.random.randn(total_samples)).astype(np.float32)

        for i in range(0, len(synthetic_speech), 1024):
            block = synthetic_speech[i : i + 1024]
            recorder._raw_queue.put(block)

        # Allow worker thread time to process all blocks
        time.sleep(0.3)

        # Diagnostics during active recording
        diag_active = recorder.get_diagnostics()
        self.assertTrue(diag_active["is_recording"])
        self.assertGreater(diag_active["sample_count"], 8000)

        # 4. Check rolling chunk call during recording (should return None safely since < 30s)
        chunk = recorder.get_rolling_chunk(min_sec=30.0, max_sec=45.0)
        self.assertIsNone(chunk)
        has_rolling = recorder.rolling_chunks_were_emitted()
        self.assertFalse(has_rolling)

        # 5. Stop recording
        wav_path, wav_bytes, duration, sample_count, rms = recorder.stop_recording()

        self.assertFalse(recorder.is_recording)
        self.assertGreater(len(wav_bytes), 1000, "WAV bytes must be generated in-memory")
        self.assertGreater(duration, 0.5, "Duration should reflect simulated audio")
        self.assertGreater(sample_count, 8000, "Samples should be accumulated")
        self.assertGreater(rms, 0.01, "RMS should reflect simulated audio energy")

        # Zero-disk check for < 30s: wav_path should be empty string (pure in-memory)
        self.assertEqual(wav_path, "", "Dictations under 30s must execute with zero disk I/O")

        # Diagnostics after stopping
        diag_stopped = recorder.get_diagnostics()
        self.assertFalse(diag_stopped["is_recording"])
        self.assertGreater(diag_stopped["sample_count"], 8000)
        self.assertGreater(diag_stopped["buffer_rms"], 0.01)

        print(f"\n[TEST PASSED] Duration={duration:.2f}s, Samples={sample_count}, Bytes={len(wav_bytes)}, RMS={rms:.4f}")

    def test_safe_disconnection_handling(self):
        """Verifies safe handling of invalid/disconnected input device without silent hijacking."""
        recorder = AudioRecorder(sample_rate=16000, channels=1)
        # Select an invalid device index that cannot be opened
        recorder.set_device(999999)

        started = recorder.start_recording()
        self.assertFalse(started, "Opening non-existent device index must fail safely")
        self.assertFalse(recorder.is_recording, "is_recording must remain False")
        self.assertTrue(recorder.device_disconnected, "device_disconnected must be True")

        # Diagnostics must report device_disconnected True and device_index 999999
        diag = recorder.get_diagnostics()
        self.assertTrue(diag["device_disconnected"])
        self.assertEqual(diag["device_index"], 999999)


if __name__ == "__main__":
    unittest.main()
