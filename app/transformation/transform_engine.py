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
            "Rewrite the following text to maximize clarity, elegance, and readability while faithfully "
            "preserving the author's original voice, meaning, proper names, and key facts. Output ONLY the rewritten text without commentary."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.3,
        icon="✨"
    ),
    TransformType.FIX_GRAMMAR: TransformPreset(
        type=TransformType.FIX_GRAMMAR,
        title="Fix Grammar & Spelling",
        description="Correct all punctuation, grammar, and typos with zero semantic distortion.",
        system_instruction=(
            "Proofread the following text with zero hallucination. Strictly correct all spelling, typos, punctuation, "
            "capitalization, subject-verb agreement, and grammatical slips. Preserve all words, phrasing, proper names, "
            "numbers, and technical terms exactly without altering the intended meaning. Output ONLY the corrected text without any explanations or quotation marks."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.1,
        icon="✅"
    ),
    TransformType.PROFESSIONAL: TransformPreset(
        type=TransformType.PROFESSIONAL,
        title="Make Professional",
        description="Transform informal drafts into polished, high-impact executive prose.",
        system_instruction=(
            "Rewrite the following text in a polished, articulate, and professional style suitable for business or professional communication. "
            "Crucially, preserve the author's original voice, perspective, and intent (e.g. if written in first-person 'I', keep it in first-person). "
            "Preserve all proper names, numbers, dates, and facts without substitution or omission. "
            "Correct all informal grammar and verb tenses (e.g. 'I buy' -> 'purchased', 'I come back home' -> 'I returned home'). "
            "When the user lists items, groceries, purchases, or tasks (including run-together items), format them into clean bullet points ('• ') on separate lines. "
            "Elevate vocabulary and sentence flow while keeping the genuine message intact. Output ONLY the rewritten text without commentary."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.3,
        icon="👔"
    ),
    TransformType.CASUAL: TransformPreset(
        type=TransformType.CASUAL,
        title="Make Casual",
        description="Rephrase into friendly, warm, conversational text.",
        system_instruction=(
            "Rephrase the following text in a warm, relaxed, and conversational tone suitable for direct messaging or Slack syncs "
            "while preserving all key facts, names, and deadlines. Output ONLY the rewritten text without commentary."
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
            "Condense the following text to its leanest, punchiest form. Remove all superfluous words and fluff while keeping "
            "100% of essential facts, names, and figures. Output ONLY the concise text without commentary."
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
            "Elaborate upon the provided text with rich context, strategic nuance, and comprehensive professional detail. "
            "Preserve all core facts and names. Output ONLY the expanded content."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.4,
        icon="📖"
    ),
    TransformType.SUMMARIZE: TransformPreset(
        type=TransformType.SUMMARIZE,
        title="Summarize",
        description="Generate clean bullet-point summary with key takeaways.",
        system_instruction=(
            "Summarize the provided content into a tight executive summary with high-signal bullet points ('• ') "
            "highlighting core conclusions, decisions, and action items. Output ONLY the summary bullet points."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.2,
        icon="📋"
    ),
    TransformType.EXPLAIN: TransformPreset(
        type=TransformType.EXPLAIN,
        title="Explain Clearly",
        description="Break down complex concepts or code with step-by-step clarity.",
        system_instruction=(
            "Explain the following concept or project update in crystal-clear, structured operational terms with step-by-step clarity. "
            "Output ONLY the explanation."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.3,
        icon="💡"
    ),
    TransformType.TECHNICAL: TransformPreset(
        type=TransformType.TECHNICAL,
        title="Technical & Code",
        description="Write clean code or refine text using rigorous engineering standards.",
        system_instruction=(
            "You are a Senior Staff Software Engineer. Write clean, complete, runnable, and idiomatic code "
            "(with functions, classes, data structures, or executable scripts) implementing, modeling, or automating "
            "the requirements, logic, workflow, or data in the input text. Always define concrete functions (`def`, `function`), "
            "classes, variables, or logic. Output ONLY the code directly without markdown code fences or conversational text."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.2,
        icon="⚙️"
    ),
    TransformType.CONVERT_PROMPT: TransformPreset(
        type=TransformType.CONVERT_PROMPT,
        title="Convert to AI Prompt",
        description="Craft an optimized, high-fidelity system/user prompt from raw notes with 100% information retention.",
        system_instruction=(
            "You are an elite, world-class AI Prompt Architect. Transform the provided text into a comprehensive, "
            "production-grade, and beautifully structured AI Prompt with Role, Objective, Context, Step-by-Step Instructions, "
            "and Expected Output Format. Preserve 100% of all information, names, constraints, and parameters. "
            "Output ONLY the finalized prompt directly without preambles or outer code fences."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.2,
        icon="🧠"
    ),
    TransformType.CONVERT_EMAIL: TransformPreset(
        type=TransformType.CONVERT_EMAIL,
        title="Convert to Email",
        description="Format into an email with subject line, greeting, and sign-off.",
        system_instruction=(
            "Convert the user's thoughts into a polished email. Include a compelling 'Subject: ' line, "
            "appropriate salutation, clean body paragraphs, and professional closing. Output ONLY the email."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.3,
        icon="✉️"
    ),
    TransformType.CONVERT_GITHUB_ISSUE: TransformPreset(
        type=TransformType.CONVERT_GITHUB_ISSUE,
        title="Convert to GitHub Issue",
        description="Structure as a bug report or feature request issue with repro steps.",
        system_instruction=(
            "Convert the provided details into a structured GitHub Issue in markdown format, including Title, Summary, "
            "Steps/Context, Technical Details & Components, and Action Items checklist (- [ ]). "
            "Preserve 100% of all technical details, component names, error codes, and notes without omitting anything. "
            "Do not echo the spoken trigger command. Output ONLY the markdown issue."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.2,
        icon="🐛"
    ),
    TransformType.CONVERT_GITHUB_PR: TransformPreset(
        type=TransformType.CONVERT_GITHUB_PR,
        title="Convert to Pull Request",
        description="Structure as a pull request description with context and test plan.",
        system_instruction=(
            "Convert the following notes into a professional GitHub Pull Request description in markdown format with "
            "Summary of Changes, Motivation & Context, Key Details & Branches, and Testing Checklist (- [ ]). "
            "Preserve 100% of all technical details, branch names, file paths, issue references, numbers, and notes without omitting anything. "
            "Do not echo the spoken trigger command. Output ONLY the markdown PR description."
        ),
        recommended_model="gemini-3.5-flash-lite",
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
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.2,
        icon="📚"
    ),
    TransformType.CONVERT_NOTES: TransformPreset(
        type=TransformType.CONVERT_NOTES,
        title="Convert to Structured Notes",
        description="Organize thoughts into hierarchical bullet points and action items.",
        system_instruction=(
            "Extract and organize all implied and explicit action items into a prioritized, actionable markdown checklist "
            "with clear check-boxes (- [ ]) and owners. Output ONLY the checklist."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.2,
        icon="📝"
    ),
    TransformType.CUSTOM: TransformPreset(
        type=TransformType.CUSTOM,
        title="Custom Transformation",
        description="Apply custom user instructions directly.",
        system_instruction=(
            "Follow the user's specific transformation instruction faithfully while preserving all proper names, numbers, and facts. "
            "Output ONLY the transformed result."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.3,
        icon="⚡"
    )
}


class TransformEngine:
    @classmethod
    def get_preset(cls, transform_type: TransformType) -> TransformPreset:
        return TRANSFORM_PRESETS.get(transform_type, TRANSFORM_PRESETS[TransformType.IMPROVE])

    @classmethod
    def build_system_instruction(
        cls,
        transform_type: TransformType,
        app_context: Optional[AppContext] = None,
        custom_instruction: str = ""
    ) -> str:
        preset = cls.get_preset(transform_type)
        base = custom_instruction.strip() if custom_instruction and custom_instruction.strip() else preset.system_instruction

        if app_context and app_context.profile_id:
            base += f" Adapt formatting seamlessly for target workspace application: '{app_context.app_name}'."

        return base
