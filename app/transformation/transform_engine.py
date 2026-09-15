"""
Universal Text Transformation Engine for Gemini Flow.
Provides 16 built-in transformation operations capable of modifying selected
or dictated text anywhere on Windows.
"""
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, Any, List

from app.intelligence.app_intelligence import AppContext
from app.router.model_router import ModelRouter

logger = logging.getLogger("GeminiFlow.TransformEngine")


class TransformType(str, Enum):
    IMPROVE = "IMPROVE"
    FIX_GRAMMAR = "FIX_GRAMMAR"
    PROFESSIONAL = "PROFESSIONAL"
    CASUAL = "CASUAL"
    CONCISE = "CONCISE"
    EXPAND = "EXPAND"
    SUMMARIZE = "SUMMARIZE"
    EXPLAIN = "EXPLAIN"
    TECHNICAL = "TECHNICAL"
    CONVERT_PROMPT = "CONVERT_PROMPT"
    PROMPT = "CONVERT_PROMPT"
    CONVERT_EMAIL = "CONVERT_EMAIL"
    CONVERT_GITHUB_ISSUE = "CONVERT_GITHUB_ISSUE"
    CONVERT_GITHUB_PR = "CONVERT_GITHUB_PR"
    CONVERT_DOCS = "CONVERT_DOCS"
    CONVERT_NOTES = "CONVERT_NOTES"
    CUSTOM = "CUSTOM"


@dataclass
class TransformPreset:
    type: TransformType
    title: str
    description: str
    system_instruction: str
    recommended_model: str
    temperature: float = 0.3
    icon: str = "✨"


TRANSFORM_PRESETS: Dict[TransformType, TransformPreset] = {
    TransformType.IMPROVE: TransformPreset(
        type=TransformType.IMPROVE,
        title="Improve Writing",
        description="Enhance clarity, flow, vocabulary, and readability while preserving meaning.",
        system_instruction=(
            "You are an elite copy editor. Improve the following text for clarity, cadence, "
            "and elegance. Keep the core meaning unchanged. Output ONLY the improved text."
        ),
        recommended_model="gemini-3.5-flash",
        temperature=0.3,
        icon="✨"
    ),
    TransformType.FIX_GRAMMAR: TransformPreset(
        type=TransformType.FIX_GRAMMAR,
        title="Fix Grammar & Spelling",
        description="Correct all punctuation, grammar, and typos with zero semantic distortion.",
        system_instruction=(
            "Proofread the following text. Correct all spelling, punctuation, capitalization, and "
            "grammatical errors. Do not alter intentional vocabulary or tone. Output ONLY the corrected text."
        ),
        recommended_model="gemini-2.5-flash",
        temperature=0.1,
        icon="✅"
    ),
    TransformType.PROFESSIONAL: TransformPreset(
        type=TransformType.PROFESSIONAL,
        title="Make Professional",
        description="Transform informal drafts into polished, high-impact executive prose.",
        system_instruction=(
            "Rewrite the following text in a polished, professional, and authoritative business tone. "
            "Eliminate slang, casual filler, and emotional vagueness. Output ONLY the rewritten text."
        ),
        recommended_model="gemini-2.5-flash",
        temperature=0.3,
        icon="👔"
    ),
    TransformType.CASUAL: TransformPreset(
        type=TransformType.CASUAL,
        title="Make Casual",
        description="Rephrase into friendly, warm, conversational text.",
        system_instruction=(
            "Rephrase the following text in a warm, relaxed, and conversational tone suitable for direct "
            "messaging or quick team syncs. Output ONLY the rewritten text."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.4,
        icon="☕"
    ),
    TransformType.CONCISE: TransformPreset(
        type=TransformType.CONCISE,
        title="Make Concise",
        description="Cut redundant words and fluff while retaining core information.",
        system_instruction=(
            "Condense the following text to its leanest, punchiest form. Remove all superfluous words "
            "and fluff while keeping 100% of essential facts. Output ONLY the concise text."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.2,
        icon="✂️"
    ),
    TransformType.EXPAND: TransformPreset(
        type=TransformType.EXPAND,
        title="Expand & Elaborate",
        description="Add thorough depth, clear explanations, and supporting nuance.",
        system_instruction=(
            "Elaborate upon the provided text with rich context, supporting nuance, and comprehensive "
            "detail. Output ONLY the expanded content."
        ),
        recommended_model="gemini-3.6-flash",
        temperature=0.5,
        icon="📖"
    ),
    TransformType.SUMMARIZE: TransformPreset(
        type=TransformType.SUMMARIZE,
        title="Summarize",
        description="Generate clean bullet-point summary with key takeaways.",
        system_instruction=(
            "Summarize the provided content into a tight executive summary with high-signal bullet "
            "points highlighting core conclusions and action items. Output ONLY the summary."
        ),
        recommended_model="gemini-3.6-flash",
        temperature=0.2,
        icon="📋"
    ),
    TransformType.EXPLAIN: TransformPreset(
        type=TransformType.EXPLAIN,
        title="Explain Clearly",
        description="Break down complex concepts or code with step-by-step clarity.",
        system_instruction=(
            "Explain the following concept, code snippet, or argument in crystal-clear, structured terms. "
            "Use intuitive metaphors where appropriate. Output ONLY the explanation."
        ),
        recommended_model="gemini-3.7-flash",
        temperature=0.3,
        icon="💡"
    ),
    TransformType.TECHNICAL: TransformPreset(
        type=TransformType.TECHNICAL,
        title="Technical Standard",
        description="Refine text using rigorous engineering and technical terminology.",
        system_instruction=(
            "Rewrite the following text adhering to rigorous software engineering and technical "
            "documentation standards. Use accurate terminology and clear specifications. Output ONLY the text."
        ),
        recommended_model="gemini-3.7-flash",
        temperature=0.2,
        icon="⚙️"
    ),
    TransformType.CONVERT_PROMPT: TransformPreset(
        type=TransformType.CONVERT_PROMPT,
        title="Convert to AI Prompt",
        description="Craft an optimized, high-fidelity system/user prompt from raw notes.",
        system_instruction=(
            "You are a Principal AI Prompt Engineer. Transform the user's raw notes or request into an "
            "optimized, high-performance AI prompt structured with Role, Context, Objective, Constraints, "
            "and Output Format."
        ),
        recommended_model="gemini-3.5-flash",
        temperature=0.3,
        icon="🧠"
    ),
    TransformType.CONVERT_EMAIL: TransformPreset(
        type=TransformType.CONVERT_EMAIL,
        title="Convert to Email",
        description="Format into an email with subject line, greeting, and sign-off.",
        system_instruction=(
            "Convert the user's thoughts into a polished email. Include a compelling 'Subject: ' line, "
            "appropriate salutation, clean body paragraphs, and professional closing."
        ),
        recommended_model="gemini-3.5-flash",
        temperature=0.3,
        icon="✉️"
    ),
    TransformType.CONVERT_GITHUB_ISSUE: TransformPreset(
        type=TransformType.CONVERT_GITHUB_ISSUE,
        title="Convert to GitHub Issue",
        description="Structure as a bug report or feature request issue with repro steps.",
        system_instruction=(
            "Convert the provided details into a structured GitHub Issue in markdown format, including:\n"
            "## Summary\n"
            "## Steps to Reproduce\n"
            "## Expected Behavior\n"
            "## Actual Behavior\n"
            "## Environment & Notes\n"
            "Output ONLY the markdown issue."
        ),
        recommended_model="gemini-3.7-flash",
        temperature=0.2,
        icon="🐛"
    ),
    TransformType.CONVERT_GITHUB_PR: TransformPreset(
        type=TransformType.CONVERT_GITHUB_PR,
        title="Convert to Pull Request",
        description="Structure as a pull request description with context and test plan.",
        system_instruction=(
            "Convert the following notes into a professional GitHub Pull Request description in markdown format:\n"
            "## Description\n"
            "## Motivation & Context\n"
            "## How Has This Been Tested?\n"
            "## Checklist\n"
            "- [ ] Tests added/updated\n"
            "- [ ] Documentation updated\n"
            "Output ONLY the markdown PR description."
        ),
        recommended_model="gemini-3.7-flash",
        temperature=0.2,
        icon="🔀"
    ),
    TransformType.CONVERT_DOCS: TransformPreset(
        type=TransformType.CONVERT_DOCS,
        title="Convert to Documentation",
        description="Format into technical docs, API specs, or code documentation.",
        system_instruction=(
            "Format the input as production-grade technical documentation or docstrings following "
            "Google/Markdown developer doc standards. Output ONLY the documentation."
        ),
        recommended_model="gemini-3.7-flash",
        temperature=0.2,
        icon="📚"
    ),
    TransformType.CONVERT_NOTES: TransformPreset(
        type=TransformType.CONVERT_NOTES,
        title="Convert to Structured Notes",
        description="Organize thoughts into hierarchical bullet points and action items.",
        system_instruction=(
            "Organize the provided text into clean, structured meeting/project notes in markdown with "
            "key headings, bullet points, and action items with checkboxes. Output ONLY the notes."
        ),
        recommended_model="gemini-3.6-flash",
        temperature=0.3,
        icon="📝"
    ),
    TransformType.CUSTOM: TransformPreset(
        type=TransformType.CUSTOM,
        title="Custom Transformation",
        description="Apply a custom user prompt instruction to the selected text.",
        system_instruction="Follow the user's custom instruction faithfully. Output ONLY the transformed text.",
        recommended_model="gemini-3.5-flash",
        temperature=0.3,
        icon="🎯"
    )
}


class TransformEngine:
    """Manages prompt construction and model selection for text transformation."""

    @staticmethod
    def get_preset(transform_type: TransformType) -> TransformPreset:
        return TRANSFORM_PRESETS.get(transform_type, TRANSFORM_PRESETS[TransformType.IMPROVE])

    @staticmethod
    def list_presets() -> List[TransformPreset]:
        return list(TRANSFORM_PRESETS.values())

    @classmethod
    def build_system_instruction(
        cls,
        transform_type: TransformType = TransformType.IMPROVE,
        app_context: Optional[AppContext] = None,
        custom_instruction: str = ""
    ) -> str:
        if custom_instruction and custom_instruction.strip():
            instruction = f"{custom_instruction.strip()}\n\nOutput ONLY the final transformed text."
        else:
            preset = cls.get_preset(transform_type)
            instruction = preset.system_instruction

        if app_context and app_context.system_prompt_addition:
            instruction += f"\n\nContext Directive for {app_context.app_name} ({app_context.category}):\n{app_context.system_prompt_addition}"

        return instruction

    @classmethod
    def resolve_model(
        cls,
        transform_type: TransformType,
        text_length: int = 0,
        manual_model: Optional[str] = None
    ) -> str:
        """Determines best model using preset recommendations and ModelRouter."""
        if manual_model and manual_model != "auto":
            return manual_model

        preset = cls.get_preset(transform_type)
        if text_length > 3000:
            return "gemini-3.6-flash"
        return preset.recommended_model
