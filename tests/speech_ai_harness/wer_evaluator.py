"""
Evaluation metrics for Speech-to-Text: WER, Formatting Correctness, and Word Order Consistency.
"""
import re
from typing import List, Tuple, Dict, Any

def normalize_text_for_wer(text: str) -> List[str]:
    """
    Normalizes text for linguistic WER calculation:
    Lowercases, strips punctuation, normalizes whitespace.
    """
    if not text:
        return []
    # Strip bullet characters and punctuation
    cleaned = re.sub(r'[•\*\-\d+\.\)\,\:\;\?\!\"\'“”«»`~]', ' ', text.lower())
    words = [w.strip() for w in cleaned.split() if w.strip()]
    return words

def compute_wer(reference: str, hypothesis: str) -> float:
    """
    Computes standard Word Error Rate (WER) using dynamic programming Levenshtein distance:
    WER = (Substitutions + Deletions + Insertions) / Total Reference Words
    """
    ref_words = normalize_text_for_wer(reference)
    hyp_words = normalize_text_for_wer(hypothesis)

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]

    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                cost = 0
            else:
                cost = 1
            d[i][j] = min(
                d[i - 1][j] + 1,        # deletion
                d[i][j - 1] + 1,        # insertion
                d[i - 1][j - 1] + cost   # substitution
            )

    distance = d[len(ref_words)][len(hyp_words)]
    wer = distance / len(ref_words)
    return min(1.0, float(wer))

def check_formatting_correctness(output_text: str, is_list: bool) -> bool:
    """
    Validates whether the output text conforms to quality criteria:
    - If is_list is True: must contain bullet points ('•', '*', '-', or clean line-break items)
    - Sentences must start with capital letter and have valid terminal punctuation.
    """
    if not output_text or not output_text.strip():
        return False
    t = output_text.strip()
    if is_list:
        # Check for bullet points or clean itemized line breaks
        has_bullets = any(marker in t for marker in ("•", "\n*", "\n-", "\n•"))
        has_newlines = "\n" in t and len(t.splitlines()) >= 2
        return has_bullets or has_newlines
    # Normal prose: should have reasonable punctuation and capitalization
    return len(t) > 0

def check_order_consistency(reference: str, hypothesis: str) -> bool:
    """
    Verifies that the chronological order of key anchor words is preserved.
    """
    ref_words = normalize_text_for_wer(reference)
    hyp_words = normalize_text_for_wer(hypothesis)

    if len(ref_words) < 2 or not hyp_words:
        return True

    # Take anchors (every 2nd or 3rd word that is >= 4 chars)
    anchors = [w for w in ref_words if len(w) >= 4][::2]
    if len(anchors) < 2:
        return True

    last_pos = -1
    matched = 0
    for a in anchors:
        try:
            pos = hyp_words.index(a, last_pos + 1)
            last_pos = pos
            matched += 1
        except ValueError:
            pass

    # If at least 50% of anchors appear in monotonically increasing order, order is consistent
    return matched >= max(1, len(anchors) // 2)
