"""
Automated Unit Tests for Phase 1: Audio Capture & Buffering.
Verifies:
1. High-fidelity polyphase resampling from native rates (44.1kHz, 48kHz, 96kHz) to 16kHz mono.
2. Stateful polyphase resampling eliminating boundary edge transients across 1024-sample blocks.
3. Active DSP filtering (80Hz Butterworth HPF and 0.95 peak normalization) for distant speech (50cm-100cm).
4. Producer-consumer continuous disk streaming without dropping frames.
5. WASAPI sample rate negotiation handling rate rejections cleanly.
6. Safe microphone disconnection handling without silent fallback.
7. Real-time audio capture diagnostics.
8. Distant speech reliability in contains_speech vs digital silence.
9. 30-minute safety cap trigger logic.
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

    def test_stateful_polyphase_resampling_continuity(self):
        """Verifies that carrying forward filter state (zi) eliminates 21ms boundary edge transients."""
        # 1.0s of 440 Hz sine wave at 48kHz
        t = np.linspace(0, 1.0, 48000, endpoint=False)
        x = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        # Chunk into 1024-sample blocks (PortAudio buffer size, ~21.3ms)
        chunk_size = 1024
        chunks = [x[i : i + chunk_size] for i in range(0, len(x), chunk_size)]

        # Stateful resampling across chunks
        outs = []
        state = None
        for c in chunks:
            chunk_out, state = resample_to_16k_mono(c, orig_sr=48000, filter_state=state)
            outs.append(chunk_out)

        total_stream = np.concatenate(outs)
        self.assertEqual(len(total_stream), 16000, "Output length must be exactly 16000 samples for 1.0s of 48kHz audio")

        # Natural derivative of 440Hz sine at 16kHz is 2*pi*440/16000 = ~0.1728
        # Unstateful resampling caused jumps > 0.35 at boundary. Stateful must have smooth steps.
        jumps = [abs(total_stream[i] - total_stream[i - 1]) for i in range(1, len(total_stream))]
        max_jump = max(jumps)
        self.assertLess(max_jump, 0.20, f"Boundary jump must remain smooth and without clicks, got {max_jump:.4f}")

    def test_stateful_polyphase_resampling_continuity_44k1(self):
        """Verifies that 44.1kHz rational resampling maintains continuous phase across 1024-sample blocks."""
        t = np.linspace(0, 1.0, 44100, endpoint=False)
        x = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        chunk_size = 1024
        chunks = [x[i : i + chunk_size] for i in range(0, len(x), chunk_size)]

        outs = []
        state = None
        for c in chunks:
            chunk_out, state = resample_to_16k_mono(c, orig_sr=44100, filter_state=state)
            outs.append(chunk_out)

        total_stream = np.concatenate(outs)
        self.assertEqual(len(total_stream), 16000, "Output length must be exactly 16000 samples for 1.0s of 44.1kHz audio")

        full_stream = resample_to_16k_mono(x, orig_sr=44100)
        self.assertEqual(len(full_stream), 16000, "Monolithic output length must be exactly 16000 samples")

        max_err = float(np.max(np.abs(total_stream - full_stream)))
        self.assertLess(max_err, 0.05, f"Waveform corrupted across chunk boundaries, max error: {max_err}")

        # Check boundary step smoothness
        jumps = [abs(total_stream[i] - total_stream[i - 1]) for i in range(1, len(total_stream))]
        max_jump = max(jumps)
        self.assertLess(max_jump, 0.20, f"Boundary jump must remain smooth without clicks, got {max_jump:.4f}")

    def test_dsp_filter_defaults(self):
        """Verifies DSP filters can be disabled and do not distort clean speech."""
        audio = np.random.uniform(-0.5, 0.5, 16000).astype(np.float32)
        filtered = apply_dsp_filters(audio, sample_rate=16000, high_pass_enabled=False, peak_norm_enabled=False)
        np.testing.assert_array_equal(audio, filtered, "Audio must remain identical when DSP is OFF")

    def test_dsp_filters_activated_and_normalizes_distant_speech(self):
        """Verifies active 80Hz Butterworth HPF and soft-capped peak normalization (capped at 2.5x to prevent noise explosion)."""
        t = np.linspace(0, 1.0, 16000, endpoint=False)
        # Moderate speech with low-frequency rumble (40Hz)
        speech = (0.45 * np.sin(2 * np.pi * 440 * t) + 0.05 * np.sin(2 * np.pi * 40 * t)).astype(np.float32)

        # Direct DSP filter verification: scales to 0.95 when gain is within 2.5x cap
        normalized = apply_dsp_filters(speech, sample_rate=16000, high_pass_enabled=True, peak_norm_enabled=True)
        peak = float(np.max(np.abs(normalized)))
        self.assertAlmostEqual(peak, 0.95, delta=0.01, msg="Peak normalization must scale signal to 0.95")

        # Verify noise floor guard: background noise (rms < 0.008) must NOT be amplified to 0.95
        noise = np.random.normal(0, 0.003, 16000).astype(np.float32)
        filtered_noise = apply_dsp_filters(noise, peak_norm_enabled=True)
        self.assertLess(float(np.max(np.abs(filtered_noise))), 0.10, "Background noise must never be amplified to 0.95")

        # AudioRecorder integration verification
        recorder = AudioRecorder(sample_rate=16000, channels=1, enable_dsp=True)
        recorder.device_sample_rate = 16000
        recorder.device_channels = 1
        recorder.is_recording = True
        recorder.start_time = time.time()

        import threading
        recorder._stop_event.clear()
        recorder._writer_thread = threading.Thread(target=recorder._writer_worker, daemon=True)
        recorder._writer_thread.start()

        # Enqueue speech chunks
        chunk = speech[:8000].reshape(-1, 1)
        recorder._audio_callback(chunk, frames=8000, time_info=None, status=None)
        time.sleep(0.08)

        wav_path, wav_bytes, duration, sample_count, rms = recorder.stop_recording()
        # Verify output WAV has normalized energy
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            pcm = wf.readframes(wf.getnframes())
        samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        output_peak = float(np.max(np.abs(samples)))
        self.assertGreater(output_peak, 0.90, "Recorded output must be normalized to standard operating amplitude (~0.95)")

    def test_continuous_disk_streaming_and_metrics(self):
        """Verifies that AudioRecorder streams continuous PCM16 to disk and calculates duration/RMS."""
        recorder = AudioRecorder(sample_rate=16000, channels=1, enable_dsp=False)
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

        if wav_path:
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

    def test_wasapi_sample_rate_negotiation(self):
        """Verifies that device resolution negotiates supported sample rates without crashing."""
        recorder = AudioRecorder(sample_rate=16000, channels=1)
        dev_idx, rate, ch = recorder._resolve_device_parameters(None)
        # Should resolve to a valid sample rate (e.g. 48000, 44100, or 16000) and at least 1 channel
        self.assertIn(rate, [16000, 44100, 48000, 32000, 96000])
        self.assertGreaterEqual(ch, 1)

    def test_safe_device_disconnection_no_silent_fallback(self):
        """Verifies that an invalid or disconnected device fails safely and does NOT hijack default mic."""
        recorder = AudioRecorder(sample_rate=16000, channels=1)
        recorder.set_device(999999)

        started = recorder.start_recording()
        self.assertFalse(started, "Opening non-existent device must return False")
        self.assertFalse(recorder.is_recording)
        self.assertTrue(recorder.device_disconnected)

        diag = recorder.get_diagnostics()
        self.assertTrue(diag["device_disconnected"])
        self.assertEqual(diag["device_index"], 999999)

    def test_audio_capture_diagnostics(self):
        """Verifies that get_diagnostics() reports complete runtime telemetry."""
        recorder = AudioRecorder(sample_rate=16000, channels=1)
        diag = recorder.get_diagnostics()

        required_keys = [
            "device_index", "device_name", "sample_rate", "channels",
            "buffer_rms", "buffers_delivered", "is_recording",
            "device_disconnected", "duration_seconds", "sample_count"
        ]
        for key in required_keys:
            self.assertIn(key, diag, f"Diagnostics must include key: {key}")

        self.assertIsInstance(diag["device_disconnected"], bool)
        self.assertIsInstance(diag["buffers_delivered"], int)
        self.assertIsInstance(diag["buffer_rms"], float)

    def test_contains_speech_distant_audio(self):
        """Verifies that quiet speech at 50-100cm passes speech check while digital silence is rejected."""
        # 1. Digital silence (all zeros)
        bio_silence = io.BytesIO()
        with wave.open(bio_silence, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(np.zeros(16000, dtype=np.int16).tobytes())
        self.assertFalse(AudioRecorder.contains_speech(bio_silence.getvalue()), "Digital silence must be rejected")

        # 2. Quiet distant speech (peak ~0.015, RMS ~0.003)
        t = np.linspace(0, 1.0, 16000, endpoint=False)
        quiet_pcm = (np.sin(2 * np.pi * 440 * t) * 0.015 * 32767).astype(np.int16)
        bio_speech = io.BytesIO()
        with wave.open(bio_speech, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(quiet_pcm.tobytes())
        self.assertTrue(AudioRecorder.contains_speech(bio_speech.getvalue()), "Distant speech must be recognized")

    def test_safety_cap_trigger(self):
        """Verifies that reaching the 30-minute safety cap triggers on_safety_cap callback."""
        cap_triggered = False

        def _on_cap():
            nonlocal cap_triggered
            cap_triggered = True

        recorder = AudioRecorder(on_safety_cap=_on_cap, enable_dsp=False)
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

    def test_output_device_zero_channels_rejection(self):
        """Verifies that an output-only device (max_input_channels=0) is cleanly caught and fails safely."""
        recorder = AudioRecorder(sample_rate=16000, channels=1)
        # Mock device query to return output-only device
        with unittest.mock.patch("sounddevice.query_devices") as mock_query:
            mock_query.return_value = {
                "name": "Headphones (Realtek Audio)",
                "index": 3,
                "max_input_channels": 0,
                "default_samplerate": 44100
            }
            recorder.set_device(3)
            started = recorder.start_recording()
            self.assertFalse(started, "Starting recording on 0-channel device must return False")
            self.assertTrue(recorder.device_disconnected)

    def test_stale_stream_disposal_on_start(self):
        """Verifies that residual stream handles are safely closed before opening a new session."""
        recorder = AudioRecorder(sample_rate=16000, channels=1)
        mock_old_stream = unittest.mock.MagicMock()
        recorder.stream = mock_old_stream

        with unittest.mock.patch("sounddevice.InputStream") as mock_input_stream:
            mock_new_stream = unittest.mock.MagicMock()
            mock_input_stream.return_value = mock_new_stream

            recorder.set_device(None)
            started = recorder.start_recording()
            self.assertTrue(started)
            mock_old_stream.stop.assert_called_once()
            mock_old_stream.close.assert_called_once()
            mock_new_stream.start.assert_called_once()

            recorder.stop_recording()
            mock_new_stream.stop.assert_called_once()
            mock_new_stream.close.assert_called_once()



if __name__ == "__main__":
    unittest.main()
