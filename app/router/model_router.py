"""
Intelligent AI Model Router for Gemini Flow.
Centralized routing layer that dynamically selects the optimal Gemini model
based on task type, input complexity, length, application context, and productivity profile.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger("GeminiFlow.ModelRouter")


@dataclass
class ModelMetadata:
    model_name: str
    display_name: str
    speed_rating: int          # 1 to 5 (5 = fastest)
    typical_latency: str       # e.g. "~1.2s"
    punctuation_style: str
    reasoning_capability: str  # "low", "balanced", "high", "deep"
    technical_capability: str  # "standard", "high", "expert"
    recommended_tasks: List[str]
    availability: str = "healthy"  # "healthy", "degraded", "unavailable"


MODEL_REGISTRY: Dict[str, ModelMetadata] = {
    "gemini-2.5-flash": ModelMetadata(
        model_name="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash (Flagship: 1.2s – 1.8s)",
        speed_rating=5,
        typical_latency="1.2s – 1.8s",
        punctuation_style="Flawless real-time speech transcription, semicolons, colons, code blocks, zero repetition",
        reasoning_capability="high",
        technical_capability="expert",
        recommended_tasks=["Universal dictation", "Antigravity coding", "ChatGPT prompts", "WhatsApp executive polish", "Long-form 20-min audio"]
    ),
    "gemini-flash-latest": ModelMetadata(
        model_name="gemini-flash-latest",
        display_name="Gemini Flash Latest (Production Auto: ~1.2s – 1.6s)",
        speed_rating=5,
        typical_latency="~1.2s – 1.6s",
        punctuation_style="Structured prose, clear punctuation, high throughput",
        reasoning_capability="high",
        technical_capability="high",
        recommended_tasks=["General purpose workflow", "stable everyday dictation", "High concurrency"]
    ),
    "gemini-flash-lite-latest": ModelMetadata(
        model_name="gemini-flash-lite-latest",
        display_name="Gemini Flash Lite (Ultra-Fast: ~0.9s – 1.3s)",
        speed_rating=5,
        typical_latency="~0.9s – 1.3s",
        punctuation_style="Rapid streaming transcription, clean formatting",
        reasoning_capability="balanced",
        technical_capability="high",
        recommended_tasks=["Instant quick dictation", "High-speed voice notes", "Sub-second typing"]
    )
}


@dataclass
class RoutingResult:
    model_name: str
    metadata: ModelMetadata
    reason: str
    is_auto: bool = True
    confidence: float = 1.0


class ModelRouter:
    """Centralized routing layer force-bound to Gemini 2.5 Flash for sub-2.2s latency and zero-drop dictation."""
    def __init__(self, default_model: str = "gemini-2.5-flash"):
        self.default_model = default_model
        self.model_registry = MODEL_REGISTRY

    def get_metadata(self, model_name: str) -> ModelMetadata:
        return self.model_registry.get(model_name, self.model_registry["gemini-2.5-flash"])

    @classmethod
    def route_model(
        cls,
        task_type: str = "dictate",
        duration_sec: float = 0.0,
        text_length: int = 0,
        app_name: str = "General",
        app_category: str = "general",
        profile_name: str = "Engineering",
        manual_override: Optional[str] = None,
        auto_cost_mode: bool = False
    ) -> RoutingResult:
        """Classmethod helper for quick routing."""
        router = cls()
        return router.route(
            task_type=task_type,
            duration_sec=duration_sec,
            text_length=text_length,
            app_name=app_name,
            app_category=app_category,
            profile_name=profile_name,
            manual_override=manual_override,
            auto_cost_mode=auto_cost_mode
        )

    def route(
        self,
        task_type: str = "dictate",
        duration_sec: float = 0.0,
        text_length: int = 0,
        app_name: str = "General",
        app_category: str = "general",
        profile_name: str = "Engineering",
        manual_override: Optional[str] = None,
        auto_cost_mode: bool = False
    ) -> RoutingResult:
        """
        Determines the most appropriate Gemini model.
        Force-binds the execution context to gemini-2.5-flash for all active text and audio processing pipelines.
        """
        meta = self.model_registry.get("gemini-2.5-flash", list(self.model_registry.values())[0])

        # 1. Check explicit manual override if not 'auto'
        if manual_override and manual_override != "auto" and manual_override in self.model_registry:
            return RoutingResult(
                model_name=manual_override,
                metadata=self.model_registry[manual_override],
                reason="Manual user override selection",
                is_auto=False
            )

        task = (task_type or "dictate").upper()
        app_lower = (app_name or "").lower()
        prof_lower = (profile_name or "").lower()

        # 2. Voice Audio Dictation Routing (Dynamic application & profile adaptation)
        if task in ("DICTATE", "VOICE", "TRANSCRIPTION", "SPEECH", "AUDIO"):
            # Antigravity Developer Environment -> Gemini 2.5 Flash
            if "antigravity" in app_lower:
                return RoutingResult(
                    model_name="gemini-2.5-flash",
                    metadata=meta,
                    reason="Antigravity environment: Configured for Gemini 2.5 Flash developer model",
                    is_auto=True
                )

            # WhatsApp -> Gemini 2.5 Flash Professional Model
            if "whatsapp" in app_lower:
                return RoutingResult(
                    model_name="gemini-2.5-flash",
                    metadata=meta,
                    reason="WhatsApp: Configured for Gemini 2.5 Flash professional executive model",
                    is_auto=True
                )

            # ChatGPT & Claude AI Chat -> Gemini 2.5 Flash
            if "chatgpt" in app_lower or "claude" in app_lower:
                return RoutingResult(
                    model_name="gemini-2.5-flash",
                    metadata=meta,
                    reason="AI Chat interface: Configured for Gemini 2.5 Flash prompt synthesis",
                    is_auto=True
                )

            # Professional, Engineering, Academic, or LinkedIn
            if prof_lower in ("professional", "engineering", "academic", "coding") or "linkedin" in app_lower:
                return RoutingResult(
                    model_name="gemini-2.5-flash",
                    metadata=meta,
                    reason=f"Profile '{profile_name}': Configured for Gemini 2.5 Flash",
                    is_auto=True
                )

            # Long-form dictation (up to 20 mins)
            if duration_sec > 60.0:
                return RoutingResult(
                    model_name="gemini-2.5-flash",
                    metadata=meta,
                    reason="Continuous multi-minute audio payload routed to high-throughput Gemini 2.5 Flash",
                    is_auto=True
                )

            # Fast real-time dictation
            return RoutingResult(
                model_name="gemini-2.5-flash",
                metadata=meta,
                reason="Voice dictation force-bound to Gemini 2.5 Flash (Target latency: 1.3s – 2.2s)",
                is_auto=True
            )

        # 3. Text Transformations & Higher Reasoning Tasks
        if task in ("GENERATE_CODE", "CODE_ASSISTANT", "EXPLAIN", "CREATE_GITHUB_ISSUE", "CREATE_GITHUB_PR"):
            return RoutingResult(
                model_name="gemini-2.5-flash",
                metadata=meta,
                reason=f"Technical task '{task}' routed to Gemini 2.5 Flash",
                is_auto=True
            )

        if task in ("SUMMARIZE", "CREATE_TASK", "CONVERT_TO_DOCUMENTATION") or duration_sec > 45.0 or text_length > 1500:
            return RoutingResult(
                model_name="gemini-2.5-flash",
                metadata=meta,
                reason="Deep synthesis / Long input routed to high-capacity Gemini 2.5 Flash",
                is_auto=True
            )

        if task in ("PROFESSIONALIZE", "ACADEMIC", "FIX_GRAMMAR", "FORMAL"):
            return RoutingResult(
                model_name="gemini-2.5-flash",
                metadata=meta,
                reason="Formal grammar & rich punctuation task routed to Gemini 2.5 Flash",
                is_auto=True
            )

        if task in ("CREATE_PROMPT", "PROMPT_ENHANCER", "CONVERT_TO_EMAIL"):
            return RoutingResult(
                model_name="gemini-2.5-flash",
                metadata=meta,
                reason="Structured prompt/email crafting routed to Gemini 2.5 Flash",
                is_auto=True
            )

        # Default fallback
        return RoutingResult(
            model_name="gemini-2.5-flash",
            metadata=meta,
            reason="Default execution context force-bound to Gemini 2.5 Flash",
            is_auto=True
        )

    def mark_model_health(self, model_name: str, status: str):
        """Updates availability state for dynamic reliability routing."""
        if model_name in self.model_registry:
            self.model_registry[model_name].availability = status
            logger.info(f"Model {model_name} status updated to: {status}")
