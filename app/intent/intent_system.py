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
    IntentCategory.FORMAT_TEXT: TransformType.CUSTOM,
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


DELIM = r'(?:\s*[:,\-—\.\?!]+\s*|\s+that\s+|\s+)'

# Intent trigger patterns and prompt mappings for all 16 command categories
INTENT_PATTERNS = [
    # 1. Professionalize
    (
        rf'^(?:please\s+)?(?:make\s+(?:this|it)\s+(?:more\s+)?professional|make\s+(?:more\s+)?professional|professionalize(?:\s+this)?|make\s+(?:this|it)\s+(?:more\s+)?formal|formalize(?:\s+this)?|executive\s+tone|professional\s+tone|make\s+(?:this|it)\s+sound\s+professional|professional\s+rewrite){DELIM}?(.*)$',
        IntentCategory.PROFESSIONALIZE,
        "Rewrite the following text in a polished, articulate, and professional style suitable for business or professional communication. Crucially, preserve the author's original voice, perspective, and intent (e.g. if written in first-person 'I', keep it in first-person). Elevate vocabulary, refine sentence flow, and remove colloquial fillers while keeping the genuine human message intact. Never convert personal speech into third-person telemetry, software execution logs, or robotic status reports. Output ONLY the rewritten text.",
        "gemini-3.5-flash-lite"
    ),
    # 2. Make Casual
    (
        rf'^(?:please\s+)?(?:make\s+(?:this|it)\s+(?:more\s+)?casual|make\s+(?:more\s+)?casual|make\s+(?:this|it)\s+(?:more\s+)?friendly|make\s+(?:this|it)\s+(?:more\s+)?informal|friendly\s+tone|casual\s+tone|informal\s+tone){DELIM}?(.*)$',
        IntentCategory.MAKE_CASUAL,
        "Rephrase the input in a friendly, conversational, and natural casual tone while preserving the essential facts and author perspective. Output ONLY the rewritten text.",
        "gemini-3.5-flash-lite"
    ),
    # 3. Create Prompt
    (
        rf'^(?:please\s+)?(?:turn\s+this\s+into\s+(?:an?\s+)?(?:ai\s+)?prompt|create\s+(?:an?\s+)?(?:ai\s+)?prompt(?:\s+(?:from|for)\s+this)?|generate\s+(?:an?\s+)?(?:ai\s+)?prompt|make\s+this\s+(?:an?\s+)?(?:ai\s+)?prompt|convert\s+(?:this\s+)?to\s+(?:an?\s+)?(?:ai\s+)?prompt|prompt\s+enhancer|(?:ai\s+)?prompt\s*[:\-—]){DELIM}?(.*)$',
        IntentCategory.CREATE_PROMPT,
        "You are an expert AI Prompt Engineer. Transform the user's raw notes into a structured, high-impact AI Prompt with Objective, Context, Step-by-Step Instructions, and Output Format. Output ONLY the finalized prompt.",
        "gemini-3.5-flash-lite"
    ),
    # 4. Summarize
    (
        rf'^(?:please\s+)?(?:summarize(?:\s+this)?|summarise(?:\s+this)?|give\s+me\s+a\s+summary(?:\s+of)?|give\s+a\s+summary(?:\s+of)?|quick\s+summary(?:\s+of)?|brief\s+summary(?:\s+of)?|bullet\s+summary(?:\s+of)?|tldr|tl;dr){DELIM}?(.*)$',
        IntentCategory.SUMMARIZE,
        "Summarize the provided content into clear, digestible bullet points highlighting key takeaways, action items, and conclusions. Output ONLY the summary bullet points.",
        "gemini-3.5-flash-lite"
    ),
    # 5. Grammar Fix
    (
        rf'^(?:please\s+)?(?:fix\s+(?:the|my)\s+grammar|fix\s+grammar|correct\s+(?:the|my)\s+grammar|correct\s+grammar|proofread(?:\s+(?:this|my\s+text))?|check\s+(?:the|my)\s+grammar|check\s+grammar|grammar\s+fix|grammar\s+check|fix\s+grammar\s+and\s+spelling|fix\s+spelling\s+and\s+grammar|fix\s+spelling|correct\s+spelling|fix\s+typos){DELIM}?(.*)$',
        IntentCategory.GRAMMAR_FIX,
        "Proofread and correct all grammar, spelling, punctuation, capitalization, subject-verb agreement, and typographical slips in the provided text. Output ONLY the corrected text without explanations or quotes.",
        "gemini-3.5-flash-lite"
    ),
    # 6. Shorten / Concise
    (
        rf'^(?:please\s+)?(?:make\s+(?:this|it)\s+(?:more\s+)?shorter|shorten(?:\s+this)?|make\s+(?:this|it)\s+(?:more\s+)?concise|make\s+concise|trim(?:\s+this)?|condense(?:\s+this)?|cut\s+(?:the\s+)?fluff){DELIM}?(.*)$',
        IntentCategory.SHORTEN,
        "Condense the input text into a concise, punchy version without losing vital context or key points. Output ONLY the concise text.",
        "gemini-3.5-flash-lite"
    ),
    # 7. Expand
    (
        rf'^(?:please\s+)?(?:expand(?:\s+on)?(?:\s+this)?|elaborate(?:\s+on)?(?:\s+this)?|add\s+more\s+details?(?:\s+to)?){DELIM}?(.*)$',
        IntentCategory.EXPAND,
        "Expand upon the thoughts and concepts provided, providing thorough elaboration, context, and clear explanatory prose. Output ONLY the expanded content.",
        "gemini-3.5-flash-lite"
    ),
    # 8. Explain
    (
        rf'^(?:please\s+)?(?:explain(?:\s+this)?|what\s+does\s+this\s+mean|break\s+down(?:\s+this)?|explain\s+what\s+this\s+means|explain\s+to\s+me){DELIM}?(.*)$',
        IntentCategory.EXPLAIN,
        "Explain the provided concept, code, or text in clear, step-by-step educational language with intuitive analogies. Output ONLY the explanation.",
        "gemini-3.5-flash-lite"
    ),
    # 9. Translate
    (
        rf'^(?:please\s+)?(?:translate\s+(?:this\s+)?(?:in|to|into)\s+([A-Za-z]+)|([A-Za-z]+)\s+translation(?:\s+of)?){DELIM}?(.*)$',
        IntentCategory.TRANSLATE,
        "Accurately translate the provided text into the target language, preserving natural idioms and cultural nuances. Output ONLY the translation.",
        "gemini-3.5-flash-lite"
    ),
    # 10. Create Email
    (
        rf'^(?:please\s+)?(?:create\s+(?:an\s+)?email|draft\s+(?:an\s+)?email|write\s+(?:an\s+)?email|compose\s+(?:an\s+)?email|email\s+draft)(?:\s+(?:to|about))?{DELIM}?(.*)$',
        IntentCategory.CREATE_EMAIL,
        "Draft a complete, well-structured email with a concise Subject line, professional salutation, clear body paragraphs, and courteous sign-off. Output ONLY the email.",
        "gemini-3.5-flash-lite"
    ),
    # 11. Create GitHub Issue
    (
        rf'^(?:please\s+)?(?:create\s+(?:a\s+)?(?:github\s+)?issue|new\s+github\s+issue|bug\s+report(?:\s+for)?|file\s+(?:a\s+)?bug(?:\s+report)?){DELIM}?(.*)$',
        IntentCategory.CREATE_GITHUB_ISSUE,
        "Format the input into a professional GitHub Issue description with Title, Description, Reproduction Steps, Expected vs Actual Behavior, and Environment. Output ONLY the markdown issue.",
        "gemini-3.5-flash-lite"
    ),
    # 12. Create GitHub PR Description
    (
        rf'^(?:please\s+)?(?:create\s+(?:a\s+)?(?:github\s+)?pr|create\s+(?:a\s+)?pull\s+request|pr\s+description(?:\s+for)?|pull\s+request\s+description(?:\s+for)?){DELIM}?(.*)$',
        IntentCategory.CREATE_GITHUB_PR,
        "Draft an exemplary GitHub Pull Request description featuring Summary of Changes, Motivation & Context, Testing Verification, and Checklist. Output ONLY the markdown PR description.",
        "gemini-3.5-flash-lite"
    ),
    # 13. Create Task List
    (
        rf'^(?:please\s+)?(?:create\s+(?:a\s+)?task\s+list|create\s+action\s+items|generate\s+(?:a\s+)?(?:todo|to-do)\s+list|make\s+(?:a\s+)?(?:todo|to-do)\s+list|(?:todo|to-do)\s+list|create\s+(?:a\s+)?checklist){DELIM}?(.*)$',
        IntentCategory.CREATE_TASK,
        "Extract and organize all implied and explicit action items into a prioritized, actionable markdown checklist with clear ownership and deliverables. Output ONLY the checklist.",
        "gemini-3.5-flash-lite"
    ),
    # 14. Generate Code
    (
        rf'^(?:please\s+)?(?:'
        rf'(?:generate|write|create|give\s+me)\s+(?:an?\s+)?([A-Za-z0-9#+]+)\s+(?:script|function|class|method|code)(?:\s+(?:to|that|for))?|'
        rf'(?:generate|write|create|give\s+me)\s+code\s+in\s+([A-Za-z0-9#+]+)(?:\s+(?:to|that|for))?|'
        rf'([A-Za-z0-9#+]+)\s+code\s*[:\-—]\s*|'
        rf'code\s+(?:this\s+)?in\s+([A-Za-z0-9#+]+)|'
        rf'(?:generate|write|create)\s+(?:an?\s+)?(?:script|function|class|method|code)(?:\s+(?:to|that|for))?'
        rf'){DELIM}?(.*)$',
        IntentCategory.GENERATE_CODE,
        "Write clean, robust, and idiomatic code adhering to modern best practices. Include concise explanatory comments and proper type annotations. Output ONLY the code.",
        "gemini-3.5-flash-lite"
    ),
    # 15. Format Text / Table
    (
        rf'^(?:please\s+)?(?:format\s+(?:this\s+)?(?:into|as)\s+(?:a\s+)?(?:markdown\s+)?table|format\s+into\s+table|format\s+as\s+table|create\s+(?:a\s+)?table(?:\s+from\s+this)?|convert\s+(?:this\s+)?to\s+(?:a\s+)?table|format\s+this){DELIM}?(.*)$',
        IntentCategory.FORMAT_TEXT,
        "Format the provided data or text cleanly into a structured markdown table according to the user's intent. Output ONLY the markdown table.",
        "gemini-3.5-flash-lite"
    ),
    # 16. Rewrite
    (
        rf'^(?:please\s+)?(?:rewrite(?:\s+this)?|rephrase(?:\s+this)?|polish(?:\s+this)?|improve\s+this|clean\s+up\s+this){DELIM}?(.*)$',
        IntentCategory.REWRITE,
        "Rewrite the text to maximize clarity, elegance, and readability while faithfully preserving the original meaning and author perspective. Output ONLY the rewritten text.",
        "gemini-3.5-flash-lite"
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
                groups = [g for g in match.groups() if g is not None]
                payload = groups[-1].strip() if groups else ""
                # Strip leading punctuation or whitespace from payload
                payload = re.sub(r'^[ :,.\-—\?!]+', '', payload).strip()

                target_lang = ""

                # Handle language translation group
                if intent == IntentCategory.TRANSLATE:
                    if len(groups) >= 2:
                        target_lang = groups[0] or "English"
                    instruction = f"Accurately translate the provided text into {target_lang or 'English'}. Output ONLY the translated text without commentary."

                # Handle generate code language group
                elif intent == IntentCategory.GENERATE_CODE:
                    if len(groups) >= 2 and groups[0]:
                        target_lang = groups[0]
                    # Also detect language from payload if not in prefix: e.g. "in Python" or "using Python"
                    if not target_lang:
                        lang_m = re.search(r'\b(?:in|using)\s+([A-Za-z0-9#+]+)\b', payload, re.IGNORECASE)
                        if lang_m:
                            target_lang = lang_m.group(1)

                    if target_lang:
                        instruction = (
                            f"Generate clean, runnable, idiomatic {target_lang} code adhering to modern best practices. "
                            "Include concise comments and proper type annotations. Output ONLY the code."
                        )
                    else:
                        instruction = (
                            "Generate clean, runnable, idiomatic code adhering to modern best practices. "
                            "Detect or choose the appropriate programming language from context. "
                            "Include concise comments and proper type annotations. Output ONLY the code."
                        )

                # Clean enclosing quotes from payload (e.g. user dictated: Fix my grammar: "...")
                if (payload.startswith(('"', "'", "“", "”", "«")) and payload.endswith(('"', "'", "“", "”", "»"))) and len(payload) > 1:
                    payload = payload[1:-1].strip()

                # If user said only the command (e.g. "make it professional") with no payload,
                # use the active selected or clipboard text as payload!
                if not payload and clipboard_fallback:
                    payload = clipboard_fallback.strip()

                trigger_matched = cleaned[:len(cleaned) - len(payload)].strip(' :,.-—!?')
                logger.info(f"Intent classified: {intent.value} (Trigger: '{trigger_matched}', Payload len: {len(payload)})")
                return IntentResult(
                    intent=intent,
                    payload=payload,
                    system_instruction=instruction,
                    target_model=target_model,
                    command_trigger=trigger_matched,
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
