"""
Common Transcription Contract for Gemini Flow.
Standardized interface across all 4 models:
1. gemini-2.5-flash
2. gemini-3.5-flash-lite
3. offline-whisper
4. ollama-gemma2 (offline-whisper ASR + Ollama Gemma 2B text cleanup)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Segment:
    start: float
    end: float
    text: str
    confidence: float = 1.0


@dataclass
class Transcript:
    text: str
    segments: List[Dict[str, Any]]
    audio_seconds: float
    covered_seconds: float
    model: str
    warnings: List[str] = field(default_factory=list)
    success: bool = True
    error_message: str = ""

    @property
    def is_fully_covered(self) -> bool:
        """Verifies if the speech is covered within 1.5s of the total duration."""
        if self.audio_seconds <= 1.5:
            return True
        return self.covered_seconds >= (self.audio_seconds - 1.5)
