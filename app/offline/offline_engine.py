"""
Offline Speech Recognition Engine for Gemini Flow.
Leverages OpenAI Whisper (via faster-whisper on CPU with int8 quantization) for world-class,
near-zero latency, accurate on-device offline dictation without any internet connection.
Gracefully falls back to Windows SAPI / SpeechRecognition if dependencies are missing.
"""
import os
import io
import time
import logging
import threading
from typing import Tuple, Optional, Any

logger = logging.getLogger("GeminiFlow.OfflineSpeech")


class OfflineSpeechEngine:
    _whisper_instance: Optional[Any] = None
    _model_lock = threading.Lock()
    _active_model_name: str = "base.en"
    _is_warming_up: bool = False

    @classmethod
    def get_whisper_model(cls, model_size: str = "base.en") -> Optional[Any]:
        """
        Thread-safe singleton accessor for faster-whisper WhisperModel.
        Loads the model once and retains it in memory for instant subsequent transcriptions.
        """
        if cls._whisper_instance is not None:
            return cls._whisper_instance

        with cls._model_lock:
            if cls._whisper_instance is not None:
                return cls._whisper_instance

            try:
                from faster_whisper import WhisperModel
                logger.info(f"Initializing local WhisperModel('{model_size}', device='cpu', compute_type='int8')...")
                t0 = time.time()
                cpu_count = os.cpu_count() or 4
                optimal_threads = max(4, min(8, cpu_count - 2))
                optimal_workers = max(2, min(4, cpu_count // 3))
                # Try loading with local_files_only first for zero-network environments
                try:
                    cls._whisper_instance = WhisperModel(
                        model_size,
                        device="cpu",
                        compute_type="int8",
                        cpu_threads=optimal_threads,
                        num_workers=optimal_workers,
                        local_files_only=True
                    )
                except Exception:
                    # Fallback to standard load (downloads if needed)
                    cls._whisper_instance = WhisperModel(
                        model_size,
                        device="cpu",
                        compute_type="int8",
                        cpu_threads=optimal_threads,
                        num_workers=optimal_workers
                    )
                cls._active_model_name = model_size
                logger.info(f"Local Whisper model '{model_size}' loaded in {time.time() - t0:.2f}s ({optimal_threads} threads, {optimal_workers} workers).")
                return cls._whisper_instance
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
    def warmup_whisper(cls, model_size: str = "base.en"):
        """
        Asynchronously warms up the local Whisper model in memory so that the first
        offline user transcription executes instantaneously without cold-start latency.
        """
        if cls._whisper_instance is not None or cls._is_warming_up:
            return

        def _do_warmup():
            cls._is_warming_up = True
            try:
                cls.get_whisper_model(model_size)
            except Exception as ex:
                logger.debug(f"Offline Whisper warmup notice: {ex}")
            finally:
                cls._is_warming_up = False

        warmup_thread = threading.Thread(target=_do_warmup, daemon=True, name="WhisperOfflineWarmup")
        warmup_thread.start()

    @classmethod
    def transcribe_wav(cls, wav_bytes: bytes, initial_prompt: Optional[str] = None) -> Tuple[bool, str]:
        """
        Transcribes WAV audio bytes in offline mode.
        Tries Whisper AI first. Falls back to Windows SAPI and SpeechRecognition if needed.
        Returns (success: bool, transcribed_text_or_error: str).
        """
        if not wav_bytes or len(wav_bytes) < 800:
            return False, "Audio is too short or empty."

        # 1. Primary: High-accuracy OpenAI Whisper (faster-whisper)
        try:
            success, text = cls._transcribe_with_whisper(wav_bytes, initial_prompt=initial_prompt)
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
    def _split_into_chunks(cls, wav_bytes: bytes, target_sec: float = 24.0) -> list[bytes]:
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
            chunks = []
            for i in range(0, len(samples), chunk_len):
                slice_data = samples[i : i + chunk_len].tobytes()
                out_bio = io.BytesIO()
                with wave.open(out_bio, "wb") as out_wf:
                    out_wf.setnchannels(nc)
                    out_wf.setsampwidth(sw)
                    out_wf.setframerate(fr)
                    out_wf.writeframes(slice_data)
                chunks.append(out_bio.getvalue())
            return chunks if chunks else [wav_bytes]
        except Exception as ex:
            logger.debug(f"Audio chunk split note: {ex}")
            return [wav_bytes]

    @classmethod
    def _transcribe_with_whisper(cls, wav_bytes: bytes, initial_prompt: Optional[str] = None) -> Tuple[bool, str]:
        model = cls.get_whisper_model()
        if model is None:
            return False, "Whisper model unavailable"

        default_prompt = "Hi, I am Sriniwas Awasthi, using Gemini Flow voice dictation in offline mode. Domain vocabulary: analyze, localhost, Chrome, test my website, verbatim transcription."
        prompt = (initial_prompt.strip() + " " + default_prompt) if initial_prompt else default_prompt

        # Estimate duration in seconds
        approx_sec = len(wav_bytes) / 32000.0

        # If audio is long (> 28s) and not pre-streamed, split into parallel chunks for sub-second/multi-core throughput
        if approx_sec > 28.0:
            chunks = cls._split_into_chunks(wav_bytes, target_sec=22.0)
            if len(chunks) > 1:
                from concurrent.futures import ThreadPoolExecutor
                def _worker(pair):
                    idx, b = pair
                    c_stream = io.BytesIO(b)
                    segs, _ = model.transcribe(
                        c_stream,
                        beam_size=1,
                        condition_on_previous_text=False,
                        temperature=0.0,
                        vad_filter=True,
                        initial_prompt=prompt
                    )
                    return idx, " ".join([s.text.strip() for s in segs if s.text.strip()])

                max_w = min(4, len(chunks))
                with ThreadPoolExecutor(max_workers=max_w) as pool:
                    results = list(pool.map(_worker, enumerate(chunks)))
                results.sort(key=lambda x: x[0])
                final_text = " ".join([r[1] for r in results if r[1].strip()]).strip()
                return True, final_text

        # Standard direct ultra-fast transcription (<= 28s)
        audio_stream = io.BytesIO(wav_bytes)
        t0 = time.time()
        segments, info = model.transcribe(
            audio_stream,
            beam_size=1,
            condition_on_previous_text=False,
            temperature=0.0,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=250, speech_pad_ms=200),
            initial_prompt=prompt
        )

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
