"""
Evaluator for Gemini Flow 600-Run Speech Benchmark Suite.
Computes:
- Word Error Rate (WER)
- Character Error Rate (CER)
- Formatting Conformance Score (0-100%)
- Hallucination / Degeneration Detection
- Real-Time Factor (RTF)
"""
import re
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Tuple, List, Optional


def normalize_words(text: str) -> List[str]:
    """Normalizes text for linguistic Word Error Rate calculation."""
    if not text:
        return []
    cleaned = re.sub(r'[\r\n\t]+', ' ', text)
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', cleaned).lower()
    return [w for w in cleaned.split() if w]


def normalize_chars(text: str) -> str:
    """Normalizes text for Character Error Rate calculation."""
    if not text:
        return ""
    cleaned = re.sub(r'\s+', ' ', text).lower()
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', cleaned)
    return cleaned.strip()


def compute_wer(reference: str, hypothesis: str) -> float:
    """
    Standard dynamic programming Levenshtein Word Error Rate (WER).
    WER = (S + D + I) / N_ref
    """
    ref_words = normalize_words(reference)
    hyp_words = normalize_words(hypothesis)

    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    if not hyp_words:
        return 1.0

    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]
    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            cost = 0 if ref_words[i - 1] == hyp_words[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,       # Deletion
                d[i][j - 1] + 1,       # Insertion
                d[i - 1][j - 1] + cost  # Substitution
            )

    dist = d[len(ref_words)][len(hyp_words)]
    return min(1.0, dist / len(ref_words))


def compute_cer(reference: str, hypothesis: str) -> float:
    """
    Standard dynamic programming Character Error Rate (CER).
    """
    ref_c = normalize_chars(reference)
    hyp_c = normalize_chars(hypothesis)

    if not ref_c:
        return 0.0 if not hyp_c else 1.0
    if not hyp_c:
        return 1.0

    d = [[0] * (len(hyp_c) + 1) for _ in range(len(ref_c) + 1)]
    for i in range(len(ref_c) + 1):
        d[i][0] = i
    for j in range(len(hyp_c) + 1):
        d[0][j] = j

    for i in range(1, len(ref_c) + 1):
        for j in range(1, len(hyp_c) + 1):
            cost = 0 if ref_c[i - 1] == hyp_c[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + cost
            )

    dist = d[len(ref_c)][len(hyp_c)]
    return min(1.0, dist / len(ref_c))


def detect_hallucination_or_loop(text: str) -> Tuple[bool, str]:
    """Detects repetitive token degenerations or infinite loops."""
    if not text:
        return False, ""
    words = text.split()
    if len(words) < 10:
        return False, ""

    # Check for repeating 3-grams or 4-grams
    for n in (3, 4, 5):
        grams = [" ".join(words[i:i + n]) for i in range(len(words) - n + 1)]
        from collections import Counter
        counts = Counter(grams)
        most_common, freq = counts.most_common(1)[0]
        if freq >= 4 and len(most_common.split()) >= 3:
            return True, f"Repetition loop of phrase '{most_common}' ({freq}x)"

    return False, ""


def evaluate_formatting_conformance(
    format_id: int,
    format_name: str,
    output_text: str,
    ground_truth: str
) -> Tuple[float, List[str]]:
    """
    Validates structural, stylistic, and semantic conformance against the requested format.
    Returns (conformance_score: float [0-100], notes: List[str]).
    """
    if not output_text or not output_text.strip():
        return 0.0, ["Output is completely empty."]

    text = output_text.strip()
    score = 100.0
    deductions = []

    # Check for degeneration loops
    has_loop, loop_msg = detect_hallucination_or_loop(text)
    if has_loop:
        score -= 40.0
        deductions.append(loop_msg)

    # Format-specific structural verification gates
    if format_id == 1:  # Verbatim Raw
        # Should not contain markdown headers or conversational chatter
        if re.search(r'^(?:Here is|Sure|Certainly|Transcript:)', text, re.IGNORECASE):
            score -= 20.0
            deductions.append("Contains conversational preamble.")
        if '#' in text or '```' in text:
            score -= 15.0
            deductions.append("Contains unexpected markdown headers or code blocks.")

    elif format_id == 2:  # Professional Business Memo
        memo_headers = ["to:", "from:", "date:", "subject:"]
        found = sum(1 for h in memo_headers if h in text.lower())
        if found < 3:
            deduct = (4 - found) * 15.0
            score -= deduct
            deductions.append(f"Missing business memo header fields (found {found}/4).")

    elif format_id == 3:  # Bulleted Executive Summary
        has_bullets = any(b in text for b in ("•", "\n*", "\n-", "\n•"))
        if not has_bullets:
            score -= 35.0
            deductions.append("Missing bullet points.")
        if not any(k in text.lower() for k in ("takeaway", "summary", "action", "key", "overview")):
            score -= 15.0
            deductions.append("Missing executive summary section headings.")

    elif format_id == 4:  # Grammar & Punctuation Auto-Repair
        fillers = ["um", "uh", "like", "you know"]
        found_fillers = [f for f in fillers if re.search(rf'\b{f}\b', text, re.IGNORECASE)]
        if found_fillers:
            score -= 10.0 * len(found_fillers)
            deductions.append(f"Verbal fillers detected: {found_fillers}")
        if text[-1] not in ('.', '!', '?', '"', "'"):
            score -= 10.0
            deductions.append("Missing terminal sentence punctuation.")

    elif format_id == 5:  # Developer Technical Documentation
        has_headers = '#' in text
        has_code = '`' in text or '```' in text
        if not has_headers:
            score -= 20.0
            deductions.append("Missing Markdown documentation headers.")
        if not has_code:
            score -= 15.0
            deductions.append("Missing technical code or identifier backticks.")

    elif format_id == 6:  # Legal Deposition Format
        has_ts = re.search(r'\[?\d{1,2}:\d{2}(?::\d{2})?\]?', text)
        has_speaker = any(s in text.upper() for s in ("Q.", "A.", "QUESTION:", "ANSWER:", "ATTORNEY", "WITNESS", "DEPOSEE"))
        if not has_ts and not has_speaker:
            score -= 40.0
            deductions.append("Missing legal deposition timestamps or speaker labels.")

    elif format_id == 7:  # Strict JSON Schema Output
        try:
            # Strip markdown json codeblock if present
            clean_json = re.sub(r'^```(?:json)?\s*', '', text)
            clean_json = re.sub(r'\s*```$', '', clean_json).strip()
            data = json.loads(clean_json)
            if not isinstance(data, dict):
                score -= 30.0
                deductions.append("JSON root is not a dictionary.")
            else:
                for req_key in ("transcript", "sentiment", "entities"):
                    if req_key not in data:
                        score -= 15.0
                        deductions.append(f"Missing JSON key: {req_key}")
        except Exception as e:
            score -= 60.0
            deductions.append(f"Invalid JSON syntax: {str(e)[:50]}")

    elif format_id == 8:  # Meeting Minutes with Deadlines
        minutes_kw = ["attendees", "discussion", "decision", "action item", "deadline"]
        found = sum(1 for k in minutes_kw if k in text.lower())
        if found < 2:
            score -= 30.0
            deductions.append("Missing meeting minutes standard sections.")

    elif format_id == 9:  # Social Media Thread Format
        has_hash = '#' in text
        has_num = bool(re.search(r'\b[1-3][\.\)]', text)) or ('🧵' in text)
        if not has_hash:
            score -= 15.0
            deductions.append("Missing hashtags.")
        if not has_num:
            score -= 15.0
            deductions.append("Missing numbered points / thread structure.")

    elif format_id == 10:  # Academic Formal Abstract
        abstract_kw = ["background", "method", "result", "conclusion", "objective", "finding"]
        found = sum(1 for k in abstract_kw if k in text.lower())
        if found < 2:
            score -= 25.0
            deductions.append("Missing academic abstract formal sections.")

    elif format_id == 14:  # GitHub PR Description
        pr_kw = ["summary", "testing", "changes", "checklist", "motivation"]
        found = sum(1 for k in pr_kw if k in text.lower())
        if found < 2:
            score -= 25.0
            deductions.append("Missing GitHub PR description sections.")

    elif format_id == 15:  # Daily Standup Update
        standup_kw = ["yesterday", "today", "blocker", "done", "focus"]
        found = sum(1 for k in standup_kw if k in text.lower())
        if found < 2:
            score -= 25.0
            deductions.append("Missing Standup Yesterday/Today/Blockers sections.")

    elif format_id == 19:  # YAML Configuration Schema
        has_colons = ':' in text and '\n' in text
        if not has_colons:
            score -= 40.0
            deductions.append("Missing YAML key-value colon structures.")

    elif format_id == 20:  # Markdown Table Structure
        has_pipes = text.count('|') >= 4 and '-|-' in text.replace(' ', '')
        if not has_pipes:
            score -= 45.0
            deductions.append("Missing Markdown table pipe delimiters or divider row.")

    elif format_id == 24:  # Concise One-Sentence TL;DR
        word_count = len(text.split())
        sentence_count = len([s for s in re.split(r'[\.\?!]\s+', text) if s.strip()])
        if word_count > 35:
            score -= min(30.0, (word_count - 25) * 2.0)
            deductions.append(f"TL;DR exceeds length limit ({word_count} words).")
        if sentence_count > 2:
            score -= 15.0
            deductions.append("TL;DR contains multiple sentences.")

    elif format_id == 40:  # Strict XML Schema Output
        try:
            clean_xml = re.sub(r'^```(?:xml)?\s*', '', text)
            clean_xml = re.sub(r'\s*```$', '', clean_xml).strip()
            ET.fromstring(clean_xml)
        except Exception:
            # Check if basic XML tags exist
            if not ('<' in text and '>' in text and '</' in text):
                score -= 50.0
                deductions.append("Malformed or missing XML tags.")
            else:
                score -= 20.0
                deductions.append("XML parsing warning.")

    elif format_id == 70:  # Gherkin BDD
        gherkin_kw = ["given", "when", "then", "scenario"]
        found = sum(1 for k in gherkin_kw if k in text.lower())
        if found < 2:
            score -= 30.0
            deductions.append("Missing Gherkin BDD keywords (Given/When/Then).")

    elif format_id == 94:  # Conventional Commit
        has_prefix = bool(re.search(r'^(?:feat|fix|chore|docs|style|refactor|perf|test)(?:\([^\)]+\))?:', text.strip(), re.IGNORECASE))
        if not has_prefix:
            score -= 30.0
            deductions.append("Missing Conventional Commit type(scope) prefix.")

    else:
        # Generic format quality check
        # Check that output is not just a 1-word echo and contains substantive content
        if len(text.split()) < 3 and len(ground_truth.split()) >= 5:
            score -= 30.0
            deductions.append("Output is abnormally truncated.")

    final_score = max(0.0, min(100.0, score))
    return round(final_score, 1), deductions
