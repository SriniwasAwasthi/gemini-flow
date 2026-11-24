"""
Offline Speech Recognition Engine for Gemini Flow.
Leverages OpenAI Whisper (via faster-whisper on CPU with int8 quantization) for world-class,
near-zero latency, accurate on-device offline dictation without any internet connection.
Gracefully falls back to whisper.cpp, Windows SAPI, and SpeechRecognition if needed.
"""
import os
os.environ.setdefault('OMP_WAIT_POLICY', 'PASSIVE')
os.environ.setdefault('KMP_BLOCKTIME', '0')
import io
import time
import wave
import logging
import threading
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Optional, Any, Dict, Union

import numpy as np

logger = logging.getLogger("GeminiFlow.OfflineSpeech")


class OfflineSpeechEngine:
    _whisper_instance: Optional[Any] = None
    _whisper_models: Dict[str, Any] = {}
    _model_lock = threading.Lock()
    _active_model_name: str = "tiny.en"
    _is_warming_up: bool = False

    @classmethod
    def get_whisper_model(cls, model_size: str = "tiny.en") -> Optional[Any]:
        """
        Thread-safe singleton accessor for faster-whisper WhisperModel.
        Loads the model once and retains it in memory for instant subsequent transcriptions.
        """
        if model_size in cls._whisper_models:
            return cls._whisper_models[model_size]

        with cls._model_lock:
            if model_size in cls._whisper_models:
                return cls._whisper_models[model_size]

            try:
                import ctranslate2
                import ctypes
                from faster_whisper import WhisperModel
                has_cuda = False
                if ctranslate2.get_cuda_device_count() > 0:
                    try:
                        ctypes.CDLL("cublas64_12.dll")
                        has_cuda = True
                    except Exception:
                        has_cuda = False
                device = "cuda" if has_cuda else "cpu"
                compute_type = "float16" if has_cuda else "int8"
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                bundled_path = os.path.join(project_root, "models", model_size)
                model_target = bundled_path if (os.path.exists(bundled_path) and os.path.exists(os.path.join(bundled_path, "model.bin"))) else model_size

                logger.info(f"Initializing WhisperModel('{model_target}', device='{device}', compute_type='{compute_type}')...")
                t0 = time.time()
                cpu_count = os.cpu_count() or 4
                optimal_threads = min(4, cpu_count)
                optimal_workers = 1
                try:
                    instance = WhisperModel(
                        model_target,
                        device=device,
                        compute_type=compute_type,
                        cpu_threads=optimal_threads,
                        num_workers=optimal_workers,
                        local_files_only=True
                    )
                except Exception:
                    try:
                        instance = WhisperModel(
                            model_target,
                            device=device,
                            compute_type=compute_type,
                            cpu_threads=optimal_threads,
                            num_workers=optimal_workers
                        )
                    except Exception as cuda_err:
                        if device == "cuda":
                            logger.warning(f"CUDA initialization failed ({cuda_err}), falling back to CPU int8...")
                            instance = WhisperModel(
                                model_target,
                                device="cpu",
                                compute_type="int8",
                                cpu_threads=min(4, cpu_count),
                                num_workers=1
                            )
                        else:
                            raise cuda_err
                cls._whisper_models[model_size] = instance
                cls._whisper_instance = instance
                cls._active_model_name = model_size
                try:
                    dummy = np.zeros(16000, dtype=np.float32)
                    _ = list(instance.transcribe(dummy, beam_size=1, word_timestamps=False)[0])
                except Exception as prime_err:
                    if device == "cuda":
                        logger.warning(f"CUDA priming failed ({prime_err}), falling back to CPU int8...")
                        instance = WhisperModel(
                            model_target,
                            device="cpu",
                            compute_type="int8",
                            cpu_threads=min(4, cpu_count),
                            num_workers=1
                        )
                        dummy = np.zeros(16000, dtype=np.float32)
                        _ = list(instance.transcribe(dummy, beam_size=1, word_timestamps=False)[0])
                        cls._whisper_models[model_size] = instance
                        cls._whisper_instance = instance
                logger.info(f"Local Whisper model '{model_size}' loaded and primed in {time.time() - t0:.2f}s ({optimal_threads} threads, {optimal_workers} workers).")
                return instance
            except Exception as e:
                logger.warning(f"Could not load Whisper model '{model_size}': {e}")
                for fallback_size in ("base.en", "tiny.en"):
                    if model_size != fallback_size:
                        try:
                            from faster_whisper import WhisperModel
                            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            bundled_fallback = os.path.join(project_root, "models", fallback_size)
                            target = bundled_fallback if os.path.exists(bundled_fallback) else fallback_size
                            logger.info(f"Attempting fallback to '{target}' Whisper model...")
                            fallback_inst = WhisperModel(
                                target,
                                device="cpu",
                                compute_type="int8",
                                cpu_threads=4,
                                num_workers=1
                            )
                            cls._whisper_models[fallback_size] = fallback_inst
                            cls._whisper_instance = fallback_inst
                            cls._active_model_name = fallback_size
                            logger.info(f"Local Whisper fallback model '{fallback_size}' initialized.")
                            return fallback_inst
                        except Exception as e2:
                            logger.error(f"Fallback to '{fallback_size}' also failed: {e2}")

        return None

    @classmethod
    def warmup_whisper(cls, model_size: str = "tiny.en", blocking: bool = False):
        """
        Warms up the local Whisper model in memory so that the first
        offline user transcription executes instantaneously without cold-start latency.
        If blocking=True, waits until the model and CPU kernels are initialized.
        """
        if model_size in cls._whisper_models:
            return

        def _do_warmup():
            cls._is_warming_up = True
            try:
                m = cls.get_whisper_model(model_size)
                if m is not None:
                    try:
                        dummy = np.zeros(16000, dtype=np.float32)
                        _ = list(m.transcribe(dummy, beam_size=1, word_timestamps=False)[0])
                    except Exception:
                        pass
            except Exception as ex:
                logger.debug(f"Offline Whisper warmup notice: {ex}")
            finally:
                cls._is_warming_up = False

        if blocking:
            _do_warmup()
        else:
            if cls._is_warming_up:
                return
            warmup_thread = threading.Thread(target=_do_warmup, daemon=True, name="WhisperOfflineWarmup")
            warmup_thread.start()

    @classmethod
    def transcribe_wav(cls, audio_data: Union[bytes, np.ndarray], initial_prompt: Optional[str] = None, language: Optional[str] = None) -> Tuple[bool, str]:
        """
        Transcribes audio (WAV bytes or 16kHz float32 numpy array) in offline mode.
        Tries Faster-Whisper first, then whisper.cpp CLI, then Windows SAPI, then speech_recognition.
        Returns (success: bool, transcribed_text_or_error: str).
        """
        if audio_data is None:
            return False, "Audio data is None."
        if isinstance(audio_data, (str, Path)) and os.path.exists(str(audio_data)):
            try:
                with open(str(audio_data), "rb") as f:
                    audio_data = f.read()
            except Exception as e:
                return False, f"Could not read audio file: {e}"
        if isinstance(audio_data, (bytes, bytearray)) and len(audio_data) < 800:
            return False, "Audio is too short or empty."
        if isinstance(audio_data, np.ndarray) and len(audio_data) < 1600:
            return False, "Audio is too short or empty."

        # 1. Primary: High-accuracy OpenAI Whisper (faster-whisper)
        try:
            success, text = cls._transcribe_with_whisper(audio_data, initial_prompt=initial_prompt, language=language)
            if success:
                logger.info(f"Local Faster-Whisper offline recognition succeeded ({len(text)} chars): {text[:60]}...")
                return True, text
        except Exception as we:
            logger.warning(f"Whisper offline transcription exception: {we}")

        # 2. Secondary: whisper.cpp CLI Fallback
        try:
            wav_bytes_conv = audio_data if isinstance(audio_data, (bytes, bytearray)) else cls._to_wav_bytes(audio_data)
            success, text = cls._transcribe_with_whisper_cpp(wav_bytes_conv)
            if success and text.strip():
                logger.info(f"whisper.cpp CLI fallback succeeded: {text[:60]}...")
                return True, text.strip()
        except Exception as we_cpp:
            logger.debug(f"whisper.cpp fallback exception: {we_cpp}")

        # 3. Tertiary: Windows SAPI Dictation Grammar Fallback
        try:
            wav_bytes_conv = audio_data if isinstance(audio_data, (bytes, bytearray)) else cls._to_wav_bytes(audio_data)
            success, text = cls._transcribe_with_sapi(wav_bytes_conv)
            if success and text.strip():
                logger.info(f"Offline SAPI recognition succeeded: {text[:60]}...")
                return True, text.strip()
        except Exception as se:
            logger.debug(f"SAPI offline transcription exception: {se}")

        # 4. Quaternary: PocketSphinx / SpeechRecognition Fallback
        try:
            wav_bytes_conv = audio_data if isinstance(audio_data, (bytes, bytearray)) else cls._to_wav_bytes(audio_data)
            success, text = cls._transcribe_with_sr(wav_bytes_conv)
            if success and text.strip():
                logger.info(f"Offline speech_recognition succeeded: {text[:60]}...")
                return True, text.strip()
        except Exception as srf:
            logger.debug(f"speech_recognition offline fallback note: {srf}")

        return False, "Local offline speech recognition could not decode audio. Please check microphone."

    @staticmethod
    def _to_wav_bytes(samples: np.ndarray, sample_rate: int = 16000) -> bytes:
        """Converts float32 16kHz numpy array to WAV bytes."""
        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            pcm16 = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
            wf.writeframes(pcm16.tobytes())
        return bio.getvalue()

    @classmethod
    def _transcribe_with_whisper(cls, audio_data: Union[bytes, np.ndarray, str, Path], initial_prompt: Optional[str] = None, language: Optional[str] = None) -> Tuple[bool, str]:
        if isinstance(audio_data, (str, Path)) and os.path.exists(str(audio_data)):
            try:
                with open(str(audio_data), "rb") as f:
                    audio_data = f.read()
            except Exception as e:
                return False, f"Could not read audio file: {e}"

        is_non_english = bool(language and language.lower() not in ("en", "english"))
        target_model_size = cls._active_model_name if cls._active_model_name in cls._whisper_models else ("tiny" if is_non_english else "tiny.en")
        model = cls.get_whisper_model(model_size=target_model_size)
        if model is None:
            model = cls.get_whisper_model(model_size="tiny.en")
        if model is None:
            model = cls.get_whisper_model(model_size="base.en")
        if model is None:
            return False, "Whisper model unavailable"

        prompt = initial_prompt or ""
        try:
            from app.vocabulary.vocab_engine import VocabEngine
            vocab_prompt = VocabEngine.get_instance().get_whisper_prompt()
            if vocab_prompt and not prompt:
                prompt = vocab_prompt
        except Exception:
            pass

        is_multilingual = getattr(getattr(model, "model", None), "is_multilingual", False)
        kwargs: dict = {
            "beam_size": 1,
            "best_of": 1,
            "temperature": 0.0,
            "condition_on_previous_text": False,
            "without_timestamps": True,
            "vad_filter": False,
            "initial_prompt": prompt
        }
        if is_multilingual and language:
            kwargs["language"] = language

        # Format input directly into float32 16kHz array for zero-copy CTranslate2 execution
        if isinstance(audio_data, np.ndarray):
            audio_input = audio_data.astype(np.float32)
        else:
            audio_input = None
            try:
                with wave.open(io.BytesIO(audio_data), "rb") as wf:
                    fr = wf.getframerate()
                    nc = wf.getnchannels()
                    sw = wf.getsampwidth()
                    pcm_data = wf.readframes(wf.getnframes())
                    if sw == 2 and pcm_data:
                        raw_arr = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
                        if nc > 1:
                            raw_arr = raw_arr.reshape(-1, nc).mean(axis=1)
                        if fr != 16000 and fr > 0:
                            new_len = int(len(raw_arr) * 16000 / fr)
                            audio_input = np.interp(
                                np.linspace(0, len(raw_arr), new_len, endpoint=False),
                                np.arange(len(raw_arr)),
                                raw_arr
                            ).astype(np.float32)
                        else:
                            audio_input = raw_arr
            except Exception:
                audio_input = None

            if audio_input is None:
                audio_input = io.BytesIO(audio_data)

        t0 = time.time()
        segments, info = model.transcribe(audio_input, **kwargs)

        phrases = [seg.text.strip() for seg in segments if seg.text.strip()]
        final_text = " ".join(phrases).strip()
        logger.debug(f"Whisper transcription took {time.time() - t0:.2f}s, detected lang: {getattr(info, 'language', 'en')}")

        if final_text:
            return True, final_text
        return True, ""  # Clean silence (no speech detected)

    @classmethod
    def _transcribe_with_whisper_cpp(cls, wav_bytes: bytes) -> Tuple[bool, str]:
        """Invokes standalone whisper-cli.exe for ultra-lightweight C++ inference fallback."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cli_candidates = [
            os.path.join(project_root, "runtime", "whisper.cpp", "whisper-cli.exe"),
            os.path.join(project_root, "runtime", "whisper.cpp", "main.exe"),
            "whisper-cli.exe"
        ]
        exe_path = None
        for cand in cli_candidates:
            if os.path.exists(cand):
                exe_path = cand
                break
        if not exe_path:
            return False, "whisper.cpp binary not found"

        model_candidates = [
            os.path.join(project_root, "models", "whisper.cpp", "ggml-small.bin"),
            os.path.join(project_root, "models", "whisper.cpp", "ggml-base.bin"),
            os.path.join(project_root, "models", "ggml-small.bin"),
            os.path.join(project_root, "models", "ggml-base.bin"),
        ]
        model_path = None
        for m_cand in model_candidates:
            if os.path.exists(m_cand):
                model_path = m_cand
                break
        if not model_path:
            return False, "whisper.cpp ggml model not found"

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            tf.write(wav_bytes)
            tmp_wav = tf.name

        try:
            cmd = [exe_path, "-m", model_path, "-f", tmp_wav, "--output-txt", "-nt"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            txt_file = tmp_wav + ".txt"
            if os.path.exists(txt_file):
                with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read().strip()
                try:
                    os.unlink(txt_file)
                except Exception:
                    pass
                if txt:
                    return True, txt
            if res.stdout and res.stdout.strip():
                return True, res.stdout.strip()
            return False, "whisper.cpp produced no output"
        except Exception as e:
            return False, str(e)
        finally:
            try:
                if os.path.exists(tmp_wav):
                    os.unlink(tmp_wav)
            except Exception:
                pass

    @classmethod
    def _transcribe_with_sapi(cls, wav_bytes: bytes) -> Tuple[bool, str]:
        import tempfile
        tmp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp_file.name
        try:
            tmp_file.write(wav_bytes)
            tmp_file.flush()
            tmp_file.close()

            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            try:
                recognized_phrases = []

                class RecoEvents:
                    def OnRecognition(self, StreamNumber, StreamPosition, RecognitionType, Result):
                        try:
                            res = win32com.client.Dispatch(Result)
                            t = res.PhraseInfo.GetText()
                            if t:
                                recognized_phrases.append(t)
                        except Exception as ex:
                            logger.debug(f"RecoEvents OnRecognition extract error: {ex}")

                    def OnFalseRecognition(self, StreamNumber, StreamPosition, Result):
                        pass

                recognizer = win32com.client.Dispatch("SAPI.SpInprocRecognizer")
                context = recognizer.CreateRecoContext()
                _handler = win32com.client.WithEvents(context, RecoEvents)
                grammar = context.CreateGrammar()
                grammar.DictationSetState(1)

                stream = win32com.client.Dispatch("SAPI.SpFileStream")
                stream.Open(tmp_path, 0)
                recognizer.AudioInputStream = stream

                start_t = time.time()
                dur = max(0.5, len(wav_bytes) / 32000.0)
                timeout_limit = min(10.0, dur * 1.5 + 1.0)

                while time.time() - start_t < timeout_limit:
                    pythoncom.PumpWaitingMessages()
                    time.sleep(0.04)

                try:
                    stream.Close()
                except Exception:
                    pass

                final_text = " ".join(recognized_phrases).strip()
                if final_text:
                    return True, final_text
                return False, "No speech detected by offline SAPI engine."
            finally:
                pythoncom.CoUninitialize()
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass

    @classmethod
    def _transcribe_with_sr(cls, wav_bytes: bytes) -> Tuple[bool, str]:
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
                audio_data = r.record(source)
            if hasattr(r, "recognize_sphinx"):
                try:
                    text = r.recognize_sphinx(audio_data)
                    if text:
                        return True, text
                except Exception:
                    pass
            return False, "Offline SR engine not available."
        except Exception as e:
            return False, str(e)
