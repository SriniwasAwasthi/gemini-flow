"""
Deepgram Nova-3 Streaming & REST ASR Provider for Gemini Flow.
Leverages Deepgram Nova-3 with Custom Dictionary keyword biasing (keyterms)
for sub-second transcription.
"""
import os
import json
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
import requests

from app.transcription.asr_interface import ASRProvider

logger = logging.getLogger("GeminiFlow.DeepgramProvider")


class DeepgramProvider(ASRProvider):
    """
    Deepgram Nova-3 ASR Engine.
    - Uses model=nova-3
    - smart_format=false (formatting is controlled by our Stage 4 LLM)
    - keyterms populated from Custom Dictionary for phonetic terminology biasing
    """

    DEEPGRAM_ENDPOINT = "https://api.deepgram.com/v1/listen"

    def __init__(self, api_key: str = "", timeout: float = 8.0):
        self.api_key = api_key or os.environ.get("DEEPGRAM_API_KEY", "")
        self.timeout = timeout
        self.session = requests.Session()

    @property
    def provider_name(self) -> str:
        return "Deepgram Nova-3 (Cloud Streaming)"

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def transcribe(
        self,
        wav_bytes: bytes,
        language: str = "en",
        dictionary_terms: Optional[List[str]] = None,
        system_instruction: str = ""
    ) -> Tuple[bool, str, Dict[str, Any]]:
        if not self.is_available():
            return False, "Deepgram API key not configured.", {}

        if not wav_bytes or len(wav_bytes) < 400:
            return False, "Audio is too short or empty.", {}

        start_time = time.time()
        headers = {
            "Authorization": f"Token {self.api_key.strip()}",
            "Content-Type": "audio/wav"
        }

        # Build query parameters
        params = {
            "model": "nova-3",
            "smart_format": "false",
            "punctuate": "true",
            "encoding": "linear16",
            "sample_rate": "16000",
            "channels": "1"
        }

        if language and language != "auto":
            lang_code = language.lower().split("-")[0].strip()
            if len(lang_code) == 2:
                params["language"] = lang_code

        # Inject Custom Dictionary as Deepgram keyterms
        if dictionary_terms:
            clean_terms = [t.strip() for t in dictionary_terms if t.strip()]
            if clean_terms:
                # Deepgram allows repeated keyterm parameters or comma-separated
                params["keyterm"] = clean_terms[:50]

        try:
            resp = self.session.post(
                self.DEEPGRAM_ENDPOINT,
                headers=headers,
                params=params,
                data=wav_bytes,
                timeout=(2.0, self.timeout)
            )

            latency = time.time() - start_time

            if resp.status_code == 200:
                data = resp.json()
                channels = data.get("results", {}).get("channels", [])
                if channels and len(channels) > 0:
                    alts = channels[0].get("alternatives", [])
                    if alts and len(alts) > 0:
                        transcript = alts[0].get("transcript", "").strip()
                        confidence = alts[0].get("confidence", 1.0)
                        words = alts[0].get("words", [])
                        return True, transcript, {
                            "latency_sec": latency,
                            "confidence": confidence,
                            "words_count": len(words),
                            "provider": self.provider_name
                        }
                return True, "", {"latency_sec": latency, "provider": self.provider_name}
            else:
                err_msg = f"Deepgram returned HTTP {resp.status_code}: {resp.text[:200]}"
                logger.warning(err_msg)
                return False, err_msg, {"latency_sec": latency}

        except Exception as e:
            latency = time.time() - start_time
            logger.warning(f"Deepgram transcription error: {e}")
            return False, str(e), {"latency_sec": latency}
