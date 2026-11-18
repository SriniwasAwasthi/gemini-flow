"""
Universal Offline Speech Recognition Backend via Sherpa-ONNX.
Part of Gemini Flow Ultra-Low Latency Subsystem.
"""
import io
import os
import wave
import logging
import threading
from pathlib import Path
from typing import Tuple, Optional, Any, Dict
import numpy as np

logger = logging.getLogger("GeminiFlow.SherpaONNX")


class SherpaONNXBackend:
    _instance: Optional[Any] = None
    _lock = threading.Lock()
    _is_available: Optional[bool] = None

    @classmethod
    def is_available(cls) -> bool:
        """Checks if sherpa-onnx Python package is installed."""
        if cls._is_available is not None:
            return cls._is_available
        try:
            import sherpa_onnx
            cls._is_available = True
        except ImportError:
            cls._is_available = False
        return cls._is_available

    @classmethod
    def get_recognizer(cls, model_dir: Optional[str] = None) -> Optional[Any]:
        """Loads and caches the Sherpa-ONNX offline recognizer singleton."""
        if not cls.is_available():
            return None
        with cls._lock:
            if cls._instance is not None:
                return cls._instance
            try:
                import sherpa_onnx
                project_root = Path(__file__).resolve().parent.parent.parent
                search_dir = Path(model_dir) if model_dir else (project_root / "models" / "sherpa-onnx")
                
                # Check for standard Zipformer or SenseVoice onnx models
                tokens = list(search_dir.glob("*tokens*.txt")) if search_dir.exists() else []
                encoder = list(search_dir.glob("*encoder*.onnx")) if search_dir.exists() else []
                decoder = list(search_dir.glob("*decoder*.onnx")) if search_dir.exists() else []

                if tokens and encoder and decoder:
                    recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                        tokens=str(tokens[0]),
                        encoder=str(encoder[0]),
                        decoder=str(decoder[0]),
                        num_threads=4,
                        sample_rate=16000,
                        feature_dim=80,
                        decoding_method="greedy_search"
                    )
                    cls._instance = recognizer
                    logger.info("Sherpa-ONNX transducer recognizer initialized.")
                    return recognizer
            except Exception as e:
                logger.debug(f"Sherpa-ONNX init note: {e}")
        return None

    @classmethod
    def transcribe(cls, audio_data: Any, sample_rate: int = 16000) -> Tuple[bool, str]:
        """
        Transcribes 16kHz float32 audio numpy array or WAV bytes with Sherpa-ONNX.
        Returns (success: bool, text_or_error: str).
        """
        if not cls.is_available():
            return False, "sherpa-onnx is not installed"

        recognizer = cls.get_recognizer()
        if recognizer is None:
            return False, "sherpa-onnx model not configured"

        try:
            if isinstance(audio_data, bytes):
                with wave.open(io.BytesIO(audio_data), "rb") as wf:
                    fr = wf.getframerate()
                    pcm = wf.readframes(wf.getnframes())
                    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
                    sample_rate = fr
            elif isinstance(audio_data, np.ndarray):
                samples = audio_data.astype(np.float32)
            else:
                return False, "Unsupported audio data type"

            stream = recognizer.create_stream()
            stream.accept_waveform(sample_rate, samples)
            recognizer.decode_stream(stream)
            result = stream.result.text.strip()
            return True, result
        except Exception as e:
            logger.error(f"Sherpa-ONNX transcription error: {e}")
            return False, str(e)
