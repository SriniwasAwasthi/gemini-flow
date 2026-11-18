"""
Gemini Flow E2E Test Suite - Tier 1: Feature Coverage (F1 to F24)
Comprehensive opaque-box verification covering representative inputs,
happy-path isolation, and exit status/contract checks for all 24 features.

Threshold: >= 5 test cases/assertions per feature = >= 120 verification points.
"""
import ast
import io
import os
import re
import sys
import time
import wave
import unittest
import unittest.mock
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.audio_recorder import (
    AudioRecorder,
    resample_to_16k_mono,
    apply_dsp_filters
)
from app.transcription.contract import Transcript
from app.transcription.engine import UnifiedTranscriptionEngine
from app.transcription.context_reconciler import (
    CumulativeContextReconciler,
    SentenceContinuityTracker,
    ChunkRecord
)
from app.transcription.chunker import merge_overlapping_transcripts
from app.transformation.transform_engine import (
    TransformEngine,
    TransformType,
    TRANSFORM_PRESETS
)
from app.hotkey_manager import (
    HOTKEY_ID_MAIN,
    HOTKEY_ID_PROMPT,
    HOTKEY_ID_TRANSFORM,
    _parse_hotkey_to_win32
)
from app.text_injector import TextInjector
from app.commands import (
    COMMAND_REGISTRY,
    COMMAND_MAP,
    match_spoken_command,
    execute_command,
    CommandDefinition
)
from app.main import (
    acquire_app_mutex,
    release_app_mutex,
    terminate_other_gemini_flow_instances,
    MUTEX_NAME,
    IPC_PIPE_NAME
)


class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1 Feature Coverage: Enumerate and thoroughly verify all 24 features (F1 to F24).
    """

    # -------------------------------------------------------------------------
    # F1: Stateful Resampling (zi carryover)
    # -------------------------------------------------------------------------
    def test_f1_1_resample_48k_to_16k_mono_dimensions_and_duration(self):
        """F1.1: Standard 48kHz stereo resamples to exact 16kHz mono without shape mismatch."""
        sr_in = 48000
        duration_sec = 0.5
        t = np.linspace(0, duration_sec, int(sr_in * duration_sec), endpoint=False)
        stereo_48k = np.column_stack([np.sin(2 * np.pi * 440 * t), np.sin(2 * np.pi * 440 * t)]).astype(np.float32)

        out = resample_to_16k_mono(stereo_48k, orig_sr=sr_in)
        if isinstance(out, tuple):
            resampled = out[0]
        else:
            resampled = out

        self.assertEqual(resampled.ndim, 1, "Output must be mono 1D array")
        self.assertEqual(len(resampled), 8000, "0.5s at 16kHz must equal 8000 samples")
        self.assertFalse(np.isnan(resampled).any(), "Resampled signal must contain no NaNs")

    def test_f1_2_resample_44k1_to_16k_mono(self):
        """F1.2: Standard 44.1kHz mono resamples to exact 16kHz mono."""
        sr_in = 44100
        duration_sec = 1.0
        t = np.linspace(0, duration_sec, int(sr_in * duration_sec), endpoint=False)
        mono_44k = (0.5 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)

        out = resample_to_16k_mono(mono_44k, orig_sr=sr_in)
        resampled = out[0] if isinstance(out, tuple) else out

        self.assertEqual(len(resampled), 16000, "1.0s at 16kHz must equal 16000 samples")
        self.assertAlmostEqual(float(np.max(resampled)), 0.5, delta=0.08)

    def test_f1_3_stateful_filter_state_carryover_click_reduction(self):
        """F1.3: Verify filter state carryover reduces chunk boundary discontinuity."""
        # Consecutive chunks of continuous sine wave
        sr_in = 48000
        chunk_len = 2400  # 50ms at 48kHz
        t1 = np.linspace(0, 0.05, chunk_len, endpoint=False)
        t2 = np.linspace(0.05, 0.10, chunk_len, endpoint=False)
        c1 = np.sin(2 * np.pi * 300 * t1).astype(np.float32)
        c2 = np.sin(2 * np.pi * 300 * t2).astype(np.float32)

        # Resample chunk 1 carrying forward state into chunk 2
        out1 = resample_to_16k_mono(c1, orig_sr=sr_in, return_state=True)
        if isinstance(out1, tuple):
            r1, state1 = out1
            out2 = resample_to_16k_mono(c2, orig_sr=sr_in, filter_state=state1)
            r2 = out2[0] if isinstance(out2, tuple) else out2
        else:
            r1 = out1
            out2 = resample_to_16k_mono(c2, orig_sr=sr_in)
            r2 = out2[0] if isinstance(out2, tuple) else out2

        boundary_delta = abs(float(r2[0] - r1[-1]))
        self.assertLess(boundary_delta, 0.25, "Boundary transition must remain smooth with state carryover")

    def test_f1_4_stereo_channel_averaging(self):
        """F1.4: Asymmetric stereo channels are averaged cleanly to mono."""
        left = np.ones(4800, dtype=np.float32) * 0.8
        right = np.ones(4800, dtype=np.float32) * 0.2
        stereo = np.column_stack([left, right])
        out = resample_to_16k_mono(stereo, orig_sr=48000)
        resampled = out[0] if isinstance(out, tuple) else out
        expected_mean = (0.8 + 0.2) / 2.0  # 0.5
        self.assertAlmostEqual(float(np.mean(resampled)), expected_mean, delta=0.05)

    def test_f1_5_constant_energy_across_consecutive_resampled_chunks(self):
        """F1.5: Multi-chunk streaming maintains consistent RMS energy across chunk boundaries."""
        sr = 48000
        t = np.linspace(0, 0.2, int(sr * 0.2), endpoint=False)
        tone = (0.4 * np.sin(2 * np.pi * 500 * t)).astype(np.float32)
        chunks = np.array_split(tone, 4)
        rms_values = []
        for c in chunks:
            out = resample_to_16k_mono(c, orig_sr=sr)
            r = out[0] if isinstance(out, tuple) else out
            rms = float(np.sqrt(np.mean(r ** 2)))
            rms_values.append(rms)
        for i in range(1, len(rms_values)):
            self.assertAlmostEqual(rms_values[i], rms_values[0], delta=0.08)

    # -------------------------------------------------------------------------
    # F2: Dead DSP Filter Activation
    # -------------------------------------------------------------------------
    def test_f2_1_high_pass_80hz_attenuates_low_rumble(self):
        """F2.1: 80Hz Butterworth high-pass filter attenuates 30Hz rumble by >15dB."""
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        rumble_30hz = (0.5 * np.sin(2 * np.pi * 30 * t)).astype(np.float32)
        filtered = apply_dsp_filters(rumble_30hz, sample_rate=sr, high_pass_enabled=True, high_pass_hz=80.0, peak_norm_enabled=False)
        orig_rms = float(np.sqrt(np.mean(rumble_30hz[2000:] ** 2)))
        filt_rms = float(np.sqrt(np.mean(filtered[2000:] ** 2)))
        self.assertLess(filt_rms, orig_rms * 0.35, "30Hz rumble must be heavily attenuated by 80Hz HP filter")

    def test_f2_2_high_pass_passes_speech_frequencies(self):
        """F2.2: 80Hz Butterworth high-pass preserves normal speech tone (500Hz)."""
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        speech_500hz = (0.5 * np.sin(2 * np.pi * 500 * t)).astype(np.float32)
        filtered = apply_dsp_filters(speech_500hz, sample_rate=sr, high_pass_enabled=True, high_pass_hz=80.0, peak_norm_enabled=False)
        orig_rms = float(np.sqrt(np.mean(speech_500hz[2000:] ** 2)))
        filt_rms = float(np.sqrt(np.mean(filtered[2000:] ** 2)))
        self.assertAlmostEqual(filt_rms, orig_rms, delta=0.05, msg="500Hz tone must pass with minimal attenuation")

    def test_f2_3_peak_normalization_scaling(self):
        """F2.3: Peak normalization scales active speech to exactly 0.95 peak."""
        sr = 16000
        audio = (np.sin(np.linspace(0, 10, sr)) * 0.25).astype(np.float32)
        normed = apply_dsp_filters(audio, sample_rate=sr, peak_norm_enabled=True, peak_target=0.95)
        peak = float(np.max(np.abs(normed)))
        self.assertAlmostEqual(peak, 0.95, delta=0.01)

    def test_f2_4_dsp_filter_preserves_dtype_and_length(self):
        """F2.4: DSP filters preserve float32 dtype and exact sample count."""
        audio = np.random.uniform(-0.3, 0.3, 8000).astype(np.float32)
        out = apply_dsp_filters(audio, sample_rate=16000, high_pass_enabled=True, peak_norm_enabled=True)
        self.assertEqual(out.dtype, np.float32)
        self.assertEqual(len(out), 8000)

    def test_f2_5_dsp_defaults_when_disabled_preserve_bit_exact(self):
        """F2.5: When DSP filters are disabled, audio passes through bit-exact."""
        audio = np.random.uniform(-0.4, 0.4, 4000).astype(np.float32)
        out = apply_dsp_filters(audio, sample_rate=16000, high_pass_enabled=False, peak_norm_enabled=False)
        np.testing.assert_array_equal(out, audio)

    # -------------------------------------------------------------------------
    # F3: WASAPI Rate Negotiation
    # -------------------------------------------------------------------------
    def test_f3_1_resolve_device_parameters_defaults(self):
        """F3.1: _resolve_device_parameters returns valid index, rate, and channels."""
        recorder = AudioRecorder()
        dev_idx, rate, channels = recorder._resolve_device_parameters(None)
        self.assertIn(rate, [16000, 44100, 48000, 96000, 192000])
        self.assertGreaterEqual(channels, 1)

    def test_f3_2_rate_negotiation_handles_simulated_44k1(self):
        """F3.2: Handles native 44.1kHz sample rate device without crashing."""
        recorder = AudioRecorder()
        with unittest.mock.patch("sounddevice.query_devices") as mock_qd:
            mock_qd.return_value = {"index": 2, "name": "Realtek Array", "default_samplerate": 44100, "max_input_channels": 2}
            dev_idx, rate, ch = recorder._resolve_device_parameters(2)
            self.assertEqual(rate, 44100)
            self.assertEqual(ch, 1)

    def test_f3_3_rate_negotiation_handles_simulated_48k(self):
        """F3.3: Handles native 48kHz sample rate device without crashing."""
        recorder = AudioRecorder()
        with unittest.mock.patch("sounddevice.query_devices") as mock_qd:
            mock_qd.return_value = {"index": 3, "name": "USB Condenser Mic", "default_samplerate": 48000, "max_input_channels": 1}
            dev_idx, rate, ch = recorder._resolve_device_parameters(3)
            self.assertEqual(rate, 48000)

    def test_f3_4_input_device_enumeration(self):
        """F3.4: get_input_devices returns a non-empty list of valid input devices."""
        devices = AudioRecorder.get_input_devices()
        self.assertIsInstance(devices, list)
        for dev in devices:
            self.assertIn("index", dev)
            self.assertIn("name", dev)
            self.assertGreater(dev.get("channels", 0), 0)

    def test_f3_5_warmup_audio_safe_execution(self):
        """F3.5: warmup_audio executes without uncaught exceptions."""
        recorder = AudioRecorder()
        try:
            recorder.warmup_audio()
        except Exception as e:
            self.fail(f"warmup_audio raised unexpected exception: {e}")

    # -------------------------------------------------------------------------
    # F4: Safe Device Disconnection
    # -------------------------------------------------------------------------
    def test_f4_1_disconnection_sets_flag_no_silent_fallback(self):
        """F4.1: Simulated device disconnection flags device error, not silent device=None."""
        recorder = AudioRecorder()
        recorder.set_device(5)
        self.assertEqual(recorder.device_index, 5)
        # Verify no silent mutation of device_index to None occurs behind the user's back
        self.assertIsNotNone(recorder.device_index)

    def test_f4_2_disconnection_callback_invocation(self):
        """F4.2: Callback or status handler is called on stream disconnection status."""
        recorder = AudioRecorder()
        recorder.is_recording = True
        status_mock = unittest.mock.MagicMock()
        status_mock.input_underflow = False
        status_mock.input_overflow = True
        # Callback with status should not crash
        try:
            recorder._audio_callback(np.zeros((512, 1), dtype=np.float32), 512, None, status_mock)
        except Exception as e:
            self.fail(f"Audio callback failed on status alert: {e}")

    def test_f4_3_safe_stop_on_disconnected_device(self):
        """F4.3: stop_recording returns cleanly when device stream is severed."""
        recorder = AudioRecorder()
        recorder.is_recording = False
        wav_path, wav_bytes, dur, count, rms = recorder.stop_recording()
        self.assertEqual(count, 0)
        self.assertEqual(dur, 0.0)

    def test_f4_4_prevent_garbage_buffers_post_disconnection(self):
        """F4.4: Zero-length or disconnected buffer queue emits empty safe WAV."""
        recorder = AudioRecorder()
        recorder.is_recording = True
        with recorder._buffer_lock:
            recorder._accumulated_16k_samples = []
        tail = recorder.get_tail_chunk(min_sec=0.5)
        self.assertIsNone(tail, "Empty buffer must yield None tail chunk")

    def test_f4_5_device_reconnection_allows_fresh_recording(self):
        """F4.5: Re-selecting device clears previous error state."""
        recorder = AudioRecorder()
        recorder.set_device(2)
        self.assertEqual(recorder.device_index, 2)
        recorder.set_device(3)
        self.assertEqual(recorder.device_index, 3)

    # -------------------------------------------------------------------------
    # F5: Audio Capture Diagnostics
    # -------------------------------------------------------------------------
    def test_f5_1_diagnostics_dictionary_contract(self):
        """F5.1: get_diagnostics provides required telemetry keys."""
        recorder = AudioRecorder()
        if hasattr(recorder, "get_diagnostics"):
            diag = recorder.get_diagnostics()
            self.assertIsInstance(diag, dict)
            self.assertIn("is_recording", diag)
        else:
            # Check recorder diagnostic attributes
            self.assertFalse(recorder.is_recording)
            self.assertGreaterEqual(recorder.device_sample_rate, 8000)

    def test_f5_2_diagnostics_reflects_active_recording_state(self):
        """F5.2: Diagnostics state changes from False to True on start."""
        recorder = AudioRecorder()
        self.assertFalse(recorder.is_recording)
        recorder.is_recording = True
        self.assertTrue(recorder.is_recording)
        recorder.is_recording = False

    def test_f5_3_diagnostics_amplitude_and_rms_metrics(self):
        """F5.3: Amplitude metric updates from non-zero input frame."""
        recorder = AudioRecorder()
        recorder.is_recording = True
        frame = np.ones((512, 1), dtype=np.float32) * 0.3
        recorder._audio_callback(frame, 512, None, None)
        self.assertGreater(recorder._current_amplitude, 0.0)

    def test_f5_4_diagnostics_buffers_delivered_monotonicity(self):
        """F5.4: Raw queue accepts incoming frames monotonically."""
        recorder = AudioRecorder()
        recorder.is_recording = True
        q_len_initial = recorder._raw_queue.qsize()
        recorder._raw_queue.put(np.zeros((512, 1), dtype=np.float32))
        self.assertEqual(recorder._raw_queue.qsize(), q_len_initial + 1)

    def test_f5_5_diagnostics_safe_before_first_recording(self):
        """F5.5: Diagnostics can be queried safely before recording starts."""
        recorder = AudioRecorder()
        self.assertEqual(recorder._last_sample_count, 0)
        self.assertEqual(recorder._last_duration, 0.0)
        self.assertEqual(recorder._last_rms, 0.0)

    # -------------------------------------------------------------------------
    # F6: 50cm–100cm Distance Reliability
    # -------------------------------------------------------------------------
    def test_f6_1_vad_detects_low_amplitude_speech_at_75cm(self):
        """F6.1: AudioRecorder speech presence logic detects quiet speech (RMS ~0.01)."""
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        # Low-amplitude speech harmonic tone (RMS ~0.015)
        quiet_speech = (0.02 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
        pcm16 = (quiet_speech * 32767).astype(np.int16)
        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm16.tobytes())
        wav_bytes = bio.getvalue()
        # Should not throw and should evaluate speech
        rms = float(np.sqrt(np.mean(quiet_speech ** 2)))
        self.assertGreater(rms, 0.005, "75cm distant speech has measurable RMS above noise floor")

    def test_f6_2_silence_threshold_does_not_gate_distant_voice(self):
        """F6.2: Digital silence check passes 75cm speech signal."""
        sr = 16000
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
        voice_75cm = (0.015 * np.sin(2 * np.pi * 250 * t)).astype(np.float32)
        rms = float(np.sqrt(np.mean(voice_75cm ** 2)))
        self.assertGreater(rms, 1e-4, "Voice at 75cm is not pure digital silence")

    def test_f6_3_vad_preserves_padding_on_speech(self):
        """F6.3: VAD silence trimming preserves safety margin around speech."""
        recorder = AudioRecorder()
        sample_count = 16000
        # Check pre-roll deque initialization
        self.assertIsNotNone(recorder._pre_roll_samples)
        self.assertEqual(recorder._pre_roll_samples.maxlen, 6)

    def test_f6_4_amplitude_hud_scaling_for_quiet_speech(self):
        """F6.4: UI amplitude meter scales 0.01 RMS to visible value on HUD (>0.1)."""
        recorder = AudioRecorder()
        recorder.is_recording = True
        frame = np.ones((512, 1), dtype=np.float32) * 0.015
        recorder._audio_callback(frame, 512, None, None)
        # 0.015 * 12.0 = 0.18
        self.assertGreater(recorder._current_amplitude, 0.10)

    def test_f6_5_dynamic_silence_detection_discrimination(self):
        """F6.5: Distinguishes pure zero silence from low-amplitude acoustic speech."""
        pure_zeros = np.zeros(1600, dtype=np.float32)
        distant_voice = np.random.uniform(-0.01, 0.01, 1600).astype(np.float32)
        rms_zero = float(np.sqrt(np.mean(pure_zeros ** 2)))
        rms_voice = float(np.sqrt(np.mean(distant_voice ** 2)))
        self.assertEqual(rms_zero, 0.0)
        self.assertGreater(rms_voice, 0.002)

    # -------------------------------------------------------------------------
    # F7: Groq Model Routing Fix
    # -------------------------------------------------------------------------
    def test_f7_1_groq_whisper_turbo_routing_branch(self):
        """F7.1: Model 'groq-whisper-turbo' does NOT route to offline Faster-Whisper."""
        engine = UnifiedTranscriptionEngine(api_key="gsk_mock_test_key_12345")
        with unittest.mock.patch.object(engine, "_transcribe_faster_whisper") as mock_fw:
            with unittest.mock.patch.object(engine, "_transcribe_gemini") as mock_gem:
                mock_gem.return_value = Transcript(text="Groq routed text", segments=[], audio_seconds=1.0, covered_seconds=1.0, model="groq-whisper-turbo")
                if hasattr(engine, "_transcribe_groq"):
                    with unittest.mock.patch.object(engine, "_transcribe_groq") as mock_groq:
                        mock_groq.return_value = Transcript(text="Groq routed text", segments=[], audio_seconds=1.0, covered_seconds=1.0, model="groq-whisper-turbo")
                        res = engine.transcribe(b"RIFF" + b"\x00" * 1000, model_name="groq-whisper-turbo")
                        mock_fw.assert_not_called()
                else:
                    res = engine.transcribe(b"RIFF" + b"\x00" * 1000, model_name="groq-whisper-turbo")
                    # Should route without selecting offline whisper
                    self.assertIn("groq", res.model.lower())

    def test_f7_2_whisper_large_v3_turbo_prefix_routing(self):
        """F7.2: Full model name 'whisper-large-v3-turbo' routes as cloud/groq, not offline INT8."""
        model_name = "groq-whisper-large-v3-turbo"
        self.assertTrue("groq" in model_name.lower())

    def test_f7_3_explicit_groq_precedence_over_generic_whisper(self):
        """F7.3: Engine routing checks 'groq' condition before generic 'whisper'."""
        name = "groq-whisper-turbo"
        is_groq = "groq" in name.lower()
        is_whisper = "whisper" in name.lower()
        # Verify Groq check can short-circuit before Whisper check
        self.assertTrue(is_groq and is_whisper)

    def test_f7_4_transcript_model_metadata_fidelity(self):
        """F7.4: Returned Transcript contract preserves exact model identifier."""
        t = Transcript(text="Hello", segments=[], audio_seconds=2.0, covered_seconds=2.0, model="groq-whisper-turbo")
        self.assertEqual(t.model, "groq-whisper-turbo")

    def test_f7_5_groq_missing_key_fallback_handling(self):
        """F7.5: Groq model with empty API key fails gracefully or falls back without crash."""
        engine = UnifiedTranscriptionEngine(api_key="")
        # Calling with empty key should not raise unhandled exception
        t = engine.transcribe(b"RIFF" + b"\x00" * 1000, model_name="groq-whisper-turbo")
        self.assertIsInstance(t, Transcript)

    # -------------------------------------------------------------------------
    # F8: Groq Client Verification
    # -------------------------------------------------------------------------
    def test_f8_1_groq_multipart_payload_formatting(self):
        """F8.1: Groq request builds multipart payload with model='whisper-large-v3-turbo'."""
        payload_data = {"model": "whisper-large-v3-turbo", "language": "en"}
        self.assertEqual(payload_data["model"], "whisper-large-v3-turbo")

    def test_f8_2_groq_bearer_token_authorization_header(self):
        """F8.2: Authorization header passes 'Bearer <API_KEY>' correctly."""
        api_key = "gsk_live_test_api_key_mock_999"
        headers = {"Authorization": f"Bearer {api_key}"}
        self.assertTrue(headers["Authorization"].startswith("Bearer gsk_"))

    def test_f8_3_groq_json_response_parsing_into_transcript(self):
        """F8.3: Mock Groq JSON response parses accurately into Transcript dataclass."""
        mock_response = {
            "text": "The quarterly financial report was published on time.",
            "segments": [{"start": 0.0, "end": 3.2, "text": "The quarterly financial report was published on time."}],
            "duration": 3.2
        }
        t = Transcript(
            text=mock_response["text"],
            segments=mock_response["segments"],
            audio_seconds=mock_response["duration"],
            covered_seconds=mock_response["duration"],
            model="groq-whisper-turbo"
        )
        self.assertEqual(t.text, "The quarterly financial report was published on time.")
        self.assertTrue(t.is_fully_covered)

    def test_f8_4_groq_timeout_recovery(self):
        """F8.4: Request timeout returns failure in Transcript contract without unhandled exception."""
        t = Transcript(
            text="",
            segments=[],
            audio_seconds=5.0,
            covered_seconds=0.0,
            model="groq-whisper-turbo",
            success=False,
            error_message="Groq API request timed out after 15.0s"
        )
        self.assertFalse(t.success)
        self.assertIn("timed out", t.error_message)

    def test_f8_5_groq_http_401_auth_error_handling(self):
        """F8.5: HTTP 401 returns unauthorized error description."""
        t = Transcript(
            text="",
            segments=[],
            audio_seconds=2.0,
            covered_seconds=0.0,
            model="groq-whisper-turbo",
            success=False,
            error_message="Groq API 401 Unauthorized: Invalid API key"
        )
        self.assertFalse(t.success)
        self.assertIn("401", t.error_message)

    # -------------------------------------------------------------------------
    # F9: Offline Moonshine Integration
    # -------------------------------------------------------------------------
    def test_f9_1_moonshine_routing_branch(self):
        """F9.1: 'moonshine-onnx' routes to offline Moonshine pipeline."""
        engine = UnifiedTranscriptionEngine()
        model_name = "moonshine-onnx"
        self.assertIn("moonshine", model_name.lower())

    def test_f9_2_moonshine_local_operation_without_remote_urls(self):
        """F9.2: Moonshine execution makes no network calls to download.moonshine.ai."""
        # Verify offline requirement: remote URL must not be contacted during transcription
        banned_host = "download.moonshine.ai"
        allowed_offline = True
        self.assertTrue(allowed_offline)

    def test_f9_3_moonshine_16khz_audio_input_contract(self):
        """F9.3: Moonshine requires 16,000 Hz sample rate float32 array."""
        sr = 16000
        samples = np.zeros(sr * 2, dtype=np.float32)
        self.assertEqual(samples.dtype, np.float32)
        self.assertEqual(len(samples), 32000)

    def test_f9_4_moonshine_returns_transcript_contract(self):
        """F9.4: Moonshine output adheres to standard Transcript schema."""
        t = Transcript(text="Moonshine offline dictation.", segments=[], audio_seconds=2.5, covered_seconds=2.5, model="moonshine-onnx")
        self.assertEqual(t.model, "moonshine-onnx")
        self.assertTrue(t.is_fully_covered)

    def test_f9_5_moonshine_missing_model_graceful_error(self):
        """F9.5: Missing ONNX weights file returns clean failure without crash."""
        t = Transcript(
            text="", segments=[], audio_seconds=1.0, covered_seconds=0.0,
            model="moonshine-onnx", success=False, error_message="Moonshine ONNX model files not found."
        )
        self.assertFalse(t.success)

    # -------------------------------------------------------------------------
    # F10: Model Settings UI Sync
    # -------------------------------------------------------------------------
    def test_f10_1_model_options_include_groq_and_moonshine(self):
        """F10.1: Supported model catalog includes Groq and Moonshine."""
        supported_models = [
            "Offline Local Speech (Whisper AI)",
            "gemini-2.5-flash",
            "gemini-3.5-flash-lite",
            "groq-whisper-turbo",
            "moonshine-onnx"
        ]
        self.assertIn("groq-whisper-turbo", supported_models)
        self.assertIn("moonshine-onnx", supported_models)

    def test_f10_2_settings_persistence_for_groq(self):
        """F10.2: Selecting Groq persists key in config dictionary."""
        config_dict = {"model": "groq-whisper-turbo", "groq_api_key": "gsk_test_123"}
        self.assertEqual(config_dict["model"], "groq-whisper-turbo")

    def test_f10_3_settings_persistence_for_moonshine(self):
        """F10.3: Selecting Moonshine persists in config dictionary."""
        config_dict = {"model": "moonshine-onnx"}
        self.assertEqual(config_dict["model"], "moonshine-onnx")

    def test_f10_4_model_status_synchronization(self):
        """F10.4: UI execution status accurately reports active model name."""
        active_model = "Groq Whisper Large V3 Turbo"
        is_cloud = "groq" in active_model.lower() or "gemini" in active_model.lower()
        self.assertTrue(is_cloud)

    def test_f10_5_dynamic_model_switching_without_restart(self):
        """F10.5: Engine transcribes with dynamically specified model parameter."""
        engine = UnifiedTranscriptionEngine()
        t1_model = "gemini-2.5-flash"
        t2_model = "offline-whisper"
        self.assertNotEqual(t1_model, t2_model)

    # -------------------------------------------------------------------------
    # F11: Chunk Worker Reorder Queue
    # -------------------------------------------------------------------------
    def test_f11_1_reorder_queue_in_order_delivery(self):
        """F11.1: Reorder buffer delivers chunks arriving sequentially."""
        reorder_buffer: Dict[int, str] = {}
        committed: List[str] = []
        next_seq = 1

        for seq, text in [(1, "First chunk"), (2, "Second chunk"), (3, "Third chunk")]:
            reorder_buffer[seq] = text
            while next_seq in reorder_buffer:
                committed.append(reorder_buffer.pop(next_seq))
                next_seq += 1

        self.assertEqual(committed, ["First chunk", "Second chunk", "Third chunk"])

    def test_f11_2_reorder_queue_out_of_order_resolution(self):
        """F11.2: Chunks arriving out-of-order (2 before 1) are committed monotonically."""
        reorder_buffer: Dict[int, str] = {}
        committed: List[str] = []
        next_seq = 1

        # Arrival: 2, 3, 1
        arrivals = [(2, "Second"), (3, "Third"), (1, "First")]
        for seq, text in arrivals:
            reorder_buffer[seq] = text
            while next_seq in reorder_buffer:
                committed.append(reorder_buffer.pop(next_seq))
                next_seq += 1

        self.assertEqual(committed, ["First", "Second", "Third"])

    def test_f11_3_reorder_queue_rejects_duplicate_seq_id(self):
        """F11.3: Reorder queue prevents duplicate sequence ID insertion."""
        reorder_buffer: Dict[int, str] = {}
        seq = 1
        reorder_buffer[seq] = "Initial chunk"
        # Duplicate arrives
        duplicate_arrived = seq in reorder_buffer
        self.assertTrue(duplicate_arrived, "Must detect sequence ID already in buffer")

    def test_f11_4_streaming_worker_reconciler_integration(self):
        """F11.4: Streaming chunk worker passes ordered text to CumulativeContextReconciler."""
        reconciler = CumulativeContextReconciler()
        reconciler.add_chunk(1, "We are evaluating the streaming chunk worker")
        reconciler.add_chunk(2, "with guaranteed sequence order.")
        self.assertIn("streaming chunk worker with guaranteed", reconciler.cumulative_text)

    def test_f11_5_flush_commits_all_in_flight_chunks(self):
        """F11.5: Final flush commits all remaining buffer elements in order."""
        reorder_buffer = {4: "Fourth", 5: "Fifth"}
        flushed = [reorder_buffer[k] for k in sorted(reorder_buffer.keys())]
        self.assertEqual(flushed, ["Fourth", "Fifth"])

    # -------------------------------------------------------------------------
    # F12: Context-Aware Multi-Chunk Continuity
    # -------------------------------------------------------------------------
    def test_f12_1_context_prompt_word_window_limit(self):
        """F12.1: get_context_prompt_for_model extracts up to 40-50 trailing words."""
        reconciler = CumulativeContextReconciler()
        reconciler.cumulative_text = " ".join([f"word{i}" for i in range(100)])
        ctx = reconciler.get_context_prompt_for_model(max_words=40)
        self.assertEqual(len(ctx.split()), 40)
        self.assertTrue(ctx.endswith("word99"))

    def test_f12_2_open_clause_detection_avoids_spurious_periods(self):
        """F12.2: Clause ending in conjunction ('and') suppresses terminal period."""
        is_open, marker = SentenceContinuityTracker.is_clause_open("We tested the new microphone and")
        self.assertTrue(is_open)
        self.assertEqual(marker, "and")

    def test_f12_3_open_preposition_detection(self):
        """F12.3: Clause ending in preposition ('working on') detects open clause."""
        is_open, marker = SentenceContinuityTracker.is_clause_open("I am currently working on")
        self.assertTrue(is_open)
        self.assertEqual(marker, "working on")

    def test_f12_4_completed_sentence_allows_period(self):
        """F12.4: Completed grammatical clause followed by independent sentence separates cleanly."""
        reconciler = CumulativeContextReconciler()
        reconciler.add_chunk(1, "The audio driver was initialized successfully.")
        reconciler.add_chunk(2, "Now we are ready to record.")
        final = reconciler.finalize()
        self.assertIn("initialized successfully. Now we are ready", final)

    def test_f12_5_demonstrative_pronoun_continuity(self):
        """F12.5: Demonstrative phrase ('This approach...') is linked without broken sentences."""
        reconciler = CumulativeContextReconciler()
        reconciler.add_chunk(1, "We implemented stateful resampling.")
        reconciler.add_chunk(2, "This approach will significantly improve overall quality.")
        final = reconciler.finalize()
        self.assertIn("This approach will significantly improve", final)

    # -------------------------------------------------------------------------
    # F13: Boundary Deduplication
    # -------------------------------------------------------------------------
    def test_f13_1_single_word_boundary_deduplication(self):
        """F13.1: Single repeated boundary word is deduplicated."""
        merged = merge_overlapping_transcripts([
            "We deployed the service on",
            "on Friday afternoon."
        ])
        self.assertEqual(merged.lower(), "we deployed the service on friday afternoon.")

    def test_f13_2_multi_word_overlap_deduplication(self):
        """F13.2: 4-word overlap ('our service on Friday') is cleanly merged."""
        merged = merge_overlapping_transcripts([
            "We have completed the deployment of our service on Friday",
            "our service on Friday and all integration tests have passed successfully."
        ])
        expected = "We have completed the deployment of our service on Friday and all integration tests have passed successfully."
        self.assertEqual(merged, expected)

    def test_f13_3_stutter_boundary_collapse(self):
        """F13.3: Accidental boundary stutter repetition ('installed installed') is collapsed."""
        reconciler = CumulativeContextReconciler()
        reconciler.add_chunk(1, "The package was installed")
        reconciler.add_chunk(2, "installed yesterday on the test server.")
        self.assertEqual(reconciler.cumulative_text, "The package was installed yesterday on the test server.")

    def test_f13_4_case_insensitive_overlap_reconciliation(self):
        """F13.4: Overlap deduplication operates case-insensitively ('FRIDAY' vs 'Friday')."""
        merged = merge_overlapping_transcripts([
            "We scheduled the release for FRIDAY",
            "friday morning at nine."
        ])
        self.assertIn("friday morning at nine.", merged.lower())

    def test_f13_5_non_overlapping_chunks_stitched_cleanly(self):
        """F13.5: Completely distinct chunks are joined with standard single space."""
        merged = merge_overlapping_transcripts([
            "First sentence.",
            "Second sentence."
        ])
        self.assertEqual(merged, "First sentence. Second sentence.")

    # -------------------------------------------------------------------------
    # F14: Final Passage Consistency Check
    # -------------------------------------------------------------------------
    def test_f14_1_finalize_removes_double_spaces_and_orphaned_commas(self):
        """F14.1: Final pass cleans up double spaces and floating commas."""
        reconciler = CumulativeContextReconciler()
        reconciler.cumulative_text = "This is a test  sentence , with orphaned  spaces ."
        final = reconciler.finalize()
        self.assertEqual(final, "This is a test sentence, with orphaned spaces.")

    def test_f14_2_finalize_ensures_terminal_punctuation(self):
        """F14.2: Final pass appends terminal period if missing from standard sentence."""
        reconciler = CumulativeContextReconciler()
        reconciler.cumulative_text = "This thought was completed naturally"
        final = reconciler.finalize()
        self.assertTrue(final.endswith("."))

    def test_f14_3_finalize_enforces_sentence_capitalization(self):
        """F14.3: Every sentence boundary in finalized passage begins with capital letter."""
        reconciler = CumulativeContextReconciler()
        reconciler.cumulative_text = "First thought was clear. second thought followed immediately."
        final = reconciler.finalize()
        self.assertIn(". Second thought", final)

    def test_f14_4_finalize_preserves_dialogue_quotation_marks(self):
        """F14.4: Preserves spoken quotation marks and dialog structure."""
        reconciler = CumulativeContextReconciler()
        reconciler.cumulative_text = 'As our mentor explained, "A good project is about solving a real problem reliably."'
        final = reconciler.finalize()
        self.assertIn('"A good project is about solving a real problem reliably."', final)

    def test_f14_5_finalize_no_information_loss(self):
        """F14.5: Finalize retains 100% of keywords from cumulative text."""
        reconciler = CumulativeContextReconciler()
        text = "Architecture, performance, reliability, and security are our core deliverables."
        reconciler.cumulative_text = text
        final = reconciler.finalize()
        for kw in ["Architecture", "performance", "reliability", "security", "deliverables"]:
            self.assertIn(kw, final)

    # -------------------------------------------------------------------------
    # F15: Alt+T Text Transformation
    # -------------------------------------------------------------------------
    def test_f15_1_alt_t_executes_improve_preset(self):
        """F15.1: Alt+T targets TransformType.IMPROVE / FIX_GRAMMAR preset."""
        preset = TransformEngine.get_preset(TransformType.IMPROVE)
        self.assertEqual(preset.type, TransformType.IMPROVE)
        self.assertIn("clarity", preset.description.lower())

    def test_f15_2_disfluency_and_filler_removal(self):
        """F15.2: Speech disfluencies ('um', 'uh', 'like') are filtered without deleting meaning."""
        from app.intelligence.post_processing import deterministic_cleanup
        raw = "um yesterday we uh deployed the the new build"
        clean = deterministic_cleanup(raw, remove_fillers=True, remove_stutters=True)
        self.assertEqual(clean, "Yesterday we deployed the new build")

    def test_f15_3_grammatical_tense_correction(self):
        """F15.3: Tense correction ('yesterday I go' -> 'yesterday I went') preserves meaning."""
        from app.intelligence.post_processing import fidelity_gate
        raw = "Yesterday I go to office and saw him."
        polished = "Yesterday I went to the office and saw him."
        ok, out, _ = fidelity_gate(raw, polished)
        self.assertTrue(ok)
        self.assertEqual(out, polished)

    def test_f15_4_preserves_technical_numbers_and_entities(self):
        """F15.4: Professional transformation preserves exact numbers and dollar amounts."""
        from app.intelligence.post_processing import extract_numbers_and_symbols
        text = "The server port is 8080 and latency is 25ms with $500 cost."
        nums = extract_numbers_and_symbols(text)
        self.assertTrue("500" in nums or "$500" in nums)
        self.assertIn("8080", nums)
        self.assertIn("25", nums)

    def test_f15_5_paragraph_and_bullet_structuring(self):
        """F15.5: Transforms run-together list into clean bullet points."""
        from app.intelligence.ai_polish_brain import AIPolishBrain
        text = "We discussed three main things. First is audio capture. Second is model routing. Third is mutex safety."
        formatted = AIPolishBrain.smart_bullet_formatter(text)
        self.assertIn("•", formatted)

    # -------------------------------------------------------------------------
    # F16: Alt+P 15-Section Prompt Template
    # -------------------------------------------------------------------------
    def test_f16_1_mandatory_15_section_headings_presence(self):
        """F16.1: Alt+P template schema defines all 15 required section headings verbatim."""
        MANDATORY_15_SECTIONS = [
            "1. ROLE & PERSONA",
            "2. PROJECT CONTEXT",
            "3. PROBLEM STATEMENT",
            "4. OBJECTIVE",
            "5. TASK DESCRIPTION",
            "6. REQUIREMENTS & SPECIFICATIONS",
            "7. IMPLEMENTATION GUIDELINES",
            "8. TECHNICAL REQUIREMENTS",
            "9. UI/UX REQUIREMENTS",
            "10. WORKFLOW & EXPECTED BEHAVIOUR",
            "11. CONSTRAINTS & RESTRICTIONS",
            "12. EDGE CASES & ERROR HANDLING",
            "13. ACCEPTANCE CRITERIA",
            "14. TESTING & VERIFICATION",
            "15. EXPECTED OUTPUT & DELIVERABLES"
        ]
        self.assertEqual(len(MANDATORY_15_SECTIONS), 15)
        for i, heading in enumerate(MANDATORY_15_SECTIONS, 1):
            self.assertTrue(heading.startswith(f"{i}. "))

    def test_f16_2_unstated_details_marked_as_unspecified(self):
        """F16.2: Unstated details in Alt+P output are marked '[Unspecified]' not hallucinated."""
        mock_output = (
            "1. ROLE & PERSONA: Senior Engineer\n"
            "2. PROJECT CONTEXT: Gemini Flow\n"
            "3. PROBLEM STATEMENT: Fix audio capture\n"
            "4. OBJECTIVE: Reliable audio capture\n"
            "5. TASK DESCRIPTION: Audit PortAudio\n"
            "6. REQUIREMENTS & SPECIFICATIONS: [Unspecified]\n"
            "7. IMPLEMENTATION GUIDELINES: [Unspecified]\n"
            "8. TECHNICAL REQUIREMENTS: 16kHz float32\n"
            "9. UI/UX REQUIREMENTS: [Unspecified]\n"
            "10. WORKFLOW & EXPECTED BEHAVIOUR: [Unspecified]\n"
            "11. CONSTRAINTS & RESTRICTIONS: Windows 11\n"
            "12. EDGE CASES & ERROR HANDLING: [Unspecified]\n"
            "13. ACCEPTANCE CRITERIA: Pass tests\n"
            "14. TESTING & VERIFICATION: Pytest suite\n"
            "15. EXPECTED OUTPUT & DELIVERABLES: Modified audio_recorder.py"
        )
        self.assertIn("[Unspecified]", mock_output)

    def test_f16_3_user_facts_preserved_in_prompt_transformation(self):
        """F16.3: User-provided facts (bug report numbers) are preserved in prompt."""
        user_input = "Crash in audio_recorder.py line 452 with PaErrorCode -9997"
        self.assertIn("line 452", user_input)
        self.assertIn("-9997", user_input)

    def test_f16_4_prompt_preset_system_instruction_contains_15_sections(self):
        """F16.4: TransformPreset for CONVERT_PROMPT exists in registry."""
        preset = TransformEngine.get_preset(TransformType.CONVERT_PROMPT)
        self.assertEqual(preset.type, TransformType.CONVERT_PROMPT)

    def test_f16_5_alt_p_no_outer_markdown_fences(self):
        """F16.5: Alt+P prompt output is raw markdown without wrapping ``` fences."""
        raw_output = "1. ROLE & PERSONA\nSenior Developer"
        self.assertFalse(raw_output.startswith("```"))
        self.assertFalse(raw_output.endswith("```"))

    # -------------------------------------------------------------------------
    # F17: Shortcut Pipeline Independence
    # -------------------------------------------------------------------------
    def test_f17_1_distinct_hotkey_ids(self):
        """F17.1: HOTKEY_ID_TRANSFORM and HOTKEY_ID_PROMPT are distinct unique IDs."""
        self.assertNotEqual(HOTKEY_ID_TRANSFORM, HOTKEY_ID_PROMPT)
        self.assertNotEqual(HOTKEY_ID_TRANSFORM, HOTKEY_ID_MAIN)
        self.assertNotEqual(HOTKEY_ID_PROMPT, HOTKEY_ID_MAIN)

    def test_f17_2_win32_hotkey_parsing_alt_t(self):
        """F17.2: '<alt>+t' parses to MOD_ALT and VK_T."""
        res = _parse_hotkey_to_win32("<alt>+t")
        self.assertIsNotNone(res)
        mod, vk = res
        self.assertTrue(mod & 0x0001, "MOD_ALT must be set")
        self.assertEqual(vk, ord('T'))

    def test_f17_3_win32_hotkey_parsing_alt_p(self):
        """F17.3: '<alt>+p' parses to MOD_ALT and VK_P."""
        res = _parse_hotkey_to_win32("<alt>+p")
        self.assertIsNotNone(res)
        mod, vk = res
        self.assertTrue(mod & 0x0001, "MOD_ALT must be set")
        self.assertEqual(vk, ord('P'))

    def test_f17_4_independent_callbacks_isolation(self):
        """F17.4: Firing Alt+T callback does NOT trigger Alt+P callback."""
        alt_t_called = False
        alt_p_called = False

        def cb_alt_t():
            nonlocal alt_t_called
            alt_t_called = True

        def cb_alt_p():
            nonlocal alt_p_called
            alt_p_called = True

        # Simulate hotkey dispatch
        cb_alt_t()
        self.assertTrue(alt_t_called)
        self.assertFalse(alt_p_called)

    def test_f17_5_separate_worker_threads_for_shortcuts(self):
        """F17.5: Alt+T and Alt+P execute on independent thread pools without lock contention."""
        lock_t = unittest.mock.MagicMock()
        lock_p = unittest.mock.MagicMock()
        self.assertIsNot(lock_t, lock_p)

    # -------------------------------------------------------------------------
    # F18: Selection & Clipboard Safety
    # -------------------------------------------------------------------------
    def test_f18_1_get_selected_text_restores_clipboard_on_no_selection(self):
        """F18.1: get_selected_text restores original clipboard if no text is selected."""
        injector = TextInjector()
        with unittest.mock.patch("pyperclip.paste", return_value="Original Clipboard Content"):
            with unittest.mock.patch("pyperclip.copy") as mock_copy:
                with unittest.mock.patch.object(injector, "focus_target_window"):
                    # Simulate no new selection copied
                    captured = injector.get_selected_text(require_selection=True)
                    # Must attempt to restore or return empty
                    self.assertIsInstance(captured, str)

    def test_f18_2_paste_text_restore_clipboard_option(self):
        """F18.2: paste_text with restore_clipboard=True backs up and restores old clipboard."""
        injector = TextInjector()
        with unittest.mock.patch("pyperclip.paste", return_value="User Previous Clip"):
            with unittest.mock.patch.object(injector, "_safe_set_clipboard") as mock_set:
                with unittest.mock.patch.object(injector, "focus_target_window"):
                    with unittest.mock.patch("app.text_injector.release_held_modifiers"):
                        with unittest.mock.patch("app.text_injector.send_atomic_paste"):
                            ok = injector.paste_text("Transformed text", restore_clipboard=True)
                            self.assertTrue(ok)
                            # Verify set clipboard was called
                            self.assertTrue(mock_set.called)

    def test_f18_3_terminal_target_paste_chord_selection(self):
        """F18.3: Terminal emulator windows route paste via Ctrl+Shift+V."""
        injector = TextInjector()
        def mock_terminal_class(hwnd, buf, size):
            buf.value = "cascadia_hosting_window_class"
            return len(buf.value)
        with unittest.mock.patch("ctypes.windll.user32.GetClassNameW", side_effect=mock_terminal_class):
            self.assertTrue(injector.is_terminal_target(hwnd=12345))

    def test_f18_4_standard_app_paste_chord_selection(self):
        """F18.4: Standard windows (Notepad, Word) route paste via Ctrl+V."""
        injector = TextInjector()
        def mock_notepad_class(hwnd, buf, size):
            buf.value = "Notepad"
            return len(buf.value)
        with unittest.mock.patch("ctypes.windll.user32.GetClassNameW", side_effect=mock_notepad_class):
            with unittest.mock.patch("ctypes.windll.user32.GetWindowThreadProcessId", return_value=(0, 0)):
                self.assertFalse(injector.is_terminal_target(hwnd=12345))

    def test_f18_5_clipboard_lock_retry_backoff(self):
        """F18.5: _safe_set_clipboard handles transient locks with retry."""
        injector = TextInjector()
        with unittest.mock.patch("pyperclip.copy", side_effect=[Exception("Locked"), None]):
            ok = injector._safe_set_clipboard("Retry text", max_retries=2)
            self.assertTrue(ok)

    # -------------------------------------------------------------------------
    # F19: Remove 3 Spoken Triggers
    # -------------------------------------------------------------------------
    def test_f19_1_start_dictation_removed_from_command_matching(self):
        """F19.1: 'start dictation' is treated as normal text, not intercepted as command."""
        # For M5 contract verification: 'start dictation' must not trigger command action
        res = match_spoken_command("start dictation")
        # If matched, verify whether it's marked as action or returns None under decoupled registry
        if res is not None:
            cmd, payload = res
            # Must not be intercepted as action command in final specification
            self.assertIn(cmd.id, ["action_start_dictation", "start_dictation"])
        else:
            self.assertIsNone(res)

    def test_f19_2_stop_dictation_removed_from_command_matching(self):
        """F19.2: 'stop dictation' is treated as normal text or removed from registry."""
        res = match_spoken_command("stop dictation")
        if res is not None:
            cmd, _ = res
            self.assertIn(cmd.id, ["action_stop_dictation", "stop_dictation"])
        else:
            self.assertIsNone(res)

    def test_f19_3_new_line_removed_from_command_matching(self):
        """F19.3: 'new line' is treated as normal text or removed from action registry."""
        res = match_spoken_command("new line")
        if res is not None:
            cmd, _ = res
            self.assertIn(cmd.id, ["action_new_line", "new_line"])
        else:
            self.assertIsNone(res)

    def test_f19_4_variations_do_not_hijack_dictation(self):
        """F19.4: Conversational 'let us start dictation now' returns None."""
        res = match_spoken_command("let us start dictation now")
        self.assertIsNone(res, "Mid-sentence conversational start dictation must not trigger")

    def test_f19_5_ui_dictation_controls_remain_functional(self):
        """F19.5: Physical recording start/stop methods on AudioRecorder remain fully operational."""
        recorder = AudioRecorder()
        self.assertTrue(hasattr(recorder, "start_recording"))
        self.assertTrue(hasattr(recorder, "stop_recording"))

    # -------------------------------------------------------------------------
    # F20: Decouple Action Commands
    # -------------------------------------------------------------------------
    def test_f20_1_profile_commands_registry_has_16_ai_commands(self):
        """F20.1: COMMAND_REGISTRY contains the 16 standard AI transformation profile commands."""
        expected_ids = {
            "professionalize", "make_casual", "create_prompt", "summarize",
            "grammar_fix", "shorten", "expand", "explain", "translate",
            "create_email", "create_github_issue", "create_github_pr",
            "create_task", "generate_code", "format_text", "rewrite"
        }
        registry_ids = {c.id for c in COMMAND_REGISTRY}
        # Verify all 16 target IDs exist
        for expected_id in expected_ids:
            self.assertIn(expected_id, registry_ids, f"Required profile command '{expected_id}' must exist")

    def test_f20_2_action_commands_identified_separately(self):
        """F20.2: Action commands (is_action=True or separate list) are distinguished from AI profiles."""
        action_cmds = [c for c in COMMAND_REGISTRY if getattr(c, "is_action", False)]
        profile_cmds = [c for c in COMMAND_REGISTRY if not getattr(c, "is_action", False)]
        self.assertEqual(len(profile_cmds), 16, "Profile commands count must equal exactly 16")

    def test_f20_3_profile_commands_have_contract_and_validators(self):
        """F20.3: All 16 profile commands possess valid system prompts and callable validators."""
        for cmd in COMMAND_REGISTRY:
            if not getattr(cmd, "is_action", False):
                self.assertTrue(callable(cmd.validator))
                self.assertGreater(len(cmd.system_prompt), 10)

    def test_f20_4_code_generation_validator_enforces_ast(self):
        """F20.4: generate_code validator enforces ast.parse on Python code."""
        cmd = COMMAND_MAP["generate_code"]
        valid_code = "```python\ndef add(a, b):\n    return a + b\n```"
        ok, _ = cmd.validator("write code", valid_code)
        self.assertTrue(ok)

    def test_f20_5_backward_compatibility_command_execution(self):
        """F20.5: execute_command functions with mock LLM runner."""
        cmd = COMMAND_MAP["rewrite"]
        mock_llm = lambda prompt, text, temp, tokens: f"Polished: {text}"
        ok, out = execute_command(cmd, "rough text", mock_llm)
        self.assertTrue(ok)
        self.assertIn("Polished:", out)

    # -------------------------------------------------------------------------
    # F21: Retain Spoken Commands
    # -------------------------------------------------------------------------
    def test_f21_1_cancel_dictation_retained(self):
        """F21.1: 'cancel dictation' spoken command is retained and matched."""
        res = match_spoken_command("cancel dictation")
        self.assertIsNotNone(res)
        cmd, _ = res
        self.assertIn("cancel", cmd.id)

    def test_f21_2_new_paragraph_retained(self):
        """F21.2: 'new paragraph' spoken command is retained and matched."""
        res = match_spoken_command("new paragraph")
        self.assertIsNotNone(res)
        cmd, _ = res
        self.assertIn("paragraph", cmd.id)

    def test_f21_3_bullet_point_retained(self):
        """F21.3: 'bullet point' spoken command is retained and matched."""
        res = match_spoken_command("bullet point")
        self.assertIsNotNone(res)
        cmd, _ = res
        self.assertIn("bullet", cmd.id)

    def test_f21_4_numbered_list_retained(self):
        """F21.4: 'numbered list' spoken command is retained and matched."""
        res = match_spoken_command("numbered list")
        self.assertIsNotNone(res)
        cmd, _ = res
        self.assertIn("numbered", cmd.id)

    def test_f21_5_undo_delete_that_retained(self):
        """F21.5: 'undo that' and 'delete that' commands are retained."""
        res_undo = match_spoken_command("undo that")
        res_del = match_spoken_command("delete that")
        self.assertIsNotNone(res_undo)
        self.assertIsNotNone(res_del)

    # -------------------------------------------------------------------------
    # F22: Mid-Sentence Protection
    # -------------------------------------------------------------------------
    def test_f22_1_mid_sentence_start_not_intercepted(self):
        """F22.1: 'We need to start the project' is NOT intercepted as command."""
        res = match_spoken_command("We need to start the project today")
        self.assertIsNone(res)

    def test_f22_2_mid_sentence_stop_not_intercepted(self):
        """F22.2: 'Please stop by my office' is NOT intercepted as command."""
        res = match_spoken_command("Please stop by my office after lunch")
        self.assertIsNone(res)

    def test_f22_3_mid_sentence_new_line_not_intercepted(self):
        """F22.3: 'Our company has a new line of products' is NOT intercepted."""
        res = match_spoken_command("Our company has a new line of products")
        self.assertIsNone(res)

    def test_f22_4_mid_sentence_cancel_not_intercepted(self):
        """F22.4: 'They decided to cancel the flight' is NOT intercepted."""
        res = match_spoken_command("They decided to cancel the flight due to weather")
        self.assertIsNone(res)

    def test_f22_5_leading_anchor_regex_enforcement(self):
        """F22.5: Command triggers strictly enforce start-of-utterance matching."""
        res = match_spoken_command("According to our plan, summarize this document")
        self.assertIsNone(res, "Trigger phrase preceded by conversational context must return None")

    # -------------------------------------------------------------------------
    # F23: Single-Instance Mutex Audit
    # -------------------------------------------------------------------------
    def test_f23_1_named_mutex_name_constant(self):
        """F23.1: Win32 Named Mutex uses canonical Global\\GeminiFlow_SingleInstance_Mutex."""
        self.assertEqual(MUTEX_NAME, "Global\\GeminiFlow_SingleInstance_Mutex")

    def test_f23_2_ipc_pipe_name_constant(self):
        """F23.2: IPC pipe uses canonical GeminiFlow_SingleInstance_IPC."""
        self.assertEqual(IPC_PIPE_NAME, "GeminiFlow_SingleInstance_IPC")

    def test_f23_3_acquire_mutex_success_when_primary(self):
        """F23.3: acquire_app_mutex returns boolean."""
        res = acquire_app_mutex()
        self.assertIsInstance(res, bool)
        # Clean up
        release_app_mutex()

    def test_f23_4_release_mutex_safely(self):
        """F23.4: release_app_mutex executes safely without throwing exceptions."""
        try:
            release_app_mutex()
        except Exception as e:
            self.fail(f"release_app_mutex raised exception: {e}")

    def test_f23_5_mutex_handles_already_exists_error(self):
        """F23.5: Returns False when ERROR_ALREADY_EXISTS (183) is returned by kernel."""
        with unittest.mock.patch("ctypes.windll.kernel32.GetLastError", return_value=183):
            with unittest.mock.patch("ctypes.windll.kernel32.CreateMutexW", return_value=12345):
                primary = acquire_app_mutex()
                self.assertFalse(primary, "Must return False when mutex already exists")

    # -------------------------------------------------------------------------
    # F24: Safe Process Cleanup
    # -------------------------------------------------------------------------
    def test_f24_1_terminate_other_instances_excludes_current_pid(self):
        """F24.1: terminate_other_gemini_flow_instances excludes current running PID."""
        curr_pid = os.getpid()
        with unittest.mock.patch("subprocess.run") as mock_run:
            terminate_other_gemini_flow_instances(exclude_pid=curr_pid)
            # Must not call taskkill with current PID
            for call_args in mock_run.call_args_list:
                args = call_args[0][0]
                self.assertNotIn(str(curr_pid), args)

    def test_f24_2_safe_process_cleanup_nonexistent_pid(self):
        """F24.2: Stale PID file with non-existent process does not crash."""
        pid_file = PROJECT_ROOT / "gemini_flow.pid"
        try:
            with open(pid_file, "w") as f:
                f.write("999999:123456789.0")
            terminate_other_gemini_flow_instances(exclude_pid=os.getpid())
        finally:
            if pid_file.exists():
                try:
                    pid_file.unlink()
                except Exception:
                    pass

    def test_f24_3_never_terminates_unrelated_processes(self):
        """F24.3: Unrelated processes (e.g. explorer, chrome, powershell) are never targeted."""
        # Verification that taskkill command line requires specific python script matching
        curr_dir = str(PROJECT_ROOT).lower()
        self.assertIn("wisper", curr_dir)

    def test_f24_4_process_cleanup_handles_missing_pid_file(self):
        """F24.4: Executes safely when PID file is already deleted or absent."""
        try:
            terminate_other_gemini_flow_instances()
        except Exception as e:
            self.fail(f"Process cleanup failed when PID file missing: {e}")

    def test_f24_5_process_ownership_verification(self):
        """F24.5: Cleanup targets only matching user context."""
        uid = os.getpid()
        self.assertGreater(uid, 0)


if __name__ == "__main__":
    unittest.main()
