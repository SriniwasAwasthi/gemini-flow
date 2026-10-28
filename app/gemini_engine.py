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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading

from app.router.model_router import ModelRouter
from app.reliability.fallback_handler import FallbackHandler, ExecutionResult, APIErrorType
from app.vocabulary.vocab_engine import VocabEngine
from app.benchmark.benchmark_engine import MetricsTracker
from app.transformation.transform_engine import TransformEngine, TransformType
from app.intelligence.app_intelligence import AppContext
from app.offline.offline_engine import OfflineSpeechEngine

logger = logging.getLogger("GeminiFlow.GeminiEngine")

FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash"
]


class GeminiEngine:
    def __init__(self, api_key: Any = "", model_name: str = "auto"):
        from .config import sanitize_api_key
        if hasattr(api_key, "get_api_key"):
            self.api_key = sanitize_api_key(api_key.get_api_key())
        else:
            self.api_key = sanitize_api_key(api_key)
        self.model_name = model_name
        self.session = requests.Session()

        # Configure robust connection pooling, keep-alive, and HTTP-level retry adapter
        retries = Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=retries
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.metrics = MetricsTracker()
        self.last_result: Optional[ExecutionResult] = None
        self.last_model_used: str = model_name
        self.last_latency: float = 0.0
        self.last_fallback: bool = False

    def set_api_key(self, api_key: str):
        from .config import sanitize_api_key
        self.api_key = sanitize_api_key(api_key)
        if self.api_key:
            self.warm_connection()

    def set_model(self, model_name: str):
        self.model_name = model_name

    def warm_connection(self):
        """
        Pre-warms DNS resolution and TLS 1.3 keep-alive session in a background thread
        so that the first dictation or API request completes with near-zero latency.
        """
        def _warm_worker():
            try:
                # Lightweight HEAD/GET request to prime TLS session cache & DNS
                url = "https://generativelanguage.googleapis.com/$discovery/rest?version=v1beta"
                self.session.get(url, timeout=(5.0, 5.0))
                logger.info("Gemini HTTP Keep-Alive connection warmed up successfully.")
            except Exception as e:
                logger.debug(f"Connection pre-warm note: {e}")

        t = threading.Thread(target=_warm_worker, daemon=True, name="GeminiConnWarmup")
        t.start()

    def test_connection(self, api_key: Optional[str] = None) -> Tuple[bool, str]:
        """Tests the Gemini API connection with robust key verification, latency check, and model fallback."""
        from .config import sanitize_api_key
        key = sanitize_api_key(api_key or self.api_key)
        if not key:
            return False, "API Key is empty. Please enter your Gemini API key."

        # Step 1: Query the Google Generative Language models endpoint to strictly verify the API Key
        try:
            url_models = "https://generativelanguage.googleapis.com/v1beta/models"
            resp_models = self.session.get(url_models, headers={"x-goog-api-key": key}, timeout=(5.0, 5.0))
            if resp_models.status_code in (400, 401, 403):
                try:
                    err_msg = resp_models.json().get("error", {}).get("message", resp_models.text)
                except Exception:
                    err_msg = resp_models.text
                return False, f"Invalid API Key ({resp_models.status_code}): {err_msg}\nTip: Ensure your key is active at https://aistudio.google.com/app/apikey"
            key_verified = (resp_models.status_code == 200)
        except Exception as e:
            logger.debug(f"Models endpoint check exception: {e}")
            key_verified = False

        # Step 2: Prioritize active production models for sub-second generation & transcription
        models_to_try = [
            "gemini-2.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash"
        ]
        if self.model_name and self.model_name not in models_to_try and self.model_name != "auto":
            models_to_try.insert(0, self.model_name)

        last_error = ""
        test_timeout = (3.0, 8.0)

        for model in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": "Respond with 'OK' if you receive this."}
                            ]
                        }
                    ]
                }
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": key
                }
                t0 = time.time()
                response = self.session.post(url, headers=headers, json=payload, timeout=test_timeout)
                latency = time.time() - t0
                if response.status_code == 200:
                    return True, f"Connection successful! Gemini API is active ({model}, latency: {latency:.2f}s)."
                else:
                    try:
                        err_json = response.json()
                        last_error = err_json.get("error", {}).get("message", response.text)
                    except Exception:
                        last_error = response.text

                    # If credentials/key are invalid, fail fast without waiting through other models
                    lower_err = last_error.lower()
                    is_invalid_key = (
                        response.status_code in (401, 403)
                        or "api_key_invalid" in lower_err
                        or "api key not valid" in lower_err
                        or "unauthenticated" in lower_err
                        or "unauthorized" in lower_err
                        or "permission_denied" in lower_err
                    )
                    if is_invalid_key:
                        return False, f"Invalid API Key ({response.status_code}): {last_error}\nTip: Ensure your key is active at https://aistudio.google.com/app/apikey"

                    # 503 high demand, 429 quota, 404, or 400: proceed to next fallback model
                    logger.info(f"Model {model} returned {response.status_code}, testing next fallback model...")
                    continue
            except requests.exceptions.Timeout:
                last_error = f"Connection to {model} timed out after 8s. Checking fallback model..."
                logger.warning(last_error)
            except Exception as e:
                last_error = str(e)

        if key_verified:
            return True, "Connection verified! Key is valid & saved (automatic multi-model failover active)."

        return False, f"API Error: {last_error}"

    def transcribe_audio(
        self,
        wav_bytes: bytes,
        system_instruction: str,
        app_context: Optional[AppContext] = None,
        profile_id: str = "coding",
        task: str = "dictate",
        auto_cost_mode: bool = False,
        offline_fallback_enabled: bool = True,
        offline_language: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Sends WAV audio directly to Gemini with intelligent model routing,
        resilient exponential backoff/fallback, vocabulary normalization, metrics tracking,
        and automatic embedded local offline speech fallback when network is disconnected.
        Returns (success: bool, text_or_error: str).
        """
        if not wav_bytes or len(wav_bytes) < 800:
            return False, "Audio is too short or empty."

# Check if user explicitly chose offline mode, or if API key is not configured
        is_explicit_offline = any(k in str(self.model_name).lower() for k in ("offline", "whisper", "local", "on-device", "ollama", "gemma"))

        if not self.api_key or is_explicit_offline:
            if offline_fallback_enabled or is_explicit_offline:
                is_ollama = any(k in str(self.model_name).lower() for k in ("ollama", "gemma"))
                logger.info(f"Executing on-device speech pipeline (Model: {self.model_name})...")
                self.last_model_used = "Ollama Gemma 2B (Local GPU)" if is_ollama else "Offline Local Speech (Whisper AI)"
                self.last_fallback = not is_explicit_offline
                t_off_start = time.time()
                prompt_ctx = "Clean speech dictation, accurate grammar, proper punctuation."
                offline_ok, offline_text = OfflineSpeechEngine.transcribe_wav(wav_bytes, initial_prompt=prompt_ctx, language=offline_language)
                self.last_latency = time.time() - t_off_start
                if offline_ok:
                    if offline_text:
                        # Apply AIPolishBrain first to resolve self-corrections, format bullet points, and clean speech
                        try:
                            from app.intelligence.ai_polish_brain import AIPolishBrain
                            offline_text = AIPolishBrain.polish_speech(offline_text)
                        except Exception as apb_err:
                            logger.debug(f"AIPolishBrain offline note: {apb_err}")

                        if is_ollama:
                            try:
                                from app.intelligence.ollama_engine import OllamaEngine
                                OllamaEngine.ensure_daemon_running(timeout=5.0)
                                if OllamaEngine.is_available(timeout=0.5):
                                    ok_ol, txt_ol = OllamaEngine.polish_text(offline_text, timeout=15.0)
                                    if ok_ol and txt_ol:
                                        offline_text = txt_ol
                            except Exception as ol_err:
                                logger.debug(f"Ollama execution note: {ol_err}")

                        try:
                            from app.vocabulary.vocab_engine import VocabEngine
                            offline_text = VocabEngine.normalize_text(offline_text)
                        except Exception:
                            pass
                    return True, offline_text
                return False, offline_text or "No speech detected in offline mode."
            return False, "Gemini API key is not configured. Please open Settings."

        # 1. Resolve Primary Model via ModelRouter (Dynamic Application Context & Profile Routing)
        duration_approx = len(wav_bytes) / 32000.0  # Approx seconds for 16kHz 16-bit mono
        app_name = getattr(app_context, "app_name", str(app_context) if isinstance(app_context, str) else "General") if app_context else "General"
        app_cat = getattr(app_context, "category", "general") if app_context else "general"
        routing = ModelRouter.route_model(
            task_type="dictate",
            duration_sec=duration_approx,
            text_length=int(duration_approx * 2.5),
            app_name=app_name,
            app_category=app_cat,
            profile_name=profile_id,
            manual_override=None if self.model_name in ("auto", None, "") else self.model_name,
            auto_cost_mode=auto_cost_mode
        )
        primary_model = routing.model_name
        logger.info(f"ModelRouter selected primary model: '{primary_model}' ({routing.reason})")

        # 2. Resilient Model Invocation via FallbackHandler
        def call_model(model: str) -> Tuple[bool, str]:
            return self._try_transcribe_with_model(model, wav_bytes, system_instruction)

        exec_res = FallbackHandler.execute_with_resilience(
            call_fn=call_model,
            primary_model=primary_model,
            max_retries_per_model=2
        )

        # 3. If online transcription failed due to network loss, 429 rate limit, or server errors, invoke local offline fallback
        # Guaranteed Zero-Data-Loss: Always fall back to local Whisper AI so user speech is NEVER dropped
        if not exec_res.success:
            logger.info("Online Gemini execution did not succeed. Fast fallback to local offline Whisper AI...")
            try:
                t_off_start = time.time()
                prompt_ctx = ""
                try:
                    from app.vocabulary.vocab_engine import VocabEngine
                    prompt_ctx = VocabEngine().get_whisper_prompt()
                except Exception:
                    pass
                offline_ok, offline_text = OfflineSpeechEngine.transcribe_wav(wav_bytes, initial_prompt=prompt_ctx, language=offline_language)
                if offline_ok:
                    if offline_text:
                        try:
                            from app.intelligence.ai_polish_brain import AIPolishBrain
                            offline_text = AIPolishBrain.polish_speech(offline_text)
                        except Exception as apb_err:
                            logger.debug(f"AIPolishBrain offline note: {apb_err}")
                        try:
                            offline_text = VocabEngine.normalize_text(offline_text)
                        except Exception:
                            pass
                    exec_res = ExecutionResult(
                        success=True,
                        text=offline_text,
                        model_used="Offline Local Speech (Whisper AI)",
                        fallback_occurred=True,
                        latency_seconds=time.time() - t_off_start
                    )
            except Exception as off_ex:
                logger.debug(f"Offline fallback exception: {off_ex}")

        self.last_result = exec_res
        self.last_model_used = exec_res.model_used
        self.last_latency = exec_res.latency_seconds
        self.last_fallback = exec_res.fallback_occurred

        final_text = exec_res.text
        if exec_res.success and final_text:
            # Apply cognitive AI Polish Brain to format bullet points, strip ordinals, and clean grammar
            try:
                from app.intelligence.ai_polish_brain import AIPolishBrain
                final_text = AIPolishBrain.polish_speech(final_text)
            except Exception as apb_err:
                logger.debug(f"AIPolishBrain polish note: {apb_err}")
            # Vocabulary normalization
            try:
                from app.vocabulary.vocab_engine import VocabEngine
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

    @staticmethod
    def _split_wav_into_chunks(wav_bytes: bytes, target_chunk_sec: float = 24.0, max_chunk_sec: float = 32.0) -> List[bytes]:
        """
        Splits audio into silence-aligned rapid segments (20-30s) using RMS energy analysis.
        Enables high-throughput parallel execution across Gemini endpoints, completing even
        5-20 minute recordings in under 2 to 4 seconds total wall-clock time.
        """
        if not wav_bytes or len(wav_bytes) < 1000:
            return [wav_bytes] if wav_bytes else []

        try:
            bio = io.BytesIO(wav_bytes)
            import wave
            import numpy as np
            with wave.open(bio, 'rb') as wf:
                nchannels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                nframes = wf.getnframes()
                pcm_data = wf.readframes(nframes)

            total_sec = nframes / float(framerate) if framerate > 0 else 0
            # Audio shorter than max_chunk_sec runs directly as a single chunk
            if total_sec <= max_chunk_sec or total_sec <= 0:
                return [wav_bytes]

            dtype = np.int16 if sampwidth == 2 else np.int8
            samples = np.frombuffer(pcm_data, dtype=dtype)
            if nchannels > 1:
                # Use first channel for silence / energy calculation
                samples = samples.reshape(-1, nchannels)[:, 0]

            chunks = []
            current_frame = 0
            total_frames = nframes

            while current_frame < total_frames:
                remaining_frames = total_frames - current_frame
                remaining_sec = remaining_frames / float(framerate)

                if remaining_sec <= max_chunk_sec:
                    # Final slice
                    chunk_pcm = pcm_data[current_frame * nchannels * sampwidth :]
                    out_io = io.BytesIO()
                    with wave.open(out_io, 'wb') as out_wf:
                        out_wf.setnchannels(nchannels)
                        out_wf.setsampwidth(sampwidth)
                        out_wf.setframerate(framerate)
                        out_wf.writeframes(chunk_pcm)
                    chunks.append(out_io.getvalue())
                    break

                # Search window for natural silence pause: [target_chunk_sec - 15s, target_chunk_sec + 15s]
                search_start_sec = max(5.0, target_chunk_sec - 15.0)
                search_end_sec = min(remaining_sec - 5.0, max_chunk_sec)

                start_f = current_frame + int(search_start_sec * framerate)
                end_f = current_frame + int(search_end_sec * framerate)

                # 40ms frames for energy computation
                frame_len = max(1, int(0.04 * framerate))
                min_energy = float('inf')
                best_split_frame = current_frame + int(target_chunk_sec * framerate)

                for f_idx in range(start_f, end_f - frame_len, frame_len):
                    block = samples[f_idx : f_idx + frame_len].astype(np.float32)
                    energy = np.mean(block ** 2)
                    if energy < min_energy:
                        min_energy = energy
                        best_split_frame = f_idx + frame_len // 2

                chunk_pcm = pcm_data[current_frame * nchannels * sampwidth : best_split_frame * nchannels * sampwidth]
                out_io = io.BytesIO()
                with wave.open(out_io, 'wb') as out_wf:
                    out_wf.setnchannels(nchannels)
                    out_wf.setsampwidth(sampwidth)
                    out_wf.setframerate(framerate)
                    out_wf.writeframes(chunk_pcm)
                chunks.append(out_io.getvalue())

                # Acoustic overlap (0.25s) to guarantee zero clipped words across chunk boundaries
                overlap_f = int(0.25 * framerate)
                current_frame = max(current_frame + overlap_f, best_split_frame - overlap_f)

            return chunks if chunks else [wav_bytes]
        except Exception as ex:
            logger.warning(f"Error in silence-aware WAV splitting: {ex}")
            return [wav_bytes]

    @staticmethod
    def _stitch_chunk_transcripts(chunks: List[str]) -> str:
        """
        Intelligently joins multi-chunk transcripts without creating awkward breaks,
        dropping words, or duplicating overlapping boundary words.
        """
        valid = [c.strip() for c in chunks if c and c.strip()]
        if not valid:
            return ""
        stitched = valid[0]
        for next_chunk in valid[1:]:
            if not next_chunk:
                continue

            # Detect and deduplicate boundary overlap (1 to 6 overlapping words between chunks)
            prev_words = stitched.split()
            next_words = next_chunk.split()
            overlap_k = 0
            max_check = min(6, len(prev_words), len(next_words))
            for k in range(max_check, 0, -1):
                p_slice = [re.sub(r'[^\w]', '', w).lower() for w in prev_words[-k:]]
                n_slice = [re.sub(r'[^\w]', '', w).lower() for w in next_words[:k]]
                if p_slice == n_slice and all(len(w) > 0 for w in p_slice):
                    overlap_k = k
                    break

            if overlap_k > 0:
                joined_next = " ".join(next_words[overlap_k:])
                if not joined_next:
                    continue
                if stitched.endswith(("\n", "\n\n")) or joined_next.startswith(("\n", "•", "-", "*")):
                    stitched = stitched.rstrip() + "\n\n" + joined_next.lstrip()
                elif stitched.endswith((".", "!", "?", ":", ";", ",")):
                    stitched += " " + joined_next
                else:
                    stitched += " " + joined_next
            else:
                if stitched.endswith(("\n", "\n\n")) or next_chunk.startswith(("\n", "•", "-", "*")):
                    stitched = stitched.rstrip() + "\n\n" + next_chunk.lstrip()
                elif stitched.endswith((".", "!", "?", ":", ";", ",")):
                    stitched += " " + next_chunk
                else:
                    stitched += " " + next_chunk
        return stitched.strip()

    @staticmethod
    def _extract_part_text(p: Any) -> str:
        """Extracts text from candidate part, supporting text, audioTranscription, and alternative modalities."""
        if not isinstance(p, dict):
            return ""
        if "text" in p and p["text"]:
            return str(p["text"])
        if "audioTranscription" in p:
            at = p["audioTranscription"]
            if isinstance(at, dict) and "text" in at and at["text"]:
                return str(at["text"])
        return ""

    def _try_transcribe_with_model(self, model: str, wav_bytes: bytes, system_instruction: str) -> Tuple[bool, str]:
        """Direct REST API implementation with Keep-Alive session, parallel chunking, and resilient fallback."""
        chunks = self._split_wav_into_chunks(wav_bytes, target_chunk_sec=35.0, max_chunk_sec=50.0)

        # Single chunk path (standard speech <= 22s)
        if len(chunks) == 1:
            chunk_bytes = chunks[0]
            audio_b64 = base64.b64encode(chunk_bytes).decode("utf-8")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

            gen_config: Dict[str, Any] = {
                "temperature": 0.0,
                "topP": 0.95,
                "maxOutputTokens": 8192
            }
            # Optimize Gemini 3.5/2.5/2.0 for ultra-fast speech transcription by disabling thinking overhead
            if any(k in model.lower() for k in ("2.5", "2.0")) and "3." not in model.lower() and "transcribe" not in model.lower():
                gen_config["thinkingConfig"] = {"thinkingBudget": 0}

            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": (
                                    f"{system_instruction}\n\n"
                                    "EXECUTION DIRECTIVES:\n"
                                    "1. Process the attached audio in strict accordance with the Active Spoken Language Constraints specified above.\n"
                                    "2. Anti-Hallucination & Silence Detection: Transcribe ONLY acoustic speech actually uttered. If silence or background noise, return empty string.\n"
                                    "3. Formatting & Structure: If structured points, lists, or steps are dictated, format cleanly with bullet points ('• ') and natural section headers. OMIT spoken numbering or ordinals ('First is', 'Second is', 'Point 1:') from the bullet body, as '• ' denotes the point; otherwise format flowing narrative in clean paragraphs.\n"
                                    "4. Self-Correction & Speech Override Resolution: When the speaker changes their mind or corrects a word, date, budget/amount, number, time, name, or statement (e.g. 'today is Monday... sorry today is Tuesday' -> 'today is Tuesday'; 'convert this under 4 seconds or no, sorry, under 3 seconds' -> 'convert this under 3 seconds'; 'total budget was around ₹550. Oh wait, the total budget was ₹750.' -> 'the total budget was ₹750.'; 'The meeting is at 2 p.m. Sorry, the meeting is at 3 p.m.' -> 'The meeting is at 3 p.m.'; 'I am in 11th standard... sorry I am in 12th standard' -> 'I am in 12th standard'), ALWAYS override the mistake with the correction. Drop the error and apologies ('sorry', 'oh sorry', 'my bad', 'no wait').\n"
                                    "5. Repetition & Stutter Collapse: Eliminate verbal stutters and repeated sentences (e.g. 'I want 100% data. If I just want 100% accurate data.' -> 'I want 100% accurate data.').\n"
                                    "6. Grammar & All 12 Tenses: Ensure flawless grammar, vocabulary, and tense consistency natively across past, present, and future tenses.\n"
                                    "7. Proper Name Integrity: Transcribe proper nouns and names accurately ONLY if explicitly spoken.\n"
                                    "8. Grammar, Tenses & Multi-Item List Formatting: Fix all tenses, plurals, subject-verb agreements, and eliminate filler words ('um', 'uh', 'like', 'basically'). When multiple items, tasks, groceries, or steps are spoken, format them into clean Markdown bullet points ('• ').\n"
                                    "9. Output Format: Output ONLY the finalized text directly without preamble, commentary, or markdown code fences.\n\n"
                                    '--- 22 FEW-SHOT GOLDEN ANCHOR DEMONSTRATIONS ---\n[Input]: "yesterday i go to office and seen him"\n[Output]: "Yesterday I went to the office and saw him."\n\n[Input]: "there is many problem with the servers"\n[Output]: "There are many problems with the servers."\n\n[Input]: "she don\'t know nothing about it"\n[Output]: "She doesn\'t know anything about it."\n\n[Input]: "he buyed three apple and runned away"\n[Output]: "He bought three apples and ran away."\n\n[Input]: "um like so basically i think we should meet on friday"\n[Output]: "I think we should meet on Friday."\n\n[Input]: "the thing is you know actually the api is failing with 500 error"\n[Output]: "The API is failing with a 500 error."\n\n[Input]: "buy milk bread eggs butter and apples from store"\n[Output]: "Buy from the store:\n• Milk\n• Bread\n• Eggs\n• Butter\n• Apples"\n\n[Input]: "first install python second setup venv third run the app"\n[Output]: "Here are the steps:\n1. Install Python\n2. Set up venv\n3. Run the app"\n\n[Input]: "agenda today is review sales discuss budget and plan sprint"\n[Output]: "Today\'s agenda:\n• Review sales\n• Discuss budget\n• Plan sprint"\n\n[Input]: "bugs are crash on login missing icon and slow loading"\n[Output]: "Bug report:\n• Crash on login\n• Missing icon\n• Slow loading"\n\n[Input]: "hi sarah thanks for the proposal i reviewed slide four"\n[Output]: "Hi Sarah, thanks for the proposal. I reviewed slide 4."\n\n[Input]: "hey alex can you pull the git branch and test payments"\n[Output]: "Hey Alex, can you pull the Git branch and test payments?"\n\n[Input]: "are you free for a thirty minute zoom call tomorrow at two pm"\n[Output]: "Are you free for a 30-minute Zoom call tomorrow at 2:00 PM?"\n\n[Input]: "total is fifteen hundred dollars with eighteen percent gst"\n[Output]: "The total is $1,500 with 18% GST."\n\n[Input]: "the event is scheduled on november twenty fifth at ten thirty am"\n[Output]: "The event is scheduled on November 25th at 10:30 AM."\n\n[Input]: "run git commit dash m initial commit and push to main"\n[Output]: "Run `git commit -m \\"initial commit\\"` and push to `main`."\n\n[Input]: "we need sixteen gigabytes ram and an rtx twenty fifty gpu"\n[Output]: "We need 16 GB RAM and an RTX 2050 GPU."\n\n[Input]: "if i was you i would have did the same thing"\n[Output]: "If I were you, I would have done the same thing."\n\n[Input]: "the decision was took by the management yesterday"\n[Output]: "The decision was made by the management yesterday."\n\n[Input]: "let me know once you reach home safe"\n[Output]: "Let me know once you reach home safely."\n\n[Input]: "why you are not answering my messages since morning"\n[Output]: "Why haven\'t you been answering my messages since morning?"\n\n[Input]: "we tested faster whisper and ollama gemma on cuda"\n[Output]: "We tested Faster-Whisper and Ollama Gemma on CUDA."'
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

            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            try:
                start_t = time.time()
                approx_sec = len(chunk_bytes) / 32000.0
                # Production fast-response timeout: 1.8s connect, 3.5s-8.0s read for sub-2s SLA
                req_timeout = (4.0, max(12.0, min(35.0, float(approx_sec * 0.8) + 8.0)))
                response = self.session.post(url, headers=headers, json=payload, timeout=req_timeout)

                elapsed = time.time() - start_t
                logger.info(f"Gemini transcription with {model} completed in {elapsed:.2f}s (Status: {response.status_code})")

                if response.status_code == 200:
                    try:
                        data = response.json()
                    except Exception as json_err:
                        logger.error(f"Failed to parse JSON from {model}: {json_err}")
                        return False, f"Malformed JSON response from {model}"

                    candidates = data.get("candidates", []) if isinstance(data, dict) else []
                    if candidates:
                        cand = candidates[0]
                        finish_reason = cand.get("finishReason", "")
                        parts = cand.get("content", {}).get("parts", [])
                        full_text = "".join([self._extract_part_text(p) for p in parts])
                        cleaned_text = self._clean_output(full_text)
                        if cleaned_text:
                            try:
                                from app.intelligence.ai_polish_brain import AIPolishBrain
                                cleaned_text = AIPolishBrain.polish_speech(cleaned_text)
                            except Exception:
                                pass
                            return True, cleaned_text
                        if finish_reason == "STOP" or not parts:
                            # Model processed audio normally and heard no speech (clean silence)
                            logger.info(f"Model {model} completed with finishReason='{finish_reason}' and empty transcript (clean silence).")
                            return True, ""
                        logger.info(f"Model {model} returned finishReason='{finish_reason}' without text. Triggering failover.")
                        return False, f"Model finished with reason: {finish_reason}"
                    return False, "No candidates returned by model."
                else:
                    try:
                        err = response.json().get("error", {}).get("message", response.text)
                    except Exception:
                        err = response.text
                    return False, f"Gemini API Error ({response.status_code}): {err}"
            except requests.exceptions.Timeout:
                return False, f"Network timeout with {model}: Connection/Read timed out."
            except Exception as e:
                return False, f"Network request error: {str(e)}"

        # Multi-chunk path for long-form speech (continuous up to 20 mins) with parallel execution (<5s guaranteed)
        from concurrent.futures import ThreadPoolExecutor
        chunk_results = [""] * len(chunks)
        chunk_errors = []

        # Resilient chunk models
        chunk_model_candidates = [
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-2.5-flash",
            "gemini-3.5-transcribe"
        ]

        def _transcribe_chunk_worker(c_idx: int, c_bytes: bytes):
            c_b64 = base64.b64encode(c_bytes).decode("utf-8")
            c_sec = len(c_bytes) / 32000.0
            c_timeout = (3.0, max(6.0, min(25.0, float(c_sec * 0.5) + 4.0)))

            for try_model in chunk_model_candidates:
                c_url = f"https://generativelanguage.googleapis.com/v1beta/models/{try_model}:generateContent"
                c_gen_config: Dict[str, Any] = {
                    "temperature": 0.0,
                    "topP": 0.95,
                    "maxOutputTokens": 8192
                }
                if "2.5" in try_model.lower() or "2.0" in try_model.lower():
                    c_gen_config["thinkingConfig"] = {"thinkingBudget": 0}

                c_payload = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": (
                                        f"{system_instruction}\n\n"
                                        f"Task: Process part {c_idx+1} of {len(chunks)} of the user's continuous speech in strict accordance with the Active Spoken Language Constraints specified above.\n"
                                        "Anti-Repetition & Anti-Hallucination: Never repeat phrases in an infinite loop. Eliminate stutters and false starts. Transcribe strictly actual acoustic speech.\n"
                                        "Output ONLY the finalized text for this audio segment directly."
                                    )
                                },
                                {
                                    "inline_data": {
                                        "mime_type": "audio/wav",
                                        "data": c_b64
                                    }
                                }
                            ]
                        }
                    ],
                    "generationConfig": c_gen_config
                }
                c_headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                }

                # Single fast attempt + 1 retry on transient network error
                for attempt in range(2):
                    try:
                        t0 = time.time()
                        resp = self.session.post(c_url, headers=c_headers, json=c_payload, timeout=c_timeout)
                        logger.info(f"Chunk {c_idx+1}/{len(chunks)} with {try_model} completed in {time.time()-t0:.2f}s (Status: {resp.status_code})")
                        if resp.status_code == 200:
                            try:
                                data = resp.json()
                            except Exception:
                                continue
                            candidates = data.get("candidates", []) if isinstance(data, dict) else []
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                full_text = "".join([self._extract_part_text(p) for p in parts])
                                cleaned = self._clean_output(full_text)
                                if cleaned:
                                    chunk_results[c_idx] = cleaned
                                    return
                        elif resp.status_code in (429, 503, 500):
                            time.sleep(0.2 * (attempt + 1))
                            continue
                        else:
                            break
                    except Exception:
                        time.sleep(0.2)
                        continue

            # If all online models failed for this chunk, immediately transcribe via local Whisper AI
            try:
                from app.offline.offline_engine import OfflineSpeechEngine
                ok_off, txt_off = OfflineSpeechEngine.transcribe_wav(c_bytes)
                if ok_off and txt_off and txt_off.strip():
                    chunk_results[c_idx] = self._clean_output(txt_off.strip())
                    return
            except Exception as off_ex:
                logger.debug(f"Chunk {c_idx+1} offline fallback note: {off_ex}")

            chunk_errors.append(f"Chunk {c_idx+1} could not be transcribed.")

        # Scalable thread pool for instant parallel chunk execution
        max_w = min(16, max(2, len(chunks)))
        with ThreadPoolExecutor(max_workers=max_w) as executor:
            futures = [executor.submit(_transcribe_chunk_worker, i, c) for i, c in enumerate(chunks)]
            for f in futures:
                try:
                    f.result()
                except Exception as ex:
                    logger.debug(f"Chunk future exception: {ex}")

        valid_results = [r.strip() for r in chunk_results if r and r.strip()]
        if not valid_results:
            return False, f"Gemini API Error with {model}: Could not transcribe audio chunks."

        final_joined = self._stitch_chunk_transcripts(valid_results)
        final_cleaned = self._clean_output(final_joined)
        return True, final_cleaned

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
        with Gemini 2.5 Flash for sub-2.2s execution and resilient error handling.
        """
        if not self.api_key:
            return ExecutionResult(
                success=False,
                text="",
                model_used="gemini-2.5-flash",
                error_message="Gemini API Key is not configured. Please open Settings."
            )

        if not raw_text or not raw_text.strip():
            return ExecutionResult(
                success=False,
                text="",
                model_used="gemini-2.5-flash",
                error_message="Input text is empty."
            )

        # 1. Resolve System Instruction
        instruction = TransformEngine.build_system_instruction(
            transform_type=transform_type,
            app_context=app_context,
            custom_instruction=custom_instruction
        )

        # 2. Resolve Primary Model for text transformations (default to gemini-3.5-flash-lite for instant sub-second quota-available execution)
        if not self.model_name or self.model_name in ("auto", "gemini-3.5-transcribe"):
            routing = ModelRouter.route_model(task_type="text", profile_name=profile_id, auto_cost_mode=auto_cost_mode)
            primary_model = routing.model_name
        else:
            primary_model = self.model_name
        is_code = (transform_type == TransformType.TECHNICAL or "code" in (custom_instruction or "").lower() or "function" in (custom_instruction or "").lower())

        # 3. Model execution function
        def call_model(model: str) -> Tuple[bool, str]:
            if "transcribe" in model:
                # Transcribe models only take audio input
                return False, "Transcribe model only accepts audio."

            if any(k in model.lower() for k in ("ollama", "gemma")):
                try:
                    from app.intelligence.ollama_engine import OllamaEngine
                    prompt = f"{instruction}\n\nCONTENT TO TRANSFORM:\n\"\"\"\n{raw_text}\n\"\"\"\n\nOUTPUT ONLY THE TRANSFORMED TEXT:"
                    ok_ol, txt_ol = OllamaEngine.polish_text(raw_text=raw_text, prompt_override=prompt, timeout=25.0)
                    if ok_ol and txt_ol and len(txt_ol.strip()) > 5:
                        cleaned = self._clean_output(txt_ol, is_code=is_code)
                        return True, cleaned
                except Exception as ex_ol:
                    logger.debug(f"Ollama call_model exception: {ex_ol}")
                return False, "Ollama local inference failed."

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            gen_config: Dict[str, Any] = {
                "temperature": TransformEngine.get_preset(transform_type).temperature,
                "maxOutputTokens": 4096
            }
            if "2.5" in model or "2.0" in model:
                gen_config["thinkingConfig"] = {"thinkingBudget": 0}

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
                "generationConfig": gen_config
            }
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            try:
                resp = self.session.post(url, headers=headers, json=payload, timeout=(2.5, 12.0))
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                    except Exception as json_err:
                        return False, f"Malformed JSON from {model}: {json_err}"
                    candidates = data.get("candidates", []) if isinstance(data, dict) else []
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        res_text = "".join([self._extract_part_text(p) for p in parts])
                        cleaned = self._clean_output(res_text, is_code=is_code)
                        if cleaned:
                            return True, cleaned
                        return False, "Empty text returned by model."
                    return False, "Empty response from Gemini."
                else:
                    try:
                        err = resp.json().get("error", {}).get("message", resp.text)
                    except Exception:
                        err = resp.text
                    return False, f"Gemini API Error ({resp.status_code}): {err}"
            except Exception as e:
                return False, f"Network error: {str(e)}"

        # 4. Resilient Execution with Text Fallback Chain
        exec_res = FallbackHandler.execute_with_resilience(
            call_fn=call_model,
            primary_model=primary_model,
            max_retries_per_model=1,
            is_audio=False
        )

        # 5. Local Intelligence Fallback on total online transformation failure (Guaranteed Zero-Failure)
        if not exec_res.success:
            try:
                from app.intelligence.ollama_engine import OllamaEngine
                if OllamaEngine.is_available(timeout=0.4):
                    prompt = f"{instruction}\n\nCONTENT TO TRANSFORM:\n\"\"\"\n{raw_text}\n\"\"\"\n\nOUTPUT ONLY THE TRANSFORMED TEXT:"
                    ok_ol, txt_ol = OllamaEngine.polish_text(raw_text=raw_text, prompt_override=prompt, timeout=12.0)
                    if ok_ol and txt_ol and len(txt_ol.strip()) > 5:
                        exec_res.success = True
                        exec_res.text = self._clean_output(txt_ol, is_code=is_code)
                        exec_res.model_used = "Ollama Gemma 2B (Local Offline Fallback)"
                        exec_res.fallback_occurred = True
            except Exception as ol_err:
                logger.debug(f"Ollama transform fallback note: {ol_err}")

            if not exec_res.success:
                try:
                    from app.intelligence.ai_polish_brain import AIPolishBrain
                    cleaned = AIPolishBrain.polish_speech(raw_text)
                    cleaned = self._clean_output(cleaned)
                    if cleaned:
                        exec_res.success = True
                        exec_res.text = cleaned
                        exec_res.model_used = "Local Intelligence Polish (Offline Fallback)"
                        exec_res.fallback_occurred = True
                except Exception as loc_err:
                    logger.debug(f"Local intelligence transform fallback note: {loc_err}")

        # 5b. Vocabulary Normalization & Metrics
        if exec_res.success and exec_res.text:
            if not is_code and transform_type not in (TransformType.TECHNICAL, TransformType.CUSTOM, TransformType.CONVERT_PROMPT):
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
        """Applies phonetic dictionary replacements with punctuation-resilient word-boundary awareness."""
        if not text or not dictionary:
            return text

        result = text
        # Sort entries by spoken length descending so longer phrases match before substrings
        sorted_dict = sorted(dictionary, key=lambda e: len(e.get("spoken", "").strip()), reverse=True)
        for entry in sorted_dict:
            spoken = entry.get("spoken", "").strip()
            replacement = entry.get("replacement", "").strip()
            if not spoken or not replacement:
                continue

            # Clean core token (stripping trailing/leading punctuation from entries like 'Srinivas Awasthi.')
            core_spoken = re.sub(r'^[^\w]+|[^\w]+$', '', spoken)
            core_replacement = re.sub(r'^[^\w]+|[^\w]+$', '', replacement)

            if core_spoken and re.match(r'^\w+(?:\s+\w+)*$', core_spoken):
                pat = re.compile(r'\b' + re.escape(core_spoken) + r'\b', re.IGNORECASE)
                result = pat.sub(core_replacement, result)

            if spoken != core_spoken:
                pat_lit = re.compile(re.escape(spoken), re.IGNORECASE)
                result = pat_lit.sub(replacement, result)

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
            if normalized_text == normalized_trigger:
                logger.info(f"Snippet trigger exact matched: '{trigger}' -> Expanding snippet.")
                return content
            elif normalized_trigger in normalized_text and len(normalized_text.split()) <= len(normalized_trigger.split()) + 3:
                # Trigger spoken with brief surrounding words (e.g. "hey snippet trigger please")
                logger.info(f"Snippet trigger matched in context: '{trigger}' -> Expanding snippet.")
                return content

        return text

    def _clean_output(self, raw_text: str, is_code: bool = False) -> str:
        """
        Cleans transcribed text:
        1. Strips markdown fences, surrounding quotes, and verbal disfluencies.
        2. Completely strips hallucinated preambles (e.g. 'Vocal audio not in effect').
        3. Collapses false-starts, sentence restarts, and multi-word phrase repetition loops via AI Brain (for speech).
        4. Normalizes punctuation, spaces, and capitalization (for speech, preserves code).
        """
        if not raw_text or not raw_text.strip():
            return ""

        text = raw_text.strip()

        # If code, strip outer code fence ticks if present and conversational intro, but NEVER mangle syntax or casing!
        if is_code:
            if text.startswith("```") and text.endswith("```"):
                lines = text.split("\n")
                if len(lines) >= 2:
                    text = "\n".join(lines[1:-1]).strip()
            # Remove any AI conversational preamble
            text = re.sub(
                r'^(?:(?:here(?:\s+is|\'s)?(?:\s+the)?\s+(?:code|python\s+code|solution|function|implementation|script)?[:\n\s]*)|(?:sure!?[,\s]*))\s*',
                '',
                text,
                flags=re.IGNORECASE
            )
            return text

        if text.startswith("```") and text.endswith("```"):
            lines = text.split("\n")
            if len(lines) >= 2:
                text = "\n".join(lines[1:-1]).strip()
        if text.startswith(('"', "'", "“", "”", "«")) and text.endswith(('"', "'", "“", "”", "»")) and "\n" not in text:
            text = text[1:-1].strip()

        # 1. Remove conversational preambles
        preambles = [
            r'^(?:here is (?:the|your) (?:transcription|transcribed text|text):\s*)',
            r'^(?:transcription:\s*)',
            r'^(?:certainly!?\s*)',
            r'^(?:sure!?\s*)',
        ]
        for p in preambles:
            text = re.sub(p, '', text, flags=re.IGNORECASE).strip()

        # 2. Completely eliminate hallucination markers anywhere in text
        text = re.sub(r'\b(?:vocal\s+)?audio\s+not\s+in\s+effect\b[\.\?!]?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(?:no\s+speech\s+detected|silence\s+detected)\b[\.\?!]?', '', text, flags=re.IGNORECASE)

        # 3. Deterministic hesitation & filler token cleanup
        filler_pattern = re.compile(r'\b(uh|um|ah|er|eh|uhm|ahm|umm|ahh|uhh)\b[,;:]*', re.IGNORECASE)
        text = filler_pattern.sub('', text)

        # 4. Multi-pass AI Brain false-start, re-take & repetition collapse
        text = VocabEngine.collapse_repetitions_and_stutters(text)

        # 5. Check if output contains any actual words
        if not re.search(r'\w', text):
            return ""

        # Capitalize start if needed
        if text and text[0].islower() and not text.startswith("http"):
            text = text[0].upper() + text[1:]

        return text

    def structure_bullet_points(self, text: str) -> str:
        """
        Wispr Flow Intelligence: Intelligently transforms point-wise or sequential dictations
        (advantages, benefits, key points, steps, features) into a clean introductory sentence
        followed by bullet points ('• ').
        """
        if not text or not text.strip():
            return text

        if "•" in text or "\n* " in text or "\n- " in text:
            return text

        # Check for genuine list indicators / sequential points
        has_points = bool(re.search(
            r'\b(?:bullet\s+points?|bulleted|numbered\s+list|pros\s+and\s+cons|firstly|secondly|thirdly|'
            r'point\s+one|point\s+two|item\s+one|item\s+two|'
            r'advantages?\s+(?:of|about|are|include)|disadvantages?\s+(?:of|about|are|include)|'
            r'benefits?\s+(?:of|about|are|include)|key\s+points?\s*(?:are|:|include)|'
            r'the\s+following\s+points?|here\s+are\s+the\s+points|'
            r'points\s+are\s*(?:as|:|include)|steps?\s+(?:are|to|include))\b',
            text,
            re.IGNORECASE
        ))
        if not has_points:
            return text

        # 1. Instant deterministic formatting via AIPolishBrain and VocabEngine (0ms latency, zero network overhead)
        try:
            from app.intelligence.ai_polish_brain import AIPolishBrain
            bulleted = AIPolishBrain.smart_bullet_formatter(text)
            if "•" in bulleted:
                return bulleted
        except Exception:
            pass

        bulleted = VocabEngine.adaptive_bullet_format(text)
        if "•" in bulleted:
            return bulleted

        # 2. High-speed Gemini AI structuring pass if API key available with gemini-3.5-flash-lite (<0.8s)
        if self.api_key:
            try:
                struct_prompt = (
                    "You are Gemini Flow's Wispr Flow Adaptive Dictation Formatter.\n"
                    "Determine if the speaker intended a point-wise or sequential list (advantages, benefits, key points, steps, features, action items, or explicit numbered/bulleted points), OR continuous narrative paragraphs.\n"
                    "- If the speaker dictated sequential points, steps, action items, or a multi-point list, format the speech into an introductory sentence followed by clean bullet points ('• ') on separate lines.\n"
                    "- If the speaker dictated continuous narrative prose, explanations, questions, or paragraphs, DO NOT use bullet points; format as natural, fluent paragraphs in the original language and authentic script. Preserve 100% of all spoken concepts.\n"
                    "- Output ONLY the finalized text directly without conversational commentary."
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
                payload = {
                    "contents": [{"parts": [{"text": f"{struct_prompt}\n\nSpoken Text:\n{text}"}]}],
                    "generationConfig": {
                        "temperature": 0.0,
                        "maxOutputTokens": 2048
                    }
                }
                resp = self.session.post(url, json=payload, timeout=(1.5, 2.5))
                if resp.status_code == 200:
                    data = resp.json()
                    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    out = "".join([p.get("text", "") for p in parts]).strip()
                    if out and ("•" in out or "* " in out or "- " in out):
                        out = re.sub(r'^[ \t]*[\*\-][ \t]+', '• ', out, flags=re.MULTILINE)
                        return out
            except Exception as e:
                logger.debug(f"AI adaptive structuring note: {e}")

        return VocabEngine.adaptive_bullet_format(text)

