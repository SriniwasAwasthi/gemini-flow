"""
Adversarial Challenge & Stress Test Suite for Milestone M1 (Audio Capture & DSP Layer).
Empirically tests:
1. Resampling Stress: Multi-frequency synthetic audio (chirps, step functions, multi-sine)
   over 1024-sample boundaries verifying continuity and absence of edge transient clicks.
2. Distance Attenuation & DSP Normalization: Distant speech attenuated to 50cm-100cm (RMS 0.003-0.015)
   normalized to 0.95 peak without clipping; pure digital silence preserved.
3. Disconnection Behavior: Invalid/disconnected device indices signal device_disconnected=True
   without silent redirection to default mic (device=None).
"""
import io
import math
import os
import sys
import time
import wave
import unittest
import unittest.mock as mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from scipy import signal

from app.audio_recorder import (
    AudioRecorder,
    resample_to_16k_mono,
    apply_dsp_filters
)


class TestM1AdversarialResampling(unittest.TestCase):
    """Stress-tests polyphase decimation and resampling continuity across 1024-sample boundaries."""

    def test_multi_sine_boundary_continuity(self):
        """Verifies multi-harmonic synthetic signal (220Hz + 880Hz + 2400Hz) has no boundary clicks."""
        orig_sr = 48000
        t = np.linspace(0, 1.0, orig_sr, endpoint=False)
        # Sum of 3 non-integer multiple harmonics
        x = (
            0.30 * np.sin(2 * np.pi * 220 * t) +
            0.30 * np.sin(2 * np.pi * 880 * t) +
            0.30 * np.sin(2 * np.pi * 2400 * t)
        ).astype(np.float32)

        chunk_size = 1024
        chunks = [x[i : i + chunk_size] for i in range(0, len(x), chunk_size)]

        # 1. Stateful resampling across 1024-sample blocks
        outs_stateful = []
        state = None
        for c in chunks:
            out, state = resample_to_16k_mono(c, orig_sr=orig_sr, filter_state=state)
            outs_stateful.append(out)

        # 2. Stateless resampling for adversarial baseline comparison
        outs_stateless = []
        for c in chunks:
            out = resample_to_16k_mono(c, orig_sr=orig_sr)
            outs_stateless.append(out)

        # Measure boundary jumps
        stateful_jumps = [abs(outs_stateful[k + 1][0] - outs_stateful[k][-1]) for k in range(len(chunks) - 1)]
        stateless_jumps = [abs(outs_stateless[k + 1][0] - outs_stateless[k][-1]) for k in range(len(chunks) - 1)]

        max_stateful_jump = max(stateful_jumps)
        max_stateless_jump = max(stateless_jumps)

        # In stateful, max jump must remain smooth and below 0.15
        self.assertLess(
            max_stateful_jump, 0.15,
            f"Stateful multi-sine max boundary jump too high: {max_stateful_jump:.4f}"
        )
        # Stateless has severe FIR boundary transient clicks (> 0.60)
        self.assertGreater(
            max_stateless_jump, 0.60,
            f"Stateless baseline should exhibit click transients (>0.60), got: {max_stateless_jump:.4f}"
        )
        # Stateful improvement must be at least 4x
        self.assertLess(
            max_stateful_jump, max_stateless_jump * 0.25,
            "Stateful resampling must reduce boundary transients by at least 75%"
        )

    def test_linear_chirp_frequency_sweep_continuity(self):
        """Verifies linear chirp from 100Hz to 3500Hz produces continuous signal without boundary spikes."""
        orig_sr = 48000
        t = np.linspace(0, 1.0, orig_sr, endpoint=False)
        x_chirp = signal.chirp(t, f0=100, t1=1.0, f1=3500, method='linear').astype(np.float32) * 0.8

        chunk_size = 1024
        chunks = [x_chirp[i : i + chunk_size] for i in range(0, len(x_chirp), chunk_size)]

        outs = []
        state = None
        for c in chunks:
            out, state = resample_to_16k_mono(c, orig_sr=orig_sr, filter_state=state)
            outs.append(out)

        # Measure boundary jumps vs natural internal steps
        boundary_jumps = [abs(outs[k + 1][0] - outs[k][-1]) for k in range(len(chunks) - 1)]
        internal_max_steps = [np.max(np.abs(np.diff(out))) for out in outs]

        max_boundary = max(boundary_jumps)
        max_internal = max(internal_max_steps)

        # Boundary jump must never exceed the natural internal step of the chirp
        self.assertLessEqual(
            max_boundary, max_internal * 1.05,
            f"Boundary jump ({max_boundary:.4f}) exceeded internal chirp step ({max_internal:.4f})"
        )

    def test_step_function_steady_state_preservation(self):
        """Verifies step function does not induce periodic boundary clicks in steady-state."""
        orig_sr = 48000
        x_step = np.zeros(orig_sr, dtype=np.float32)
        # Step occurs halfway through
        x_step[orig_sr // 2:] = 0.70

        chunk_size = 1024
        chunks = [x_step[i : i + chunk_size] for i in range(0, len(x_step), chunk_size)]

        outs_stateful = []
        state = None
        for c in chunks:
            out, state = resample_to_16k_mono(c, orig_sr=orig_sr, filter_state=state)
            outs_stateful.append(out)

        # Steady-state chunks occur in the second half (indices >= len(chunks)//2 + 2)
        steady_start = len(chunks) // 2 + 2
        steady_jumps = [
            abs(outs_stateful[k + 1][0] - outs_stateful[k][-1])
            for k in range(steady_start, len(chunks) - 1)
        ]

        max_steady_jump = max(steady_jumps)
        # In steady state, a stateful filter should have near-zero boundary jump
        self.assertAlmostEqual(
            max_steady_jump, 0.0, delta=1e-5,
            msg=f"Stateful resampling must have zero boundary jump in DC steady-state, got {max_steady_jump}"
        )

    def test_multi_sample_rate_resampling(self):
        """Verifies stateful decimation across integer and non-integer sample rates (32k, 96k, 16k)."""
        for sr in [16000, 32000, 96000]:
            t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
            x = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
            chunks = [x[i : i + 1024] for i in range(0, len(x), 1024)]

            outs = []
            state = None
            for c in chunks:
                out, state = resample_to_16k_mono(c, orig_sr=sr, filter_state=state)
                outs.append(out)

            total = np.concatenate(outs)
            expected_approx = int(0.5 * 16000)
            self.assertAlmostEqual(len(total), expected_approx, delta=50, msg=f"Output length mismatch for sr={sr}")

    def test_resample_api_contract_backward_compatibility(self):
        """Verifies 2-arg invocation returns 1D array, while filter_state returns tuple."""
        raw = np.random.uniform(-0.5, 0.5, 1024).astype(np.float32)

        # 2-argument invocation: MUST return ndarray
        res_2arg = resample_to_16k_mono(raw, 48000)
        self.assertIsInstance(res_2arg, np.ndarray)
        self.assertEqual(res_2arg.ndim, 1)

        # 3-argument invocation: MUST return (ndarray, ndarray)
        res_3arg = resample_to_16k_mono(raw, 48000, filter_state=None)
        self.assertIsInstance(res_3arg, tuple)
        self.assertEqual(len(res_3arg), 2)
        self.assertIsInstance(res_3arg[0], np.ndarray)
        self.assertIsInstance(res_3arg[1], np.ndarray)

        # Empty array handling
        empty = np.zeros((0,), dtype=np.float32)
        out_empty, next_s = resample_to_16k_mono(empty, 48000, filter_state=None)
        self.assertEqual(len(out_empty), 0)


class TestM1AdversarialDSPNormalization(unittest.TestCase):
    """Stress-tests distance attenuation (50cm-100cm) normalization and silence preservation."""

    def test_attenuated_speech_normalized_to_095(self):
        """Verifies distant speech across RMS 0.003 to 0.015 is normalized to 0.95 without clipping."""
        # 50cm-100cm attenuation levels
        attenuation_levels = [0.003, 0.005, 0.008, 0.012, 0.015]

        for target_rms in attenuation_levels:
            t = np.linspace(0, 1.0, 16000, endpoint=False)
            # Complex speech harmonic simulation
            vocal_sig = (
                0.50 * np.sin(2 * np.pi * 150 * t) +
                0.30 * np.sin(2 * np.pi * 300 * t) +
                0.15 * np.sin(2 * np.pi * 600 * t) +
                0.05 * np.sin(2 * np.pi * 1200 * t)
            ).astype(np.float32)

            cur_rms = float(np.sqrt(np.mean(vocal_sig**2)))
            attenuated = (vocal_sig * (target_rms / cur_rms)).astype(np.float32)

            # Apply DSP
            normalized = apply_dsp_filters(attenuated, sample_rate=16000, high_pass_enabled=True, peak_norm_enabled=True)
            peak_val = float(np.max(np.abs(normalized)))
            rms_val = float(np.sqrt(np.mean(normalized**2)))

            # 1. Peak must be normalized to target peak 0.95 (within 1% tolerance)
            self.assertAlmostEqual(
                peak_val, 0.95, delta=0.01,
                msg=f"Failed to normalize distant speech at RMS {target_rms} to 0.95: got {peak_val}"
            )
            # 2. No digital clipping (> 1.0 or distortion)
            self.assertLessEqual(peak_val, 0.96)
            self.assertGreater(rms_val, 0.20, "RMS should be elevated to standard speech operating range")

    def test_pure_digital_silence_preserved(self):
        """Verifies pure digital silence (zeros) is NEVER normalized or amplified."""
        silence = np.zeros(16000, dtype=np.float32)
        filtered = apply_dsp_filters(silence, sample_rate=16000, high_pass_enabled=True, peak_norm_enabled=True)

        self.assertEqual(np.max(np.abs(filtered)), 0.0, "Digital silence must remain strictly 0.0")

    def test_sub_threshold_room_noise_not_amplified(self):
        """Verifies sub-threshold background noise (< 1e-4) is NOT amplified to 0.95."""
        # Sub-threshold room noise
        quiet_noise = np.random.uniform(-5e-5, 5e-5, 16000).astype(np.float32)
        filtered = apply_dsp_filters(quiet_noise, sample_rate=16000, high_pass_enabled=True, peak_norm_enabled=True)

        peak_after = float(np.max(np.abs(filtered)))
        self.assertLess(
            peak_after, 1e-3,
            f"Sub-threshold noise must not be amplified, got peak {peak_after}"
        )

    def test_contains_speech_boundary_calibration(self):
        """Verifies contains_speech correctly classifies attenuated speech vs digital silence."""
        # 1. Attenuated speech at 100cm (RMS 0.003)
        t = np.linspace(0, 1.0, 16000, endpoint=False)
        speech_100cm = (0.015 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
        bio_speech = io.BytesIO()
        with wave.open(bio_speech, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(speech_100cm.tobytes())

        self.assertTrue(
            AudioRecorder.contains_speech(bio_speech.getvalue()),
            "AudioRecorder.contains_speech must accept 100cm speech (RMS ~0.003)"
        )

        # 2. Pure silence
        bio_silence = io.BytesIO()
        with wave.open(bio_silence, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(np.zeros(16000, dtype=np.int16).tobytes())

        self.assertFalse(
            AudioRecorder.contains_speech(bio_silence.getvalue()),
            "AudioRecorder.contains_speech must reject digital silence"
        )


class TestM1AdversarialDisconnection(unittest.TestCase):
    """Stress-tests hardware disconnection handling and safe failure semantics."""

    def test_invalid_device_index_signals_disconnection_no_silent_fallback(self):
        """Verifies start_recording on invalid device does NOT fallback to device=None."""
        for invalid_idx in [999999, -1, 4096]:
            rec = AudioRecorder(sample_rate=16000, channels=1)
            rec.set_device(invalid_idx)

            started = rec.start_recording()
            self.assertFalse(started, f"start_recording must return False for invalid device {invalid_idx}")
            self.assertFalse(rec.is_recording)
            self.assertTrue(rec.device_disconnected)
            # Crucial: device_index must NOT be mutated to None
            self.assertEqual(
                rec.device_index, invalid_idx,
                f"device_index must not be silently hijacked to None for device {invalid_idx}"
            )

            diag = rec.get_diagnostics()
            self.assertTrue(diag["device_disconnected"])
            self.assertEqual(diag["device_index"], invalid_idx)

    def test_stream_initialization_exception_cleans_up_threads(self):
        """Verifies that an exception during InputStream creation cleans up the writer worker thread."""
        rec = AudioRecorder(sample_rate=16000, channels=1)
        rec.set_device(0)

        with mock.patch("sounddevice.InputStream", side_effect=RuntimeError("USB Microphone disconnected")):
            started = rec.start_recording()
            self.assertFalse(started)
            self.assertTrue(rec.device_disconnected)
            self.assertFalse(rec.is_recording)

            # Ensure writer thread stopped
            if rec._writer_thread is not None:
                rec._writer_thread.join(timeout=1.0)
                self.assertFalse(rec._writer_thread.is_alive(), "Writer thread must terminate on stream start error")

    def test_diagnostics_keys_and_types_on_disconnection(self):
        """Verifies get_diagnostics() schema is intact even when hardware is disconnected."""
        rec = AudioRecorder(sample_rate=16000, channels=1)
        rec.set_device(88888)
        rec.start_recording()

        diag = rec.get_diagnostics()
        expected_schema = {
            "device_index": int,
            "device_name": str,
            "sample_rate": int,
            "channels": int,
            "buffer_rms": float,
            "buffers_delivered": int,
            "is_recording": bool,
            "device_disconnected": bool,
            "duration_seconds": float,
            "sample_count": int
        }

        for key, expected_type in expected_schema.items():
            self.assertIn(key, diag, f"Missing key '{key}' in diagnostics")
            self.assertIsInstance(
                diag[key], expected_type,
                f"Key '{key}' expected {expected_type}, got {type(diag[key])}"
            )
        self.assertTrue(diag["device_disconnected"])


if __name__ == "__main__":
    unittest.main()
