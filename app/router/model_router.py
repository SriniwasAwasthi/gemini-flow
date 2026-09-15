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
    "gemini-3.5-flash-lite": ModelMetadata(
        model_name="gemini-3.5-flash-lite",
        display_name="Gemini 3.5 Flash-Lite (Blazing Fast)",
        speed_rating=5,
        typical_latency="~0.8s",
        punctuation_style="Commas, periods, 100% filler removal (Lowest Latency)",
        reasoning_capability="low",
        technical_capability="standard",
        recommended_tasks=["Instant chat", "WhatsApp", "ChatGPT", "Antigravity", "quick search", "real-time typing"]
    ),
    "gemini-3.6-flash": ModelMetadata(
        model_name="gemini-3.6-flash",
        display_name="Gemini 3.6 Flash (Fast Advanced Reasoning)",
        speed_rating=4,
        typical_latency="~1.3s",
        punctuation_style="Executive polish, flawless grammar, rich punctuation, prompt synthesis",
        reasoning_capability="high",
        technical_capability="high",
        recommended_tasks=["Executive polish", "formal client proposals", "high-impact prompt engineering", "grammar upgrade"]
    ),
    "gemini-3.5-flash": ModelMetadata(
        model_name="gemini-3.5-flash",
        display_name="Gemini 3.5 Flash (Balanced Dictation)",
        speed_rating=4,
        typical_latency="~1.5s",
        punctuation_style="Refined flow, semicolons, compound sentences",
        reasoning_capability="balanced",
        technical_capability="high",
        recommended_tasks=["Daily emails", "PR descriptions", "prompt crafting", "clean notes"]
    ),
    "gemini-flash-latest": ModelMetadata(
        model_name="gemini-flash-latest",
        display_name="Gemini Flash Latest (Production Auto)",
        speed_rating=4,
        typical_latency="~1.6s",
        punctuation_style="Smooth conversational phrasing, standard capitalization",
        reasoning_capability="balanced",
        technical_capability="high",
        recommended_tasks=["General purpose workflow", "stable everyday dictation"]
    ),
    "gemini-3.7-flash": ModelMetadata(
        model_name="gemini-3.7-flash",
        display_name="Gemini 3.7 Flash (Technical & Coding)",
        speed_rating=3,
        typical_latency="~2.1s",
        punctuation_style="Colons, technical syntax, camelCase/snake_case formatting",
        reasoning_capability="high",
        technical_capability="expert",
        recommended_tasks=["IDE code comments", "developer documentation", "technical instructions", "VS Code / coding"]
    ),
    "gemini-2.5-flash": ModelMetadata(
        model_name="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash (Rich Textbook Punctuation)",
        speed_rating=3,
        typical_latency="~2.5s",
        punctuation_style="Textbook grammar, semicolons, formal clause balance",
        reasoning_capability="high",
        technical_capability="standard",
        recommended_tasks=["Formal correspondence", "legal & academic writing", "textbook grammar"]
    ),
    "gemini-2.5-pro": ModelMetadata(
        model_name="gemini-2.5-pro",
        display_name="Gemini 2.5 Pro (Deep Thought & Documents)",
        speed_rating=2,
        typical_latency="~5.0s",
        punctuation_style="Automatic outlines, bullets, multi-paragraph synthesis",
        reasoning_capability="deep",
        technical_capability="expert",
        recommended_tasks=["Long dictations (1-5m)", "essays", "meeting recaps", "action item breakdowns"]
    ),
}


@dataclass
class RoutingResult:
    model_name: str
    metadata: ModelMetadata
    reason: str
    is_auto: bool = True
    confidence: float = 1.0


class ModelRouter:
    """Centralized routing layer for automatic and manual Gemini model selection."""
    def __init__(self, default_model: str = "gemini-3.5-flash-lite"):
        self.default_model = default_model
        self.model_registry = MODEL_REGISTRY

    def get_metadata(self, model_name: str) -> ModelMetadata:
        return self.model_registry.get(model_name, self.model_registry["gemini-3.5-flash-lite"])

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
        Supports manual override when requested, defaulting to intelligent automatic routing
        with optional Auto Cost Mode optimization.
        """
        # 1. Check explicit manual override
        if manual_override and manual_override != "auto":
            clean_name = manual_override.strip()
            if clean_name in self.model_registry:
                meta = self.model_registry[clean_name]
                return RoutingResult(
                    model_name=clean_name,
                    metadata=meta,
                    reason="Manual user override selection",
                    is_auto=False
                )

        # 2. Auto Cost Mode Optimization Strategy
        # Favors ultra-inexpensive/fast models for trivial requests and reserves expensive models for long/complex work
        if auto_cost_mode:
            task = (task_type or "").upper()
            if task in ("SUMMARIZE", "CONVERT_TO_DOCUMENTATION") and (duration_sec > 60.0 or text_length > 2000):
                return RoutingResult(
                    model_name="gemini-3.6-flash",
                    metadata=self.model_registry["gemini-3.6-flash"],
                    reason="Auto Cost Mode: Selected 3.6 Flash for deep long-form document synthesis",
                    is_auto=True
                )
            if task in ("GENERATE_CODE", "CODE_ASSISTANT") and duration_sec > 30.0:
                return RoutingResult(
                    model_name="gemini-3.7-flash",
                    metadata=self.model_registry["gemini-3.7-flash"],
                    reason="Auto Cost Mode: Heavy code task routed to 3.7 Flash",
                    is_auto=True
                )
            # All other dictation & standard prompt generation routed to ultra-cost-efficient Flash-Lite
            return RoutingResult(
                model_name="gemini-3.5-flash-lite",
                metadata=self.model_registry["gemini-3.5-flash-lite"],
                reason="Auto Cost Mode: Selected ultra-inexpensive & lowest-latency model (<1.2s, 85% cost savings)",
                is_auto=True
            )

        # 3. Standard Intelligent Router (Quality & Context Optimization)
        task = (task_type or "").upper()
        if task in ("GENERATE_CODE", "CODE_ASSISTANT", "EXPLAIN", "CREATE_GITHUB_ISSUE", "CREATE_GITHUB_PR"):
            return RoutingResult(
                model_name="gemini-3.7-flash",
                metadata=self.model_registry["gemini-3.7-flash"],
                reason=f"Technical task '{task}' routed to High-Reasoning Technical model",
                is_auto=True
            )

        if task in ("SUMMARIZE", "CREATE_TASK", "CONVERT_TO_DOCUMENTATION") or duration_sec > 45.0 or text_length > 1500:
            return RoutingResult(
                model_name="gemini-3.6-flash",
                metadata=self.model_registry["gemini-3.6-flash"],
                reason="Deep synthesis / Long input routed to High-Reasoning 3.6 Flash",
                is_auto=True
            )

        if task in ("PROFESSIONALIZE", "ACADEMIC", "FIX_GRAMMAR", "FORMAL"):
            return RoutingResult(
                model_name="gemini-2.5-flash",
                metadata=self.model_registry["gemini-2.5-flash"],
                reason="Formal grammar & rich punctuation task routed to Textbook Flash model",
                is_auto=True
            )

        if task in ("CREATE_PROMPT", "PROMPT_ENHANCER", "CONVERT_TO_EMAIL"):
            return RoutingResult(
                model_name="gemini-3.5-flash",
                metadata=self.model_registry["gemini-3.5-flash"],
                reason="Structured prompt/email crafting routed to Balanced Flash model",
                is_auto=True
            )

        # 3. Evaluate Application Context
        cat = (app_category or "").lower()
        app_lower = (app_name or "").lower()

        # Antigravity IDE optimization: Ultra-fast <1.2s voice dictation
        if "antigravity" in app_lower:
            return RoutingResult(
                model_name="gemini-3.5-flash-lite",
                metadata=self.model_registry["gemini-3.5-flash-lite"],
                reason="Antigravity voice dictation optimized for Ultra-Low Latency (<1.2s)",
                is_auto=True
            )

        if cat == "communication" or any(c in app_lower for c in ["whatsapp", "telegram", "slack", "discord"]):
            return RoutingResult(
                model_name="gemini-3.5-flash-lite",
                metadata=self.model_registry["gemini-3.5-flash-lite"],
                reason=f"Real-time messaging ({app_name}) routed to Low-Latency Flash-Lite",
                is_auto=True
            )

        if cat == "email" or "outlook" in app_lower or "mail" in app_lower:
            return RoutingResult(
                model_name="gemini-3.5-flash",
                metadata=self.model_registry["gemini-3.5-flash"],
                reason=f"Email context ({app_name}) routed to Balanced Flash",
                is_auto=True
            )

        if cat == "dev" or "code" in app_lower or "terminal" in app_lower or "powershell" in app_lower:
            # For rapid cursor typing / brief speech (<25s), use ultra-fast Flash-Lite
            if duration_sec < 25.0 and text_length < 600:
                return RoutingResult(
                    model_name="gemini-3.5-flash-lite",
                    metadata=self.model_registry["gemini-3.5-flash-lite"],
                    reason=f"Developer app ({app_name}) dictation optimized for Ultra-Fast typing (<1.2s)",
                    is_auto=True
                )
            return RoutingResult(
                model_name="gemini-3.7-flash",
                metadata=self.model_registry["gemini-3.7-flash"],
                reason=f"Active Developer app ({app_name}) extended input routed to Technical 3.7 Flash",
                is_auto=True
            )

        # 4. Evaluate Productivity Profile
        p_name = (profile_name or "").lower()
        if p_name in ("engineering", "coding"):
            if duration_sec < 25.0 and text_length < 600:
                chosen = "gemini-3.5-flash-lite"
                reason = f"Profile '{profile_name}' dictation optimized for Ultra-Fast speed (<1.2s)"
            else:
                chosen = "gemini-3.7-flash"
                reason = f"Profile '{profile_name}' extended dictation routed to Technical 3.7 Flash"
        elif p_name == "academic":
            chosen = "gemini-2.5-flash"
            reason = "Academic profile prioritizes textbook grammar & formal punctuation"
        elif p_name == "casual":
            chosen = "gemini-3.5-flash-lite"
            reason = "Casual profile prioritizes instant response speed"
        else:
            # Default / Professional: balanced between speed and grammar
            if duration_sec < 8.0 and text_length < 250:
                chosen = "gemini-3.5-flash-lite"
                reason = "Brief dictation routed to Ultra-Fast Flash-Lite"
            else:
                chosen = "gemini-3.5-flash"
                reason = "Standard dictation routed to Balanced 3.5 Flash"

        meta = self.model_registry.get(chosen, self.model_registry["gemini-3.5-flash-lite"])
        return RoutingResult(
            model_name=chosen,
            metadata=meta,
            reason=reason,
            is_auto=True
        )

    def mark_model_health(self, model_name: str, status: str):
        """Updates availability state for dynamic reliability routing."""
        if model_name in self.model_registry:
            self.model_registry[model_name].availability = status
            logger.info(f"Model {model_name} status updated to: {status}")
