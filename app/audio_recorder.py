"""
Audio Recorder Module for Gemini Flow.
Captures microphone audio at the hardware's native rate, resamples with high-fidelity
polyphase filtering to 16 kHz mono float32, continuously streams PCM16 WAV directly
to disk in a dedicated thread using an unbounded producer-consumer queue, enforces
a 30-minute safety cap, and provides crash-recovery tracking.
"""
import io
import math
import os
import queue
import time
import wave
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple

import numpy as np
from scipy import signal

logger = logging.getLogger("GeminiFlow.AudioRecorder")

try:
    import sounddevice as sd
except ImportError:
    sd = None
    logger.warning("sounddevice is not installed or available.")


def get_recordings_dir() -> Path:
    """Returns the persistent recordings directory in %LOCALAPPDATA%/GeminiFlow/recordings with resilient fallback."""
    candidates = []
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "GeminiFlow" / "recordings")
    if os.environ.get("APPDATA"):
        candidates.append(Path(os.environ["APPDATA"]) / "GeminiFlow" / "recordings")
    # Project-local fallback for sandboxed, portable, or restricted permission environments
    candidates.append(Path(__file__).resolve().parent.parent / "recordings")

    for cand in candidates:
        try:
            cand.mkdir(parents=True, exist_ok=True)
            test_file = cand / f".write_test_{int(time.time() * 1000) % 100000}"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            return cand
        except Exception:
            continue

    fallback = Path.cwd() / "recordings"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def resample_to_16k_mono(audio_data: np.ndarray, orig_sr: int) -> np.ndarray:
    """
    High-fidelity polyphase down/up-sampling to 16,000 Hz mono float32.
    Avoids linear interpolation spectral aliasing and preserves full phonetic bandwidth.
    """
    if audio_data is None or len(audio_data) == 0:
        return np.zeros((0,), dtype=np.float32)

    data = audio_data.astype(np.float32)
    # Downmix multi-channel to mono
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    if orig_sr == 16000:
        return data

    gcd_val = math.gcd(16000, orig_sr)
    up = 16000 // gcd_val
    down = orig_sr // gcd_val
    try:
        resampled = signal.resample_poly(data, up, down).astype(np.float32)
        return resampled
    except Exception as ex:
        logger.warning(f"resample_poly failed ({ex}), falling back to Fourier resample: {orig_sr} -> 16000")
        target_len = int(round(len(data) * 16000.0 / orig_sr))
        return signal.resample(data, target_len).astype(np.float32)


def apply_dsp_filters(
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    high_pass_enabled: bool = False,
    high_pass_hz: float = 80.0,
    peak_norm_enabled: bool = False
) -> np.ndarray:
    """
    Applies gentle, optional DSP filters behind explicit settings (OFF by default):
    1. Gentle 80 Hz 2nd-order Butterworth High-Pass Filter: strips AC rumble without affecting fundamental voice pitch.
    2. Peak Normalization: scales peak speech amplitude to -0.5 dBFS (0.95) if enabled.
    Note: Bandpass (300-3400 Hz) and dynamic noise gates are strictly prohibited to avoid degrading Whisper WER.
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    processed = audio_data.copy().astype(np.float32)

    # 1. Gentle 80 Hz High-Pass Filter (OFF by default)
    if high_pass_enabled:
        try:
            sos = signal.butter(N=2, Wn=high_pass_hz, btype='highpass', fs=sample_rate, output='sos')
            processed = signal.sosfilt(sos, processed, axis=0)
        except Exception as hp_err:
            logger.debug(f"High-pass DSP filter note: {hp_err}")

    # 2. Peak Normalization (OFF by default)
    if peak_norm_enabled:
        try:
            peak = float(np.max(np.abs(processed)))
            if peak > 1e-5:
                processed = (processed / peak) * 0.95
        except Exception as norm_err:
            logger.debug(f"Peak normalization note: {norm_err}")

    return processed


class AudioRecorder:
    SAFETY_CAP_SECONDS = 1800.0  # 30 minutes hard safety cap

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        on_amplitude: Optional[Callable[[float], None]] = None,
        on_safety_cap: Optional[Callable[[], None]] = None,
        config_manager: Optional[Any] = None
    ):
        self.target_sample_rate = 16000
        self.target_channels = 1
        self.on_amplitude = on_amplitude
        self.on_safety_cap = on_safety_cap
        self.config = config_manager

        self.device_index: Optional[int] = None
        self.device_sample_rate: int = 16000
        self.device_channels: int = 1

        self.is_recording = False
        self.stream: Optional[Any] = None
        self.start_time = 0.0

        # Unbounded producer/consumer queue (zero drop under load)
        self._raw_queue: queue.Queue = queue.Queue()
        self._writer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._buffer_lock = threading.Lock()

        # Recording session metrics & storage
        self._current_wav_path: Optional[Path] = None
        self._accumulated_16k_samples: List[np.ndarray] = []
        self._current_amplitude: float = 0.0
        self._last_duration: float = 0.0
        self._last_sample_count: int = 0
        self._last_rms: float = 0.0
        self._active_wav_file: Optional[wave.Wave_write] = None

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

    def _resolve_device_parameters(self, dev_idx: Optional[int]) -> Tuple[Optional[int], int, int]:
        """Resolves device index, native sample rate, and channels."""
        if sd is None:
            return None, 16000, 1
        try:
            if dev_idx is not None:
                info = sd.query_devices(dev_idx)
            else:
                info = sd.query_devices(kind="input")
                dev_idx = info.get("index", None)
            native_rate = int(info.get("default_samplerate", 16000))
            max_ch = int(info.get("max_input_channels", 1))
            channels = 1 if max_ch >= 1 else 1
            return dev_idx, native_rate, channels
        except Exception as ex:
            logger.warning(f"Could not resolve device parameters for index {dev_idx}: {ex}")
            return None, 16000, 1

    def set_device(self, device_index: Optional[int]):
        self.device_index = device_index

    def warmup_audio(self):
        """Pre-warms PortAudio subsystem so first user recording starts instantaneously."""
        if sd is None:
            return
        try:
            dev_idx, rate, ch = self._resolve_device_parameters(self.device_index)
            with sd.InputStream(samplerate=rate, channels=ch, dtype="float32", device=dev_idx, blocksize=512):
                time.sleep(0.04)
            logger.info("PortAudio microphone driver warmed up successfully.")
        except Exception as e:
            logger.debug(f"Audio driver warmup note: {e}")

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: Any, status: Any):
        """
        Lightweight sounddevice InputStream callback.
        Enqueues raw audio without blocking; computes RMS for UI visualization.
        """
        if status:
            logger.warning(f"Audio stream status: {status}")

        if not self.is_recording:
            return

        # Zero blocking: enqueue raw frame copy
        self._raw_queue.put(indata.copy())

        # Amplitude calculation for UI
        rms = float(np.sqrt(np.mean(np.square(indata)) + 1e-9))
        scaled = min(1.0, float(rms * 12.0))
        self._current_amplitude = scaled
        if self.on_amplitude:
            try:
                self.on_amplitude(scaled)
            except Exception:
                pass

    def _writer_worker(self):
        """
        Dedicated background worker thread:
        Pulls raw frames from queue, resamples once to 16 kHz mono float32,
        converts to PCM16, and continuously writes frames to disk in real-time.
        """
        rec_dir = get_recordings_dir()
        ts_str = time.strftime("%Y%m%d_%H%M%S")
        self._current_wav_path = rec_dir / f"recording_{ts_str}_{int(time.time() * 1000) % 1000:03d}.wav"

        try:
            wf = wave.open(str(self._current_wav_path), "wb")
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            self._active_wav_file = wf
        except Exception as ex:
            logger.error(f"Failed to open WAV file for continuous writing: {ex}")
            wf = None

        total_16k_samples = 0

        while not self._stop_event.is_set() or not self._raw_queue.empty():
            try:
                raw_chunk = self._raw_queue.get(timeout=0.08)
            except queue.Empty:
                continue

            # Queue lag warning if queue depth grows significantly (>100 frames = ~2 seconds backlog)
            qsize = self._raw_queue.qsize()
            if qsize > 100:
                logger.warning(f"Audio disk writer queue backlog: {qsize} frames pending.")

            # Polyphase resampling to 16 kHz mono float32
            chunk_16k = resample_to_16k_mono(raw_chunk, self.device_sample_rate)
            if len(chunk_16k) == 0:
                continue

            with self._buffer_lock:
                self._accumulated_16k_samples.append(chunk_16k)

            total_16k_samples += len(chunk_16k)

            # Continuous disk streaming as PCM16
            if wf is not None:
                pcm16 = (np.clip(chunk_16k, -1.0, 1.0) * 32767).astype(np.int16)
                try:
                    wf.writeframes(pcm16.tobytes())
                except Exception as w_err:
                    logger.error(f"Error writing continuous WAV frame to disk: {w_err}")

            # Check 30-minute safety cap
            curr_duration = total_16k_samples / 16000.0
            if curr_duration >= self.SAFETY_CAP_SECONDS and self.is_recording:
                logger.warning(f"Audio safety cap reached ({curr_duration:.1f}s >= {self.SAFETY_CAP_SECONDS}s). Triggering auto-stop.")
                if self.on_safety_cap:
                    try:
                        self.on_safety_cap()
                    except Exception as cap_err:
                        logger.error(f"Error in on_safety_cap callback: {cap_err}")

        # Finalize and close WAV file
        if wf is not None:
            try:
                wf.close()
            except Exception as close_err:
                logger.error(f"Error closing WAV writer: {close_err}")
            self._active_wav_file = None

    def start_recording(self) -> bool:
        """Starts hardware capture at native rate and begins continuous disk writing."""
        with self._buffer_lock:
            if self.is_recording:
                return False
            if sd is None:
                logger.error("sounddevice is not available.")
                return False

            self.is_recording = True
            self.start_time = time.time()
            self._current_amplitude = 0.0
            self._accumulated_16k_samples = []
            self._raw_queue = queue.Queue()
            self._stop_event.clear()

        dev_idx, native_rate, channels = self._resolve_device_parameters(self.device_index)
        self.device_index = dev_idx
        self.device_sample_rate = native_rate
        self.device_channels = channels

        # Start continuous disk writer thread
        self._writer_thread = threading.Thread(target=self._writer_worker, daemon=True, name="AudioDiskWriter")
        self._writer_thread.start()

        try:
            self.stream = sd.InputStream(
                samplerate=self.device_sample_rate,
                channels=self.device_channels,
                dtype="float32",
                device=self.device_index,
                callback=self._audio_callback,
                blocksize=1024
            )
            self.stream.start()
            logger.info(f"Continuous audio recording started: device={self.device_index}, native_sr={self.device_sample_rate}, ch={self.device_channels}")
            return True
        except Exception as e:
            logger.warning(f"Failed to start audio stream on device {self.device_index}: {e}. Retrying default mic...")
            try:
                self.stream = sd.InputStream(
                    samplerate=self.device_sample_rate,
                    channels=self.device_channels,
                    dtype="float32",
                    device=None,
                    callback=self._audio_callback,
                    blocksize=1024
                )
                self.stream.start()
                logger.info("Recording started on fallback default microphone.")
                return True
            except Exception as e2:
                logger.error(f"Fallback to default audio device failed: {e2}")
                with self._buffer_lock:
                    self.is_recording = False
                    self._stop_event.set()
                return False

    def stop_recording(self) -> Tuple[str, bytes, float, int, float]:
        """
        Stops audio capture, waits for all pending frames to be written to disk,
        and returns (wav_path, wav_bytes, duration_seconds, sample_count, rms).
        """
        with self._buffer_lock:
            if not self.is_recording:
                return "", b"", 0.0, 0, 0.0
            self.is_recording = False

        wall_duration = max(0.1, time.time() - self.start_time)

        # Stop audio hardware stream
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
        except Exception as e:
            logger.error(f"Error stopping audio stream: {e}")

        # Signal writer thread to flush queue and finish file
        self._stop_event.set()
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=3.0)

        with self._buffer_lock:
            if self._accumulated_16k_samples:
                full_16k = np.concatenate(self._accumulated_16k_samples, axis=0)
            else:
                full_16k = np.zeros((0,), dtype=np.float32)

        sample_count = len(full_16k)
        duration_sec = sample_count / 16000.0 if sample_count > 0 else wall_duration
        rms = float(np.sqrt(np.mean(full_16k ** 2) + 1e-9)) if sample_count > 0 else 0.0

        # Read the verified WAV bytes from disk
        wav_path_str = str(self._current_wav_path) if self._current_wav_path and self._current_wav_path.exists() else ""
        wav_bytes = b""
        if wav_path_str and os.path.exists(wav_path_str):
            try:
                with open(wav_path_str, "rb") as rf:
                    wav_bytes = rf.read()
            except Exception as r_err:
                logger.error(f"Failed to read WAV file from disk: {r_err}")

        # If disk read failed, serialize in memory
        if not wav_bytes and sample_count > 0:
            bio = io.BytesIO()
            with wave.open(bio, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                pcm16 = (np.clip(full_16k, -1.0, 1.0) * 32767).astype(np.int16)
                wf.writeframes(pcm16.tobytes())
            wav_bytes = bio.getvalue()

        self._last_duration = duration_sec
        self._last_sample_count = sample_count
        self._last_rms = rms

        logger.info(
            f"[AUDIO CAPTURE METRICS] Path='{wav_path_str}', Duration={duration_sec:.2f}s, "
            f"Samples={sample_count} (16kHz), RMS={rms:.5f}, Size={len(wav_bytes)} bytes"
        )
        return wav_path_str, wav_bytes, duration_sec, sample_count, rms

    @property
    def current_amplitude(self) -> float:
        return self._current_amplitude

    @staticmethod
    def contains_speech(wav_bytes: bytes, threshold_rms: float = 0.0002, threshold_peak: float = 0.001) -> bool:
        """Determines whether the audio buffer contains speech energy, rejecting true digital silence."""
        if not wav_bytes or len(wav_bytes) < 1000:
            return False
        try:
            with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
                nframes = wf.getnframes()
                if nframes < 800:
                    return False
                pcm = wf.readframes(nframes)
            samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
            peak = float(np.max(np.abs(samples)))
            rms = float(np.sqrt(np.mean(samples ** 2)))
            return peak >= threshold_peak or rms >= threshold_rms
        except Exception:
            return True

    @staticmethod
    def get_orphaned_recordings() -> List[Path]:
        """Scans recordings directory for orphaned WAV files that have not been transcribed."""
        rec_dir = get_recordings_dir()
        if not rec_dir.exists():
            return []
        wav_files = sorted(rec_dir.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
        # Keep recordings from the last 24 hours that are > 2000 bytes
        cutoff = time.time() - 86400
        orphaned = [f for f in wav_files if f.stat().st_mtime > cutoff and f.stat().st_size > 2000]
        return orphaned
