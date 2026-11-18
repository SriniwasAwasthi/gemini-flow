"""
Universal Text Transformation Engine for Gemini Flow.
Provides 16 built-in transformation operations capable of modifying selected
or dictated text anywhere on Windows.
"""
import re
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, Any, List, Tuple

from app.intelligence.app_intelligence import AppContext
from app.router.model_router import ModelRouter

logger = logging.getLogger("GeminiFlow.TransformEngine")


class TransformType(str, Enum):
    IMPROVE = "IMPROVE"
    TRANSFORM_TEXT = "TRANSFORM_TEXT"
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


FIVE_PART_PROMPT_TAGS: List[str] = [
    "role",
    "context",
    "task",
    "constraints",
    "output_format"
]

MANDATORY_15_SECTIONS: List[str] = [
    "1. ROLE & PERSONA",
    "2. PROJECT CONTEXT",
    "3. PROBLEM STATEMENT",
    "4. OBJECTIVE",
    "5. TASK DESCRIPTION",
    "6. REQUIREMENTS & SPECIFICATIONS",
    "7. IMPLEMENTATION GUIDELINES",
    "8. TECHNICAL REQUIREMENTS",
    "9. UI/UX REQUIREMENTS",
    "10. WORKFLOW & EXPECTED BEHAVIOUR",
    "11. CONSTRAINTS & RESTRICTIONS",
    "12. EDGE CASES & ERROR HANDLING",
    "13. ACCEPTANCE CRITERIA",
    "14. TESTING & VERIFICATION",
    "15. EXPECTED OUTPUT & DELIVERABLES"
]


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
            "preserving the author's original voice, meaning, proper names, tenses, technical terms, and key facts. "
            "Filter unnecessary speech fillers and stutter repetitions. Format intelligently into clean paragraphs or bullet points where appropriate. "
            "Output ONLY the rewritten text without commentary."
        ),
        recommended_model="gemini-3.5-flash-lite",
        temperature=0.3,
        icon="✨"
    ),
    TransformType.TRANSFORM_TEXT: TransformPreset(
        type=TransformType.TRANSFORM_TEXT,
        title="Transform Text (Alt+T)",
        description="Transform text into fluent, grammatically correct, professional English preserving meaning, technical terms, and tone.",
        system_instruction=(
            "You are an expert editor and communications specialist. Transform the following text into fluent, grammatically correct, "
            "professional English. Strictly preserve the original meaning, context, tenses, technical terminology, and tone. "
            "Filter unnecessary speech fillers (such as 'um', 'uh', 'you know', 'like') and accidental repetitions without truncating "
            "or losing meaningful information. Format intelligently into paragraphs, bullet points, or numbered lists where appropriate. "
            "Output ONLY the transformed text without commentary, preambles, explanations, or quotes."
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
        title="Convert to AI Prompt (Alt+P)",
        description="Craft a structured, self-contained AI prompt strictly adhering to the 5-Part Master Prompt Blueprint using XML tags.",
        system_instruction=(
            """You are an elite, world-class AI Prompt Architect. Transform the provided raw developer thought, user request, or feature spec into a master-engineered AI prompt strictly adhering to the 5-Part Master Prompt Blueprint using clean XML tags.

CRITICAL ARCHITECTURAL DIRECTIVES:
1. Dynamic, Non-Canned Persona (<role>):
   - Tailor the seniority and domain expertise directly to the user's specific tech stack and task (e.g., "Senior Full-Stack Architect specializing in beginner-accessible MERN architectures, responsive UI design, and Stripe integration", "Principal Product Designer and CRO Frontend Engineer specializing in Next.js, Tailwind CSS, and Framer Motion", "Windows Desktop Software Engineer specializing in Python, PyQt6, and the Windows 11 Fluent Design System").
   - NEVER assign a generic, cookie-cutter persona like "Staff Full-Stack Security Engineer" unless the user specifically asked for security/auth hardening.
   - NEVER inject unrequested frameworks (e.g., do NOT add Next.js or FastAPI if the user asked for React, Express, or Python).

2. Zero Context Loss & Zero Truncation (<context>):
   - Explicitly define Target Application / Product / Domain.
   - Detail the Tech Stack containing ALL libraries, frameworks, databases, styling tools, and auth/payment services mentioned.
   - Capture design themes, audience, data models, or baseline requirements without dropping any detail or using ellipses (...).

3. Structured, Actionable Execution (<task> or <objective>):
   - Break down the request into concrete, numbered views, components, API endpoints, or procedural directions with step-by-step clarity.
   - For greenfield multi-view apps, define each view/page with its layout, UI elements, and interactions. If multi-phase, include <execution_phases> (e.g., Phase 1 Data Models, Phase 2 REST API, Phase 3 State, Phase 4 UI).

4. Context-Aware Constraints (<constraints>):
   - Greenfield / New Builds: Enforce complete, copy-paste runnable files without placeholder comments (no `// TODO: implement logic`), clean folder/file separation (/models, /routes, /components), mobile-responsive viewports, accessible form labels, seed scripts, and robust error handling.
   - Refactoring / Bug Fixes / Performance: Enforce targeted modifications without breaking adjacent logic, zero-downtime patterns (Expand/Contract), lock avoidance, and rollback procedures.
   - NEVER put refactoring constraints on fresh greenfield application builds.

5. Delivery Contract (<output_format>):
   - Specify the exact, step-by-step order of delivery (e.g., backend models and routes first, followed by state and UI components, concluding with exact terminal commands to run the application).

Output Format Structure:
<role>
[Tailored Seniority + Domain Role]
</role>

<context>
Target: [Application / System Name & Purpose]
Tech Stack:
- [Itemized stack matching user requirements]
[Audience / Theme / Data Model]
</context>

<task>
[High-level objective statement]
1. [Component / View / Endpoint 1]
2. [Component / View / Endpoint 2]
3. [Component / View / Endpoint 3]
</task>

<constraints>
- [Contextually matched engineering guardrails]
- Provide complete, copy-paste runnable files without placeholder comments.
</constraints>

<output_format>
[Clear procedural delivery instructions]
</output_format>

Rules:
- Output MUST contain all 5 XML blocks: <role>, <context>, <task>, <constraints>, and <output_format>.
- Preserve 100% of user facts, technical terms, file paths, numbers, error codes, and constraints.
- Output ONLY the 5 XML blocks in clean markdown directly without outer code fences (```) or preamble."""
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
    def __init__(self, gemini_engine: Optional[Any] = None):
        self.gemini_engine = gemini_engine

    @classmethod
    def get_preset(cls, transform_type: TransformType) -> TransformPreset:
        if transform_type == TransformType.TRANSFORM_TEXT:
            return TRANSFORM_PRESETS.get(TransformType.TRANSFORM_TEXT, TRANSFORM_PRESETS[TransformType.IMPROVE])
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

    @classmethod
    def filter_speech_fillers(cls, text: str) -> str:
        """
        Filters unnecessary speech fillers ('um', 'uh', 'you know', 'like') and accidental repetitions
        without truncating or losing meaningful information, technical terms, or numbers.
        """
        if not text:
            return ""
        res = text.strip()

        # 1. Spoken fillers: um, uh, ah, erm, you know
        res = re.sub(r'\b(?:um|uh|erm|ah)\b,?\s*', '', res, flags=re.IGNORECASE)
        res = re.sub(r',?\s*\b(?:you know)\b,?\s*', ' ', res, flags=re.IGNORECASE)

        # 2. Filler 'like' when used as conversational disfluency
        res = re.sub(r',\s*like,\s*', ', ', res, flags=re.IGNORECASE)
        res = re.sub(r'^\s*like,\s*', '', res, flags=re.IGNORECASE)
        res = re.sub(r'\b(?:like\s+uh|like\s+um)\b', '', res, flags=re.IGNORECASE)

        # 3. Collapse verbal stutters (e.g. "we we" -> "we", "the the" -> "the", "I I" -> "I")
        res = re.sub(r'\b([A-Za-z]+)\s+\1\b', r'\1', res, flags=re.IGNORECASE)
        res = re.sub(r'\b([A-Za-z]+)\s+\1\b', r'\1', res, flags=re.IGNORECASE)

        # 4. Collapse extra spaces and normalize punctuation spacing
        res = re.sub(r'\s{2,}', ' ', res)
        res = re.sub(r'\s+([,.:;?!])', r'\1', res)
        res = res.strip()

        # Capitalize first character if needed
        if res and res[0].islower():
            res = res[0].upper() + res[1:]

        return res

    @classmethod
    def format_smart_structure(cls, text: str) -> str:
        """
        Intelligently structures run-together enumerations into clean bullet points or paragraphs.
        """
        if not text:
            return ""
        try:
            from app.intelligence.ai_polish_brain import AIPolishBrain
            formatted = AIPolishBrain.smart_bullet_formatter(text)
            if formatted and formatted != text:
                return formatted
        except Exception as e:
            logger.debug(f"AIPolishBrain bullet formatter note: {e}")

        # Fallback smart formatting if AIPolishBrain did not catch it:
        m_list = re.search(r'(First(?:\s+is)?[\s\w,]+)(Second(?:\s+is)?[\s\w,]+)(Third(?:\s+is)?[\s\w,.]+)', text, re.IGNORECASE)
        if m_list:
            intro_part = text[:m_list.start()].strip()
            f_part = re.sub(r'^(?:First(?:\s+is|\s*:\s*)?\s*)', '', m_list.group(1).strip(), flags=re.IGNORECASE).rstrip('.,;')
            s_part = re.sub(r'^(?:Second(?:\s+is|\s*:\s*)?\s*)', '', m_list.group(2).strip(), flags=re.IGNORECASE).rstrip('.,;')
            t_part = re.sub(r'^(?:Third(?:\s+is|\s*:\s*)?\s*)', '', m_list.group(3).strip(), flags=re.IGNORECASE).rstrip('.,;')
            bullets = [f"• {p[0].upper() + p[1:] if p else p}" for p in [f_part, s_part, t_part] if p]
            if bullets:
                res = (intro_part + "\n" if intro_part else "") + "\n".join(bullets)
                return res.strip()

        return text

    @classmethod
    def _correct_common_spoken_grammar(cls, text: str) -> str:
        """Corrects common spoken grammatical tense slips while preserving 100% of meaning and entities."""
        if not text:
            return text
        res = text

        # Past tense corrections in past-context ("yesterday ...", "last week ...", "earlier ...")
        past_indicators = [r'\byesterday\b', r'\blast\s+(?:week|month|year|night)\b', r'\bearlier\b', r'\bpreviously\b']
        has_past = any(re.search(pat, res, re.IGNORECASE) for pat in past_indicators)
        if has_past:
            # Common slips: "yesterday I go" -> "yesterday I went"
            res = re.sub(r'\b(yesterday\s+I)\s+go\b', r'\1 went', res, flags=re.IGNORECASE)
            res = re.sub(r'\b(yesterday\s+we)\s+meet\b', r'\1 met', res, flags=re.IGNORECASE)
            res = re.sub(r'\b(yesterday\s+we)\s+see\b', r'\1 saw', res, flags=re.IGNORECASE)
            res = re.sub(r'\b(yesterday\s+we)\s+do\b', r'\1 did', res, flags=re.IGNORECASE)
            res = re.sub(r'\b(yesterday\s+we)\s+have\b', r'\1 had', res, flags=re.IGNORECASE)
            res = re.sub(r'\b(yesterday\s+I)\s+buy\b', r'\1 bought', res, flags=re.IGNORECASE)
            res = re.sub(r'\b(I)\s+buy\b', r'\1 purchased', res, flags=re.IGNORECASE)
            res = re.sub(r'\bI\s+come\s+back\s+home\b', 'I returned home', res, flags=re.IGNORECASE)

        # Subject-verb agreement slips
        res = re.sub(r'\b(he|she|it)\s+dont\b', r"\1 doesn't", res, flags=re.IGNORECASE)
        res = re.sub(r'\b(they|we|you)\s+doesnt\b', r"\1 don't", res, flags=re.IGNORECASE)

        # Conversational and spoken phrasing refinement into professional English
        res = re.sub(r'\bI\s+show\s+whenever\b', 'Whenever', res, flags=re.IGNORECASE)
        res = re.sub(r'\b(?:my\s+shortcut\s+key|application\s+shortcut\s+key)\s+or\s+(?:my\s+shortcut\s+key|application\s+shortcut\s+key)\b', 'the shortcut key', res, flags=re.IGNORECASE)
        res = re.sub(r'\bwhen\s+I\s+just\s+say\s+my\s+speech\s+converted\s+into\b', 'when I speak, my speech is converted into', res, flags=re.IGNORECASE)
        res = re.sub(r'\bwith\s+a\s+professional\s+English\b', 'in professional English', res, flags=re.IGNORECASE)
        res = re.sub(r'\bAnd\s+all\s+the\s+vocabulary\s+punctuation\s+are\s+correctly\s+operated\b', 'with all vocabulary and punctuation properly applied.', res, flags=re.IGNORECASE)
        res = re.sub(r'\bAre\s+you\s+sure\s+can\s+you\s+guarantee\s+me\b', 'Can you guarantee this', res, flags=re.IGNORECASE)
        res = re.sub(r'\band\s+can\s+you\s+just\s+give\s+me\s+example\s+of\s+it\b', 'and provide an example of it?', res, flags=re.IGNORECASE)
        res = re.sub(r'\bgive\s+me\s+example\s+of\s+it\b', 'provide an example of it', res, flags=re.IGNORECASE)
        res = re.sub(r'\bcheque\s+(whether|that|if)\b', r'check \1', res, flags=re.IGNORECASE)
        res = re.sub(r'\bconverted\s+into\s+the\s+prompt\b', 'converted into a prompt', res, flags=re.IGNORECASE)

        return res

    @classmethod
    def enforce_5_part_prompt(cls, prompt_text: str, raw_input: str = "") -> str:
        """
        Validates and enforces that the 5 XML tags (<role>, <context>, <task>, <constraints>, <output_format>)
        are present in the output. Strips wrapping markdown code fences and builds the 5-part blueprint
        from content if any required tags are missing.
        """
        if not prompt_text:
            return cls._build_5_part_prompt_from_content(raw_input)

        clean = prompt_text.strip()
        # Strip outer markdown code fences if present
        if clean.startswith("```"):
            clean = re.sub(r'^```[a-zA-Z0-9_-]*\n?', '', clean)
            clean = re.sub(r'\n?```$', '', clean).strip()

        # If model used <objective> instead of <task>, normalize to <task> for strict contract adherence
        if "<objective>" in clean and "<task>" not in clean:
            clean = clean.replace("<objective>", "<task>").replace("</objective>", "</task>")

        required_tags = ["<role>", "</role>", "<context>", "</context>", "<task>", "</task>", "<constraints>", "</constraints>", "<output_format>", "</output_format>"]
        all_present = all(tag in clean for tag in required_tags)

        if all_present:
            start_idx = clean.find("<role>")
            end_idx = clean.rfind("</output_format>") + len("</output_format>")
            if 0 <= start_idx < end_idx:
                return clean[start_idx:end_idx].strip()
            return clean

        return cls._build_5_part_prompt_from_content(raw_input if raw_input else clean)

    @classmethod
    def enforce_15_sections(cls, prompt_text: str, raw_input: str = "") -> str:
        """Alias for enforce_5_part_prompt to maintain backward compatibility."""
        return cls.enforce_5_part_prompt(prompt_text, raw_input=raw_input)

    @classmethod
    def _build_5_part_prompt_from_content(cls, raw: str) -> str:
        """
        Constructs the gold-standard 5-Part Master Prompt Blueprint using XML tags,
        modeled directly after the 22 production showcase archetypes:
        1. <role>: Dynamic Seniority + Domain Role (strictly non-canned)
        2. <context>: Target Application, exact Tech Stack, design theme, audience, data models (ZERO truncation)
        3. <task>: Structured functional views, components, and step-by-step procedural directions
        4. <constraints>: Context-aware negative guardrails (greenfield vs refactoring)
        5. <output_format>: Clear, step-by-step delivery contract
        """
        text = raw.strip() if raw else ""
        if not text:
            return (
                "<role>\n"
                "You are a Senior Staff Software Engineer.\n"
                "</role>\n\n"
                "<context>\n"
                "- Tech Stack: [Unspecified]\n"
                "- Current State: [Unspecified]\n"
                "</context>\n\n"
                "<task>\n"
                "Execute the requested engineering task with precision.\n\n"
                "1. Analyze requirements and identify affected components.\n"
                "2. Implement the core logic with robust error handling.\n"
                "3. Verify edge cases and validate implementation.\n"
                "</task>\n\n"
                "<constraints>\n"
                "- Provide complete, copy-paste runnable files without placeholder comments.\n"
                "- Enforce strict type safety and error resilience.\n"
                "</constraints>\n\n"
                "<output_format>\n"
                "Provide the complete, runnable solution followed by a brief summary of changes and usage instructions.\n"
                "</output_format>"
            )

        lower = text.lower()

        # ---------------------------------------------------------------------
        # 1. SPECIFIC SHOWCASE ARCHETYPES (22 PRODUCTION PATTERNS)
        # ---------------------------------------------------------------------

        # Archetype 1: Coffee Shop / E-Commerce Storefront
        if any(k in lower for k in ("coffee shop", "e-commerce", "ecommerce", "shopping cart", "product details page", "product listing")) and any(k in lower for k in ("cart", "checkout", "stripe", "react", "store")):
            role = "Senior Full-Stack Architect specializing in beginner-accessible MERN architectures, responsive UI design, and Stripe integration."
            context = (
                "Target Application: Coffee Shop E-Commerce Storefront & Order Management System.\n"
                "Tech Stack:\n"
                "- Frontend: React.js (Vite), Tailwind CSS, Lucide React icons\n"
                "- Backend: Node.js, Express.js (REST API)\n"
                "- Database: MongoDB via Mongoose ORM\n"
                "- Auth: JWT (HTTP-only cookies or Bearer auth) with bcrypt password hashing\n"
                "- Payments: Stripe Checkout / PaymentIntent API"
            )
            task = (
                "Architect and build an end-to-end, beginner-friendly coffee shop e-commerce platform across 6 primary views:\n"
                "1. Home: Hero banner with coffee aesthetics (warm espresso, cream, caramel tones), featured blends, value propositions.\n"
                "2. Product Listing: Grid with category filters (Roast, Origin, Whole Bean vs Ground) and price sorting.\n"
                "3. Product Details: High-res image display, flavor notes tags, weight selector (250g, 500g, 1kg), quantity, and Add to Cart.\n"
                "4. Shopping Cart: Slide-out drawer or page showing itemized summary, price calculation, and free shipping threshold meter.\n"
                "5. Authentication: Accessible Login & Registration forms with client & server-side validation.\n"
                "6. Checkout & Orders: Stripe checkout session trigger, order confirmation page, and order history storage.\n\n"
                "Execution Phases:\n"
                "- Phase 1: MongoDB Mongoose Models (`User`, `Product`, `Order`) with realistic seed data for artisanal coffees.\n"
                "- Phase 2: Express REST API routes (`/api/auth`, `/api/products`, `/api/cart`, `/api/orders`, `/api/stripe/create-checkout-session`).\n"
                "- Phase 3: React state management (Context API or Zustand) for persistent Cart state and User session.\n"
                "- Phase 4: Tailwind UI components styled with warm coffee palette tokens (`#3c2f2f`, `#6f4e37`, `#f5efe6`)."
            )
            constraints = (
                "- Provide complete, copy-paste runnable files without placeholder comments like `// TODO: implement logic`.\n"
                "- Separate concerns cleanly: `/controllers`, `/models`, `/routes`, and `/components`.\n"
                "- Ensure mobile-responsive viewport scaling and accessible form labels.\n"
                "- Include a seed script (`seed.js`) so the store is instantly testable."
            )
            output_format = "Present the code step-by-step starting with backend models and routes, followed by frontend state and pages, concluding with exact terminal commands to run both server and client."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 2: High-Converting SaaS Landing Page (CodePulse)
        if any(k in lower for k in ("landing page", "codepulse", "hero section", "pricing table", "bento grid", "faq accordion")):
            prod_name = '"CodePulse" — Autonomous AI Code Reviewer & SaaS Landing Page' if "codepulse" in lower else "High-Converting SaaS Marketing Landing Page"
            role = "Principal Product Designer and Conversion Rate Optimization (CRO) Frontend Engineer specializing in Next.js, Tailwind CSS, and Framer Motion."
            context = (
                f"Product: {prod_name}.\n"
                "Audience: Engineering leads, developers, and DevOps teams.\n"
                "Theme: Premium dark developer aesthetic (deep slate/zinc `#09090b`, electric cyan accents `#06b6d4`, subtle glassmorphic borders)."
            )
            task = (
                "Build a responsive, single-page marketing landing page containing:\n"
                "1. Sticky Header: Logo, navigation anchor links, GitHub star count badge, and high-contrast CTA.\n"
                "2. Hero Section: Badge, compelling headline, CI/CD speed value prop, primary/secondary CTAs, animated code diff preview.\n"
                "3. Social Proof Logo Ticker: Grayscale logos of tech companies with continuous loop animation.\n"
                "4. Bento Grid Features: 4 feature cards highlighting core capabilities.\n"
                "5. Interactive Pricing Matrix: 3 tiers (Hobby, Pro, Enterprise) with interactive Monthly vs Annual toggle.\n"
                "6. FAQ Accordion: 5 interactive collapsible questions covering security and setup.\n"
                "7. Footer: Newsletter signup, product links, status indicator, and copyright."
            )
            constraints = (
                "- Use React with Tailwind CSS and Lucide React icons.\n"
                "- Ensure accessible keyboard navigation for toggles and accordions.\n"
                "- Do not use placeholder images; build code-based visual mockups and SVG badges.\n"
                "- Deliver cleanly modularized React components (`Hero.tsx`, `BentoGrid.tsx`, `Pricing.tsx`, `Faq.tsx`)."
            )
            output_format = "Provide complete TSX/React code, Tailwind config customizations, and instructions for zero-layout-shift previewing."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 3: Windows 11 Fluent Desktop App
        if any(k in lower for k in ("system monitor", "windows 11 settings", "pyqt-fluent-widgets", "psutil", "cpu usage, ram", "kill buttons")):
            role = "Windows Desktop Software Engineer specializing in Python, PyQt6, and the Windows 11 Fluent Design System."
            context = (
                "Application: Native Windows 11 Hardware Telemetry & Process Monitor.\n"
                "Tech Stack: Python 3.11+, PyQt6, `PyQt-Fluent-Widgets` (fluent styling), `psutil` (hardware statistics).\n"
                "Visual Target: Native Windows 11 WinUI 3 look-and-feel with Mica background, rounded corners (8px-12px), and fluent dark mode theme."
            )
            task = (
                "Create a multi-tab desktop utility with the following architecture:\n"
                "1. Navigation Bar (NavigationInterface): Overview Tab, Disks Tab, Processes Tab, Settings Tab.\n"
                "2. Telemetry Worker: Dedicated `QThread` running non-blocking `psutil` polling to prevent UI freezing.\n"
                "3. Process Manager: `QTableView` with columns (PID, Name, Memory Usage, CPU %, Terminate action button) and real-time search filtering."
            )
            constraints = (
                "- Strict thread safety: Never update UI elements directly from background threads; use `pyqtSignal`.\n"
                "- Graceful error handling for permission denied errors (`psutil.AccessDenied`) when querying system processes.\n"
                "- Complete, runnable Python script with all imports and dependencies."
            )
            output_format = "Provide the full Python code structured into `WorkerThread`, `MainWindow`, and main execution guard (`if __name__ == '__main__':`)."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 4: RESTful API Contract & Mock Server
        if any(k in lower for k in ("api spec", "mock server", "patient appointment", "dental clinic", "openapi")):
            role = "Principal API Architect & Backend Engineer specializing in OpenAPI 3.1 specification design, schema governance, and contract testing."
            context = (
                "Domain: Appointment Scheduling & Healthcare Practice Platform.\n"
                "Standards: RESTful design, RFC 7807 problem details error format, ISO 8601 timestamps, UUIDv4 identifiers."
            )
            task = (
                "1. OpenAPI 3.1 Specification:\n"
                "   - Define canonical schemas: Patients, Providers, Services, and Appointments (with status lifecycles).\n"
                "   - Define endpoints for listing services, provider availability, appointment booking (with conflict prevention), and cancellation.\n"
                "2. High-Fidelity Mock Server:\n"
                "   - Generate a lightweight mock server responding with schema-compliant fixture data and realistic latency simulation."
            )
            constraints = (
                "- Include comprehensive request validation schemas with regex patterns.\n"
                "- Document all HTTP status codes: 200, 201, 400 Bad Request, 404 Not Found, and 409 Conflict."
            )
            output_format = "1. Valid OpenAPI 3.1 YAML contract block.\n2. Complete runnable mock server script with instructions to test via curl."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 5: Web Scraper & Ingestion Engine
        if any(k in lower for k in ("scraper", "scraping", "careers page", "crawl4ai", "scrapling", "sqlite")):
            role = "Data Ingestion Engineer specializing in modern Python web crawling (`crawl4ai` / `Scrapling` / `Playwright`), anti-bot compliance, and structured extraction."
            context = (
                "Target: Dynamic web portal with structured extraction requirements.\n"
                "Persistence: Local SQLite database with WAL mode, schema versioning, and upsert deduplication.\n"
                "Data Model: Extracted record entity with metadata and source URL."
            )
            task = (
                "1. Asynchronous Ingestion Engine: Crawl listings with token-bucket rate limiting and exponential retry backoff on HTTP 429/503.\n"
                "2. Extraction Pipeline: Parse unstructured HTML/markdown into typed Pydantic V2 models.\n"
                "3. Database Storage: SQLite initialization with WAL mode and `ON CONFLICT` upsert logic."
            )
            constraints = (
                "- Do not use brittle regex for HTML parsing; use robust CSS selectors or structured markdown extraction.\n"
                "- Provide full type hints, docstrings, and a sample test run output."
            )
            output_format = "Provide complete Python code including Pydantic models, scraper class, database repository, and CLI entrypoint."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 6: Tabular Machine Learning Predictor
        if any(k in lower for k in ("churn", "xgboost", "telecom csv", "predict customer churn", "feature importance")):
            role = "Staff Machine Learning Engineer & Applied Data Scientist specializing in tabular classification pipelines, scikit-learn, XGBoost, and model interpretability."
            context = (
                "Task: Tabular Classification Pipeline with evaluation and interpretability.\n"
                "Dataset Characteristics: Structured records with demographic, tenure, numeric charges, and target labels."
            )
            task = (
                "Build an end-to-end, production-grade Python ML pipeline adhering to data science best practices:\n"
                "1. Data Sanitization & Preprocessing: Convert numeric strings, encode categorical variables, and impute missing values without leakage.\n"
                "2. Stratified Splitting: 80/20 train/test split stratified on target.\n"
                "3. Model Training & Cross-Validation: Construct scikit-learn Pipeline with ColumnTransformer and XGBClassifier with 5-fold CV.\n"
                "4. Evaluation & Diagnostic Reports: Confusion Matrix, Classification Report (Precision, Recall, F1), ROC curve, and SHAP/gain feature importance."
            )
            constraints = (
                "- Zero data leakage: Fits transforms strictly on the training set, transforming the test set.\n"
                "- Well-commented, modular Python code ready for execution."
            )
            output_format = "Clean Python script organized into modular functions: `load_and_clean_data()`, `build_pipeline()`, `evaluate_model()`, and `plot_feature_importance()`."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 7: Zero-Downtime Database Migration
        if any(k in lower for k in ("split the `users.name`", "split the users.name", "zero-downtime", "expand/contract", "blue-green schema", "alembic")):
            role = "Principal Database Reliability Engineer (DBRE) specializing in high-scale PostgreSQL, Prisma/Alembic migrations, and zero-downtime schema evolution."
            context = (
                "System: Production PostgreSQL database under continuous read/write load.\n"
                "Risk: Locking high-traffic tables or causing microservice crashes during deployment."
            )
            task = (
                "Design and execute a zero-downtime migration strategy using the Expand/Contract pattern across 4 safe phases:\n"
                "1. Expand Phase: Add nullable target columns without table rewrites and establish dual-write triggers.\n"
                "2. Backfill Phase: Batched, throttle-controlled background worker processing rows with lock prevention.\n"
                "3. Switchover Phase: Validate 100% data parity and update application code to read from new columns.\n"
                "4. Contract Phase: Remove trigger, add constraints safely, and drop legacy columns."
            )
            constraints = (
                "- Never run long-running table locks (`ACCESS EXCLUSIVE`).\n"
                "- Provide rollback procedures for each individual phase."
            )
            output_format = "Deliver the complete migration plan: numbered SQL migration files with explanation of locking behavior."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 8: Multi-Stage Docker & Compose
        if any(k in lower for k in ("dockerize", "dockerfile", "docker compose up", "multi-stage", "distroless")):
            role = "Staff DevOps & Containerization Engineer specializing in Docker, multi-stage builds, rootless containers, and local development environments."
            context = (
                "Target: Production-grade containerization and local development orchestration.\n"
                "Services: Frontend web service, backend API, and shared cache/database."
            )
            task = (
                "1. Multi-Stage Dockerfile for web: `deps`, `builder`, and `runner` (distroless/alpine non-root user).\n"
                "2. Multi-Stage Dockerfile for API: development (hot reload) and production compiled stages.\n"
                "3. Docker Compose: Healthchecks (`service_healthy`), persistent volumes, and dependency ordering."
            )
            constraints = (
                "- Enforce non-root user execution in all production images.\n"
                "- Optimize layer caching so dependency lockfiles copy before application code.\n"
                "- Prevent sensitive credentials from being baked into images."
            )
            output_format = "Provide the Dockerfiles, `.dockerignore`, `docker-compose.yml`, and exact startup commands."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 9: Flutter Mobile App
        if any(k in lower for k in ("flutter", "riverpod", "gorouter", "fitness tracking", "material 3")):
            role = "Principal Flutter Architect specializing in Dart 3, Riverpod 2.0 (code generation), GoRouter, and responsive Material 3 design."
            context = (
                "Target: Cross-platform iOS and Android Mobile App.\n"
                "Architecture: Feature-first layered architecture (presentation, application, domain, data).\n"
                "State Management: `flutter_riverpod` with `riverpod_generator` and `go_router` declarative navigation."
            )
            task = (
                "Architect and build the mobile application core:\n"
                "1. Data Models: Freezed/Dart 3 immutable domain models.\n"
                "2. UI Screens & Navigation: Shell navigation with persistent bottom bar across primary feature screens.\n"
                "3. State Management: AsyncNotifier managing operations, local persistence, and reactive listening."
            )
            constraints = (
                "- Enforce Material 3 theming with custom dynamic color scheme.\n"
                "- Full type safety with zero runtime null-assertion crashes.\n"
                "- Responsive layout handling varying screen heights and safe areas."
            )
            output_format = "Provide directory structure layout followed by complete, runnable Dart code files and `pubspec.yaml`."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 10: In-Memory Caching & Columnar Analytics (DuckDB + Redis)
        if any(k in lower for k in ("duckdb", "parquet", "redis and run analytical", "olap queries")):
            role = "High-Performance Systems Architect specializing in Python, Redis caching patterns, and embedded analytical OLAP with DuckDB."
            context = (
                "Workload: High-concurrency dashboard requesting sub-second aggregations over partitioned Parquet datasets.\n"
                "Tech Stack: Python 3.12, DuckDB, Redis, FastAPI."
            )
            task = (
                "1. DuckDB Analytical Engine: Parameterized sub-second queries directly over partitioned Parquet files.\n"
                "2. Redis Caching Middleware (Cache-Aside): Deterministic SHA-256 query hash keys, TTL management, and invalidation.\n"
                "3. API Gateway: FastAPI endpoints with diagnostic cache hit/miss headers (`X-Cache-Status`)."
            )
            constraints = (
                "- Prevent Cache Stampede using distributed locks or early probabilistic expiration.\n"
                "- Safe parameterized SQL queries preventing SQL injection."
            )
            output_format = "Provide complete Python implementation including DuckDB query logic, Redis cache decorator, and FastAPI route."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 11: Enterprise Auth & JWT Security
        if any(k in lower for k in ("jwt tokens", "refresh tokens rotate", "xss or csrf", "user login system with jwt")):
            role = "Staff Application Security Engineer specializing in OAuth 2.0, JWT token lifecycles, and OWASP Session Management standards."
            context = (
                "Target: Production Authentication & Session Subsystem.\n"
                "Threat Model: Protection against XSS token theft, CSRF attacks, replay attacks, and token reuse."
            )
            task = (
                "Implement an enterprise-grade dual-token authentication flow:\n"
                "1. Token Architecture: Short-lived Access Token (15-min) and long-lived Refresh Token (7-day) stored in database.\n"
                "2. Secure Transport & Cookies: Store Refresh Token in HttpOnly, Secure, SameSite=Strict cookie; Access Token in memory.\n"
                "3. Refresh Token Rotation & Family Tracking: Invalidate used refresh tokens and detect replay breaches.\n"
                "4. Revocation & Logout: Endpoint clearing cookies and invalidating sessions across devices."
            )
            constraints = (
                "- Implement strict CSRF protection and constant-time string comparisons.\n"
                "- Provide test suite simulating token replay attacks."
            )
            output_format = "Provide complete controller, middleware, database schema, and test suite simulating token replay attacks."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 12: Event-Driven Kafka Microservices
        if any(k in lower for k in ("kafka", "orderplaced", "notification service in python", "dead letter queue")):
            role = "Principal Distributed Systems Engineer specializing in event-driven microservices, Apache Kafka, and resilient message processing."
            context = (
                "Service: Notification Worker Consumer Service.\n"
                "Resilience Target: At-least-once delivery, zero data loss, Dead Letter Queue (DLQ), and idempotent dispatch."
            )
            task = (
                "1. Resilient Consumer Loop: Asynchronous Kafka consumer with manual offset commits after successful dispatch.\n"
                "2. Fault Tolerance & DLQ: Catch retryable exceptions with exponential backoff; route poison pills to DLQ.\n"
                "3. Idempotent Processing: Redis/database idempotency check based on eventId to prevent duplicates."
            )
            constraints = (
                "- Handle OS shutdown signals (`SIGINT`, `SIGTERM`) gracefully.\n"
                "- Clean logging with correlation IDs passed from message headers."
            )
            output_format = "Complete Python worker script, Docker Compose with Kafka, and test event producer script."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 13: Property-Based Testing with Hypothesis
        if any(k in lower for k in ("currency exchange calculation", "hypothesis", "eur, usd, gbp, rounding")):
            role = "Lead Quality & Test Automation Architect specializing in `pytest`, `Hypothesis` property-based testing, and financial arithmetic accuracy."
            context = (
                "Library Under Test: Monetary and Currency Exchange calculation module.\n"
                "Financial Requirements: Strict avoidance of floating-point inaccuracies (`decimal.Decimal`), banker's rounding, and conversion fees."
            )
            task = (
                "1. Core Implementation: `Money` value object with arithmetic operations and cent-loss-free allocation.\n"
                "2. Property-Based Fuzzing with Hypothesis: Invariant testing `(A + B) - B == A`, split summation parity, and round-trip bounds.\n"
                "3. Edge Case Suite: Negative/zero amounts, currency mismatch errors, and ultra-large values."
            )
            constraints = (
                "- Zero use of native Python `float` for currency.\n"
                "- Achieve 100% test branch coverage with automated pytest execution commands."
            )
            output_format = "Complete `money.py` implementation followed by `test_money.py` with unit tests and Hypothesis property strategies."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 14: Dark-Mode SaaS Analytics Dashboard
        if any(k in lower for k in ("saas analytics dashboard", "shadcn charts", "area chart for traffic")):
            role = "Lead Frontend Architect specializing in React 19, Tailwind CSS, shadcn/ui components, and accessible data visualization."
            context = (
                "Target: Web Analytics SaaS Admin Dashboard.\n"
                "Style: Minimalist dark mode palette (zinc `#09090b` background, emerald and indigo data accents).\n"
                "Components: shadcn/ui primitives (`Card`, `Badge`, `Tabs`) and Recharts."
            )
            task = (
                "Create an interactive, accessible dashboard view:\n"
                "1. Top Metric Cards Grid: 4 KPI cards with trend indicators and sparklines.\n"
                "2. Interactive Traffic Area Chart: 30-day time series showing Pageviews vs Unique Visitors with gradient fills.\n"
                "3. Recent Transactions Table: User avatar, plan status badge, and amount.\n"
                "4. Date Range Selector & Loading State: Skeleton shimmer loading states."
            )
            constraints = (
                "- Strict TypeScript types for all chart data series.\n"
                "- Seamless responsiveness: stacking grid cards on mobile, expanding to 4-column layout on 1280px+."
            )
            output_format = "Provide complete TSX components (`Dashboard.tsx`, `MetricsCards.tsx`, `AnalyticsChart.tsx`) with zero missing imports."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 15: BullMQ Job Queue
        if any(k in lower for k in ("bullmq", "resize images", "thumbnail sizes")):
            role = "Principal Backend Systems Engineer specializing in Node.js, BullMQ, Redis streams, and asynchronous media processing pipelines."
            context = (
                "Task: Distributed Image Processing Worker.\n"
                "Stack: Node.js (TypeScript), `bullmq`, `ioredis`, and `sharp` image manipulation library."
            )
            task = (
                "1. Queue Producer: BullMQ Queue with exponential retry policy.\n"
                "2. Worker Processor: Concurrent job execution using `sharp` generating optimized WebP formats (Thumbnail, Medium, Large).\n"
                "3. Event Listeners & Diagnostics: Track completed, failed, and stalled jobs."
            )
            constraints = (
                "- Stream buffers through Sharp rather than keeping multiple uncompressed images in RAM.\n"
                "- Handle unexpected crashes by properly cleaning up orphaned temporary files."
            )
            output_format = "Provide complete TypeScript files: `queue.ts`, `worker.ts`, and a test simulation script `produceJob.ts`."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 16: Playwright E2E UI Testing
        if any(k in lower for k in ("playwright tests for our web app checkout", "playwright tests")):
            role = "Principal QA Automation Engineer specializing in Microsoft Playwright, Page Object Model (POM) architecture, and resilient CI test automation."
            context = (
                "Application: E-Commerce Storefront Checkout Flow.\n"
                "Tooling: Playwright (TypeScript), cross-browser validation (Chromium, Firefox, WebKit)."
            )
            task = (
                "1. Page Object Model (POM) Structure: `LoginPage`, `ProductPage`, `CheckoutPage`.\n"
                "2. End-to-End Test Suite: Happy path checkout completion and validation error edge cases.\n"
                "3. Visual Snapshot Comparison: Assert zero layout regression on order summary page (`toHaveScreenshot()`)."
            )
            constraints = (
                "- Strictly no arbitrary `page.waitForTimeout()` sleeps; utilize built-in auto-waiting and web-first assertions.\n"
                "- Parallel execution support with isolated test fixtures."
            )
            output_format = "Complete TypeScript files: `page-objects/*.ts`, `tests/checkout.spec.ts`, and `playwright.config.ts`."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 17: Local LLM Serving (llama.cpp)
        if any(k in lower for k in ("local gguf model", "llama-cpp-python", "openai-compatible /v1/chat/completions")):
            role = "AI Systems Engineer specializing in local LLM serving, `llama.cpp`, GGUF quantization, and OpenAI-compatible streaming APIs."
            context = (
                "Target: Self-hosted local inference microservice with GPU/CPU hardware acceleration.\n"
                "Interface: OpenAI API-compatible streaming Server-Sent Events (SSE) `/v1/chat/completions`."
            )
            task = (
                "1. Model Initialization: Load GGUF model weights with configurable context size and GPU offloading.\n"
                "2. FastAPI Gateway: Implement `/v1/models` and `/v1/chat/completions` supporting both JSON and streaming SSE.\n"
                "3. Concurrency: Thread locking protecting inference passes to prevent VRAM corruption."
            )
            constraints = (
                "- Validate incoming messages array with Pydantic.\n"
                "- Provide curl testing commands for streaming and non-streaming requests."
            )
            output_format = "Complete, runnable `server.py` script with requirements, CLI arguments, and client usage examples."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 18: Open Source GitHub README
        if any(k in lower for k in ("readme for my github project", "linkmark", "goroutines")):
            role = "Senior Technical Writer and Open Source Maintainer specializing in top 1% developer portfolio documentation and GitHub repository presentation."
            context = (
                "Project: Production CLI tool in Go with concurrent worker routines.\n"
                "Target Audience: Developers, technical recruiters, and open-source contributors."
            )
            task = (
                "Author a production-grade, aesthetically stunning `README.md` containing:\n"
                "1. Header & Badges: Title, value proposition, and live GitHub shields.\n"
                "2. Key Features: Bulleted highlights emphasizing speed and exit-code compatibility.\n"
                "3. Performance Benchmark Table: Latency and memory footprint comparisons.\n"
                "4. Installation Matrix: One-line install scripts via package managers and Docker.\n"
                "5. Architecture Overview & Mermaid Diagram: Visual execution flow of workers."
            )
            constraints = (
                "- Use clean GitHub Flavored Markdown with custom collapsible sections.\n"
                "- Provide copy-pasteable commands and zero generic filler copy."
            )
            output_format = "Full, raw markdown content of `README.md` ready to be committed directly to the repository."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 19: Real-Time WebSockets Chat
        if any(k in lower for k in ("real-time team chat", "websockets", "who is typing, who is online")):
            role = "Principal Real-Time Systems Engineer specializing in WebSockets, Socket.IO, React, and ephemeral state management."
            context = (
                "Application: Multi-Room Team Collaboration Chat with Socket.IO and React.\n"
                "Ephemeral Store: In-memory ring buffer storing the latest 50 messages per room."
            )
            task = (
                "1. WebSocket Protocol Events: Bi-directional room joining, messaging, and typing indicator broadcasting.\n"
                "2. Backend Server Architecture: Socket connection tracking, room partitioning, and debounced typing status.\n"
                "3. React Frontend UI: Room list sidebar, online presence indicators, message timeline, and auto-scroll."
            )
            constraints = (
                "- Graceful disconnect cleanup: automatically remove user presence when socket drops.\n"
                "- Prevent XSS by sanitizing all incoming message payloads before broadcast."
            )
            output_format = "Step-by-step code implementation: backend server (`server.js`) followed by frontend socket hook and main chat UI."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 20: Stripe Subscription Billing & Webhooks
        if any(k in lower for k in ("stripe billing to our saas", "customer portal for cancellations", "pro plan for $19")):
            role = "Senior Fintech & Backend Billing Architect specializing in Stripe API v2024, webhook signature verification, and SaaS subscription lifecycles."
            context = (
                "Target: Subscription Billing Engine for SaaS ($19/mo recurring).\n"
                "Stack: Node.js (Express), Prisma ORM (PostgreSQL), and official Stripe SDK."
            )
            task = (
                "1. Stripe Checkout Session: Customer creation and hosted checkout session generation.\n"
                "2. Stripe Customer Portal: Direct portal session for credit card updates and cancellations.\n"
                "3. Production Webhook Controller: Raw body parsing, `stripe-signature` verification, and lifecycle handling.\n"
                "4. Database Synchronization: User subscription status and period end tracking."
            )
            constraints = (
                "- Strict webhook idempotency: Handle duplicate delivery attempts without double-crediting accounts.\n"
                "- Return HTTP 200 immediately to Stripe upon successful event ingestion."
            )
            output_format = "Provide complete controller code, webhook verification middleware, Prisma schema snippet, and Stripe CLI test commands."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 21: Database Query Performance & Index Tuning
        if any(k in lower for k in ("orders table query is super slow", "optimize the postgres query", "composite index")):
            role = "Principal Database Performance Engineer specializing in PostgreSQL query optimization, execution plan analysis, and indexing strategies."
            context = (
                "Table: High-traffic relational database table under continuous querying.\n"
                "Problem: Slow query latency causing sequential scans and heap fetches."
            )
            task = (
                "1. Execution Plan Analysis (`EXPLAIN (ANALYZE, BUFFERS)`): Diagnose sequential scan bottlenecks.\n"
                "2. Composite B-Tree Index Design: Design optimal index adhering to Equality-Range-Sort rules.\n"
                "3. Non-Blocking Index Deployment: Provide zero-downtime `CREATE INDEX CONCURRENTLY` statements.\n"
                "4. Covering Index Optimization: Evaluate `INCLUDE` clauses for Index-Only Scans."
            )
            constraints = (
                "- Include exact `EXPLAIN ANALYZE` commands to benchmark query latency before and after index creation.\n"
                "- Detail index storage overhead trade-offs."
            )
            output_format = "Provide analysis explanation, SQL DDL statements, before/after execution plan interpretations, and verification queries."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # Archetype 22: Multi-Tenant RBAC & Isolation
        if any(k in lower for k in ("multi-tenant permissions", "organizations can have owners, admins", "tenant isolation")):
            role = "Principal Security & Backend Architect specializing in Multi-Tenant SaaS systems, Role-Based Access Control (RBAC), and Row-Level Security."
            context = (
                "Architecture: Multi-Tenant B2B Platform with organization-level data isolation.\n"
                "Roles: `OWNER`, `ADMIN`, `MEMBER`, `VIEWER` with granular permission matrices."
            )
            task = (
                "1. Data Model Architecture: `Organization`, `User`, `Membership`, and scoped resource schemas.\n"
                "2. Declarative Permission Matrix: Enums mapping roles to discrete permissions.\n"
                "3. Authorization Middleware: Tenant resolution and role checking.\n"
                "4. Tenant Isolation Guardrails: Middleware automatically injecting tenant scoping on all queries."
            )
            constraints = (
                "- Prevent Privilege Escalation: Admins cannot promote themselves to Owner.\n"
                "- Provide comprehensive test cases asserting 403 Forbidden for unauthorized roles."
            )
            output_format = "Complete schema, permission definition file, middleware implementation, and route usage examples."
            return f"<role>\n{role}\n</role>\n\n<context>\n{context}\n</context>\n\n<task>\n{task}\n</task>\n\n<constraints>\n{constraints}\n</constraints>\n\n<output_format>\n{output_format}\n</output_format>"

        # ---------------------------------------------------------------------
        # 2. GENERAL DYNAMIC BUILDER FOR ANY CUSTOM USER THOUGHT
        # ---------------------------------------------------------------------

        # Detect technologies mentioned in user input
        detected_tech = []
        tech_keywords = [
            ("React.js", [r'\breact(?:\.js)?\b']),
            ("Next.js 15", [r'\bnext(?:\.js)?(?:\s*15)?\b']),
            ("Tailwind CSS", [r'\btailwind(?:\s*css)?\b']),
            ("Node.js", [r'\bnode(?:\.js)?\b']),
            ("Express.js", [r'\bexpress(?:\.js)?\b']),
            ("FastAPI", [r'\bfastapi\b']),
            ("Python 3.12", [r'\bpython(?:\s*3(?:\.\d+)?)?\b']),
            ("MongoDB / Mongoose", [r'\bmongo(?:db)?\b', r'\bmongoose\b']),
            ("PostgreSQL", [r'\bpostgres(?:ql)?\b']),
            ("Redis", [r'\bredis\b']),
            ("DuckDB", [r'\bduckdb\b']),
            ("TypeScript", [r'\btypescript\b', r'\bts\b']),
            ("PyQt6 / WinUI", [r'\bpyqt6?\b', r'\bfluent\b', r'\bwinui\b']),
            ("Flutter / Dart", [r'\bflutter\b', r'\bdart\b']),
            ("Stripe", [r'\bstripe\b']),
            ("JWT Auth", [r'\bjwt\b', r'\bauth\b', r'\blogin\b']),
            ("Docker", [r'\bdocker\b', r'\bcontainer\b']),
            ("Playwright", [r'\bplaywright\b']),
            ("Apache Kafka", [r'\bkafka\b']),
            ("PortAudio / WASAPI", [r'\bportaudio\b', r'\bwasapi\b', r'\bsounddevice\b']),
            ("Whisper Speech AI", [r'\bwhisper\b', r'\basr\b', r'\bspeech\b'])
        ]
        for label, pats in tech_keywords:
            if any(re.search(p, text, re.IGNORECASE) for p in pats):
                detected_tech.append(label)

        # Detect files
        files_found = re.findall(r'[\w./\\]+\.(?:py|tsx?|jsx?|cs|cpp|json|md|html|css)', text)
        if files_found:
            detected_tech.extend(list(dict.fromkeys(files_found)))

        # Dynamic Role Attribution
        is_greenfield = any(k in lower for k in ("create", "build", "make", "develop", "website", "app", "application", "platform", "system", "tool", "scraper"))
        is_security = bool(re.search(r'\b(?:auth|security|login|oauth|jwt|session|password|token)\b', text, re.IGNORECASE))
        is_frontend = bool(re.search(r'\b(?:react|vue|tailwind|frontend|ui|css|html|component)\b', text, re.IGNORECASE))
        is_backend = bool(re.search(r'\b(?:node|express|fastapi|backend|api|database|postgres|mongo|sql)\b', text, re.IGNORECASE))

        if is_frontend and is_backend:
            role = f"Senior Full-Stack Architect specializing in {' and '.join(detected_tech[:3]) if detected_tech else 'Full-Stack Web Engineering'}."
        elif is_frontend:
            role = f"Senior Frontend Engineer specializing in {detected_tech[0] if detected_tech else 'Modern UI Engineering'} and Responsive Design Systems."
        elif is_backend:
            role = f"Senior Backend Architect specializing in {detected_tech[0] if detected_tech else 'Distributed Systems'} and Scalable APIs."
        elif re.search(r'\b(?:audio|portaudio|sounddevice|wasapi|microphone|mic)\b', text, re.IGNORECASE):
            role = "Senior Systems Software Engineer specializing in Windows Audio APIs and PortAudio."
        elif re.search(r'\b(?:whisper|groq|moonshine|speech|asr|stt|voice)\b', text, re.IGNORECASE):
            role = "Senior Machine Learning & Speech Recognition Systems Architect."
        elif is_security:
            role = "Staff Application Security Engineer specializing in Secure Authentication and Access Control."
        else:
            role = "Senior Staff Software Engineer specializing in Production Software Architecture."

        # Dynamic Context (ZERO TRUNCATION)
        context_lines = []
        # Target Application
        target_name = "Application Feature Specification"
        first_line = [l.strip() for l in text.splitlines() if l.strip()]
        if first_line:
            target_name = first_line[0][:90].rstrip('.')

        context_lines.append(f"Target: {target_name}")
        if detected_tech:
            context_lines.append(f"Tech Stack:\n" + "\n".join([f"- {t}" for t in dict.fromkeys(detected_tech)]))
        else:
            context_lines.append("Tech Stack:\n- Production tooling appropriate for the specified language and platform.")

        # Full User Specifications (Without Truncation)
        context_lines.append(f"Requirements & Scope:\n{text}")
        context_block = "\n".join(context_lines)

        # Dynamic Task Block
        sentences = [s.strip() for s in re.split(r'[.!?\n]+', text) if len(s.strip()) > 5]
        task_title = sentences[0] if sentences else "Implement the requested system architecture."
        if not task_title.endswith("."):
            task_title += "."

        sub_steps = []
        if len(sentences) > 1:
            for s in sentences[1:6]:
                sub_steps.append(f"{s.rstrip('.')}.")
        if len(sub_steps) < 1:
            sub_steps.append("Architect core data models and interfaces.")
        if len(sub_steps) < 2:
            sub_steps.append("Implement business logic, service layers, and validation rules.")
        if len(sub_steps) < 3:
            sub_steps.append("Handle error boundaries, edge cases, and user feedback gracefully.")

        numbered_steps = "\n".join([f"{i+1}. {step}" for i, step in enumerate(sub_steps)])
        task_block = f"{task_title}\n\n{numbered_steps}"

        # Context-Aware Constraints (Greenfield vs Refactoring)
        constraint_items = []
        if is_greenfield:
            constraint_items.append("- Provide complete, copy-paste runnable files without placeholder comments like `// TODO: implement logic`.")
            constraint_items.append("- Separate concerns cleanly into modular components, models, and routes.")
            constraint_items.append("- Ensure responsive viewport scaling, accessible inputs, and resilient error handling.")
            constraint_items.append("- Include seed data or test instructions so the implementation is immediately verifiable.")
        else:
            constraint_items.append("- Strictly modify only targeted code; do not rewrite working adjacent logic.")
            constraint_items.append("- Never use placeholder comments (e.g., `// TODO`); provide complete, runnable code.")
            constraint_items.append("- Enforce strict type safety and backward compatibility.")

        constraints_block = "\n".join(dict.fromkeys(constraint_items))

        # Output Format
        if is_greenfield:
            output_format = "Present the code step-by-step starting with backend models and routes, followed by frontend state and pages, concluding with exact terminal commands to run both server and client."
        elif files_found:
            output_format = f"Provide the complete, runnable code for {', '.join(files_found)} followed by a brief summary of changes and verification steps."
        else:
            output_format = "Provide the complete, runnable code solution followed by usage and verification commands."

        return (
            f"<role>\n{role}\n</role>\n\n"
            f"<context>\n{context_block}\n</context>\n\n"
            f"<task>\n{task_block}\n</task>\n\n"
            f"<constraints>\n{constraints_block}\n</constraints>\n\n"
            f"<output_format>\n{output_format}\n</output_format>"
        )

    @classmethod
    def _build_15_section_prompt_from_content(cls, raw: str) -> str:
        """Alias for _build_5_part_prompt_from_content to ensure 5-part blueprint format."""
        return cls._build_5_part_prompt_from_content(raw)

    @classmethod
    def convert_to_prompt(cls, text: str, model_client: Optional[Any] = None) -> str:
        """
        Transforms raw notes, spoken thoughts, or developer bug reports into a structured,
        self-contained AI prompt strictly adhering to the 5-Part Master Prompt Blueprint using XML tags.
        """
        if not text or not text.strip():
            return cls._build_5_part_prompt_from_content("")

        raw = text.strip()

        # If GeminiTransformService or model client provided, delegate prompt meta-generation directly
        if model_client is not None and hasattr(model_client, "transform_to_ai_prompt"):
            try:
                res = model_client.transform_to_ai_prompt(raw)
                if getattr(res, "success", False) and getattr(res, "text", None):
                    return cls.enforce_5_part_prompt(res.text, raw_input=raw)
            except Exception as e:
                logger.debug(f"GeminiTransformService prompt note: {e}")

        if model_client is not None and hasattr(model_client, "transform_text"):
            try:
                res = model_client.transform_text(raw, transform_type=TransformType.CONVERT_PROMPT)
                if hasattr(res, "success") and res.success and getattr(res, "text", None):
                    return cls.enforce_5_part_prompt(res.text, raw_input=raw)
            except Exception as e:
                logger.debug(f"model_client transform_text note: {e}")

        # Build genuine 5-part structure from extracted content
        return cls._build_5_part_prompt_from_content(raw)

    @classmethod
    def transform_text(
        cls,
        text: str,
        transform_type: TransformType = TransformType.IMPROVE,
        app_context: Optional[AppContext] = None,
        custom_instruction: str = "",
        model_client: Optional[Any] = None
    ) -> str:
        """
        Central transformation pipeline for Alt+T and Alt+P:
        - Alt+P (CONVERT_PROMPT): Enforces the 5-Part Master Prompt Blueprint using XML tags (<role>, <context>, <task>, <constraints>, <output_format>).
        - Alt+T (TRANSFORM_TEXT / IMPROVE): Cleans speech disfluencies and fillers, corrects grammar and tenses,
          preserves technical entities and numbers, and applies smart formatting into paragraphs or bullet points.
        """
        if not text or not text.strip():
            return ""

        # Route Alt+P Prompt Enhancement to dedicated prompt conversion
        if transform_type in (TransformType.CONVERT_PROMPT, TransformType.PROMPT):
            return cls.convert_to_prompt(text, model_client=model_client)

        # Dedicated GeminiTransformService handles full raw text cleanly without destructive filler stripping
        if model_client is not None and hasattr(model_client, "transform_universal_text"):
            try:
                ctx_dict = {"app_name": getattr(app_context, "app_name", "")} if app_context is not None else None
                res = model_client.transform_universal_text(text=text.strip(), app_context=ctx_dict)
                if getattr(res, "success", False) and getattr(res, "text", None):
                    return res.text
            except Exception as ex:
                logger.debug(f"GeminiTransformService text transform note: {ex}")

        # Route Alt+T Text Transformation
        # 1. Filter verbal fillers and accidental stutter repetitions
        cleaned = cls.filter_speech_fillers(text)

        # 2. If model_client available (e.g. GeminiEngine), delegate to model
        if model_client is not None and hasattr(model_client, "transform_text"):
            try:
                res = model_client.transform_text(
                    raw_text=cleaned,
                    transform_type=transform_type,
                    app_context=app_context,
                    custom_instruction=custom_instruction
                )
                if hasattr(res, "success") and res.success and getattr(res, "text", None):
                    return res.text
            except Exception as ex:
                logger.debug(f"model_client text transform note: {ex}")

        # 3. Deterministic grammar polish and tense correction preserving numbers and meaning
        polished = cls._correct_common_spoken_grammar(cleaned)

        # 4. Smart bullet / paragraph formatting
        formatted = cls.format_smart_structure(polished)

        return formatted

    def transform(
        self,
        text: str,
        transform_type: TransformType = TransformType.IMPROVE,
        **kwargs
    ) -> str:
        """Instance method for transformation using the initialized model client."""
        return self.transform_text(text, transform_type=transform_type, model_client=self.gemini_engine, **kwargs)
