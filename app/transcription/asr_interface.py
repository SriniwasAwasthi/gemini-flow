"""
ASR Provider Interface for Gemini Flow (Wispr Flow Alternative).
Provides decoupled, interchangeable speech recognition engines:
1. Streaming WebSocket Mode (Deepgram Nova-3) - Lowest live latency (<100ms TTFS)
2. Fast Clause-Sliced Batch Mode (Groq whisper-large-v3-turbo) - Ultra-fast clause ASR (<250ms)
3. Offline / Zero-Retention Mode (Local faster-whisper-large-v3-turbo int8) - Privacy fallback
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, Tuple
import logging

logger = logging.getLogger("GeminiFlow.ASRInterface")


class ASRProvider(ABC):
    """Abstract Base Class for Interchangeable ASR Providers."""

    @abstractmethod
    def transcribe(
        self,
        wav_bytes: bytes,
        language: str = "en",
        dictionary_terms: Optional[List[str]] = None,
        system_instruction: str = ""
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Transcribes audio bytes into text.
        Returns: (success: bool, text: str, metadata: dict)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if provider is configured and available."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the human-readable provider name."""
        pass
