"""
Offline Speech Recognition Engine for Gemini Flow.
Leverages OpenAI Whisper (via faster-whisper on CPU with int8 quantization) for world-class,
near-zero latency, accurate on-device offline dictation without any internet connection.
Gracefully falls back to Windows SAPI / SpeechRecognition if dependencies are missing.
"""
import os
os.environ.setdefault('OMP_WAIT_POLICY', 'PASSIVE')
os.environ.setdefault('KMP_BLOCKTIME', '0')
import io
import time
import logging
import threading
from typing import Tuple, Optional, Any, Dict

logger = logging.getLogger("GeminiFlow.OfflineSpeech")


class OfflineSpeechEngine:
    _whisper_instance: Optional[Any] = None
    _whisper_models: Dict[str, Any] = {}
    _model_lock = threading.Lock()
    _active_model_name: str = "base.en"
    _is_warming_up: bool = False

    @classmethod
    def get_whisper_model(cls, model_size: str = "base.en") -> Optional[Any]:
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
                optimal_threads = 1 if has_cuda else min(4, cpu_count)
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
                    import numpy as np
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
                        import numpy as np
                        dummy = np.zeros(16000, dtype=np.float32)
                        _ = list(instance.transcribe(dummy, beam_size=1, word_timestamps=False)[0])
                        cls._whisper_models[model_size] = instance
                        cls._whisper_instance = instance
                logger.info(f"Local Whisper model '{model_size}' loaded and primed in {time.time() - t0:.2f}s ({optimal_threads} threads, {optimal_workers} workers).")
                return instance
            except Exception as e:
                logger.warning(f"Could not load Whisper model '{model_size}': {e}")
                if model_size != "tiny.en":
                    try:
                        from faster_whisper import WhisperModel
                        logger.info("Attempting fallback to 'tiny.en' Whisper model...")
                        cls._whisper_instance = WhisperModel(
                            "tiny.en",
                            device="cpu",
                            compute_type="int8",
                            cpu_threads=4,
                            num_workers=2,
                            local_files_only=True
                        )
                        cls._active_model_name = "tiny.en"
                        logger.info("Local Whisper fallback model 'tiny.en' initialized.")
                        return cls._whisper_instance
                    except Exception as e2:
                        logger.error(f"Fallback to 'tiny.en' also failed: {e2}")

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
                        import numpy as np
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
    def transcribe_wav(cls, wav_bytes: bytes, initial_prompt: Optional[str] = None, language: Optional[str] = None) -> Tuple[bool, str]:
        """
        Transcribes WAV audio bytes in offline mode.
        Tries Whisper AI first. Falls back to Windows SAPI and SpeechRecognition if needed.
        Returns (success: bool, transcribed_text_or_error: str).
        """
        if not wav_bytes or len(wav_bytes) < 800:
            return False, "Audio is too short or empty."

        # 1. Primary: High-accuracy OpenAI Whisper (faster-whisper)
        try:
            success, text = cls._transcribe_with_whisper(wav_bytes, initial_prompt=initial_prompt, language=language)
            if success:
                logger.info(f"Local Whisper AI offline recognition succeeded ({len(text)} chars): {text[:60]}...")
                return True, text
        except Exception as we:
            logger.warning(f"Whisper offline transcription exception: {we}")

        # 2. Secondary: Windows SAPI Dictation Grammar Fallback
        try:
            success, text = cls._transcribe_with_sapi(wav_bytes)
            if success and text.strip():
                logger.info(f"Offline SAPI recognition succeeded: {text[:60]}...")
                return True, text.strip()
        except Exception as se:
            logger.debug(f"SAPI offline transcription exception: {se}")

        # 3. Tertiary: PocketSphinx / SpeechRecognition Fallback
        try:
            success, text = cls._transcribe_with_sr(wav_bytes)
            if success and text.strip():
                logger.info(f"Offline speech_recognition succeeded: {text[:60]}...")
                return True, text.strip()
        except Exception as srf:
            logger.debug(f"speech_recognition offline fallback note: {srf}")

        return False, "Local offline speech recognition could not decode audio. Please check microphone."

    @classmethod
    def _split_into_chunks(cls, wav_bytes: bytes, target_sec: float = 24.0, overlap_sec: float = 0.3) -> list[bytes]:
        import wave
        import numpy as np
        try:
            bio = io.BytesIO(wav_bytes)
            with wave.open(bio, "rb") as wf:
                nc = wf.getnchannels()
                sw = wf.getsampwidth()
                fr = wf.getframerate()
                pcm = wf.readframes(wf.getnframes())

            samples = np.frombuffer(pcm, dtype=np.int16 if sw == 2 else np.int8)
            total_sec = len(samples) / (fr * nc) if fr > 0 else 0
            if total_sec <= target_sec * 1.25 or total_sec <= 0:
                return [wav_bytes]

            chunk_len = int(target_sec * fr * nc)
            overlap_len = int(overlap_sec * fr * nc)
            chunks = []
            start = 0
            while start < len(samples):
                end = min(len(samples), start + chunk_len)
                slice_data = samples[start:end].tobytes()
                out_bio = io.BytesIO()
                with wave.open(out_bio, "wb") as out_wf:
                    out_wf.setnchannels(nc)
                    out_wf.setsampwidth(sw)
                    out_wf.setframerate(fr)
                    out_wf.writeframes(slice_data)
                chunks.append(out_bio.getvalue())
                if end >= len(samples):
                    break
                start = end - overlap_len
            return chunks if chunks else [wav_bytes]
        except Exception as ex:
            logger.debug(f"Audio chunk split note: {ex}")
            return [wav_bytes]

    @classmethod
    def _transcribe_with_whisper(cls, wav_bytes: bytes, initial_prompt: Optional[str] = None, language: Optional[str] = None) -> Tuple[bool, str]:
        is_non_english = bool(language and language.lower() not in ("en", "english"))
        target_model_size = "base" if is_non_english else "base.en"
        model = cls.get_whisper_model(model_size=target_model_size)
        if model is None:
            # Fallback to default model
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
            "condition_on_previous_text": False,
            "temperature": 0.0,
            "repetition_penalty": 1.2,
            "no_repeat_ngram_size": 3,
            "vad_filter": True,
            "vad_parameters": dict(threshold=0.25, min_silence_duration_ms=300, speech_pad_ms=200),
            "initial_prompt": prompt
        }
        if is_multilingual and language:
            kwargs["language"] = language

        # Estimate duration in seconds
        approx_sec = len(wav_bytes) / 32000.0

        # Direct sequential C++ decoding (handles any length seamlessly with zero thread contention)

        # Standard direct high-accuracy transcription (<= 28s)
        # Fast path: decode 16-bit PCM into float32 numpy array & ensure 16kHz for sub-second Whisper decoding
        audio_input = None
        try:
            import numpy as np
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
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
            audio_input = io.BytesIO(wav_bytes)

        t0 = time.time()
        segments, info = model.transcribe(audio_input, **kwargs)

        phrases = [seg.text.strip() for seg in segments if seg.text.strip()]
        final_text = " ".join(phrases).strip()
        logger.debug(f"Whisper transcription took {time.time() - t0:.2f}s, detected lang: {getattr(info, 'language', 'en')}")

        if final_text:
            return True, final_text
        return True, ""  # Clean silence (no speech detected)

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

                # 0 = SSFMOpenForRead
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
