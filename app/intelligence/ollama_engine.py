"""
Ollama Engine for Gemini Flow (Wispr Flow AI Alternative).
Stage 2 Local Grammar & Self-Correction Engine.
Provides 100% private, on-device local LLM text polishing, grammar correction,
and bullet point structuring using Gemma 2B or Qwen 2.5 via Ollama (http://localhost:11434).
Enforces strict single-turn formatting with temperature=0.0 and a 1.5s timeout.
If Ollama is offline, falls back instantly to regex-based AIPolishBrain (<1ms).
"""
import json
import logging
import threading
import time
import urllib.request
import urllib.error
from typing import Tuple, Optional

logger = logging.getLogger("GeminiFlow.OllamaEngine")

_OLLAMA_LOCK = threading.Lock()
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

OLLAMA_SYSTEM_PROMPT = """You are a fast, highly accurate speech-to-text post-processing and formatting engine.
Rules:
1. Fix grammar, verb tenses (past/present/future), irregular verbs, and singular/plural mismatches.
2. Completely remove verbal fillers ("um", "uh", "ah", "like", "you know", "basically", "actually", "mean").
3. Auto-format multi-point thoughts, sequential steps, or item lists into clean Markdown bullet points (•) on new lines. Omit spoken numbering words ("First is", "Second is") from bullet items.
4. Resolve self-corrections (when the speaker overrides a mistake, e.g. "Monday, sorry Tuesday", output only the corrected statement "Tuesday").
5. Output ONLY the polished text with ZERO conversational remarks or preamble.

--- EXAMPLES ---
[Input]: "yesterday i go to office and seen him"
[Output]: "Yesterday I went to the office and saw him."
[Input]: "he buyed three apple and runned away"
[Output]: "He bought three apples and ran away."
[Input]: "today is Monday sorry today is Tuesday"
[Output]: "Today is Tuesday."
[Input]: "the budget is $500 actually $750"
[Output]: "The budget is $750."
[Input]: "buy milk bread eggs and butter from store"
[Output]: "Buy from the store:
• Milk
• Bread
• Eggs
• Butter"
[Input]: "we discussed three things first deploy model second fix bug third write test"
[Output]: "We discussed three things:
• Deploy the model
• Fix the bug
• Write the test"
"""


class OllamaEngine:
    _instance = None
    _is_available: Optional[bool] = None
    _default_model: str = "llama3.2:1b"
    _FAST_MODELS = [
        "llama3.2:1b",
        "qwen2.5:1.5b",
        "qwen2.5:0.5b",
        "qwen2.5-coder:1.5b",
        "gemma2:2b",
        "qwen2.5:3b",
        "llama3.2:latest"
    ]

    @classmethod
    def get_available_models(cls, timeout: float = 0.5) -> list:
        """Returns list of model names currently installed and available in Ollama."""
        try:
            req = urllib.request.Request(OLLAMA_TAGS_URL, headers={"User-Agent": "GeminiFlow"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    return models
        except Exception:
            pass
        return []

    @classmethod
    def get_preferred_model(cls, preferred_candidate: Optional[str] = None) -> str:
        """
        Selects the best, lowest-latency model available on the local machine.
        Prioritizes ultra-fast edge models (1B-2B params, sub-300ms inference).
        """
        available = cls.get_available_models(timeout=0.3)
        if available:
            if preferred_candidate and any(preferred_candidate in m for m in available):
                return preferred_candidate
            for fast in cls._FAST_MODELS:
                for inst in available:
                    if fast in inst:
                        return inst
            return available[0]
        return preferred_candidate or cls._default_model

    @classmethod
    def ensure_daemon_running(cls, timeout: float = 3.0) -> bool:
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
                creationflags = 0x08000000 | 0x00000008  # CREATE_NO_WINDOW | DETACHED_PROCESS
                subprocess.Popen([ollama_bin, "serve"], creationflags=creationflags, close_fds=True)
                logger.info(f"Spawned Ollama daemon: {ollama_bin} serve")
                t0 = time.time()
                while time.time() - t0 < timeout:
                    time.sleep(0.15)
                    if cls.is_available(timeout=0.2):
                        cls._is_available = True
                        return True
            except Exception as ex:
                logger.warning(f"Could not auto-start Ollama: {ex}")
        return False

    @classmethod
    def is_available(cls, timeout: float = 0.5) -> bool:
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
    def polish_text(cls, raw_text: str, model_name: Optional[str] = None, timeout: float = 1.5, prompt_override: Optional[str] = None) -> Tuple[bool, str]:
        """
        Refines raw transcribed speech using local Ollama (Llama 3.2 1B / Qwen 2.5) with strict single-turn formatting.
        Enforces temperature=0.0 and 1.5s timeout.
        If Ollama is offline or times out, falls back instantly to regex-based AIPolishBrain (<1ms).
        """
        if not model_name:
            model_name = cls.get_preferred_model()
        if not prompt_override and (not raw_text or not raw_text.strip()):
            return True, ""

        if prompt_override:
            prompt = prompt_override
        else:
            prompt = f"{OLLAMA_SYSTEM_PROMPT}\n\n[Input]: \"{raw_text}\"\n[Output]:"

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "top_p": 0.95,
                "num_predict": 512
            }
        }

        try:
            req = urllib.request.Request(
                OLLAMA_API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with _OLLAMA_LOCK:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        output = data.get("response", "").strip()
                        output = cls._clean_ollama_output(output)
                        if output:
                            logger.info(f"Ollama ({model_name}) polished text successfully ({len(output)} chars).")
                            return True, output
        except Exception as e:
            logger.debug(f"Ollama local inference unavailable or timed out ({e}). Falling back to AIPolishBrain...")

        # Instant sub-millisecond fallback to regex-based AIPolishBrain
        try:
            from app.intelligence.ai_polish_brain import AIPolishBrain
            polished = AIPolishBrain.polish_speech(raw_text)
            return True, polished
        except Exception as apb_err:
            logger.debug(f"AIPolishBrain fallback note: {apb_err}")
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
