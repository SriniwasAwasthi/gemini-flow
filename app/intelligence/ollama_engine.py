"""
Ollama Engine for Gemini Flow (Wispr Flow AI Alternative).
Provides 100% private, on-device local LLM text polishing, grammar correction,
and bullet point structuring using Gemma 2B via Ollama (http://localhost:11434).
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Tuple, Optional

logger = logging.getLogger("GeminiFlow.OllamaEngine")

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"


OLLAMA_SYSTEM_PROMPT = """You are a fast speech-to-text formatting engine.
Rules:
1. Fix grammar, verb tenses (past/present/future), and singular/plural mismatches.
2. Strip verbal fillers ("um", "uh", "ah", "like", "you know", "basically").
3. Auto-format lists into clean Markdown bullet points (•).
4. Output ONLY the polished text with ZERO conversational remarks.

--- EXAMPLES ---
[Input]: "yesterday i go to office and seen him"
[Output]: "Yesterday I went to the office and saw him."
[Input]: "he buyed three apple and runned away"
[Output]: "He bought three apples and ran away."
[Input]: "buy milk bread eggs and butter from store"
[Output]: "Buy from the store:
• Milk
• Bread
• Eggs
• Butter"
"""


import time

class OllamaEngine:
    @classmethod
    def ensure_daemon_running(cls, timeout: float = 2.0) -> bool:
        """Ensures the Ollama server daemon is active; auto-starts it if installed."""
        if cls.is_available(timeout=0.3):
            return True
        import os, shutil, subprocess
        from pathlib import Path
        ollama_bin = shutil.which("ollama")
        if not ollama_bin:
            candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
            if candidate.exists():
                ollama_bin = str(candidate)
        if ollama_bin and os.path.exists(ollama_bin):
            try:
                creationflags = 0x08000000 | 0x00000008 # CREATE_NO_WINDOW | DETACHED_PROCESS
                subprocess.Popen([ollama_bin, "serve"], creationflags=creationflags, close_fds=True)
                logger.info(f"Spawned Ollama daemon: {ollama_bin} serve")
                t0 = time.time()
                while time.time() - t0 < timeout:
                    time.sleep(0.2)
                    if cls.is_available(timeout=0.2):
                        cls._is_available = True
                        return True
            except Exception as ex:
                logger.warning(f"Could not auto-start Ollama: {ex}")
        return False

    _instance = None
    _is_available: Optional[bool] = None
    _default_model: str = "gemma2:2b"

    @classmethod
    def is_available(cls, timeout: float = 1.0) -> bool:
        """Quickly checks if the Ollama daemon is running at localhost:11434."""
        try:
            req = urllib.request.Request(OLLAMA_TAGS_URL, headers={"User-Agent": "GeminiFlow"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    cls._is_available = True
                    return True
        except Exception:
            cls._is_available = False
        return False

    @classmethod
    def polish_text(cls, raw_text: str, model_name: str = "gemma2:2b", timeout: float = 12.0) -> Tuple[bool, str]:
        """
        Refines raw transcribed speech using local Ollama (Gemma 2B) on RTX 2050:
        - Fixes all grammar, irregular verbs, tenses, and plurals.
        - Formats lists into clean Markdown bullet points.
        - Strips conversational boilerplate ("Here is the text...").
        """
        if not raw_text or not raw_text.strip():
            return True, ""

        prompt = f"{OLLAMA_SYSTEM_PROMPT}\n\n[Input]: \"{raw_text}\"\n[Output]:"

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "top_p": 0.95,
                "num_predict": 256
            }
        }

        try:
            req = urllib.request.Request(
                OLLAMA_API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    output = data.get("response", "").strip()
                    output = cls._clean_ollama_output(output)
                    if output:
                        logger.info(f"Ollama ({model_name}) polished text successfully ({len(output)} chars).")
                        return True, output
        except Exception as e:
            logger.warning(f"Ollama local inference failed: {e}")

        return False, raw_text

    @staticmethod
    def _clean_ollama_output(text: str) -> str:
        """Strips accidental model preamble, conversational filler, or outer quotes."""
        if not text:
            return ""
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            low = line.strip().lower()
            if any(low.startswith(p) for p in [
                "here is the", "here are the", "sure,", "here's the", "corrected text:", "output:"
            ]):
                continue
            cleaned_lines.append(line)
        cleaned = "\n".join(cleaned_lines).strip()
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1].strip()
        return cleaned
