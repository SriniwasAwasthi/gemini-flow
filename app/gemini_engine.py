"""
Gemini Engine for Gemini Flow.
Sends raw audio and text transformations to Gemini models with zero-latency Keep-Alive sessions,
intelligent model routing, resilient fallback failovers, phonetic dictionary corrections,
personal vocabulary normalization, and telemetry metrics tracking.
"""
import io
import re
import json
import time
import base64
import logging
from typing import Tuple, Optional, List, Dict, Any

import requests

from app.router.model_router import ModelRouter
from app.reliability.fallback_handler import FallbackHandler, ExecutionResult, APIErrorType
from app.vocabulary.vocab_engine import VocabEngine
from app.benchmark.benchmark_engine import MetricsTracker
from app.transformation.transform_engine import TransformEngine, TransformType
from app.intelligence.app_intelligence import AppContext
from app.offline.offline_engine import OfflineSpeechEngine

logger = logging.getLogger("GeminiFlow.GeminiEngine")

FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash"
]


class GeminiEngine:
    def __init__(self, api_key: str = "", model_name: str = "gemini-3.5-flash-lite"):
        self.api_key = api_key.strip()
        self.model_name = model_name
        self.session = requests.Session()
        self.metrics = MetricsTracker()
        self.last_result: Optional[ExecutionResult] = None
        self.last_model_used: str = model_name
        self.last_latency: float = 0.0
        self.last_fallback: bool = False

    def set_api_key(self, api_key: str):
        self.api_key = api_key.strip()

    def set_model(self, model_name: str):
        self.model_name = model_name

    def test_connection(self, api_key: Optional[str] = None) -> Tuple[bool, str]:
        """Tests the Gemini API connection with a simple prompt."""
        key = (api_key or self.api_key).strip()
        if not key:
            return False, "API Key is empty."

        models_to_try = [self.model_name] if self.model_name and self.model_name != "auto" else []
        for m in ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-latest"]:
            if m not in models_to_try:
                models_to_try.append(m)

        last_error = ""
        for model in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": "Respond with 'OK' if you receive this."}
                            ]
                        }
                    ]
                }
                headers = {"Content-Type": "application/json"}
                response = self.session.post(url, headers=headers, json=payload, timeout=8)
                if response.status_code == 200:
                    return True, f"Connection successful! Gemini API is active (using {model})."
                else:
                    try:
                        err_json = response.json()
                        last_error = err_json.get("error", {}).get("message", response.text)
                    except Exception:
                        last_error = response.text
            except Exception as e:
                last_error = str(e)

        return False, f"API Error: {last_error}"

    def transcribe_audio(
        self,
        wav_bytes: bytes,
        system_instruction: str,
        app_context: Optional[AppContext] = None,
        profile_id: str = "coding",
        task: str = "dictate",
        auto_cost_mode: bool = False,
        offline_fallback_enabled: bool = True
    ) -> Tuple[bool, str]:
        """
        Sends WAV audio directly to Gemini with intelligent model routing,
        resilient exponential backoff/fallback, vocabulary normalization, metrics tracking,
        and automatic embedded local offline speech fallback when network is disconnected.
        Returns (success: bool, text_or_error: str).
        """
        if not wav_bytes or len(wav_bytes) < 800:
            return False, "Audio is too short or empty."

        if not self.api_key:
            if offline_fallback_enabled:
                logger.info("API key is missing: Attempting local offline speech recognition fallback...")
                self.last_model_used = "Offline Local Speech (Windows SAPI)"
                self.last_fallback = True
                offline_ok, offline_text = OfflineSpeechEngine.transcribe_wav(wav_bytes)
                if offline_ok and offline_text:
                    return True, offline_text
                return False, offline_text or "No speech detected in offline mode."
            return False, "Gemini API key is not configured. Please open Settings."

        # 1. Resolve Primary Model
        duration_approx = len(wav_bytes) / 32000.0  # Approx seconds for 16kHz 16-bit mono
        if self.model_name == "auto" or not self.model_name:
            app_nm = app_context.app_name if app_context else "General"
            app_cat = app_context.category if app_context else "general"
            routing = ModelRouter.route_model(
                task_type=task,
                duration_sec=duration_approx,
                app_name=app_nm,
                app_category=app_cat,
                profile_name=profile_id,
                auto_cost_mode=auto_cost_mode
            )
            primary_model = routing.model_name
        else:
            primary_model = self.model_name

        # 2. Resilient Model Invocation via FallbackHandler
        def call_model(model: str) -> Tuple[bool, str]:
            return self._try_transcribe_with_model(model, wav_bytes, system_instruction)

        exec_res = FallbackHandler.execute_with_resilience(
            call_fn=call_model,
            primary_model=primary_model,
            max_retries_per_model=2
        )

        # 3. If online transcription failed due to network / connection drops, invoke local offline fallback
        if not exec_res.success and offline_fallback_enabled:
            logger.info("Cloud API unreachable or failed. Attempting Embedded Local Offline Speech Recognition fallback...")
            try:
                offline_ok, offline_text = OfflineSpeechEngine.transcribe_wav(wav_bytes)
                if offline_ok and offline_text:
                    exec_res = ExecutionResult(
                        success=True,
                        text=offline_text,
                        model_used="Offline Local Speech (Windows SAPI)",
                        fallback_occurred=True,
                        latency_seconds=exec_res.latency_seconds
                    )
            except Exception as off_ex:
                logger.debug(f"Offline fallback exception: {off_ex}")

        self.last_result = exec_res
        self.last_model_used = exec_res.model_used
        self.last_latency = exec_res.latency_seconds
        self.last_fallback = exec_res.fallback_occurred

        final_text = exec_res.text
        if exec_res.success and final_text:
            # Vocabulary normalization
            try:
                final_text = VocabEngine.normalize_text(final_text)
            except Exception as ve_err:
                logger.debug(f"Vocab normalization note: {ve_err}")

        # 3. Telemetry Tracking
        words_count = len(final_text.split()) if exec_res.success else 0
        app_str = app_context.app_name if app_context else "General"
        self.metrics.record_event(
            model=exec_res.model_used,
            latency=exec_res.latency_seconds,
            success=exec_res.success,
            words_count=words_count,
            intent=task.value if hasattr(task, "value") else str(task),
            app_name=app_str,
            fallback=exec_res.fallback_occurred
        )

        if exec_res.success:
            return True, final_text
        return False, exec_res.error_message or "Transcription failed across all models."

    def _try_transcribe_with_model(self, model: str, wav_bytes: bytes, system_instruction: str) -> Tuple[bool, str]:
        """Direct REST API implementation with Keep-Alive session and zero-thinking config."""
        audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

        gen_config: Dict[str, Any] = {
            "temperature": 0.0,
            "topP": 0.9,
            "maxOutputTokens": 2048
        }

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                f"{system_instruction}\n\n"
                                "Task: Transcribe and refine the audio attached below according to the system rules above. "
                                "Output ONLY the final transcribed text."
                            )
                        },
                        {
                            "inline_data": {
                                "mime_type": "audio/wav",
                                "data": audio_b64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": gen_config
        }

        headers = {"Content-Type": "application/json"}
        try:
            start_t = time.time()
            approx_sec = len(wav_bytes) / 32000.0
            req_timeout = max(35, min(120, int(approx_sec * 1.8) + 20))
            response = self.session.post(url, headers=headers, json=payload, timeout=req_timeout)

            # If 400 with thinkingConfig unsupported, retry once without thinkingConfig
            if response.status_code == 400 and "thinkingConfig" in response.text:
                payload["generationConfig"].pop("thinkingConfig", None)
                response = self.session.post(url, headers=headers, json=payload, timeout=req_timeout)

            elapsed = time.time() - start_t
            logger.info(f"Gemini transcription with {model} completed in {elapsed:.2f}s (Status: {response.status_code})")

            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return False, "No speech detected or empty response from Gemini."
                parts = candidates[0].get("content", {}).get("parts", [])
                full_text = "".join([p.get("text", "") for p in parts if "text" in p])
                cleaned_text = self._clean_output(full_text)
                return True, cleaned_text
            else:
                try:
                    err = response.json().get("error", {}).get("message", response.text)
                except Exception:
                    err = response.text
                return False, f"Gemini API Error ({response.status_code}): {err}"
        except Exception as e:
            return False, f"Network request error: {str(e)}"

    def transform_text(
        self,
        raw_text: str,
        transform_type: TransformType = TransformType.IMPROVE,
        app_context: Optional[AppContext] = None,
        custom_instruction: str = "",
        profile_id: str = "coding",
        auto_cost_mode: bool = False
    ) -> ExecutionResult:
        """
        Executes text transformation across the 16 preset operations or custom prompt
        with intelligent model routing, exponential backoff, and fallback failover.
        """
        if not self.api_key:
            return ExecutionResult(
                success=False,
                text="",
                model_used="",
                error_message="Gemini API Key is not configured. Please open Settings."
            )

        if not raw_text or not raw_text.strip():
            return ExecutionResult(
                success=False,
                text="",
                model_used="",
                error_message="Input text is empty."
            )

        # 1. Resolve System Instruction
        instruction = TransformEngine.build_system_instruction(
            transform_type=transform_type,
            app_context=app_context,
            custom_instruction=custom_instruction
        )

        # 2. Resolve Primary Model
        if self.model_name == "auto" or not self.model_name:
            if auto_cost_mode and len(raw_text) < 1500 and transform_type not in (TransformType.SUMMARIZE, TransformType.CONVERT_DOCS):
                primary_model = "gemini-3.5-flash-lite"
            else:
                primary_model = TransformEngine.resolve_model(
                    transform_type=transform_type,
                    text_length=len(raw_text)
                )
        else:
            primary_model = self.model_name

        # 3. Model execution function
        def call_model(model: str) -> Tuple[bool, str]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"{instruction}\n\nCONTENT TO TRANSFORM:\n\"\"\"\n{raw_text}\n\"\"\""
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": TransformEngine.get_preset(transform_type).temperature,
                    "maxOutputTokens": 2048
                }
            }
            try:
                resp = self.session.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        res_text = "".join([p.get("text", "") for p in parts if "text" in p])
                        return True, self._clean_output(res_text)
                    return False, "Empty response from Gemini."
                else:
                    try:
                        err = resp.json().get("error", {}).get("message", resp.text)
                    except Exception:
                        err = resp.text
                    return False, f"Gemini API Error ({resp.status_code}): {err}"
            except Exception as e:
                return False, f"Network error: {str(e)}"

        # 4. Resilient Execution
        exec_res = FallbackHandler.execute_with_resilience(
            call_fn=call_model,
            primary_model=primary_model,
            max_retries_per_model=2
        )

        # 5. Vocabulary Normalization & Metrics
        if exec_res.success and exec_res.text:
            try:
                exec_res.text = VocabEngine.normalize_text(exec_res.text)
            except Exception:
                pass

        words_count = len(exec_res.text.split()) if exec_res.success else 0
        app_str = app_context.app_name if app_context else "General"
        self.metrics.record_event(
            model=exec_res.model_used,
            latency=exec_res.latency_seconds,
            success=exec_res.success,
            words_count=words_count,
            intent=transform_type.value,
            app_name=app_str,
            fallback=exec_res.fallback_occurred
        )

        self.last_result = exec_res
        self.last_model_used = exec_res.model_used
        self.last_latency = exec_res.latency_seconds
        self.last_fallback = exec_res.fallback_occurred

        return exec_res

    def enhance_to_ai_prompt(self, raw_text: str) -> Tuple[bool, str]:
        """Transforms messy dictation or raw notes into a world-class, structured AI Prompt."""
        res = self.transform_text(raw_text, transform_type=TransformType.CONVERT_PROMPT)
        if res.success:
            return True, res.text
        return False, res.error_message or "Prompt enhancement failed."

    @staticmethod
    def apply_dictionary(text: str, dictionary: List[Dict[str, str]]) -> str:
        """Applies phonetic dictionary replacements."""
        if not text or not dictionary:
            return text

        result = text
        for entry in dictionary:
            spoken = entry.get("spoken", "").strip()
            replacement = entry.get("replacement", "").strip()
            if not spoken or not replacement:
                continue
            pattern = re.compile(re.escape(spoken), re.IGNORECASE)
            result = pattern.sub(replacement, result)

        return result

    @staticmethod
    def apply_snippets(text: str, snippets: List[Dict[str, str]]) -> str:
        """Checks if the transcribed text matches a snippet trigger phrase."""
        if not text or not snippets:
            return text

        normalized_text = re.sub(r'[^\w\s]', '', text).strip().lower()
        for snip in snippets:
            trigger = snip.get("trigger", "").strip()
            content = snip.get("content", "").strip()
            if not trigger or not content:
                continue

            normalized_trigger = re.sub(r'[^\w\s]', '', trigger).strip().lower()
            if normalized_text == normalized_trigger or normalized_trigger in normalized_text:
                logger.info(f"Snippet trigger matched: '{trigger}' -> Expanding snippet.")
                return content

        return text

    def _clean_output(self, raw_text: str) -> str:
        """Removes accidental code fences, quotation wraps, markdown preamble, and verbal disfluencies."""
        text = raw_text.strip()
        if text.startswith("```") and text.endswith("```"):
            lines = text.split("\n")
            if len(lines) >= 2:
                text = "\n".join(lines[1:-1]).strip()
        if text.startswith('"') and text.endswith('"') and "\n" not in text:
            text = text[1:-1].strip()

        # Deterministic hesitation & filler token cleanup safety net
        # Matches: uh, um, ah, er, eh, uhm, ahm, uhh, ahh surrounded by word boundaries
        filler_pattern = re.compile(r'\b(uh|um|ah|er|eh|uhm|ahm|umm|ahh|uhh)\b[,;:]*', re.IGNORECASE)
        text = filler_pattern.sub('', text)

        # Remove repeated identical words (e.g. "and and", "the the", "if if", "in in", "is is")
        repeat_pattern = re.compile(r'\b([a-zA-Z]{2,})\s+\1\b', re.IGNORECASE)
        # Apply twice for triplets like "and and and"
        text = repeat_pattern.sub(r'\1', text)
        text = repeat_pattern.sub(r'\1', text)

        # Normalize multiple spaces and cleanup dangling punctuation from removed fillers
        text = re.sub(r'[,;]\s*(na|ya)\s*([.?!]?)$', r'\2', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*,\s*,+', ',', text)
        text = re.sub(r'\s*,\s*\.', '.', text)
        text = re.sub(r'^\s*[,;:\.]\s*', '', text)  # leading punctuation
        text = re.sub(r'\s+([,.:;?!])', r'\1', text)  # space before punctuation
        text = re.sub(r'[ \t]{2,}', ' ', text).strip()

        # Capitalize start if needed
        if text and text[0].islower() and not text.startswith("http"):
            text = text[0].upper() + text[1:]

        return text
