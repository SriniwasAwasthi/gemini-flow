"""
Reliability & Fallback System for Gemini Flow.
Implements exponential backoff on 500/503/timeouts, instant model failover
on 429 rate limits, clipboard insertion fallbacks, and plain-English messaging.
"""
import time
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Callable, Tuple, Any

import pyperclip

logger = logging.getLogger("GeminiFlow.Reliability")


class APIErrorType(str, Enum):
    RATE_LIMIT_429 = "RATE_LIMIT_429"
    SERVER_UNAVAILABLE_503 = "SERVER_UNAVAILABLE_503"
    INTERNAL_SERVER_ERROR_500 = "INTERNAL_SERVER_ERROR_500"
    TIMEOUT = "TIMEOUT"
    INVALID_KEY = "INVALID_KEY"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN = "UNKNOWN"


@dataclass
class FallbackReason:
    original_model: str
    fallback_model: str
    error_type: APIErrorType
    user_message: str


@dataclass
class ExecutionResult:
    success: bool
    text: str
    model_used: str
    fallback_occurred: bool = False
    fallback_reason: Optional[FallbackReason] = None
    latency_seconds: float = 0.0
    retries_attempted: int = 0
    error_message: str = ""


# Fallback hierarchy progression: heavy/advanced models step down to resilient flash tiers
MODEL_FALLBACK_CHAINS = {
    "gemini-2.5-pro": ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash"],
    "gemini-3.7-flash": ["gemini-3.5-flash-lite", "gemini-3.5-flash"],
    "gemini-2.5-flash": ["gemini-3.5-flash-lite", "gemini-3.5-flash"],
    "gemini-3.6-flash": ["gemini-3.5-flash-lite", "gemini-3.5-flash"],
    "gemini-3.5-flash": ["gemini-3.5-flash-lite", "gemini-3.6-flash"],
    "gemini-3.5-flash-lite": ["gemini-3.5-flash", "gemini-3.6-flash"]
}


class FallbackHandler:
    """Manages resilient execution of Gemini API requests and graceful UI degradations."""

    @staticmethod
    def get_fallback_chain(primary_model: str) -> List[str]:
        chain = [primary_model]
        fallbacks = MODEL_FALLBACK_CHAINS.get(primary_model, ["gemini-3.5-flash-lite", "gemini-3.5-flash"])
        for m in fallbacks:
            if m not in chain:
                chain.append(m)
        return chain

    @staticmethod
    def classify_error(status_code: int, error_text: str) -> Tuple[APIErrorType, str]:
        lower_err = (error_text or "").lower()

        if status_code == 429 or "429" in lower_err or "quota" in lower_err or "resource_exhausted" in lower_err:
            return (
                APIErrorType.RATE_LIMIT_429,
                "API rate limit reached. Switched to high-throughput fallback model automatically."
            )
        elif status_code == 503 or "503" in lower_err or "overloaded" in lower_err or "high demand" in lower_err:
            return (
                APIErrorType.SERVER_UNAVAILABLE_503,
                "Gemini service is experiencing high traffic. Retrying connection..."
            )
        elif status_code == 500 or "500" in lower_err or "internal" in lower_err:
            return (
                APIErrorType.INTERNAL_SERVER_ERROR_500,
                "Gemini internal server error. Retrying with fallback model..."
            )
        elif "timeout" in lower_err or "timed out" in lower_err:
            return (
                APIErrorType.TIMEOUT,
                "Request timed out. Falling back to faster model."
            )
        elif status_code in (400, 403) and ("key" in lower_err or "unregistered" in lower_err or "unauthorized" in lower_err):
            return (
                APIErrorType.INVALID_KEY,
                "API key is invalid or lacks access. Please verify in Settings."
            )
        elif "connection" in lower_err or "failed to establish" in lower_err:
            return (
                APIErrorType.NETWORK_ERROR,
                "Network connection lost. Please check your internet access."
            )

        return (
            APIErrorType.UNKNOWN,
            f"API Error ({status_code}): {error_text[:120] if error_text else 'Unknown error'}"
        )

    @classmethod
    def execute_with_resilience(
        cls,
        call_fn: Callable[[str], Tuple[bool, str]],
        primary_model: str,
        max_retries_per_model: int = 2
    ) -> ExecutionResult:
        """
        Executes an API call function `call_fn(model_name) -> (success, text_or_error)`.
        Automatically handles retries with exponential backoff on 500/503/timeouts,
        and seamlessly switches models on 429/failures.
        """
        models_to_try = cls.get_fallback_chain(primary_model)
        start_overall = time.time()
        retries_count = 0
        last_error_msg = ""
        fallback_occurred = False
        fallback_reason = None

        for idx, model in enumerate(models_to_try):
            if idx > 0 and not fallback_occurred:
                fallback_occurred = True

            for attempt in range(max_retries_per_model):
                try:
                    success, text_or_err = call_fn(model)
                    if success:
                        elapsed = time.time() - start_overall
                        return ExecutionResult(
                            success=True,
                            text=text_or_err,
                            model_used=model,
                            fallback_occurred=fallback_occurred,
                            fallback_reason=fallback_reason,
                            latency_seconds=elapsed,
                            retries_attempted=retries_count
                        )
                    else:
                        last_error_msg = text_or_err
                        # Parse status code if in format "Gemini API Error (XYZ): ..."
                        status_code = 0
                        import re
                        m = re.search(r'\((\d{3})\)', text_or_err)
                        if m:
                            status_code = int(m.group(1))

                        err_type, friendly_msg = cls.classify_error(status_code, text_or_err)

                        # If rate limit 429, do not waste time retrying this model; fail over immediately!
                        if err_type == APIErrorType.RATE_LIMIT_429:
                            logger.warning(f"Model {model} hit rate limit. Instant failover to next model.")
                            fallback_reason = FallbackReason(
                                original_model=primary_model,
                                fallback_model=models_to_try[idx + 1] if idx + 1 < len(models_to_try) else "none",
                                error_type=err_type,
                                user_message=friendly_msg
                            )
                            break  # Move to next model immediately

                        # If invalid API key, fail out completely
                        if err_type == APIErrorType.INVALID_KEY:
                            return ExecutionResult(
                                success=False,
                                text="",
                                model_used=model,
                                error_message=friendly_msg,
                                latency_seconds=time.time() - start_overall,
                                retries_attempted=retries_count
                            )

                        # On 500/503/Timeout: retry with exponential backoff
                        if attempt < max_retries_per_model - 1:
                            retries_count += 1
                            backoff = 0.4 * (2 ** attempt)
                            logger.info(f"Retrying {model} in {backoff:.2f}s due to: {friendly_msg}")
                            time.sleep(backoff)
                        else:
                            fallback_reason = FallbackReason(
                                original_model=primary_model,
                                fallback_model=models_to_try[idx + 1] if idx + 1 < len(models_to_try) else "none",
                                error_type=err_type,
                                user_message=friendly_msg
                            )

                except Exception as ex:
                    last_error_msg = str(ex)
                    retries_count += 1
                    time.sleep(0.3)

        elapsed = time.time() - start_overall
        _, friendly_final = cls.classify_error(0, last_error_msg)
        return ExecutionResult(
            success=False,
            text="",
            model_used=models_to_try[-1],
            fallback_occurred=fallback_occurred,
            fallback_reason=fallback_reason,
            latency_seconds=elapsed,
            retries_attempted=retries_count,
            error_message=friendly_final
        )

    @staticmethod
    def safe_insert_text(text: str, insert_action: Callable[[], None]) -> Tuple[bool, str]:
        """
        Executes text insertion. If insertion fails or window loses focus,
        safely persists text to the system clipboard and notifies user.
        """
        try:
            # First, copy to clipboard so the text is safe no matter what
            pyperclip.copy(text)
            # Execute keyboard paste action
            insert_action()
            return True, "Inserted successfully"
        except Exception as e:
            logger.warning(f"Direct insertion failed ({e}). Text is safe on clipboard.")
            try:
                pyperclip.copy(text)
                return True, "Copied to clipboard (direct insertion unavailable)"
            except Exception as clip_err:
                logger.error(f"Clipboard fallback failed: {clip_err}")
                return False, f"Insertion error: {e}"
