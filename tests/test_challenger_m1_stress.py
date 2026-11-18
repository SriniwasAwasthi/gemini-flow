"""
Challenger M1 Stress Test Harness:
Empirical verification of WASAPI rate negotiation, multi-rate resampling,
buffer queue throughput, memory behavior, and rapid start/stop cycles.
"""
import io
import os
import sys
import time
import math
import wave
import queue
import tempfile
import threading
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import sounddevice as sd
from app.audio_recorder import (
    AudioRecorder,
    resample_to_16k_mono,
    apply_dsp_filters
)


class TestWASAPIRateNegotiationStress(unittest.TestCase):
    """Adversarial stress testing of WASAPI rate negotiation and multi-rate resampling."""

    def test_multi_rate_resampling_coverage(self):
        """Stress tests resample_to_16k_mono across 48k, 44.1k, 16k, 32k, 88.2k, 96k, 8k, 192k."""
        test_rates = [48000, 44100, 16000, 32000, 88200, 96000, 8000, 192000]
        duration_sec = 0.5
        freq = 440.0

        for sr in test_rates:
            with self.subTest(rate=sr):
                n_samples = int(sr * duration_sec)
                t = np.linspace(0, duration_sec, n_samples, endpoint=False)
                tone = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)

                # Test 1: Single full chunk
                resampled = resample_to_16k_mono(tone, orig_sr=sr)
                self.assertIsInstance(resampled, np.ndarray)
                self.assertFalse(np.isnan(resampled).any(), f"NaNs detected for rate {sr}")
                self.assertFalse(np.isinf(resampled).any(), f"Infs detected for rate {sr}")
                expected_len = int(duration_sec * 16000)
                self.assertAlmostEqual(len(resampled), expected_len, delta=20,
                                       msg=f"Length mismatch for rate {sr}: got {len(resampled)}, expected ~{expected_len}")

                # Test 2: Chunked streaming with state carryover (1024-sample blocks)
                block_size = max(64, int(sr * 0.02))  # ~20ms blocks
                chunks = [tone[i:i + block_size] for i in range(0, len(tone), block_size)]
                stream_out = []
                state = None
                for c in chunks:
                    c_out, state = resample_to_16k_mono(c, orig_sr=sr, filter_state=state)
                    stream_out.append(c_out)

                concat_stream = np.concatenate(stream_out)
                self.assertFalse(np.isnan(concat_stream).any(), f"NaNs in chunked stream for rate {sr}")
                self.assertAlmostEqual(len(concat_stream), expected_len, delta=50,
                                       msg=f"Stream length mismatch for rate {sr}")

    def test_resolve_device_parameters_rate_matrix(self):
        """Stress tests _resolve_device_parameters across various device configurations."""
        recorder = AudioRecorder()

        # Matrix of simulated device configurations
        scenarios = [
            # (native_rate, max_ch, check_settings_rejects, expected_rate, expected_ch)
            (48000, 2, [], 48000, 1),
            (44100, 1, [], 44100, 1),
            (16000, 1, [], 16000, 1),
            (32000, 2, [], 32000, 1),
            (88200, 2, [], 88200, 1),
            (96000, 2, [], 96000, 1),
            # Case where native rate 88200 is rejected by check_input_settings, but 48000 succeeds
            (88200, 2, [88200], 48000, 1),
            # Case where 48000 and 44100 are rejected, only 16000 succeeds
            (48000, 1, [48000, 44100], 16000, 1),
            # Case where device only supports 2 channels, not 1
            (48000, 2, [(48000, 1)], 48000, 2),
        ]

        for native_sr, max_ch, rejected, exp_sr, exp_ch in scenarios:
            with self.subTest(native_sr=native_sr, max_ch=max_ch, rejected=rejected):
                with unittest.mock.patch("sounddevice.query_devices") as mock_qd, \
                     unittest.mock.patch("sounddevice.check_input_settings") as mock_chk:

                    mock_qd.return_value = {
                        "index": 4,
                        "name": f"Mock Mic {native_sr}Hz",
                        "default_samplerate": native_sr,
                        "max_input_channels": max_ch
                    }

                    def side_effect(device, channels, dtype, samplerate):
                        for rej in rejected:
                            if isinstance(rej, tuple):
                                if (samplerate, channels) == rej:
                                    raise RuntimeError(f"Rejected {samplerate}Hz {channels}ch")
                            elif samplerate == rej:
                                raise RuntimeError(f"Rejected {samplerate}Hz")
                        return True

                    mock_chk.side_effect = side_effect

                    dev_idx, resolved_rate, resolved_ch = recorder._resolve_device_parameters(4)
                    self.assertEqual(resolved_rate, exp_sr, f"Failed rate resolution for native {native_sr}")
                    self.assertEqual(resolved_ch, exp_ch, f"Failed channel resolution for native {native_sr}")
                    self.assertEqual(dev_idx, 4)

    def test_resolve_device_parameters_total_rejection_resilience(self):
        """When check_input_settings rejects ALL rates, it falls back to native_rate without throwing."""
        recorder = AudioRecorder()
        with unittest.mock.patch("sounddevice.query_devices") as mock_qd, \
             unittest.mock.patch("sounddevice.check_input_settings") as mock_chk:

            mock_qd.return_value = {
                "index": 7,
                "name": "Hostile Hardware",
                "default_samplerate": 48000,
                "max_input_channels": 2
            }
            # Reject all rates
            mock_chk.side_effect = RuntimeError("WASAPI PaErrorCode -9997")

            dev_idx, rate, ch = recorder._resolve_device_parameters(7)
            # Must return gracefully without crashing
            self.assertEqual(dev_idx, 7)
            self.assertEqual(rate, 48000)
            self.assertIn(ch, [1, 2])

    def test_resolve_device_parameters_invalid_device_index(self):
        """When device index does not exist, marks device_disconnected=True and does not crash."""
        recorder = AudioRecorder()
        with unittest.mock.patch("sounddevice.query_devices") as mock_qd:
            mock_qd.side_effect = ValueError("Invalid device index 999999")

            dev_idx, rate, ch = recorder._resolve_device_parameters(999999)
            self.assertEqual(dev_idx, 999999)
            self.assertTrue(recorder.device_disconnected)
            self.assertEqual(rate, 16000)
            self.assertEqual(ch, 1)

    def test_resolve_device_parameters_none_device_no_crash(self):
        """When dev_idx=None, resolves default input device safely."""
        recorder = AudioRecorder()
        dev_idx, rate, ch = recorder._resolve_device_parameters(None)
        # Should return without exception
        self.assertIn(rate, [16000, 44100, 48000, 32000, 88200, 96000])
        self.assertGreaterEqual(ch, 1)


class TestBufferQueueThroughputAndMemoryStress(unittest.TestCase):
    """Adversarial stress testing of buffer queue, memory leakage, and worker throughput."""

    def test_rapid_injection_100_plus_chunks(self):
        """Rapidly injects 150 audio chunks into AudioRecorder pipeline and verifies queue stability."""
        recorder = AudioRecorder(sample_rate=16000, channels=1, enable_dsp=True)
        recorder.device_sample_rate = 48000
        recorder.device_channels = 1
        recorder.is_recording = True
        recorder.start_time = time.time()
        recorder._stop_event.clear()

        recorder._writer_thread = threading.Thread(target=recorder._writer_worker, daemon=True)
        recorder._writer_thread.start()

        num_chunks = 150
        chunk_size = 1024  # 1024 samples at 48kHz = ~21.3ms

        t = np.linspace(0, 0.0213, chunk_size, endpoint=False)
        base_chunk = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32).reshape(-1, 1)

        # Rapid injection loop
        for i in range(num_chunks):
            recorder._audio_callback(base_chunk, frames=chunk_size, time_info=None, status=None)

        # Verify diagnostics buffers_delivered counts all injected buffers
        diag = recorder.get_diagnostics()
        self.assertEqual(diag["buffers_delivered"], num_chunks,
                         f"Expected {num_chunks} buffers delivered, got {diag['buffers_delivered']}")

        # Give worker up to 2 seconds to drain queue
        t_start = time.time()
        while not recorder._raw_queue.empty() and time.time() - t_start < 2.0:
            time.sleep(0.01)

        self.assertTrue(recorder._raw_queue.empty(), "Worker failed to drain raw queue within timeout")

        # Verify raw accumulated samples before stop_recording
        with recorder._buffer_lock:
            raw_accumulated = sum(len(c) for c in recorder._accumulated_16k_samples)

        expected_16k_samples = int(num_chunks * chunk_size * 16000 / 48000)
        self.assertAlmostEqual(raw_accumulated, expected_16k_samples, delta=1000,
                               msg="Accumulated sample count must match injected audio frames")

        # Stop recording and check metrics
        wav_path, wav_bytes, duration, sample_count, rms = recorder.stop_recording()

        self.assertGreater(sample_count, 0)
        self.assertGreater(len(wav_bytes), sample_count * 2, "WAV bytes must contain PCM16 frames")
        self.assertGreater(rms, 0.01, "RMS must reflect non-zero energy")
        self.assertFalse(recorder.is_recording)

    def test_rapid_start_stop_cycles(self):
        """Performs 20 rapid start/stop cycles to verify zero deadlocks or thread leaks."""
        for cycle in range(20):
            recorder = AudioRecorder(sample_rate=16000, channels=1, enable_dsp=False)
            recorder.device_sample_rate = 16000
            recorder.is_recording = True
            recorder.start_time = time.time()
            recorder._stop_event.clear()

            recorder._writer_thread = threading.Thread(target=recorder._writer_worker, daemon=True)
            recorder._writer_thread.start()

            # Push 5 chunks
            chunk = np.zeros((512, 1), dtype=np.float32)
            for _ in range(5):
                recorder._audio_callback(chunk, frames=512, time_info=None, status=None)

            # Rapid stop
            wav_path, wav_bytes, dur, count, rms = recorder.stop_recording()
            self.assertFalse(recorder.is_recording)
            self.assertFalse(recorder._writer_thread.is_alive())

    def test_status_flags_underflow_overflow_resilience(self):
        """Verifies that PortAudio status flags (overflow, underflow) are handled without crashing."""
        recorder = AudioRecorder(sample_rate=16000, channels=1)
        recorder.is_recording = True

        status_mock = unittest.mock.MagicMock()
        status_mock.input_underflow = True
        status_mock.input_overflow = True
        status_mock.__str__.return_value = "input overflow, input underflow"

        chunk = np.ones((512, 1), dtype=np.float32) * 0.1
        try:
            recorder._audio_callback(chunk, frames=512, time_info=None, status=status_mock)
        except Exception as e:
            self.fail(f"Audio callback crashed on PortAudio status flags: {e}")

        self.assertEqual(recorder._buffers_delivered, 1)

    def test_long_session_ram_to_disk_rollover(self):
        """Verifies that recordings over 30 seconds trigger WAV file writing without memory corruption."""
        temp_dir = Path(tempfile.gettempdir()) / "gf_challenger_test_rec"
        temp_dir.mkdir(parents=True, exist_ok=True)

        with unittest.mock.patch("app.audio_recorder.get_recordings_dir", return_value=temp_dir):
            recorder = AudioRecorder(sample_rate=16000, channels=1, enable_dsp=False)
            recorder.device_sample_rate = 16000
            recorder.is_recording = True
            recorder.start_time = time.time()
            recorder._stop_event.clear()

            recorder._writer_thread = threading.Thread(target=recorder._writer_worker, daemon=True)
            recorder._writer_thread.start()

            # Inject 32 seconds worth of audio: 32 * 16000 = 512,000 samples
            # Chunk size 16000 (1 second per chunk) -> 32 chunks
            chunk = (0.1 * np.ones((16000, 1), dtype=np.float32))
            for _ in range(32):
                recorder._raw_queue.put(chunk)

            # Allow worker thread to process
            time.sleep(0.5)

            wav_path, wav_bytes, duration, sample_count, rms = recorder.stop_recording()

            self.assertGreater(duration, 30.0, "Duration should exceed 30s")
            # WAV file path should have been set since duration > 30s
            self.assertTrue(wav_path, "WAV path should be populated for recordings > 30s")
            self.assertTrue(os.path.exists(wav_path), f"File {wav_path} should exist")

            # Cleanup
            try:
                os.remove(wav_path)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
