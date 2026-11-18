"""
Centralized Command Registry for Gemini Flow.
Contains the unified definitions, prompts, contracts, and validators for all 16 command categories.
Commands execute only when selected in the Profile tab or when the spoken trigger phrase
appears as the FIRST words of the dictation.
"""
import ast
import re
import difflib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Tuple, Set

from app.intelligence.post_processing import fidelity_gate, extract_numbers_and_symbols


@dataclass
class CommandDefinition:
    id: str
    name: str
    trigger_phrases: List[str]
    system_prompt: str
    input_contract: str
    output_contract: str
    validator: Callable[[str, str], Tuple[bool, str]]  # (input_text, output_text) -> (is_valid, error_reason)
    default_temperature: float = 0.2
    max_tokens: int = 2048
    sample_input: str = ""
    is_action: bool = False


# -------------------------------------------------------------------------
# INDIVIDUAL COMMAND VALIDATORS
# -------------------------------------------------------------------------


_NUMBER_WORDS: Dict[str, str] = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
    "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
    "eighty": "80", "ninety": "90",
}


def _extract_normalized_numbers(text: str, include_words: bool = False) -> Set[str]:
    """Extracts numeric tokens normalized without currency symbols, commas, or % signs."""
    nums: Set[str] = set()
    for tok in extract_numbers_and_symbols(text):
        cleaned = re.sub(r'^[\$€£₹¥]+|%+$', '', tok).replace(",", "").strip()
        if cleaned:
            nums.add(cleaned)
    if include_words:
        for word in re.findall(r'\b[a-z]+\b', (text or "").lower()):
            if word in _NUMBER_WORDS:
                nums.add(_NUMBER_WORDS[word])
    return nums


def _check_preserved_numbers(inp: str, out: str, context_label: str) -> Tuple[bool, str]:
    """Verify all numeric values from input survive in output (allowing spelled-out number words)."""
    raw_nums = _extract_normalized_numbers(inp, include_words=False)
    out_nums = _extract_normalized_numbers(out, include_words=True)
    missing = raw_nums - out_nums
    if missing:
        return False, f"{context_label} dropped numbers: {missing}"
    return True, "Valid"


def validate_action(inp: str, out: str) -> Tuple[bool, str]:
    return True, "Valid action"


def validate_professionalize(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Output is empty."
    return _check_preserved_numbers(inp, out, "Professionalize")


def validate_fix_grammar(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Grammar output is empty."
    ok, _, reason = fidelity_gate(inp, out)
    if ok:
        return True, "Valid"
    # For short sentences (<= 25 words), legitimate verb tense / plural / article fixes
    # (e.g. "go -> went", "seen -> saw", "problem -> problems") legitimately exceed 25% word-token diff.
    inp_words = inp.strip().split()
    out_words = out.strip().split()
    if len(inp_words) <= 25:
        raw_nums = _extract_normalized_numbers(inp, include_words=False)
        out_nums = _extract_normalized_numbers(out, include_words=True)
        if not (raw_nums - out_nums):
            len_diff = abs(len(out_words) - len(inp_words)) / float(max(1, len(inp_words)))
            char_sim = difflib.SequenceMatcher(None, inp.strip().lower(), out.strip().lower()).ratio()
            if len_diff <= 0.35 and char_sim >= 0.65:
                return True, "Valid grammar correction"
    return False, f"Fidelity gate failed: {reason}"


def validate_generate_code(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Code output is empty."
    # Check explicit language fence first
    lang_match = re.search(r'```([a-zA-Z0-9_+#-]*)\s*(.*?)\s*```', out, re.DOTALL)
    if lang_match:
        lang = (lang_match.group(1) or "").strip().lower()
        code_body = lang_match.group(2).strip()
        pre_fence = out[:lang_match.start()].strip()
        post_fence = out[lang_match.end():].strip()
        if pre_fence and len(pre_fence.split("\n")) > 2:
            return False, "Excessive prose before code fence."
        if post_fence and len(post_fence.split("\n")) > 2:
            return False, "Excessive prose after code fence."
        if not code_body:
            return False, "Code block is empty."
        if lang and lang not in ("python", "py", "python3"):
            return True, f"Valid fenced {lang} code."
        code_to_parse = code_body
    else:
        code_to_parse = out.strip()

    try:
        ast.parse(code_to_parse)
        return True, "Valid Python code syntax."
    except SyntaxError as se:
        return False, f"Code failed ast.parse: {se}"


def validate_summarize(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Summary is empty."
    inp_words = inp.strip().split()
    out_words = out.strip().split()
    if len(inp_words) >= 15 and len(out_words) >= len(inp_words):
        return False, f"Summary must be strictly shorter than input ({len(out_words)} >= {len(inp_words)} words)."
    return True, "Valid"


def validate_create_prompt(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "AI Prompt is empty."
    low = out.lower()
    # Expect at least two structured sections
    expected_sections = ["role", "task", "context", "instructions", "constraints", "output"]
    matched = sum(1 for s in expected_sections if s in low)
    if matched < 2:
        return False, "AI Prompt lacks structured sections (Role, Task, Context, etc.)."
    return True, "Valid"


def validate_make_casual(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Casual rewrite is empty."
    return _check_preserved_numbers(inp, out, "Make casual")


def validate_shorten(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Shortened text is empty."
    inp_words = inp.strip().split()
    out_words = out.strip().split()
    if len(inp_words) >= 10 and len(out_words) >= len(inp_words):
        return False, f"Shortened output is not shorter than input ({len(out_words)} >= {len(inp_words)})."
    return True, "Valid"


def validate_expand(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Expanded text is empty."
    inp_words = inp.strip().split()
    out_words = out.strip().split()
    if len(inp_words) >= 5 and len(out_words) <= len(inp_words):
        return False, f"Expanded output is not longer than input ({len(out_words)} <= {len(inp_words)})."
    return True, "Valid"


def validate_explain(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Explanation is empty."
    if len(out.strip().split()) < 8:
        return False, "Explanation is too brief."
    return True, "Valid"


def validate_translate(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Translation is empty."
    return True, "Valid"


def validate_create_email(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Email output is empty."
    low = out.lower()
    has_subject = "subject:" in low or "subject" in low
    if not has_subject and len(out.split("\n")) < 3:
        return False, "Email missing Subject line or structure."
    return True, "Valid"


def validate_github_issue(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Issue output is empty."
    if "- [ ]" not in out and "- [x]" not in out and "## " not in out:
        return False, "GitHub Issue missing markdown headers (##) or checklist (- [ ])."
    return True, "Valid"


def validate_github_pr(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "PR output is empty."
    if "summary" not in out.lower() and "## " not in out:
        return False, "GitHub PR description missing Summary or markdown headers."
    return True, "Valid"


def validate_create_task(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Task list is empty."
    # Expect checklist items or bullets
    has_items = any(mark in out for mark in ["- [ ]", "- [x]", "•", "* ", "1."])
    if not has_items:
        return False, "Task list lacks checklist marks or bullet points."
    return True, "Valid"


def validate_format_text(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Formatted text is empty."
    # Expect table syntax or structured bullets
    if "|" in out:
        lines = [line.strip() for line in out.split("\n") if line.strip()]
        has_table_sep = any(re.search(r'\|[-:\s|]+\|', line) for line in lines)
        if has_table_sep:
            return True, "Valid markdown table."
    if any(mark in out for mark in ["•", "- ", "* ", "1."]):
        return True, "Valid structured format."
    return False, "Output is not formatted as a table or structured list."


def validate_rewrite(inp: str, out: str) -> Tuple[bool, str]:
    if not out or not out.strip():
        return False, "Rewritten text is empty."
    return _check_preserved_numbers(inp, out, "Rewrite")


# -------------------------------------------------------------------------
# RETAINED APPLICATION ACTION COMMANDS (Decoupled from COMMAND_REGISTRY)
# -------------------------------------------------------------------------
# Features 19-21 (R6):
# Strictly removed: "start dictation", "stop dictation", "new line"
# Retained: "cancel dictation", "new paragraph", "bullet point",
#           "numbered list", "undo that", "select all", "copy all", "clear all"

ACTION_COMMANDS: List[CommandDefinition] = [
    CommandDefinition(
        id="action_bullet_point",
        name="Bullet Point",
        trigger_phrases=["start bullet points", "start bullet point", "bullet point", "next bullet"],
        system_prompt="Inserts a bullet point item at current caret.",
        input_contract="Spoken formatting command.",
        output_contract="Bullet point.",
        validator=validate_action,
        sample_input="bullet point",
        is_action=True
    ),
    CommandDefinition(
        id="action_numbered_list",
        name="Numbered List",
        trigger_phrases=["start numbered list", "numbered list", "next number"],
        system_prompt="Inserts a numbered item at current caret.",
        input_contract="Spoken formatting command.",
        output_contract="Numbered list item.",
        validator=validate_action,
        sample_input="numbered list",
        is_action=True
    ),
    CommandDefinition(
        id="action_undo",
        name="Undo / Delete",
        trigger_phrases=["undo that", "delete that", "scratch that"],
        system_prompt="Reverts the last inserted text action.",
        input_contract="Spoken editing command.",
        output_contract="Simulates Undo.",
        validator=validate_action,
        sample_input="undo that",
        is_action=True
    ),
    CommandDefinition(
        id="action_select_all",
        name="Select All",
        trigger_phrases=["select all", "highlight all"],
        system_prompt="Selects all content in active window.",
        input_contract="Spoken editing command.",
        output_contract="Select All.",
        validator=validate_action,
        sample_input="select all",
        is_action=True
    ),
    CommandDefinition(
        id="action_copy_all",
        name="Copy All",
        trigger_phrases=["copy that", "copy all"],
        system_prompt="Copies selected content to clipboard.",
        input_contract="Spoken editing command.",
        output_contract="Copy to clipboard.",
        validator=validate_action,
        sample_input="copy all",
        is_action=True
    ),
    CommandDefinition(
        id="action_clear_all",
        name="Clear All",
        trigger_phrases=["clear all", "clear text", "delete all"],
        system_prompt="Clears selected or current text.",
        input_contract="Spoken editing command.",
        output_contract="Clear text.",
        validator=validate_action,
        sample_input="clear all",
        is_action=True
    ),
]

# -------------------------------------------------------------------------
# THE 16 COMMAND REGISTRY (Strict Order & Declarative Specifications)
# -------------------------------------------------------------------------

COMMAND_REGISTRY: List[CommandDefinition] = [
    # 1. Professionalize
    CommandDefinition(
        id="professionalize",
        name="Professionalize",
        trigger_phrases=[
            "make it more professional", "make this more professional",
            "make this professional", "make professional", "professionalize",
            "make it formal", "make formal", "formalize this", "formalize",
            "executive tone", "professional tone"
        ],
        system_prompt=(
            "Rewrite the provided text in a polished, articulate, and professional style suitable for "
            "business or executive communication. Preserve the author's original voice, perspective, "
            "all proper names, numbers, dates, and facts without substitution or omission. "
            "Format listed items into clean bullet points ('• '). Output ONLY the rewritten text."
        ),
        input_contract="Raw conversational, unpolished, or informal speech dictation.",
        output_contract="Formal, articulate business English preserving 100% of facts and numbers.",
        validator=validate_professionalize,
        default_temperature=0.2,
        max_tokens=2048,
        sample_input="hey boss we finished the v2 update yesterday budget was fifteen hundred dollars and tests pass"
    ),

    # 2. Make Casual
    CommandDefinition(
        id="make_casual",
        name="Make Casual",
        trigger_phrases=[
            "make this casual", "make it casual", "make casual",
            "make it friendly", "make this friendly", "friendly tone",
            "conversational tone", "tone down"
        ],
        system_prompt=(
            "Rephrase the input in a friendly, warm, natural conversational tone while preserving "
            "every essential fact, author perspective, and all specific numbers. Output ONLY the rewritten text."
        ),
        input_contract="Rigid or formal text requiring conversational softening.",
        output_contract="Friendly, relaxed phrasing with identical factual content.",
        validator=validate_make_casual,
        default_temperature=0.2,
        max_tokens=2048,
        sample_input="Please be advised that the quarterly projection has been revised upwards by twelve percent."
    ),

    # 3. Create AI Prompt
    CommandDefinition(
        id="create_prompt",
        name="Create AI Prompt",
        trigger_phrases=[
            "turn this into a prompt", "create a prompt from this", "create an ai prompt",
            "create ai prompt", "generate a prompt", "create a prompt", "create prompt",
            "prompt engineering", "prompt enhancer"
        ],
        system_prompt=(
            "You are a Principal AI Prompt Architect. Transform the provided rough thoughts or requirements into a "
            "structured, context-aware, production-grade AI prompt formatted with exact XML tags: "
            "<role>, <context>, <task>, <constraints>, and <output_format>. "
            "Match <role> accurately to the actual domain requested (never inject unrelated personas), "
            "preserve 100% of every technology, constraint, and requirement without '...' truncation, and output ONLY the structured prompt."
        ),
        input_contract="Rough concept or user description of what an AI agent should do.",
        output_contract="Structured 5-part XML prompt containing <role>, <context>, <task>, <constraints>, and <output_format>.",
        validator=validate_create_prompt,
        default_temperature=0.2,
        max_tokens=3072,
        sample_input="build a python script that connects to postgres and cleans up duplicate user accounts"
    ),

    # 4. Summarize / TLDR
    CommandDefinition(
        id="summarize",
        name="Summarize / TLDR",
        trigger_phrases=[
            "summarize this", "summarize", "give me a summary", "quick summary",
            "brief summary of", "brief summary", "tldr", "tl;dr", "executive summary"
        ],
        system_prompt=(
            "Distill the provided content into a 1-sentence **TL;DR:** headline and at most 2 ultra-short "
            "bullet takeaways (omit bullets for short inputs) highlighting key metrics and action items. "
            "CRITICAL: Total output word count MUST be strictly under 60% of the input word count with "
            "zero fabricated claims. Output ONLY the TL;DR summary."
        ),
        input_contract="Multi-paragraph or dense speech.",
        output_contract="Crisp TL;DR headline and concise bulleted summary strictly shorter than input.",
        validator=validate_summarize,
        default_temperature=0.2,
        max_tokens=1024,
        sample_input="We had our quarterly review today. Overall revenue grew by twenty percent across all sectors. The mobile app saw thirty thousand new downloads. However customer support tickets increased by fifteen percent due to login glitches. We decided to hire two additional support engineers and deploy an authentication hotfix by Friday."
    ),

    # 5. Fix Grammar
    CommandDefinition(
        id="grammar_fix",
        name="Fix Grammar",
        trigger_phrases=[
            "fix the grammar", "fix grammar", "fix my grammar", "correct grammar",
            "proofread this", "check grammar"
        ],
        system_prompt=(
            "Proofread and correct all grammar, spelling, punctuation, capitalization, subject-verb agreement, "
            "and typographical slips in the provided text. Never alter meaning, style, or content. "
            "Output ONLY the corrected text without explanations or quotes."
        ),
        input_contract="Text with syntax errors, typos, or wrong verb tenses.",
        output_contract="Syntactically flawless English passing strict fidelity gate.",
        validator=validate_fix_grammar,
        default_temperature=0.0,
        max_tokens=2048,
        sample_input="yesterday i go to office and seen three problem with the database"
    ),

    # 6. Shorten / Concise
    CommandDefinition(
        id="shorten",
        name="Shorten / Concise",
        trigger_phrases=[
            "make this shorter", "make it shorter", "shorten this", "shorten",
            "make it concise", "make concise", "be concise", "trim this", "cut the fluff"
        ],
        system_prompt=(
            "Condense the input text into a concise, punchy version without losing vital context, key points, "
            "or numbers. Output ONLY the concise text."
        ),
        input_contract="Wordy or rambling text.",
        output_contract="Compact, high-impact phrasing strictly shorter than input.",
        validator=validate_shorten,
        default_temperature=0.2,
        max_tokens=1024,
        sample_input="In order to properly ensure that the database server operates without running into unexpected errors, it is absolutely essential that we perform a reboot at ten pm."
    ),

    # 7. Expand / Elaborate
    CommandDefinition(
        id="expand",
        name="Expand / Elaborate",
        trigger_phrases=[
            "expand on this", "expand this", "elaborate on this", "elaborate",
            "add more details", "add more detail to", "add more detail", "flesh this out"
        ],
        system_prompt=(
            "Expand upon the thoughts and concepts provided, providing thorough elaboration, context, and clear "
            "explanatory prose while preserving the core premise. Output ONLY the expanded content."
        ),
        input_contract="Short brief or bullet points.",
        output_contract="Detailed, well-developed explanatory paragraphs.",
        validator=validate_expand,
        default_temperature=0.2,
        max_tokens=2048,
        sample_input="We need to adopt microservices to scale our backend."
    ),

    # 8. Explain Simply / ELI5
    CommandDefinition(
        id="explain",
        name="Explain Simply",
        trigger_phrases=[
            "explain concept", "explain this", "what does this mean",
            "break this down", "break down this", "break down", "explain simply", "eli5"
        ],
        system_prompt=(
            "Explain the provided concept, code, or text in clear, step-by-step educational language with intuitive analogies "
            "suitable for a general audience. Output ONLY the explanation."
        ),
        input_contract="Complex technical or domain-specific concept.",
        output_contract="Clear, analogy-driven educational explanation.",
        validator=validate_explain,
        default_temperature=0.2,
        max_tokens=2048,
        sample_input="How does faster-whisper CTranslate2 quantization work?"
    ),

    # 9. Translate
    CommandDefinition(
        id="translate",
        name="Translate",
        trigger_phrases=[
            "translate this to", "translate this into", "translate to", "translate into", "translate this"
        ],
        system_prompt=(
            "Accurately translate the provided text into the requested target language, preserving natural idioms, "
            "factual nuance, and numbers. Output ONLY the translation."
        ),
        input_contract="Text plus target language specification.",
        output_contract="Fluent, natural translation in the requested language.",
        validator=validate_translate,
        default_temperature=0.2,
        max_tokens=2048,
        sample_input="translate to Spanish: Good morning, our team meeting will start at 10:30 AM."
    ),

    # 10. Create Email
    CommandDefinition(
        id="create_email",
        name="Create Email",
        trigger_phrases=[
            "create an email", "draft an email", "draft email",
            "write an email", "compose an email", "email draft"
        ],
        system_prompt=(
            "Draft a complete, well-structured professional email with a clear Subject: line, appropriate salutation, "
            "structured body paragraphs, and courteous sign-off based on the provided notes. Output ONLY the email."
        ),
        input_contract="Spoken notes or objectives of the email.",
        output_contract="Complete email with Subject line, salutation, body, and sign-off.",
        validator=validate_create_email,
        default_temperature=0.2,
        max_tokens=2048,
        sample_input="email to Alex saying the demo is ready for review and ask if we can meet on Thursday at 2 pm"
    ),

    # 11. Create GitHub Issue
    CommandDefinition(
        id="create_github_issue",
        name="Create GitHub Issue",
        trigger_phrases=[
            "create a github issue", "file a github issue", "new github issue",
            "file a bug report", "bug report for", "bug report",
            "github issue", "new issue"
        ],
        system_prompt=(
            "Convert the provided details into a clean GitHub Issue in Markdown format with sections: "
            "## Title, ## Summary, ## Steps to Reproduce (or ## Acceptance Criteria), "
            "## Expected vs Actual Behavior, ## Environment, and ## Action Items checklist (- [ ]). "
            "Preserve all technical details, logs, and error codes. Output ONLY the Markdown issue."
        ),
        input_contract="Spoken bug report or feature request.",
        output_contract="Markdown issue formatted with title, repro steps, expected vs actual, and checklist items.",
        validator=validate_github_issue,
        default_temperature=0.2,
        max_tokens=2048,
        sample_input="bug report: settings dialog crashes with AttributeError when clicking audio tab on clean install"
    ),

    # 12. Create GitHub PR Description
    CommandDefinition(
        id="create_github_pr",
        name="Create GitHub PR Description",
        trigger_phrases=[
            "create a github pr", "create a pull request", "create a pr", "create pr",
            "pr description for", "draft pr description", "github pr", "pr description"
        ],
        system_prompt=(
            "Convert the following notes into a professional GitHub Pull Request description in markdown format with "
            "## Summary, ## Key Changes, and ## Verification Checklist (- [ ]). "
            "Output ONLY the markdown PR description."
        ),
        input_contract="Notes regarding code changes, bugfixes, or features.",
        output_contract="Comprehensive GitHub PR description with headers and test checklists.",
        validator=validate_github_pr,
        default_temperature=0.2,
        max_tokens=2048,
        sample_input="PR details: refactored audio recorder to use polyphase resampling at 16khz and added unit tests"
    ),

    # 13. Create Task List
    CommandDefinition(
        id="create_task",
        name="Create Task List",
        trigger_phrases=[
            "create a task list", "create task list", "create tasks", "task list",
            "create action items", "action items", "make a checklist",
            "generate a todo list", "generate todo list", "todo list"
        ],
        system_prompt=(
            "Extract and organize all implied and explicit action items into a prioritized, actionable markdown checklist "
            "(- [ ]) with clear deliverables and owners/subtasks if mentioned. Output ONLY the checklist."
        ),
        input_contract="Meeting notes or spoken to-do thoughts.",
        output_contract="Markdown checklist (- [ ]) formatted sequentially.",
        validator=validate_create_task,
        default_temperature=0.2,
        max_tokens=1024,
        sample_input="we need to deploy the new build, verify database migrations, notify the QA team, and update release notes"
    ),

    # 14. Generate Code
    CommandDefinition(
        id="generate_code",
        name="Generate Code",
        trigger_phrases=[
            "generate code", "write code", "create code", "write a python script", "generate script"
        ],
        system_prompt=(
            "You are a Senior Staff Software Engineer. Write clean, complete, runnable, idiomatic code in the language "
            "specified or implied by the request (defaulting to Python 3 with type hints, docstrings, PEP 8 compliance, "
            "error handling, and a __main__ guard when no other language is requested). "
            "Enclose the entire code in exactly one markdown code fence (```<lang> ... ```) with zero extra prose."
        ),
        input_contract="Spoken software requirements or algorithm description.",
        output_contract="Clean, runnable code inside a single markdown code fence.",
        validator=validate_generate_code,
        default_temperature=0.0,
        max_tokens=3072,
        sample_input="write a python script to compute SHA256 hash of all files in a folder"
    ),

    # 15. Format as Table
    CommandDefinition(
        id="format_text",
        name="Format as Table",
        trigger_phrases=[
            "format this into a table", "format as a markdown table", "format into a table",
            "format as a table", "format into table", "format this table",
            "format table", "create a table", "table format", "markdown table"
        ],
        system_prompt=(
            "Format the provided data or list cleanly into a standard GitHub-Flavored Markdown table with a header row "
            "(| Col 1 | Col 2 |), a separator row (|---|---|), and aligned data rows. "
            "Output ONLY the markdown table with zero extra prose."
        ),
        input_contract="Unstructured data, lists, or comparison items.",
        output_contract="Well-formatted markdown table (| col1 | col2 |).",
        validator=validate_format_text,
        default_temperature=0.2,
        max_tokens=1024,
        sample_input="apples 5 dollars, bananas 3 dollars, oranges 4 dollars"
    ),

    # 16. Polish & Rewrite
    CommandDefinition(
        id="rewrite",
        name="Polish & Rewrite",
        trigger_phrases=[
            "rewrite this", "polish this", "improve this text", "rephrase this",
            "rewrite and polish", "rewrite / polish", "polish and rewrite"
        ],
        system_prompt=(
            "Rewrite and polish the provided text to maximize clarity, elegance, and natural flow while strictly "
            "preserving the author's original meaning, numbers, and facts. Output ONLY the polished text."
        ),
        input_contract="Draft prose or speech needing stylistic elevation.",
        output_contract="Fluid, eloquent rewrite retaining 100% of facts.",
        validator=validate_rewrite,
        default_temperature=0.2,
        max_tokens=2048,
        sample_input="I think the plan is good but we might see some issues with the timeline if we dont start now"
    ),
]

# Map for O(1) lookups
COMMAND_MAP: Dict[str, CommandDefinition] = {c.id: c for c in COMMAND_REGISTRY}
ACTION_MAP: Dict[str, CommandDefinition] = {c.id: c for c in ACTION_COMMANDS}
ALL_COMMANDS: List[CommandDefinition] = COMMAND_REGISTRY + ACTION_COMMANDS
ALL_COMMAND_MAP: Dict[str, CommandDefinition] = {**COMMAND_MAP, **ACTION_MAP}

# Spoken triggers explicitly removed (Feature 19, R6)
# Ordinary speech containing these words must NEVER be intercepted as commands.
REMOVED_SPOKEN_TRIGGERS: Set[str] = {
    "start dictation", "start recording", "begin dictation", "start speech", "start",
    "stop dictation", "stop recording", "finish dictation", "stop",
    "new line", "start new line", "next line",
    "cancel dictation", "cancel speech", "cancel that", "discard speech", "cancel",
    "start new paragraph", "new paragraph", "next paragraph"
}


def match_spoken_command(
    raw_utterance: str,
    selected_text: str = "",
    in_dictation: bool = True
) -> Optional[Tuple[CommandDefinition, str]]:
    """
    Matches a spoken utterance to a registered command ONLY when the trigger phrase
    is anchored at the START of the utterance (Features 19-22, R6).
    Mid-sentence occurrences of trigger words (e.g. 'start', 'stop', 'new line')
    are treated as regular speech dictation and return None.

    Returns:
        (CommandDefinition, payload_text) or None if normal dictation.
    """
    cleaned = raw_utterance.strip()
    if not cleaned:
        return None

    norm_clean = re.sub(r'^[.,!?;:\s]+|[.,!?;:\s]+$', '', cleaned).lower()

    # Explicitly removed triggers must NEVER be intercepted as commands
    if norm_clean in REMOVED_SPOKEN_TRIGGERS or norm_clean in {f"please {t}" for t in REMOVED_SPOKEN_TRIGGERS}:
        return None

    # Conversational speech starting with filler phrases like "let us start" or "tomorrow we start"
    # must not match
    if any(norm_clean.startswith(f"{prefix} ") for prefix in [
        "let us", "lets", "we need to", "tomorrow we", "we cannot", "this creates",
        "our company has", "according to", "in our"
    ]):
        return None

    # 1. Retained Action Commands Matching (Standalone or colon-delimited)
    for cmd in ACTION_COMMANDS:
        for phrase in cmd.trigger_phrases:
            p_clean = phrase.lower().strip()
            # Exact standalone match (e.g. "cancel dictation", "please cancel", "undo that", "bullet point")
            if norm_clean == p_clean or norm_clean == f"please {p_clean}":
                payload = selected_text.strip() if selected_text else ""
                return cmd, payload

            # Explicitly delimited action command (e.g. "bullet point: apples")
            act_match = re.match(rf'^(?:please\s+)?{re.escape(p_clean)}\s*[:,\-—]\s*(.+)$', cleaned, re.IGNORECASE | re.DOTALL)
            if act_match:
                payload = act_match.group(1).strip()
                payload = re.sub(r'^[ :,.\-—\?!]+', '', payload).strip()
                return cmd, payload

    # 2. Standalone Profile Commands Matching (with selected_text on screen)
    for cmd in COMMAND_REGISTRY:
        for phrase in cmd.trigger_phrases:
            p_clean = phrase.lower().strip()
            if norm_clean == p_clean or norm_clean == f"please {p_clean}":
                payload = selected_text.strip() if selected_text else ""
                return cmd, payload

    # 3. Leading-Anchored Profile Commands with Spoken Payload
    # Pattern strictly anchored at the start: allows optional leading fillers (e.g. "Um, please")
    # followed by the trigger phrase and a delimiter (colon, comma, dash, period, or whitespace).
    delim_pattern = r'(?:\s*[:,\-—\.\?!]+\s*|\s+that\s+|\s+)'

    # Sort all profile commands by longest trigger phrase first
    sorted_cmds = []
    for cmd in COMMAND_REGISTRY:
        for phrase in cmd.trigger_phrases:
            sorted_cmds.append((phrase, cmd))
    sorted_cmds.sort(key=lambda item: len(item[0]), reverse=True)

    for phrase, cmd in sorted_cmds:
        # Regex anchor at the start with optional filler/politeness prefix
        pattern = rf'^(?:(?:um|uh|ah|well)\s*[,.]?\s*)?(?:please\s+)?{re.escape(phrase)}{delim_pattern}(.+)$'
        match = re.match(pattern, cleaned, re.IGNORECASE | re.DOTALL)
        if match:
            payload = match.group(1).strip()
            # Clean leading punctuation from payload
            payload = re.sub(r'^[ :,.\-—\?!]+', '', payload).strip()
            if (not payload or len(payload) < 2) and selected_text and len(selected_text.strip()) >= 2:
                payload = selected_text.strip()
            return cmd, payload

    return None


def execute_command(
    cmd: CommandDefinition,
    payload: str,
    llm_fn: Callable[[str, str, float, int], str]
) -> Tuple[bool, str]:
    """
    Executes a command definition with up to 1 retry at temperature 0 on validator failure.
    llm_fn signature: (system_prompt, user_content, temperature, max_tokens) -> response_text
    Returns:
        (success: bool, result_or_error: str)
    """
    last_reason = ""
    for attempt in range(2):
        temp = cmd.default_temperature if attempt == 0 else 0.0
        prompt = cmd.system_prompt
        if attempt == 1:
            prompt += " Ensure complete fidelity to output requirements."
        try:
            output = llm_fn(prompt, payload, temp, cmd.max_tokens)
            is_valid, reason = cmd.validator(payload, output)
            if is_valid:
                return True, output
            last_reason = reason
        except Exception as e:
            if attempt == 1:
                return False, str(e)
            last_reason = str(e)
    return False, f"Validation failed: {last_reason}"

