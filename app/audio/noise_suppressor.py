"""
Noise Suppression and Audio Pre-Processing Module for Gemini Flow.
Provides real-time DSP noise gating, 80Hz high-pass filtering (AC hum / desk rumble removal),
Whisper Mode quiet speech amplification with soft-limiter saturation, and
silence gating to prevent downstream Whisper hallucinations.
"""
import logging
from typing import Tuple, Optional
import numpy as np
from scipy import signal

logger = logging.getLogger("GeminiFlow.NoiseSuppressor")


class NoiseSuppressor:
    """
    Real-time noise suppressor and speech conditioner.
    Implements:
    - 4th-order Butterworth High-Pass Filter (80 Hz cutoff).
    - Spectral noise floor tracking and soft noise gate.
    - Whisper Mode soft-saturation gain boost for low-volume dictation.
    - Pre-VAD energy threshold verification.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        high_pass_hz: float = 80.0,
        gate_threshold_db: float = -42.0,
        whisper_mode: bool = False,
        whisper_gain_db: float = 10.88  # ~3.5x soft gain as specified
    ):
        self.sample_rate = sample_rate
        self.high_pass_hz = high_pass_hz
        self.gate_threshold_db = gate_threshold_db
        self.whisper_mode = whisper_mode
        self.whisper_gain_db = whisper_gain_db

        # Pre-compute Butterworth SOS filter for 16 kHz
        try:
            self._hp_sos = signal.butter(
                4, self.high_pass_hz, btype="highpass", fs=self.sample_rate, output="sos"
            )
        except Exception as e:
            logger.warning(f"Failed to pre-compute Butterworth SOS filter: {e}")
            self._hp_sos = None

        # Exponential moving average for noise floor estimation
        self._noise_floor_rms: float = 0.005
        self._alpha_noise: float = 0.05

    def filter_highpass(self, audio: np.ndarray) -> np.ndarray:
        """Applies 80 Hz high-pass Butterworth filter to strip DC offset and sub-audible hum."""
        if audio is None or len(audio) < 32 or self._hp_sos is None:
            return audio
        try:
            return signal.sosfilt(self._hp_sos, audio).astype(np.float32)
        except Exception as e:
            logger.debug(f"Highpass filter fallback: {e}")
            return audio

    def apply_soft_noise_gate(
        self,
        audio: np.ndarray,
        threshold_db: Optional[float] = None,
        attenuation_db: float = -14.0
    ) -> np.ndarray:
        """
        Applies a smooth soft noise gate to suppress background fan hiss and room reverberation.
        Unlike a hard gate which creates audio clicking, this uses a smooth sigmoid attenuation curve.
        """
        if audio is None or len(audio) == 0:
            return audio

        th_db = threshold_db if threshold_db is not None else self.gate_threshold_db
        linear_threshold = 10.0 ** (th_db / 20.0)
        rms = float(np.sqrt(np.mean(audio ** 2) + 1e-9))

        # Update noise floor estimate when energy is low
        if rms < linear_threshold * 1.5:
            self._noise_floor_rms = (
                (1.0 - self._alpha_noise) * self._noise_floor_rms + self._alpha_noise * rms
            )

        # Calculate frame envelope
        envelope = np.abs(audio)
        # Smoothing window ~10ms (160 samples at 16kHz)
        win_size = min(len(audio), int(self.sample_rate * 0.01))
        if win_size > 4:
            kernel = np.ones(win_size) / win_size
            smooth_env = np.convolve(envelope, kernel, mode="same")
        else:
            smooth_env = envelope

        # Soft sigmoid gain mask: values above threshold get gain ~1.0; below get attenuation
        scale = 10.0 / (linear_threshold + 1e-6)
        gain = 1.0 / (1.0 + np.exp(-scale * (smooth_env - linear_threshold)))
        min_gain = 10.0 ** (attenuation_db / 20.0)  # e.g. -14dB ~ 0.20
        effective_gain = min_gain + (1.0 - min_gain) * gain

        return (audio * effective_gain).astype(np.float32)

    def apply_whisper_mode_gain(
        self,
        audio: np.ndarray,
        gain_db: Optional[float] = None
    ) -> np.ndarray:
        """
        Whisper Mode: Boosts quiet whispered speech (+6dB to +12dB) with hyperbolic tangent (tanh)
        soft limiter to prevent digital clipping or harsh distortion.
        """
        if audio is None or len(audio) == 0:
            return audio

        g_db = gain_db if gain_db is not None else self.whisper_gain_db
        linear_gain = 10.0 ** (g_db / 20.0)  # +9dB is ~2.82x

        boosted = audio * linear_gain
        # Soft-saturating tanh limiter keeps amplitudes bounded in [-0.98, 0.98]
        limited = np.tanh(boosted) * 0.98
        return limited.astype(np.float32)

    def process(
        self,
        audio: np.ndarray,
        is_whisper_mode: Optional[bool] = None,
        apply_gate: bool = True
    ) -> Tuple[np.ndarray, bool, float]:
        """
        Full conditioning pipeline:
        1. 80 Hz high-pass filtering
        2. Soft noise gate
        3. Optional Whisper Mode gain boost
        Returns (conditioned_audio, contains_speech, rms).
        """
        if audio is None or len(audio) == 0:
            return np.zeros((0,), dtype=np.float32), False, 0.0

        # Step 1: Strip low-frequency room and electrical noise
        conditioned = self.filter_highpass(audio)

        # Step 2: Soft noise gate
        if apply_gate:
            conditioned = self.apply_soft_noise_gate(conditioned)

        # Step 3: Whisper Mode boost if enabled
        active_whisper = is_whisper_mode if is_whisper_mode is not None else self.whisper_mode
        if active_whisper:
            conditioned = self.apply_whisper_mode_gain(conditioned)

        # Step 4: Metrics and speech presence
        rms = float(np.sqrt(np.mean(conditioned ** 2) + 1e-9))
        peak = float(np.max(np.abs(conditioned))) if len(conditioned) > 0 else 0.0

        # Speech threshold: must have energy above ambient noise floor
        speech_threshold = max(0.006, self._noise_floor_rms * 1.8)
        contains_speech = (rms >= speech_threshold) and (peak >= 0.02)

        return conditioned, contains_speech, rms


def condition_audio_for_transcription(
    audio_16k: np.ndarray,
    whisper_mode: bool = False,
    gate_threshold_db: float = -42.0
) -> Tuple[np.ndarray, bool, float]:
    """Convenience helper for conditioning 16kHz mono audio before VAD and ASR."""
    suppressor = NoiseSuppressor(
        sample_rate=16000,
        gate_threshold_db=gate_threshold_db,
        whisper_mode=whisper_mode
    )
    return suppressor.process(audio_16k)
