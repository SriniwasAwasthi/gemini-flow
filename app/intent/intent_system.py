"""
Voice Intent & Command Classifier for Gemini Flow.
Detects user intent from spoken utterances (Voice -> Intent -> Processing)
supporting all 18 standard intent categories.
"""
import re
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

from app.transformation.transform_engine import TransformType

logger = logging.getLogger("GeminiFlow.IntentSystem")


class IntentCategory(str, Enum):
    DICTATE = "DICTATE"
    REWRITE = "REWRITE"
    GRAMMAR_FIX = "GRAMMAR_FIX"
    PROFESSIONALIZE = "PROFESSIONALIZE"
    MAKE_CASUAL = "MAKE_CASUAL"
    SUMMARIZE = "SUMMARIZE"
    EXPAND = "EXPAND"
    SHORTEN = "SHORTEN"
    CREATE_PROMPT = "CREATE_PROMPT"
    EXPLAIN = "EXPLAIN"
    TRANSLATE = "TRANSLATE"
    CREATE_EMAIL = "CREATE_EMAIL"
    CREATE_GITHUB_ISSUE = "CREATE_GITHUB_ISSUE"
    CREATE_GITHUB_PR = "CREATE_GITHUB_PR"
    CREATE_TASK = "CREATE_TASK"
    GENERATE_CODE = "GENERATE_CODE"
    FORMAT_TEXT = "FORMAT_TEXT"
    QUICK_TEXT = "QUICK_TEXT"


INTENT_TO_TRANSFORM_MAP: Dict[IntentCategory, TransformType] = {
    IntentCategory.DICTATE: TransformType.IMPROVE,
    IntentCategory.REWRITE: TransformType.IMPROVE,
    IntentCategory.GRAMMAR_FIX: TransformType.FIX_GRAMMAR,
    IntentCategory.PROFESSIONALIZE: TransformType.PROFESSIONAL,
    IntentCategory.MAKE_CASUAL: TransformType.CASUAL,
    IntentCategory.SUMMARIZE: TransformType.SUMMARIZE,
    IntentCategory.EXPAND: TransformType.EXPAND,
    IntentCategory.SHORTEN: TransformType.CONCISE,
    IntentCategory.CREATE_PROMPT: TransformType.CONVERT_PROMPT,
    IntentCategory.EXPLAIN: TransformType.EXPLAIN,
    IntentCategory.TRANSLATE: TransformType.CUSTOM,
    IntentCategory.CREATE_EMAIL: TransformType.CONVERT_EMAIL,
    IntentCategory.CREATE_GITHUB_ISSUE: TransformType.CONVERT_GITHUB_ISSUE,
    IntentCategory.CREATE_GITHUB_PR: TransformType.CONVERT_GITHUB_PR,
    IntentCategory.CREATE_TASK: TransformType.CONVERT_NOTES,
    IntentCategory.GENERATE_CODE: TransformType.TECHNICAL,
    IntentCategory.FORMAT_TEXT: TransformType.IMPROVE,
    IntentCategory.QUICK_TEXT: TransformType.IMPROVE,
}


@dataclass
class IntentResult:
    intent: IntentCategory
    payload: str
    system_instruction: str
    target_model: str
    confidence: float = 1.0
    command_trigger: str = ""
    target_language: str = ""


# Intent trigger patterns and prompt mappings
INTENT_PATTERNS = [
    # 1. Professionalize
    (
        r'^(?:please\s+)?(?:make\s+this\s+professional|professionalize\s+this|make\s+it\s+formal|formalize\s+this)(?:\s*[:,\-—]\s*|\s+that\s+|\s+)?(.*)$',
        IntentCategory.PROFESSIONALIZE,
        "Transform the input into clear, articulate, and polished executive professional writing. Maintain the core message without colloquialisms or filler.",
        "gemini-2.5-flash"
    ),
    # 2. Make Casual
    (
        r'^(?:please\s+)?(?:make\s+this\s+casual|make\s+it\s+casual|make\s+it\s+friendly|friendly\s+tone)(?:\s*[:,\-—]\s*|\s+that\s+|\s+)?(.*)$',
        IntentCategory.MAKE_CASUAL,
        "Rephrase the input in a friendly, conversational, and natural casual tone while preserving the essential facts.",
        "gemini-3.5-flash-lite"
    ),
    # 3. Create Prompt
    (
        r'^(?:please\s+)?(?:turn\s+this\s+into\s+a\s+prompt|create\s+a\s+prompt\s+from\s+this|prompt\s+enhancer|make\s+this\s+a\s+prompt)(?:\s*[:,\-—]\s*|\s+that\s+|\s+)?(.*)$',
        IntentCategory.CREATE_PROMPT,
        "You are an expert AI Prompt Engineer. Transform the user's raw notes into a structured, high-impact AI Prompt with Objective, Context, Step-by-Step Instructions, and Output Format.",
        "gemini-3.5-flash"
    ),
    # 4. Summarize
    (
        r'^(?:please\s+)?(?:summarize\s+this|give\s+me\s+a\s+summary|tldr|brief\s+summary\s+of)(?:\s*[:,\-—]\s*|\s+that\s+|\s+)?(.*)$',
        IntentCategory.SUMMARIZE,
        "Summarize the provided content into clear, digestible bullet points highlighting key takeaways, action items, and conclusions.",
        "gemini-2.5-pro"
    ),
    # 5. Grammar Fix
    (
        r'^(?:please\s+)?(?:fix\s+the\s+grammar|fix\s+grammar|correct\s+grammar|proofread\s+this)(?:\s*[:,\-—]\s*|\s+that\s+|\s+)?(.*)$',
        IntentCategory.GRAMMAR_FIX,
        "Proofread and correct all grammar, spelling, punctuation, and typographical slips in the provided text. Output ONLY the corrected text.",
        "gemini-2.5-flash"
    ),
    # 6. Shorten / Concise
    (
        r'^(?:please\s+)?(?:make\s+this\s+shorter|shorten\s+this|make\s+it\s+concise|trim\s+this)(?:\s*[:,\-—]\s*|\s+that\s+|\s+)?(.*)$',
        IntentCategory.SHORTEN,
        "Condense the input text into a concise, punchy version without losing vital context or key points.",
        "gemini-3.5-flash-lite"
    ),
    # 7. Expand
    (
        r'^(?:please\s+)?(?:expand\s+this|elaborate\s+on\s+this|add\s+more\s+detail\s+to)(?:\s*[:,\-—]\s*|\s+that\s+|\s+)?(.*)$',
        IntentCategory.EXPAND,
        "Expand upon the thoughts and concepts provided, providing thorough elaboration, context, and clear explanatory prose.",
        "gemini-2.5-pro"
    ),
    # 8. Explain
    (
        r'^(?:please\s+)?(?:explain\s+this|what\s+does\s+this\s+mean|break\s+down\s+this)(?:\s*[:,\-—]\s*|\s+that\s+|\s+)?(.*)$',
        IntentCategory.EXPLAIN,
        "Explain the provided concept, code, or text in clear, step-by-step educational language with intuitive analogies.",
        "gemini-3.7-flash"
    ),
    # 9. Translate
    (
        r'^(?:please\s+)?(?:translate\s+this\s+to\s+([A-Za-z]+)|translate\s+to\s+([A-Za-z]+))(?:\s*[:,\-—]\s*|\s+)?(.*)$',
        IntentCategory.TRANSLATE,
        "Accurately translate the provided text into the target language, preserving natural idioms and cultural nuances.",
        "gemini-3.5-flash"
    ),
    # 10. Create Email
    (
        r'^(?:please\s+)?(?:create\s+(?:an\s+)?email|draft\s+(?:an\s+)?email|write\s+(?:an\s+)?email\s+(?:to|about)?)(?:\s*[:,\-—]\s*|\s+)?(.*)$',
        IntentCategory.CREATE_EMAIL,
        "Draft a complete, well-structured email with a concise Subject line, professional salutation, clear body paragraphs, and courteous sign-off.",
        "gemini-3.5-flash"
    ),
    # 11. Create GitHub Issue
    (
        r'^(?:please\s+)?(?:create\s+(?:a\s+)?github\s+issue|new\s+github\s+issue|bug\s+report\s+for)(?:\s*[:,\-—]\s*|\s+)?(.*)$',
        IntentCategory.CREATE_GITHUB_ISSUE,
        "Format the input into a professional GitHub Issue description with Title, Description, Reproduction Steps, Expected vs Actual Behavior, and Environment.",
        "gemini-3.7-flash"
    ),
    # 12. Create GitHub PR Description
    (
        r'^(?:please\s+)?(?:create\s+(?:a\s+)?(?:github\s+)?pr|create\s+pull\s+request|pr\s+description\s+for)(?:\s*[:,\-—]\s*|\s+)?(.*)$',
        IntentCategory.CREATE_GITHUB_PR,
        "Draft an exemplary GitHub Pull Request description featuring Summary of Changes, Motivation & Context, Testing Verification, and Checklist.",
        "gemini-3.7-flash"
    ),
    # 13. Create Task List
    (
        r'^(?:please\s+)?(?:create\s+task\s+list|create\s+action\s+items|generate\s+todo\s+list|action\s+items\s+from)(?:\s*[:,\-—]\s*|\s+)?(.*)$',
        IntentCategory.CREATE_TASK,
        "Extract and organize all implied and explicit action items into a prioritized, actionable markdown checklist with clear ownership and deliverables.",
        "gemini-2.5-pro"
    ),
    # 14. Generate Code
    (
        r'^(?:please\s+)?(?:generate\s+code|write\s+code|code\s+in\s+([A-Za-z0-9#+]+)|write\s+a\s+(?:python|javascript|typescript|c\+\+|sql|rust|html|css)\s+(?:script|function|class)\s+to)(?:\s*[:,\-—]\s*|\s+)?(.*)$',
        IntentCategory.GENERATE_CODE,
        "Write clean, robust, and idiomatic code adhering to modern best practices. Include concise explanatory comments.",
        "gemini-3.7-flash"
    ),
    # 15. Format Text / Markdown
    (
        r'^(?:please\s+)?(?:format\s+this|format\s+as\s+(?:a\s+)?markdown\s+table|format\s+into\s+table)(?:\s*[:,\-—]\s*|\s+)?(.*)$',
        IntentCategory.FORMAT_TEXT,
        "Format the provided data or text cleanly into a structured markdown table or outline according to the user's intent.",
        "gemini-3.5-flash"
    ),
    # 16. Rewrite
    (
        r'^(?:please\s+)?(?:rewrite\s+this|rephrase\s+this|polish\s+this)(?:\s*[:,\-—]\s*|\s+that\s+|\s+)?(.*)$',
        IntentCategory.REWRITE,
        "Rewrite the text to maximize clarity, elegance, and readability while faithfully preserving the original meaning.",
        "gemini-3.5-flash"
    )
]


class IntentClassifier:
    """Classifies user speech or text into structured IntentResult."""

    @classmethod
    def classify(cls, text: str, clipboard_fallback: str = "") -> IntentResult:
        cleaned = text.strip()
        if not cleaned:
            return IntentResult(
                intent=IntentCategory.DICTATE,
                payload="",
                system_instruction="Transcribe spoken words accurately.",
                target_model="gemini-3.5-flash-lite"
            )

        # Check regex patterns
        for pattern_str, intent, instruction, target_model in INTENT_PATTERNS:
            match = re.search(pattern_str, cleaned, re.IGNORECASE)
            if match:
                groups = match.groups()
                # Find payload group (usually the last group)
                payload = groups[-1].strip() if groups else ""
                target_lang = ""

                # Handle language translation group
                if intent == IntentCategory.TRANSLATE and len(groups) >= 2:
                    target_lang = groups[0] or groups[1] or "English"
                    instruction = f"Accurately translate the provided text into {target_lang}."

                # If user said only the command (e.g. "make this professional") with no payload,
                # use the active clipboard text as payload!
                if not payload and clipboard_fallback:
                    payload = clipboard_fallback.strip()

                logger.info(f"Intent classified: {intent.value} (Payload length: {len(payload)})")
                return IntentResult(
                    intent=intent,
                    payload=payload,
                    system_instruction=instruction,
                    target_model=target_model,
                    command_trigger=match.group(0).split()[0],
                    target_language=target_lang
                )

        # Default standard dictation
        return IntentResult(
            intent=IntentCategory.DICTATE,
            payload=cleaned,
            system_instruction="Transcribe the spoken audio into clear, clean, and grammatically accurate text.",
            target_model="gemini-3.5-flash-lite"
        )


IntentSystem = IntentClassifier
