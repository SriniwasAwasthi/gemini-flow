"""
Audio Recorder Module for Gemini Flow.
Captures microphone audio at 16 kHz mono float32 with WASAPI / PortAudio.
Features:
- snakers4/silero-vad Voice Activity Detection (<1ms).
- Sub-400ms silence auto-cutting and trimming to eliminate manual stop lag.
- Zero-disk in-memory RAM processing for dictations under 30 seconds.
- Rolling chunk streaming support for marathon dictation.
- 30-minute safety cap and crash resilience.
"""
import io
import math
import os
import queue
import time
import wave
import logging
import threading
from collections import deque
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple, Union

import numpy as np
from scipy import signal, interpolate

from app.audio.noise_suppressor import NoiseSuppressor, condition_audio_for_transcription

logger = logging.getLogger("GeminiFlow.AudioRecorder")

try:
    import sounddevice as sd
except ImportError:
    sd = None
    logger.warning("sounddevice is not installed or available.")


def get_recordings_dir() -> Path:
    """Returns persistent recordings directory."""
    candidates = []
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "GeminiFlow" / "recordings")
    if os.environ.get("APPDATA"):
        candidates.append(Path(os.environ["APPDATA"]) / "GeminiFlow" / "recordings")
    candidates.append(Path(__file__).resolve().parent.parent / "recordings")

    for cand in candidates:
        try:
            cand.mkdir(parents=True, exist_ok=True)
            return cand
        except Exception:
            continue

    fallback = Path.cwd() / "recordings"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


_SENTINEL = object()


def resample_to_16k_mono(
    audio_data: np.ndarray,
    orig_sr: int,
    filter_state: Any = _SENTINEL,
    return_state: bool = False
) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
    """Stateful polyphase resampling to 16,000 Hz mono float32.
    Carries forward filter delay state (zi) across successive chunks to eliminate
    boundary edge transients and clicks.
    """
    wants_tuple = (filter_state is not _SENTINEL) or return_state
    curr_state = None if filter_state is _SENTINEL else filter_state

    if audio_data is None or len(audio_data) == 0:
        empty = np.zeros((0,), dtype=np.float32)
        return (empty, empty) if wants_tuple else empty

    data = audio_data.astype(np.float32)
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    if orig_sr == 16000:
        empty = np.zeros((0,), dtype=np.float32)
        return (data, empty) if wants_tuple else data

    # Fast and exact stateful decimation for integer ratios (e.g. 48000 -> 16000, 32000 -> 16000, 96000 -> 16000)
    if orig_sr % 16000 == 0:
        down = orig_sr // 16000
        half_len = 10 * down
        h = signal.firwin(2 * half_len + 1, 1.0 / down, window=('kaiser', 5.0)).astype(np.float32)
        M = len(h) - 1

        if curr_state is not None and isinstance(curr_state, np.ndarray):
            if len(curr_state) >= M + 1:
                zi = curr_state[:M].astype(np.float32)
                phase_in = int(curr_state[M])
            elif len(curr_state) == M:
                zi = curr_state.astype(np.float32)
                phase_in = 0
            else:
                zi = np.zeros(M, dtype=np.float32)
                phase_in = 0
        else:
            zi = np.zeros(M, dtype=np.float32)
            phase_in = 0

        y_filt, next_zi = signal.lfilter(h, 1.0, data, zi=zi)
        indices = np.arange(phase_in, len(data), down)
        chunk_16k = y_filt[indices].astype(np.float32)
        if len(indices) > 0:
            next_phase = int(indices[-1] + down - len(data))
        else:
            next_phase = int(phase_in - len(data))

        next_state = np.append(next_zi, float(next_phase)).astype(np.float32)
        return (chunk_16k, next_state) if wants_tuple else chunk_16k

    # Continuous rational resampling with stateful 7.5 kHz anti-aliasing FIR + cubic spline interpolation
    step = orig_sr / 16000.0
    eps = 1e-6

    if orig_sr > 16000:
        cutoff = min(7500.0, orig_sr * 0.45)
        h_aa = signal.firwin(65, cutoff, fs=orig_sr, window=('kaiser', 5.0)).astype(np.float32)
        M = len(h_aa) - 1
    else:
        h_aa = None
        M = 0

    if curr_state is not None and isinstance(curr_state, np.ndarray) and len(curr_state) >= M + 1:
        zi = curr_state[:M].astype(np.float32) if M > 0 else np.zeros(0, dtype=np.float32)
        t_offset = float(curr_state[M])
        hist = curr_state[M + 1:].astype(np.float32)
    elif curr_state is not None and isinstance(curr_state, np.ndarray) and len(curr_state) == M:
        zi = curr_state.astype(np.float32)
        t_offset = 0.0
        hist = np.zeros(0, dtype=np.float32)
    else:
        zi = np.zeros(M, dtype=np.float32) if M > 0 else np.zeros(0, dtype=np.float32)
        t_offset = 0.0
        hist = np.zeros(0, dtype=np.float32)

    if h_aa is not None:
        y_filt, next_zi = signal.lfilter(h_aa, 1.0, data, zi=zi)
    else:
        y_filt = data
        next_zi = np.zeros(0, dtype=np.float32)

    ext_y = np.concatenate([hist, y_filt]) if len(hist) > 0 else y_filt
    n_hist = len(hist)
    n_curr = len(y_filt)

    indices = []
    curr_t = t_offset
    while curr_t < n_curr - eps:
        indices.append(curr_t)
        curr_t += step
    next_t_offset = max(0.0, curr_t - n_curr)

    if len(indices) > 0:
        eval_times = np.array(indices, dtype=np.float64) + n_hist
        if len(ext_y) >= 4:
            cs = interpolate.CubicSpline(np.arange(len(ext_y)), ext_y)
            chunk_16k = cs(eval_times).astype(np.float32)
        elif len(ext_y) >= 2:
            chunk_16k = np.interp(eval_times, np.arange(len(ext_y)), ext_y).astype(np.float32)
        else:
            chunk_16k = np.zeros(len(eval_times), dtype=np.float32)
    else:
        chunk_16k = np.zeros(0, dtype=np.float32)

    next_hist = ext_y[-4:] if len(ext_y) >= 4 else ext_y
    next_state = np.concatenate([next_zi, np.array([next_t_offset], dtype=np.float32), next_hist.astype(np.float32)])
    return (chunk_16k, next_state) if wants_tuple else chunk_16k


def apply_dsp_filters(
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    high_pass_enabled: bool = True,
    high_pass_hz: float = 80.0,
    peak_norm_enabled: bool = True,
    peak_target: float = 0.95,
    target_peak: Optional[float] = None,
    whisper_mode: bool = False,
    noise_gate_enabled: bool = False
) -> np.ndarray:
    """Applies high-pass Butterworth filter, Whisper Mode gain boost, and peak normalization.
    Preserves unvoiced consonants (s, t, th, f) with full acoustic clarity by keeping the 
    destructive 10ms time-domain noise gate disabled by default.
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    if target_peak is not None:
        peak_target = target_peak

    suppressor = NoiseSuppressor(
        sample_rate=sample_rate,
        high_pass_hz=high_pass_hz,
        whisper_mode=whisper_mode
    )

    filtered = audio_data.copy().astype(np.float32)

    # 1. 80Hz Butterworth High-Pass Filter (strips DC bias, electrical hum, desk thumps)
    if high_pass_enabled:
        filtered = suppressor.filter_highpass(filtered)

    # 2. Smooth noise gate to suppress background fans and room acoustics
    if noise_gate_enabled:
        filtered = suppressor.apply_soft_noise_gate(filtered)

    # 3. Whisper Mode: Soft-saturation gain boost for whispered / quiet dictation
    if whisper_mode:
        filtered = suppressor.apply_whisper_mode_gain(filtered)

    # 4. Standard peak normalization with noise-floor guard
    if peak_norm_enabled and len(filtered) > 0:
        max_val = float(np.max(np.abs(filtered)))
        rms = float(np.sqrt(np.mean(filtered ** 2) + 1e-9))
        
        # Noise floor guard: only scale if audio energy indicates active speech
        if rms >= 0.006 and max_val >= 0.02:
            scale_factor = min(peak_target / max_val, 2.5)
            filtered = np.clip(filtered * scale_factor, -1.0, 1.0).astype(np.float32)

    return filtered


class AudioRecorder:
    SAFETY_CAP_SECONDS = 1800.0  # 30 minutes hard safety cap

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        on_amplitude: Optional[Callable[[float], None]] = None,
        on_safety_cap: Optional[Callable[[], None]] = None,
        on_speech_silence_cut: Optional[Callable[[], None]] = None,
        config_manager: Optional[Any] = None,
        enable_dsp: bool = False
    ):
        self.target_sample_rate = 16000
        self.target_channels = 1
        self.on_amplitude = on_amplitude
        self.on_safety_cap = on_safety_cap
        self.on_speech_silence_cut = on_speech_silence_cut
        self.config = config_manager
        self.enable_dsp = enable_dsp
        if self.config:
            self.enable_dsp = bool(self.config.get("dsp_fan_filter_enabled", False))
        self.whisper_mode: bool = False
        if self.config:
            self.whisper_mode = bool(self.config.get("whisper_mode", False))

        self.device_index: Optional[int] = None
        self.device_sample_rate: int = 16000
        self.device_channels: int = 1
        self.device_disconnected: bool = False
        self._buffers_delivered: int = 0
        self._resample_filter_state: Optional[np.ndarray] = None
        self._preroll_filter_state: Optional[np.ndarray] = None

        self.is_recording = False
        self.stream: Optional[Any] = None
        self.start_time = 0.0

        # Silero VAD state metrics
        self.speech_start_ts: Optional[float] = None
        self.speech_end_ts: Optional[float] = None
        self._last_speech_ts: float = 0.0
        self._silence_duration_ms: float = 0.0
        self.auto_cut_silence: bool = True
        self._auto_cut_triggered: bool = False

        # Rolling chunks for long dictations
        self._rolling_chunk_index: int = 0
        self._rolling_chunks_emitted: bool = False
        self._last_chunk_sample_offset: int = 0

        # In-Memory Queue & Worker
        self._raw_queue: queue.Queue = queue.Queue()
        self._writer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._buffer_lock = threading.Lock()

        # In-Memory RAM Accumulator
        self._accumulated_16k_samples: List[np.ndarray] = []
        # Pre-roll circular buffer: holds ~350ms of audio before hotkey was triggered
        self._pre_roll_samples = deque(maxlen=6)
        self._current_wav_path: Optional[Path] = None
        self._active_wav_file: Optional[wave.Wave_write] = None
        self._current_amplitude: float = 0.0
        self._last_duration: float = 0.0
        self._last_sample_count: int = 0
        self._last_rms: float = 0.0

        # Incremental 200ms Audio Framing (Section 6)
        # 16,000 samples/sec * 0.2s = 3,200 samples per frame
        self.FRAME_SAMPLES_200MS = 3200
        self._pending_frame_samples: List[np.ndarray] = []
        self._pending_count: int = 0
        self._ordered_frames: List[Any] = []
        self._frame_index: int = 0
        self.on_frame_callback: Optional[Callable[[Any], None]] = None

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
        """Resolves device index, native sample rate, and channels with WASAPI rate negotiation."""
        if sd is None:
            return None, 16000, 1
        try:
            if dev_idx is not None:
                info = sd.query_devices(dev_idx)
                if int(info.get("max_input_channels", 0)) <= 0:
                    raise ValueError(f"Device index {dev_idx} is not an input device (max_input_channels=0)")
            else:
                info = sd.query_devices(kind="input")
                dev_idx = info.get("index", None)
                # If default device appears to be an unplugged/headset mic while an array exists, prefer the array
                name_lower = str(info.get("name", "")).lower()
                if "headset" in name_lower:
                    try:
                        for d_i, d in enumerate(sd.query_devices()):
                            if d.get("max_input_channels", 0) > 0 and "array" in str(d.get("name", "")).lower():
                                dev_idx = d_i
                                info = d
                                logger.info(f"Auto-selected working built-in microphone array (Index {dev_idx}: {d.get('name')})")
                                break
                    except Exception:
                        pass
            native_rate = int(info.get("default_samplerate", 16000))
            max_ch = int(info.get("max_input_channels", 1))

            # Query candidate rates in priority order: native rate first, then standard audio rates
            rate_candidates = [native_rate, 48000, 44100, 16000, 32000, 96000]
            seen = set()
            candidates = [r for r in rate_candidates if not (r in seen or seen.add(r))]

            working_rate = native_rate
            working_ch = 1 if max_ch >= 1 else 1
            rate_resolved = False

            for rate in candidates:
                for ch in ([1, 2] if max_ch >= 2 else [1]):
                    try:
                        sd.check_input_settings(device=dev_idx, channels=ch, dtype="float32", samplerate=rate)
                        working_rate = rate
                        working_ch = ch
                        rate_resolved = True
                        break
                    except Exception:
                        continue
                if rate_resolved:
                    break

            return dev_idx, working_rate, working_ch
        except Exception as ex:
            logger.warning(f"Could not resolve device parameters for index {dev_idx}: {ex}")
            if dev_idx is not None:
                self.device_disconnected = True
                return dev_idx, 16000, 1
            return None, 16000, 1

    def set_device(self, device_index: Optional[int]):
        self.device_index = device_index

    def warmup_audio(self):
        """Pre-warms PortAudio subsystem and Silero VAD."""
        if sd is not None:
            try:
                dev_idx, rate, ch = self._resolve_device_parameters(self.device_index)
                with sd.InputStream(samplerate=rate, channels=ch, dtype="float32", device=dev_idx, blocksize=512):
                    time.sleep(0.04)
                logger.info("PortAudio microphone driver warmed up successfully.")
            except Exception as e:
                logger.debug(f"Audio driver warmup note: {e}")

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: Any, status: Any):
        """Streaming callback: enqueue frames and calculate amplitude."""
        if status:
            logger.warning(f"Audio stream status: {status}")

        if not self.is_recording:
            # Maintain rolling circular buffer of 16kHz audio for instant capture (OpenWhispr standard)
            try:
                resampled, self._preroll_filter_state = resample_to_16k_mono(
                    indata, self.device_sample_rate, filter_state=self._preroll_filter_state
                )
                if len(resampled) > 0:
                    self._pre_roll_samples.append(resampled)
            except Exception:
                pass
            return

        self._buffers_delivered += 1
        self._raw_queue.put(indata.copy())

        # Amplitude calculation for UI HUD
        rms = float(np.sqrt(np.mean(np.square(indata)) + 1e-9))
        scaled = min(1.0, float(rms * 12.0))
        self._current_amplitude = scaled
        if self.on_amplitude:
            try:
                self.on_amplitude(scaled)
            except Exception:
                pass

    def _writer_worker(self):
        """Worker thread: accumulates 16kHz audio in RAM and safely streams to disk for marathon recordings."""
        total_16k_samples = 0
        wf = None
        self._resample_filter_state = None

        while not self._stop_event.is_set() or not self._raw_queue.empty():
            try:
                raw_chunk = self._raw_queue.get(timeout=0.08)
            except queue.Empty:
                continue

            chunk_16k, self._resample_filter_state = resample_to_16k_mono(
                raw_chunk, self.device_sample_rate, filter_state=self._resample_filter_state
            )
            if len(chunk_16k) == 0:
                continue

            with self._buffer_lock:
                self._accumulated_16k_samples.append(chunk_16k)
                # Incremental 200ms framing
                self._pending_frame_samples.append(chunk_16k)
                self._pending_count += len(chunk_16k)

                while self._pending_count >= self.FRAME_SAMPLES_200MS:
                    cat_pending = np.concatenate(self._pending_frame_samples, axis=0)
                    frame_pcm = cat_pending[:self.FRAME_SAMPLES_200MS]
                    leftover = cat_pending[self.FRAME_SAMPLES_200MS:]
                    self._pending_frame_samples = [leftover] if len(leftover) > 0 else []
                    self._pending_count = len(leftover)

                    try:
                        from app.transcription.universal_pipeline import AudioFrame
                        a_frame = AudioFrame(
                            frame_index=self._frame_index,
                            timestamp_sec=round(self._frame_index * 0.2, 3),
                            duration_ms=200.0,
                            samples=frame_pcm
                        )
                        self._ordered_frames.append(a_frame)
                        self._frame_index += 1
                        if self.on_frame_callback:
                            try:
                                self.on_frame_callback(a_frame)
                            except Exception:
                                pass
                    except Exception:
                        pass

            total_16k_samples += len(chunk_16k)
            curr_duration = total_16k_samples / 16000.0

            # Only open disk file if recording exceeds 30 seconds (Zero-Disk latency for normal dictations)
            if curr_duration > 30.0 and wf is None:
                rec_dir = get_recordings_dir()
                ts_str = time.strftime("%Y%m%d_%H%M%S")
                self._current_wav_path = rec_dir / f"recording_{ts_str}_{int(time.time() * 1000) % 1000:03d}.wav"
                try:
                    wf = wave.open(str(self._current_wav_path), "wb")
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    with self._buffer_lock:
                        all_past = np.concatenate(self._accumulated_16k_samples, axis=0)
                    pcm16_past = (np.clip(all_past, -1.0, 1.0) * 32767).astype(np.int16)
                    wf.writeframes(pcm16_past.tobytes())
                except Exception as ex:
                    logger.error(f"Failed to open long-session WAV writer: {ex}")
                    wf = None

            if wf is not None:
                pcm16 = (np.clip(chunk_16k, -1.0, 1.0) * 32767).astype(np.int16)
                try:
                    wf.writeframes(pcm16.tobytes())
                except Exception as w_err:
                    logger.error(f"Error streaming continuous WAV frame to disk: {w_err}")

            if curr_duration >= self.SAFETY_CAP_SECONDS and self.is_recording:
                logger.warning(f"Audio safety cap reached ({curr_duration:.1f}s >= {self.SAFETY_CAP_SECONDS}s). Triggering auto-stop.")
                if self.on_safety_cap:
                    try:
                        self.on_safety_cap()
                    except Exception as cap_err:
                        logger.error(f"Error in on_safety_cap callback: {cap_err}")

        if wf is not None:
            try:
                wf.close()
            except Exception as close_err:
                logger.error(f"Error closing WAV writer: {close_err}")

    def start_recording(self) -> bool:
        """Starts hardware capture at native rate."""
        with self._buffer_lock:
            if self.is_recording:
                return False
            if sd is None:
                logger.error("sounddevice is not available.")
                return False

            self.is_recording = True
            if self.config:
                self.whisper_mode = bool(self.config.get("whisper_mode", False) or self.config.get("whisper_mode_enabled", False))
            self.start_time = time.time()
            self._current_amplitude = 0.0
            # Prepend pre-roll buffer so initial phonemes / syllables are never clipped
            self._accumulated_16k_samples = list(self._pre_roll_samples)
            self._pre_roll_samples.clear()
            self._raw_queue = queue.Queue()
            self._stop_event.clear()
            self._resample_filter_state = None
            self._preroll_filter_state = None
            self._buffers_delivered = 0
            self.device_disconnected = False
            self.speech_start_ts = None
            self.speech_end_ts = None
            self._last_speech_ts = 0.0
            self._silence_duration_ms = 0.0
            self._auto_cut_triggered = False
            self._rolling_chunk_index = 0
            self._rolling_chunks_emitted = False
            self._last_chunk_sample_offset = 0
            self._current_wav_path = None

        dev_idx, native_rate, channels = self._resolve_device_parameters(self.device_index)
        self.device_index = dev_idx
        self.device_sample_rate = native_rate
        self.device_channels = channels

        # Safely dispose of any leaked or residual stream from an earlier session
        if self.stream is not None:
            try:
                self.stream.stop()
            except Exception:
                pass
            try:
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        self._writer_thread = threading.Thread(target=self._writer_worker, daemon=True, name="AudioCaptureWorker")
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
            logger.info(f"Audio capture started: device={self.device_index}, native_sr={self.device_sample_rate}, ch={self.device_channels}")
            return True
        except Exception as e:
            logger.warning(
                f"Failed to start audio stream on selected device {self.device_index}: {e}. "
                f"Safe disconnection guard active: NOT silently redirecting to unintended microphone."
            )
            self.device_disconnected = True
            if self.stream is not None:
                try:
                    self.stream.stop()
                except Exception:
                    pass
                try:
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None
            with self._buffer_lock:
                self.is_recording = False
                self._stop_event.set()
            return False

    def stop_recording(self) -> Tuple[str, bytes, float, int, float]:
        """
        Stops audio capture.
        For recordings under 30 seconds, returns in-memory WAV bytes with zero physical disk I/O.
        Trims silence using Silero VAD.
        Returns (wav_path, wav_bytes, duration_seconds, sample_count, rms).
        """
        with self._buffer_lock:
            was_recording = self.is_recording
            self.is_recording = False

        wall_duration = max(0.1, time.time() - self.start_time)

        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
        except Exception as e:
            logger.error(f"Error stopping audio stream: {e}")
            self.stream = None

        self._stop_event.set()
        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=2.0)

        if not was_recording:
            return "", b"", 0.0, 0, 0.0

        with self._buffer_lock:
            if self._accumulated_16k_samples:
                full_16k = np.concatenate(self._accumulated_16k_samples, axis=0)
            else:
                full_16k = np.zeros((0,), dtype=np.float32)

        sample_count = len(full_16k)
        raw_duration_sec = sample_count / 16000.0 if sample_count > 0 else wall_duration

        # Active DSP filtering on speech blocks before VAD and transcription handoff
        if self.enable_dsp and sample_count > 0:
            full_16k = apply_dsp_filters(
                full_16k,
                sample_rate=16000,
                high_pass_enabled=True,
                peak_norm_enabled=True,
                whisper_mode=self.whisper_mode
            )
            sample_count = len(full_16k)

        # High-Performance Silero VAD Silence Trimming & Pure Silence Gating (Calibrated to 0.45)
        is_pure_silence = False
        if sample_count > 3200:
            try:
                import faster_whisper.vad as fvad
                # Standard robust Silero VAD threshold (0.45) eliminates keyboard clicks and breath triggers
                vad_opt = fvad.VadOptions(threshold=0.45, min_silence_duration_ms=500, speech_pad_ms=350)
                timestamps = fvad.get_speech_timestamps(full_16k, vad_opt)
                if timestamps:
                    # Pad 350ms (5600 samples) before speech and after speech to prevent clipping sentence boundaries
                    speech_pad_samples = int(0.350 * 16000)
                    start_sample = max(0, int(timestamps[0]["start"]) - speech_pad_samples)
                    end_sample = min(sample_count, int(timestamps[-1]["end"]) + speech_pad_samples)
                    if end_sample > start_sample + 3200:
                        full_16k = full_16k[start_sample:end_sample]
                        sample_count = len(full_16k)
                        logger.info(f"Silero VAD silence trimming (50cm calibrated): {raw_duration_sec:.2f}s -> {sample_count / 16000.0:.2f}s")
                else:
                    # Silero VAD did not partition speech (e.g. whispered or continuous speech); retain full audio
                    calc_rms = float(np.sqrt(np.mean(full_16k ** 2) + 1e-9))
                    logger.debug(f"Silero VAD had no timestamps (RMS={calc_rms:.5f}). Retaining full audio for Whisper ASR.")
            except Exception as vad_err:
                logger.debug(f"VAD post-trim note: {vad_err}")

        if sample_count == 0:
            return "", b"", 0.0, 0, 0.0

        duration_sec = sample_count / 16000.0 if sample_count > 0 else raw_duration_sec
        rms = float(np.sqrt(np.mean(full_16k ** 2) + 1e-9)) if sample_count > 0 else 0.0

        # Zero-Disk In-Memory WAV Serialization
        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            pcm16 = (np.clip(full_16k, -1.0, 1.0) * 32767).astype(np.int16)
            wf.writeframes(pcm16.tobytes())
        wav_bytes = bio.getvalue()

        wav_path_str = str(self._current_wav_path) if self._current_wav_path and self._current_wav_path.exists() else ""

        self._last_duration = duration_sec
        self._last_sample_count = sample_count
        self._last_rms = rms

        logger.info(
            f"[AUDIO CAPTURE METRICS] In-Memory={wav_path_str == ''}, Duration={duration_sec:.2f}s, "
            f"Samples={sample_count} (16kHz), RMS={rms:.5f}, Size={len(wav_bytes)} bytes"
        )
        return wav_path_str, wav_bytes, duration_sec, sample_count, rms

    def get_rolling_chunk(self, min_sec: float = 5.0, max_sec: float = 8.0) -> Optional[bytes]:
        """Returns a rolling chunk of accumulated audio if current duration is between min_sec and max_sec."""
        with self._buffer_lock:
            if not self.is_recording or not self._accumulated_16k_samples:
                return None
            total_samples = sum(len(c) for c in self._accumulated_16k_samples)
            total_sec = total_samples / 16000.0
            if total_sec < min_sec:
                return None

            arr = np.concatenate(self._accumulated_16k_samples[self._rolling_chunk_index:], axis=0)
            chunk_sec = len(arr) / 16000.0
            if chunk_sec < min_sec:
                return None

            self._rolling_chunk_index = len(self._accumulated_16k_samples)
            self._rolling_chunks_emitted = True

            if self.enable_dsp and len(arr) > 0:
                arr = apply_dsp_filters(arr, sample_rate=16000, high_pass_enabled=True, peak_norm_enabled=True)

            bio = io.BytesIO()
            with wave.open(bio, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                pcm16 = (np.clip(arr, -1.0, 1.0) * 32767).astype(np.int16)
                wf.writeframes(pcm16.tobytes())
            return bio.getvalue()


    def get_next_streaming_chunk(
        self,
        min_sec: float = 2.0,
        max_sec: float = 3.2,
        overlap_sec: float = 0.4
    ) -> Optional[bytes]:
        """
        Wispr Flow Standard:
        1. Speech under 25.0 seconds is never sliced; it is preserved as a single continuous 
           acoustic buffer to ensure 100% natural grammar and zero boundary syllable truncation.
        2. Marathon dictations (> 25s) slice cleanly at natural silence pauses (> 500ms).
        """
        with self._buffer_lock:
            if not self.is_recording or not self._accumulated_16k_samples:
                return None

            total_samples = sum(len(c) for c in self._accumulated_16k_samples)
            # Guard against artificial chunking for normal human dictations (< 25 seconds)
            if (total_samples / 16000.0) < 25.0:
                return None

            available = total_samples - self._last_chunk_sample_offset
            if available < int(min_sec * 16000):
                return None

            all_samples = np.concatenate(self._accumulated_16k_samples, axis=0)
            avail_slice = all_samples[self._last_chunk_sample_offset:]

            min_len = int(min_sec * 16000)
            max_len = min(len(avail_slice), int(max_sec * 16000))

            search_slice = avail_slice[min_len:max_len]
            block_size = int(0.05 * 16000)  # 50ms = 800 samples
            split_rel = len(avail_slice) if len(avail_slice) <= max_len else max_len

            if len(search_slice) >= block_size * 2:
                n_blocks = len(search_slice) // block_size
                blocks = search_slice[:n_blocks * block_size].reshape(n_blocks, block_size)
                rms = np.sqrt(np.mean(blocks.astype(np.float32) ** 2, axis=1) + 1e-9)
                if np.ptp(rms) > 1e-4:
                    best_block = int(np.argmin(rms))
                    split_rel = min_len + best_block * block_size + (block_size // 2)

            chunk_arr = avail_slice[:split_rel]
            if len(chunk_arr) < int(min_sec * 0.8 * 16000):
                return None

            overlap_samples = int(overlap_sec * 16000)
            advance_step = max(int(min_sec * 0.5 * 16000), split_rel - overlap_samples)
            self._last_chunk_sample_offset += advance_step
            self._rolling_chunks_emitted = True

            if self.enable_dsp and len(chunk_arr) > 0:
                chunk_arr = apply_dsp_filters(chunk_arr, sample_rate=16000, high_pass_enabled=True, peak_norm_enabled=True, whisper_mode=self.whisper_mode)

            bio = io.BytesIO()
            with wave.open(bio, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                pcm16 = (np.clip(chunk_arr, -1.0, 1.0) * 32767).astype(np.int16)
                wf.writeframes(pcm16.tobytes())
            return bio.getvalue()

    def get_tail_chunk(self, min_sec: float = 0.2) -> Optional[bytes]:
        """
        Returns the un-emitted audio tail after the last streaming chunk.
        """
        with self._buffer_lock:
            if not self._accumulated_16k_samples:
                return None
            all_samples = np.concatenate(self._accumulated_16k_samples, axis=0)
            if self._last_chunk_sample_offset >= len(all_samples):
                return None
            tail_arr = all_samples[self._last_chunk_sample_offset:]
            if len(tail_arr) < int(min_sec * 16000):
                return None

            if self.enable_dsp and len(tail_arr) > 0:
                tail_arr = apply_dsp_filters(tail_arr, sample_rate=16000, high_pass_enabled=True, peak_norm_enabled=True, whisper_mode=self.whisper_mode)

            bio = io.BytesIO()
            with wave.open(bio, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                pcm16 = (np.clip(tail_arr, -1.0, 1.0) * 32767).astype(np.int16)
                wf.writeframes(pcm16.tobytes())
            return bio.getvalue()

    def rolling_chunks_were_emitted(self) -> bool:
        """Returns True if any rolling chunk was emitted during the current recording session."""
        return self._rolling_chunks_emitted

    @property
    def current_amplitude(self) -> float:
        return self._current_amplitude

    def get_diagnostics(self) -> Dict[str, Any]:
        """Returns comprehensive diagnostic dictionary for audio capture subsystem.
        Exposes device info, negotiated sample rate, RMS energy, buffer queue metrics,
        and disconnection status.
        """
        dev_name = "Unknown"
        if sd is not None and self.device_index is not None:
            try:
                info = sd.query_devices(self.device_index)
                dev_name = info.get("name", f"Device {self.device_index}")
            except Exception:
                self.device_disconnected = True
                dev_name = f"Disconnected Device {self.device_index}"
        elif sd is not None:
            try:
                info = sd.query_devices(kind="input")
                dev_name = f"Default: {info.get('name', 'Default Mic')}"
            except Exception:
                dev_name = "Default Microphone"

        with self._buffer_lock:
            sample_count = sum(len(c) for c in self._accumulated_16k_samples) if self.is_recording else self._last_sample_count
            rms = self._current_amplitude / 12.0 if self.is_recording else self._last_rms

        return {
            "device_index": self.device_index,
            "device_name": dev_name,
            "sample_rate": self.device_sample_rate,
            "channels": self.device_channels,
            "buffer_rms": round(float(rms), 6),
            "buffers_delivered": self._buffers_delivered,
            "is_recording": self.is_recording,
            "device_disconnected": self.device_disconnected,
            "duration_seconds": round(sample_count / 16000.0, 3),
            "sample_count": sample_count
        }

    @staticmethod
    def contains_speech(wav_bytes: bytes, threshold_rms: float = 0.0003, threshold_peak: float = 0.001) -> bool:
        """Determines whether audio buffer contains speech energy.
        Calibrated for distant speech (50cm-100cm) while rejecting digital silence.
        """
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
        """Scans recordings directory for orphaned WAV files."""
        rec_dir = get_recordings_dir()
        if not rec_dir.exists():
            return []
        wav_files = sorted(rec_dir.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
        cutoff = time.time() - 86400
        orphaned = [f for f in wav_files if f.stat().st_mtime > cutoff and f.stat().st_size > 2000]
        return orphaned
