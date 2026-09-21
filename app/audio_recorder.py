"""
Audio Recorder Module for Gemini Flow
Captures microphone audio at 16kHz mono, provides live amplitude feedback, and outputs WAV bytes.
"""
import io
import wave
import time
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger("GeminiFlow.AudioRecorder")

try:
    import sounddevice as sd
except ImportError:
    sd = None
    logger.warning("sounddevice is not installed or available.")


def apply_dsp_filters(
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    high_pass_enabled: bool = True,
    high_pass_hz: float = 85.0,
    noise_gate_enabled: bool = True,
    noise_gate_threshold_db: float = -42.0
) -> np.ndarray:
    """
    Applies real-time Digital Signal Processing (DSP) audio enhancement:
    1. 85 Hz 2nd-order Butterworth High-Pass Filter: Eliminates 50/60 Hz electrical hums and 20-75 Hz ceiling fan/AC motor rumble.
    2. Dynamic RMS Noise Gate: Smoothly suppresses ambient room hiss, breathing, and background whispers during pauses in speech.
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    processed = audio_data.copy().astype(np.float32)

    # 1. 85 Hz Butterworth High-Pass Filter
    if high_pass_enabled:
        try:
            from scipy import signal
            sos = signal.butter(N=2, Wn=high_pass_hz, btype='highpass', fs=sample_rate, output='sos')
            processed = signal.sosfilt(sos, processed, axis=0)
        except Exception as hp_err:
            logger.debug(f"High-pass DSP filter note: {hp_err}")

    # 2. Dynamic RMS Noise Gate
    if noise_gate_enabled:
        try:
            # 20ms block frames (320 samples @ 16kHz)
            frame_len = int(sample_rate * 0.02)
            if frame_len > 0 and len(processed) >= frame_len:
                num_frames = len(processed) // frame_len
                shape_2d = processed.ndim > 1
                reshaped = processed[:num_frames * frame_len].reshape(num_frames, frame_len, -1) if shape_2d else processed[:num_frames * frame_len].reshape(num_frames, frame_len)
                rms = np.sqrt(np.mean(reshaped ** 2, axis=1, keepdims=True) + 1e-9)
                rms_db = 20.0 * np.log10(rms + 1e-9)

                # Soft-knee gain curve
                knee_width = 6.0
                diff = rms_db - noise_gate_threshold_db
                gains = np.where(
                    diff >= knee_width / 2.0, 1.0,
                    np.where(diff <= -knee_width / 2.0, 0.05,
                             0.05 + 0.95 * ((diff + knee_width / 2.0) / knee_width))
                )

                expanded_gains = np.repeat(gains, frame_len, axis=0)
                if shape_2d:
                    processed[:len(expanded_gains)] *= expanded_gains
                else:
                    processed[:len(expanded_gains)] *= expanded_gains.flatten()
        except Exception as ng_err:
            logger.debug(f"Noise gate DSP note: {ng_err}")

    return processed


class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        on_amplitude: Optional[Callable[[float], None]] = None,
        config_manager: Optional[Any] = None
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.on_amplitude = on_amplitude
        self.config = config_manager
        self.dsp_fan_filter_enabled = True
        self.dsp_noise_gate_enabled = True
        self.dsp_noise_gate_threshold_db = -42.0
        self.is_recording = False
        self.stream: Optional[Any] = None
        self.audio_chunks: List[np.ndarray] = []
        self.start_time = 0.0
        self.device_index: Optional[int] = None
        self._current_amplitude: float = 0.0

    @staticmethod
    def get_input_devices() -> List[Dict[str, Any]]:
        """Returns a list of input audio devices."""
        if sd is None:
            return []
        devices = []
        try:
            device_list = sd.query_devices()
            for idx, dev in enumerate(device_list):
                if dev.get("max_input_channels", 0) > 0:
                    devices.append({
                        "index": idx,
                        "name": dev.get("name", f"Device {idx}"),
                        "channels": dev.get("max_input_channels"),
                        "default_samplerate": dev.get("default_samplerate", 16000)
                    })
        except Exception as e:
            logger.error(f"Error querying audio devices: {e}")
        return devices

    def set_device(self, device_index: Optional[int]):
        self.device_index = device_index

    def warmup_audio(self):
        """
        Pre-warms the PortAudio driver and queries audio devices in the background
        so that the very first user recording starts instantaneously with zero audio latency or clipping.
        """
        if sd is None:
            return
        try:
            # 1. Query devices to initialize PortAudio driver subsystem
            _ = sd.query_devices()
            # 2. Briefly test opening an input stream for 50ms to prime OS audio buffer
            target_device = self.device_index
            try:
                with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype="float32", device=target_device, blocksize=512):
                    time.sleep(0.04)
            except Exception:
                with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype="float32", device=None, blocksize=512):
                    time.sleep(0.04)
            logger.info("PortAudio microphone driver warmed up successfully.")
        except Exception as e:
            logger.debug(f"Audio driver warmup note: {e}")

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: Any, status: Any):
        """Internal callback for sounddevice InputStream."""
        if status:
            logger.warning(f"Audio stream status: {status}")
        if self.is_recording:
            # indata shape is (frames, channels)
            self.audio_chunks.append(indata.copy())
            # Calculate RMS amplitude for UI visualization (0.0 to 1.0)
            rms = np.sqrt(np.mean(np.square(indata)))
            # Scale slightly so normal speech animates nicely
            scaled = min(1.0, float(rms * 12.0))
            self._current_amplitude = scaled
            if self.on_amplitude:
                try:
                    self.on_amplitude(scaled)
                except Exception:
                    pass

    @property
    def current_amplitude(self) -> float:
        return self._current_amplitude

    def start_recording(self) -> bool:
        """Starts recording audio from the selected microphone."""
        if self.is_recording:
            return False
        if sd is None:
            logger.error("sounddevice is not available.")
            return False

        self.audio_chunks = []
        self.is_recording = True
        self.start_time = time.time()
        self._current_amplitude = 0.0

        # Attempt with configured device index, or fallback to system default
        target_device = self.device_index
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                device=target_device,
                callback=self._audio_callback,
                blocksize=1024
            )
            self.stream.start()
            logger.info(f"Audio recording started on device: {target_device}")
            return True
        except Exception as e:
            if target_device is not None:
                logger.warning(f"Device {target_device} unavailable (likely reset/sleep). Falling back to Windows default mic: {e}")
                try:
                    self.stream = sd.InputStream(
                        samplerate=self.sample_rate,
                        channels=self.channels,
                        dtype="float32",
                        device=None,
                        callback=self._audio_callback,
                        blocksize=1024
                    )
                    self.stream.start()
                    logger.info("Audio recording successfully started on fallback default microphone.")
                    return True
                except Exception as e2:
                    logger.error(f"Fallback to default audio device also failed: {e2}")
            else:
                logger.error(f"Failed to start audio recording on default device: {e}")

            self.is_recording = False
            return False

    def stop_recording(self) -> tuple[bytes, float]:
        """
        Stops recording and returns (wav_bytes, duration_seconds).
        """
        if not self.is_recording:
            return b"", 0.0

        self.is_recording = False
        duration = max(0.1, time.time() - self.start_time)

        try:
            if self.stream:
                # Allow a tiny moment for in-flight audio frames from OS buffer
                time.sleep(0.04)
                self.stream.stop()
                self.stream.close()
                self.stream = None
        except Exception as e:
            logger.error(f"Error stopping audio stream: {e}")

        if not self.audio_chunks:
            logger.warning("No audio recorded.")
            return b"", 0.0

        try:
            # Combine all chunks into one continuous array
            audio_data = np.concatenate(self.audio_chunks, axis=0)

            # Apply Real-Time DSP Filters (Ceiling Fan / AC High-Pass + Dynamic Noise Gate)
            fan_filter_on = self.config.get_dsp_fan_filter_enabled() if hasattr(self.config, "get_dsp_fan_filter_enabled") else self.dsp_fan_filter_enabled
            noise_gate_on = self.config.get_dsp_noise_gate_enabled() if hasattr(self.config, "get_dsp_noise_gate_enabled") else self.dsp_noise_gate_enabled
            gate_thresh = self.config.get_dsp_noise_gate_threshold_db() if hasattr(self.config, "get_dsp_noise_gate_threshold_db") else self.dsp_noise_gate_threshold_db

            if fan_filter_on or noise_gate_on:
                audio_data = apply_dsp_filters(
                    audio_data=audio_data,
                    sample_rate=self.sample_rate,
                    high_pass_enabled=fan_filter_on,
                    high_pass_hz=85.0,
                    noise_gate_enabled=noise_gate_on,
                    noise_gate_threshold_db=gate_thresh
                )

            # Clip and convert float32 (-1.0 to 1.0) to int16 PCM
            audio_data = np.clip(audio_data, -1.0, 1.0)
            pcm16_data = (audio_data * 32767).astype(np.int16)

            # Write into in-memory WAV buffer
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit = 2 bytes
                wf.setframerate(self.sample_rate)
                wf.writeframes(pcm16_data.tobytes())

            wav_bytes = wav_io.getvalue()
            logger.info(f"Recorded & DSP filtered {len(wav_bytes)} bytes of WAV audio ({duration:.2f}s).")
            return wav_bytes, duration
        except Exception as e:
            logger.error(f"Error converting audio to WAV: {e}")
            return b"", duration
