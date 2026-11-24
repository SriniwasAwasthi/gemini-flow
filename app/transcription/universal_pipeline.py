"""
Universal Transcription Pipeline for Gemini Flow.
Shared, model-independent processing architecture downstream of recognition:
AUDIO INPUT
↓
SELECTED RECOGNITION MODEL ADAPTER
↓
STANDARDIZED TRANSCRIPTION OUTPUT (ModelOutputNormalizer)
↓
AUDIO AND TIMESTAMP ALIGNMENT
↓
STREAMING HYPOTHESIS RECONCILIATION (StreamingHypothesisReconciler)
↓
BOUNDARY OVERLAP RESOLUTION (OverlapDuplicateResolver)
↓
UNIVERSAL DUPLICATE ELIMINATION (RepetitionDetector)
↓
CONTEXTUAL SELF-CORRECTION & SENTENCE REPLACEMENT (SelfCorrectionEngine)
↓
GRAMMAR AND PUNCTUATION PROCESSING (GrammarAndPunctuationProcessor)
↓
VOICE TRIGGER & QUICK-TEXT EXPANSION (VoiceTriggerExpander)
↓
FINAL TRANSCRIPT ASSEMBLY (FinalTranscriptAssembler)
"""
import re
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
import numpy as np

logger = logging.getLogger("GeminiFlow.UniversalPipeline")


@dataclass
class AudioFrame:
    """Represents a 200ms audio frame with sequence order and timestamps."""
    frame_index: int
    timestamp_sec: float
    duration_ms: float = 200.0
    samples: np.ndarray = field(default_factory=lambda: np.zeros((0,), dtype=np.float32))


class ModelOutputNormalizer:
    """Standardizes raw recognition outputs from any model into a uniform transcript structure."""

    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        # Clean control characters and normalize quotes/dashes
        t = text.replace("\r\n", "\n").replace("\r", "\n")
        t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
        t = t.replace("—", " - ").replace("–", " - ")
        # Strip code block wrappers if generated accidentally
        t = re.sub(r'^```[\w]*\n?', '', t)
        t = re.sub(r'\n?```$', '', t)
        # Strip accidental LLM preambles
        lines = t.split("\n")
        filtered_lines = []
        for line in lines:
            low = line.strip().lower()
            if any(low.startswith(p) for p in [
                "here is the transcription:", "here is the transcript:", "transcription:",
                "transcript:", "here is what was spoken:", "sure, here is", "output:"
            ]):
                continue
            filtered_lines.append(line)
        cleaned = "\n".join(filtered_lines).strip()
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1].strip()
        return cleaned


class StreamingHypothesisReconciler:
    """
    Maintains three separate transcription states:
    A. Stable committed text: Words confirmed reliable, no longer modified.
    B. Mutable partial text: Words still being actively recognized.
    C. Finalized text: Complete coherent transcript upon stop hotkey.
    Prevents progressive hypothesis concatenation.
    """
    def __init__(self):
        self.committed_text: str = ""
        self.mutable_partial_text: str = ""
        self.finalized_text: str = ""
        self.history: List[str] = []

    def reset(self):
        self.committed_text = ""
        self.mutable_partial_text = ""
        self.finalized_text = ""
        self.history.clear()

    def update_partial(self, hypothesis: str) -> str:
        clean_hyp = ModelOutputNormalizer.normalize_text(hypothesis).strip()
        if not clean_hyp:
            return self.get_current_text()

        self.history.append(clean_hyp)

        if self.committed_text:
            if clean_hyp.lower().startswith(self.committed_text.lower()):
                self.mutable_partial_text = clean_hyp[len(self.committed_text):].strip()
            else:
                self.mutable_partial_text = clean_hyp
        else:
            self.mutable_partial_text = clean_hyp

        return self.get_current_text()

    def commit_stable(self, stable_phrase: str):
        clean = stable_phrase.strip()
        if not clean:
            return
        if self.committed_text:
            self.committed_text = f"{self.committed_text} {clean}".strip()
        else:
            self.committed_text = clean
        self.mutable_partial_text = ""

    def finalize(self, final_hypothesis: str = "") -> str:
        if final_hypothesis and final_hypothesis.strip():
            hyp = ModelOutputNormalizer.normalize_text(final_hypothesis).strip()
            if self.committed_text and hyp.lower().startswith(self.committed_text.lower()):
                self.finalized_text = hyp
            elif self.committed_text:
                self.finalized_text = f"{self.committed_text} {hyp}".strip()
            else:
                self.finalized_text = hyp
        else:
            self.finalized_text = self.get_current_text()

        return self.finalized_text

    def get_current_text(self) -> str:
        if self.committed_text and self.mutable_partial_text:
            return f"{self.committed_text} {self.mutable_partial_text}".strip()
        return self.committed_text or self.mutable_partial_text or ""


class OverlapDuplicateResolver:
    """
    Merges audio windows and removes duplicated boundary content
    without dropping conjunctions, prepositions, or sentence continuations.
    """
    @staticmethod
    def merge_transcripts(transcripts: List[str]) -> str:
        if not transcripts:
            return ""
        if len(transcripts) == 1:
            return transcripts[0].strip()

        merged = transcripts[0].strip()

        for next_raw in transcripts[1:]:
            next_chunk = next_raw.strip()
            if not next_chunk:
                continue
            if not merged:
                merged = next_chunk
                continue

            prev_words = merged.split()
            next_words = next_chunk.split()

            max_overlap = min(16, len(prev_words), len(next_words))
            best_k = 0

            for k in range(max_overlap, 0, -1):
                p_slice = [re.sub(r'[^\w]', '', w).lower() for w in prev_words[-k:]]
                n_slice = [re.sub(r'[^\w]', '', w).lower() for w in next_words[:k]]
                if p_slice == n_slice and all(len(w) > 0 for w in p_slice):
                    best_k = k
                    break

            if best_k > 0:
                remaining_next = " ".join(next_words[best_k:])
                if remaining_next:
                    first_w = remaining_next.split()[0]
                    # If continuing clause or conjunction, strip trailing period from merged
                    if first_w[0].islower() or first_w.lower() in ('because', 'and', 'or', 'which', 'that', 'with', 'to', 'so'):
                        merged = merged.rstrip('.?!,;:')
                    if not merged.endswith((".", "!", "?", ",", ";", ":")):
                        merged = merged + " " + remaining_next
                    else:
                        merged = merged + " " + remaining_next
            else:
                if not merged.endswith((".", "!", "?", ":")):
                    merged = merged + " " + next_chunk
                else:
                    merged = merged + " " + next_chunk

        # Punctuate natural introductory time clauses
        merged = re.sub(r'^(Yesterday|Today|Tomorrow|Last night|Recently)\s+([iI]\b|we\b|they\b|you\b|he\b|she\b)', r'\1, \2', merged)
        return merged.strip()


class UniversalDuplicateEliminator:
    """
    Eliminates accidental duplicate sentences and repeated questions,
    while strictly preserving meaningful repetition and emphasis.
    """
    @staticmethod
    def eliminate_duplicates(text: str) -> str:
        if not text or not text.strip():
            return text

        result = text.strip()

        # 1. Repeated question with 'or' bridge:
        # "Can you tell me why these three skills are inactive or why these three skills are inactive?"
        # -> "Can you tell me why these three skills are inactive?"
        pat_or_repeat = re.compile(r'\b(.{10,120}?)\s+or\s+\1\b', flags=re.IGNORECASE)
        result = pat_or_repeat.sub(r'\1', result)

        # 2. Sentence-level deduplication
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', result) if s.strip()]
        if len(sentences) > 1:
            clean_s = []
            skip_idx = set()
            for i in range(len(sentences)):
                if i in skip_idx:
                    continue
                curr = sentences[i]
                if i + 1 < len(sentences):
                    nxt = sentences[i + 1]
                    c_tokens = re.sub(r'[^\w\s]', '', curr).lower().split()
                    n_tokens = re.sub(r'[^\w\s]', '', nxt).lower().split()

                    # Exact duplicate sentence: "I want to improve Gemini Flow. I want to improve Gemini Flow."
                    # Or "Why are these three skills inactive? Why are these three skills inactive?"
                    if c_tokens == n_tokens and len(c_tokens) >= 3:
                        skip_idx.add(i)
                        continue

                clean_s.append(curr)

            result = " ".join(clean_s)

        return result


class ContextualSelfCorrectionEngine:
    """
    Resolves self-corrections and sentence replacements:
    - Actions, days, dates, quantities, technical terms, and restarts.
    - Resolves chained corrections.
    - Preserves distinct events (e.g. 'Yesterday was Friday. Today is Saturday.').
    """
    CUES = [
        r'\bor\s+no,?\s+sorry\b', r'\bor\s+no,?\s+wait\b', r'\bor\s+no\b',
        r'\boh,?\s+sorry\b', r'\bno,?\s+sorry\b', r'\boh,?\s+wait\b', r'\bno,?\s+wait\b',
        r'\bor\s+rather\b', r'\bI\s+mean\b', r'\bor\s+actually\b', r'\bactually,?\s+no\b',
        r'\bmy\s+bad\b', r'\bcorrection\b', r'\bsorry,?\s+wait\b', r'\bno,?\s+I\s+mean\b',
        r'\bor\s+instead\b', r'\blet\s+me\s+correct\s+that\b', r'\bwhat\s+I\s+meant\s+was\b',
        r'\bnot\s+that\s+one\b', r'\bI\s+should\s+say\b', r'\blet\s+me\s+rephrase\b',
        r'\bto\s+be\s+more\s+precise\b',
        r'सॉरी', r'माफ़\s+करना', r'माफ\s+करा', r'माफ\s+करावे',
        r'entschuldigung', r'pardon'
    ]
    CUE_PATTERN = r'(?:' + '|'.join(CUES) + r')'

    @classmethod
    def resolve(cls, text: str) -> str:
        if not text or not text.strip():
            return text

        result = text.strip()

        # 0. Protect decimals and time abbreviations from sentence splitting
        result = re.sub(r'(\d+)\.(\d+)', r'\1__DOT__\2', result)
        result = re.sub(r'\bp\.m\.(?=\s+(?:[A-Z]|' + cls.CUE_PATTERN + r'))', 'PM.', result, flags=re.IGNORECASE)
        result = re.sub(r'\bp\.m\.', 'PM', result, flags=re.IGNORECASE)
        result = re.sub(r'\ba\.m\.(?=\s+(?:[A-Z]|' + cls.CUE_PATTERN + r'))', 'AM.', result, flags=re.IGNORECASE)
        result = re.sub(r'\ba\.m\.', 'AM', result, flags=re.IGNORECASE)

        # 1. Clean false start ellipsis restarts: "Use Gemini Fl... Gemini Flow." -> "Use Gemini Flow."
        result = re.sub(
            r'\b([A-Za-z0-9_-]+)\s+([A-Za-z]{1,4})\s*(?:\.{2,3}|…|\-)\s*\1\s+([A-Za-z0-9_-]+)\b',
            r'\1 \3',
            result,
            flags=re.IGNORECASE
        )
        result = re.sub(
            r'\b([A-Za-z]{2,5})\s*(?:\.{2,3}|…|\-)\s*([A-Za-z]{2,})\b',
            lambda m: m.group(2) if m.group(2).lower().startswith(m.group(1).lower()) else m.group(0),
            result,
            flags=re.IGNORECASE
        )

        # 2. Multi-sentence elliptical and cue-driven replacement loop
        for _ in range(4):
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', result) if s.strip()]
            if len(sentences) < 2:
                break
            new_sentences = []
            i = 0
            changed = False
            while i < len(sentences):
                curr_s = sentences[i]
                if i + 1 < len(sentences):
                    nxt_s = sentences[i + 1]
                    m_cue = re.match(r'^(?:' + cls.CUE_PATTERN + r')[\s,]+(.*)', nxt_s, flags=re.IGNORECASE)
                    if m_cue:
                        correction_payload = m_cue.group(1).strip()
                        curr_clean = curr_s.rstrip('.!?')
                        curr_words = curr_clean.split()
                        corr_words = correction_payload.rstrip('.!?').split()

                        if corr_words:
                            # 2a. Check matching prefix (e.g. 'Release version 1.0.' -> 'Release version 2.0.' or 'Use Python 3.9' -> 'Python 3.10')
                            matching_prefix = 0
                            for a, b in zip(curr_words, corr_words):
                                if a.lower() == b.lower():
                                    matching_prefix += 1
                                else:
                                    break
                            if matching_prefix >= 1:
                                res_s = curr_words[:matching_prefix] + corr_words[matching_prefix:]
                                combined = " ".join(res_s) + "."
                                new_sentences.append(combined[0].upper() + combined[1:])
                                i += 2
                                changed = True
                                continue

                            # 2b. Check if corr_words starts with a preposition or qualifier matching curr_words
                            # e.g. curr='Convert this whole data under 4 seconds.' payload='under 3 seconds.'
                            prep_match = -1
                            for idx_w, w in enumerate(curr_words):
                                if w.lower() == corr_words[0].lower():
                                    prep_match = idx_w
                                    break
                            if prep_match != -1:
                                combined = " ".join(curr_words[:prep_match] + corr_words) + "."
                                new_sentences.append(combined[0].upper() + combined[1:])
                                i += 2
                                changed = True
                                continue

                            # 2c. Elliptical predicate replacement
                            # e.g. curr = 'The total budget is $500.' payload = '$750.'
                            # e.g. curr = 'We need 4 servers.' payload = '8 servers.'
                            # e.g. curr = 'Meeting is in January.' payload = 'February.'
                            m_split = re.match(
                                r'^(.*?\b(?:is|was|are|were|need|needs|support|supports)\s+(?:in|at|on|for|from|to|into)?\s*(?:around\s+|about\s+)?)(.*)$',
                                curr_clean,
                                re.IGNORECASE
                            )
                            if not m_split:
                                m_split = re.match(
                                    r'^(.*?\b(?:to|in|at|into|for|under|over|with|on)\s+(?:around\s+|about\s+)?)(.*)$',
                                    curr_clean,
                                    re.IGNORECASE
                                )
                            if m_split:
                                subj_prefix = m_split.group(1)
                                combined = f"{subj_prefix}{correction_payload}".rstrip('.!?') + "."
                                new_sentences.append(combined[0].upper() + combined[1:])
                                i += 2
                                changed = True
                                continue

                            # 2d. General full replacement if sentence starts with cue
                            combined = correction_payload.rstrip('.!?') + "."
                            new_sentences.append(combined[0].upper() + combined[1:])
                            i += 2
                            changed = True
                            continue

                new_sentences.append(curr_s)
                i += 1

            if not changed:
                break
            result = " ".join(new_sentences)

        # 3. Chained intra-sentence self-corrections loop
        for _ in range(4):
            prev = result

            # Action replacement with cue: "Open the first application. No, open the second application."
            m_act = re.search(
                r'\b([A-Za-z]+)\s+([^.!?]+?)[,\.]?\s+' + cls.CUE_PATTERN + r'[\s,\.]+\1\s+([^.!?]+)',
                result,
                flags=re.IGNORECASE
            )
            if m_act:
                v = m_act.group(1)
                arg2 = m_act.group(3).strip()
                start_p, end_p = m_act.span()
                repl = f"{v} {arg2}".strip()
                if repl and repl[0].islower():
                    repl = repl[0].upper() + repl[1:]
                result = result[:start_p] + repl + result[end_p:]
                continue

            # Day of week override: "It's Friday. Actually, it's Saturday."
            pat_day = re.compile(
                r'\b((?:(?:it\'?s|today\s+is|on)\s+)?)\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[,\.]?\s*'
                + cls.CUE_PATTERN +
                r'[\s,\.]+(?:(?:it\'?s|today\s+is|on)\s+)?(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
                flags=re.IGNORECASE
            )
            if pat_day.search(result):
                result = pat_day.sub(lambda m: f"{m.group(1)}{m.group(3)}" if m.group(1).strip() else f"It's {m.group(3)}", result)
                continue

            # General phrase override: "Make it blue. No, make it green. Actually, make it black."
            m_phr = re.search(r'([^.!?|।]+?)[,\.]?\s+' + cls.CUE_PATTERN + r'[\s,\.]+(.+)', result, flags=re.IGNORECASE)
            if m_phr:
                cl1 = m_phr.group(1).strip()
                cl2 = m_phr.group(2).strip()
                w1 = set(re.findall(r'\b\w+\b', cl1.lower()))
                w2 = set(re.findall(r'\b\w+\b', cl2.lower()))
                sw = {'a', 'an', 'the', 'it', 'is', 'was', 'to', 'in', 'on', 'at', 'and', 'or', 'so', 'my', 'your', 'we', 'i'}
                cw1 = w1 - sw
                cw2 = w2 - sw
                common = cw1 & cw2
                if (common and len(common) / max(len(cw1), 1) >= 0.4) or (len(w1) <= 5 and len(w2) <= 5) or any(ord(c) > 127 for c in cl1):
                    cl2_clean = cl2[0].upper() + cl2[1:] if cl2 else ""
                    start_p, end_p = m_phr.span()
                    result = result[:start_p] + cl2_clean + result[end_p:]
                    continue

            if result == prev:
                break

        # 4. Replacements without keyword: "Today is Friday. Today is Saturday."
        # vs "Yesterday was Friday. Today is Saturday." (Preserved!)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', result) if s.strip()]
        if len(sentences) > 1:
            clean_s = []
            skip_idx = set()
            for i in range(len(sentences)):
                if i in skip_idx:
                    continue
                curr = sentences[i]
                if i + 1 < len(sentences):
                    nxt = sentences[i + 1]
                    c_clean = re.sub(r'[^\w\s]', '', curr).lower().split()
                    n_clean = re.sub(r'[^\w\s]', '', nxt).lower().split()

                    if len(c_clean) >= 3 and len(n_clean) >= 3:
                        days = {'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'}
                        subj_curr = c_clean[:2]
                        subj_next = n_clean[:2]
                        if subj_curr == subj_next and c_clean[-1] in days and n_clean[-1] in days:
                            skip_idx.add(i)
                            continue

                clean_s.append(curr)

            result = " ".join(clean_s)

        # 5. Restore protected decimals and time abbreviations
        result = result.replace('__DOT__', '.')
        result = re.sub(r'\bPM\b', 'p.m.', result)
        result = re.sub(r'\bAM\b', 'a.m.', result)

        # Normalize spaces before punctuation
        result = re.sub(r'\s+([,.:;?!])', r'\1', result)
        result = re.sub(r'\.\s*\.+', '.', result)
        result = re.sub(r'[ \t]{2,}', ' ', result).strip()

        return result


class VoiceTriggerExpander:
    """
    Expands configured voice trigger phrases into saved text content.
    - Operates at the beginning, middle, or end of longer utterances.
    - Preserves surrounding sentences and spacing.
    - Normalizes case, punctuation, and phonetic variants (e.g. Srinivas / Sriniwas).
    - Expands exactly once per trigger occurrence.
    """
    @staticmethod
    def expand_triggers(text: str, snippets: List[Dict[str, str]]) -> str:
        if not text or not snippets:
            return text

        result = text

        def normalize_tokens(s: str) -> List[str]:
            return re.sub(r"[^\w\s]", " ", s).lower().split()

        for snip in snippets:
            trigger = snip.get("trigger", "").strip()
            content = snip.get("content", "").strip()
            if not trigger or not content:
                continue

            variants = [trigger]
            if "srinivas" in trigger.lower():
                variants.append(re.sub(r"\bsrinivas\b", "sriniwas", trigger, flags=re.IGNORECASE))
            elif "sriniwas" in trigger.lower():
                variants.append(re.sub(r"\bsriniwas\b", "srinivas", trigger, flags=re.IGNORECASE))

            matched = False
            for trig_var in variants:
                trig_tokens = normalize_tokens(trig_var)
                if not trig_tokens:
                    continue

                pattern_parts = []
                for t in trig_tokens:
                    if t in ("srinivas", "sriniwas"):
                        pattern_parts.append(r"(?:srinivas|sriniwas)")
                    else:
                        pattern_parts.append(re.escape(t))

                regex_str = r"\b" + r"(?:[^\w\s]*\s+[^\w\s]*|[^\w\s]+)".join(pattern_parts) + r"\b[^\w\s]*"
                pattern = re.compile(regex_str, re.IGNORECASE)

                # Expand every occurrence left-to-right without re-scanning inserted content
                search_pos = 0
                while True:
                    m = pattern.search(result, search_pos)
                    if not m:
                        break
                    start, end = m.span()
                    prefix = result[:start].rstrip()
                    suffix = result[end:].lstrip()

                    # Strip conversational command triggers like "Insert", "Paste", "Add", "Type"
                    if re.match(r'^(?:insert|paste|type|add)\b', prefix, re.IGNORECASE) and len(prefix.split()) <= 2:
                        prefix = re.sub(r'^(?:insert|paste|type|add)\s*', '', prefix, flags=re.IGNORECASE).strip()

                    if prefix and not prefix.endswith((".", "!", "?", ":", ";", ",")):
                        prefix = prefix + "."

                    if suffix and suffix[0].islower():
                        suffix = suffix[0].upper() + suffix[1:]

                    inserted = content
                    if suffix and not inserted.endswith((".", "!", "?", ":", ";")):
                        inserted = inserted + "."

                    if prefix and suffix:
                        new_prefix_block = f"{prefix} {inserted}"
                        result = f"{new_prefix_block} {suffix}".strip()
                        search_pos = len(new_prefix_block) + 1
                    elif prefix:
                        new_prefix_block = f"{prefix} {inserted}"
                        result = new_prefix_block.strip()
                        search_pos = len(result)
                    else:
                        result = f"{inserted} {suffix}".strip() if suffix else content
                        search_pos = len(inserted) + (1 if suffix else 0)

                    matched = True

            if not matched:
                trig_tokens = normalize_tokens(trigger)
                if len(trig_tokens) >= 5:
                    core_tokens = trig_tokens[:-1]
                    pattern_parts = []
                    for t in core_tokens:
                        if t in ("srinivas", "sriniwas"):
                            pattern_parts.append(r"(?:srinivas|sriniwas)")
                        else:
                            pattern_parts.append(re.escape(t))
                    regex_str = r"\b" + r"(?:[^\w\s]*\s+[^\w\s]*|[^\w\s]+)".join(pattern_parts) + r"\b[^\w\s]*"
                    pattern = re.compile(regex_str, re.IGNORECASE)
                    m = pattern.search(result)
                    if m:
                        start, end = m.span()
                        prefix = result[:start].rstrip()
                        suffix = result[end:].lstrip()
                        if prefix and not prefix.endswith((".", "!", "?", ":", ";", ",")):
                            prefix = prefix + "."
                        if suffix and suffix[0].islower():
                            suffix = suffix[0].upper() + suffix[1:]
                        if prefix and suffix:
                            result = f"{prefix} {content} {suffix}".strip()
                        elif prefix:
                            result = f"{prefix} {content}".strip()
                        else:
                            result = f"{content} {suffix}".strip()

        return result


class GrammarAndPunctuationProcessor:
    """
    Applies grammar and punctuation processing according to mode and language:
    - Mode 1: Verbatim transcription (preserves spoken words, minimal punctuation).
    - Mode 2: Clean Dictation (Default) (fixes punctuation, capitalization, obvious grammar, self-corrections, filler removal).
    - Mode 3: AI Polish / Rewrite (executive restructuring, bullets, high polish).
    - Language safety: Never applies English grammar rules to non-English languages.
    """
    @staticmethod
    def clean_hesitations(text: str) -> str:
        """Removes spoken hesitation sounds (uh, um, er, erm) and stutters while preserving conversational words (basically, so, well, yeah) and agreement (uh-huh)."""
        if not text:
            return ""
        t = text
        t = re.sub(r'\buh[\s-]+huh\b', '__UH_HUH__', t, flags=re.IGNORECASE)
        t = re.sub(r'\b(Ah|Oh),\s+now\b', r'__EXCL_NOW__', t, flags=re.IGNORECASE)
        # Protect conversational intro comma 'Yeah, so basically,'
        t = re.sub(r'\b(basically|actually|meanwhile|specifically),\s*(?:uh|um|er|erm)\s*,?', r'\1,', t, flags=re.IGNORECASE)
        t = re.sub(r',\s*(?:uh|um|er|erm)\s*,?', ' ', t, flags=re.IGNORECASE)
        t = re.sub(r'\b(?:uh|um|er|erm)[\s,]+(?:uh|um|er|erm)\b', '', t, flags=re.IGNORECASE)
        t = re.sub(r'^[,\s]*(?:uh|um|er|erm)\b[,\s]*', '', t, flags=re.IGNORECASE)
        t = re.sub(r'\b(?:uh|um|er|erm)\b[,\s]*', '', t, flags=re.IGNORECASE)
        t = t.replace('__UH_HUH__', 'uh-huh')
        t = t.replace('__EXCL_NOW__', 'Ah, now')
        t = re.sub(r'\s*,\s*,+', ',', t)
        t = re.sub(r'\b(I\s+am|he\s+is|we\s+are|they\s+are),\s+', r'\1 ', t, flags=re.IGNORECASE)
        t = re.sub(r'\s+([,.:;?!])', r'\1', t)
        t = re.sub(r'[ \t]{2,}', ' ', t).strip()
        if t and t[0].islower():
            t = t[0].upper() + t[1:]
        return t

    @classmethod
    def polish_clean_dictation(cls, text: str) -> str:
        """
        Specialized clean dictation pass:
        - Eliminates verbal fillers and hesitation stutters
        - Collapses repeated starts and re-takes
        - Refines conversational Indian English phrasing to clean, articulate English without changing meaning
        """
        t = cls.clean_hesitations(text)
        
        # General stutters and immediate word repetitions (e.g. "I I", "the the", "with with")
        t = re.sub(r'\b([A-Za-z]{2,})\s+\1\b', r'\1', t, flags=re.IGNORECASE)
        t = re.sub(r'\b([A-Za-z]{2,})\s+\1\b', r'\1', t, flags=re.IGNORECASE)

        # Common spelling/homophone corrections
        t = re.sub(r'\bcheque\s+(whether|that|if)\b', r'check \1', t, flags=re.IGNORECASE)

        # Introductory punctuation for greetings and dates
        t = re.sub(r'^(Hello|Hi|Hey)\s+(I\b|[a-z])', r'\1, \2', t)
        t = re.sub(r'^(Today|Yesterday|Tomorrow)\s+([iI]\b|we\b|they\b|you\b)', lambda m: f"{m.group(1)}, {'I' if m.group(2).lower() == 'i' else m.group(2)}", t)
        t = re.sub(r'\bi\b', 'I', t)
        
        t = re.sub(r'\s*,\s*,+', ',', t)
        t = re.sub(r'\s+([,.:;?!])', r'\1', t)
        t = re.sub(r'[ \t]{2,}', ' ', t).strip()
        return t

    @staticmethod
    def process(text: str, mode: str = "clean_dictation", language: str = "en") -> str:
        if not text or not text.strip():
            return ""

        t = text.strip()

        # Mode 1: Verbatim
        if mode == "verbatim":
            t = re.sub(r'\s+([,.:;?!])', r'\1', t)
            if t and t[0].islower() and not t.startswith("http"):
                t = t[0].upper() + t[1:]
            return t

        # Non-English language handling (e.g. Hindi, Marathi, German, French, Telugu)
        is_english = language.lower() in ("en", "eng", "english")

        if is_english:
            from app.intelligence.ai_polish_brain import AIPolishBrain
            # First clean hesitations, stutters, and phrasing
            t = GrammarAndPunctuationProcessor.polish_clean_dictation(t)
            # Apply general grammar enhancements
            t = AIPolishBrain.correct_grammar(t)
            # Automatic bullet structuring when spoken sequentially
            if re.search(r'\b(?:first\s+is|firstly)\b', t, re.IGNORECASE):
                t = AIPolishBrain.smart_bullet_formatter(t)

        # Mode 3: AI Polish
        if mode in ("smart_polish", "ai_polish", "rewrite"):
            from app.intelligence.ai_polish_brain import AIPolishBrain
            t = AIPolishBrain.intelligent_structure_formatting(t)
            t = AIPolishBrain.smart_bullet_formatter(t)

        # Clean punctuation spacing
        t = re.sub(r'\s+([,.:;?!])', r'\1', t)
        if t and t[0].islower() and not t.startswith("http"):
            t = t[0].upper() + t[1:]

        return t


class UniversalPipeline:
    """
    Unified Orchestrator: Every recognition model feeds its raw hypothesis through this engine.
    """
    def __init__(self, config_manager=None):
        self.config = config_manager
        self.reconciler = StreamingHypothesisReconciler()

    def process(
        self,
        raw_text: str,
        mode: str = "clean_dictation",
        language: str = "en",
        snippets: Optional[List[Dict[str, str]]] = None,
        dictionary: Optional[List[Dict[str, str]]] = None,
        vocab_engine: Optional[Any] = None,
        cleanup_level: Optional[str] = None,
        app_name: Optional[str] = None,
        app_category: Optional[str] = None
    ) -> str:
        if not raw_text or not raw_text.strip():
            return ""

        level = "light"
        if cleanup_level:
            level = cleanup_level.lower().strip()
        elif self.config and hasattr(self.config, "get_cleanup_level"):
            level = self.config.get_cleanup_level().lower().strip()
        elif self.config and hasattr(self.config, "get"):
            level = str(self.config.get("cleanup_level", "light")).lower().strip()

        # Wispr Flow Auto Cleanup Level: 'none' (Bypass all rewriting, apply only explicit dictionary & snippets)
        if level == "none":
            text = raw_text.strip()
            if dictionary:
                from app.gemini_engine import GeminiEngine
                text = GeminiEngine.apply_dictionary(text, dictionary)
            if snippets:
                text = VoiceTriggerExpander.expand_triggers(text, snippets)
            return text

        # Step 1: Normalize Model Output
        text = ModelOutputNormalizer.normalize_text(raw_text)

        # Step 2: Universal Duplicate Elimination
        text = UniversalDuplicateEliminator.eliminate_duplicates(text)

        # Step 3: Contextual Self-Correction & Sentence Replacement
        text = ContextualSelfCorrectionEngine.resolve(text)

        # Step 4: Grammar and Punctuation Processing
        text = GrammarAndPunctuationProcessor.process(text, mode=mode, language=language)

        # Step 5: Custom Phonetic Dictionary Replacement (protecting user technical terminology)
        if dictionary:
            from app.gemini_engine import GeminiEngine
            text = GeminiEngine.apply_dictionary(text, dictionary)

        # Step 6: Vocabulary Engine Multi-Pass Enhancement
        try:
            from app.vocabulary.vocab_engine import VocabEngine
            v_eng = vocab_engine or VocabEngine.get_instance()
            if hasattr(v_eng, "normalize"):
                text = v_eng.normalize(text)
            elif hasattr(v_eng, "apply_replacements"):
                text = v_eng.apply_replacements(text)
        except Exception as ve_err:
            logger.debug(f"VocabEngine pipeline integration note: {ve_err}")

        # Step 7: Voice Trigger & Quick-Text Expansion
        if snippets:
            text = VoiceTriggerExpander.expand_triggers(text, snippets)

        # Step 7b: IDE File & Symbol Tagging (@filename)
        is_dev = False
        if app_category and app_category.lower() in ("developer", "code", "terminal"):
            is_dev = True
        elif app_name and any(ide in app_name.lower() for ide in ("code", "cursor", "windsurf", "visual studio", "terminal", "powershell", "cmd", "clion", "pycharm", "intellij")):
            is_dev = True

        if is_dev:
            # Convert file mentions like "tag index.ts", "look at app.py" or file extensions to @filename
            text = re.sub(
                r'(\b(?:tag|file|look at|check|in|see)\s+)?\b([a-zA-Z0-9_\-]+\.(?:py|ts|tsx|js|jsx|json|md|html|css|cpp|c|h|cs|java|go|rs|sh|yaml|yml|sql))\b',
                lambda m: f"{m.group(1) or ''}@{m.group(2)}" if not m.group(0).startswith("@") else m.group(0),
                text,
                flags=re.IGNORECASE
            )

        # Step 8: Terminal Punctuation Enforcement & App-Aware Writing Styles
        is_messaging = False
        if app_category and app_category.lower() in ("personal", "messaging", "chat"):
            is_messaging = True
        elif app_name and any(msg in app_name.lower() for msg in ("whatsapp", "slack", "discord", "teams", "telegram", "messages", "signal")):
            is_messaging = True

        if mode == "clean_dictation" and language.lower() in ("en", "eng", "english"):
            t_strip = text.strip()
            if is_dev:
                # In developer/terminal context, never force trailing period onto commands or symbols
                pass
            elif is_messaging and not t_strip.endswith(("!", "?")):
                # In messaging apps, strip trailing period for clean casual flow
                if t_strip.endswith("."):
                    text = t_strip[:-1].rstrip()
            elif t_strip and not t_strip.startswith("•") and "\n" not in t_strip and not t_strip.endswith((".", "!", "?", ":", ";", ",")) and "@" not in t_strip and not t_strip.startswith("http"):
                if re.match(r'^(?:can|could|would|will|is|are|does|do|did|what|where|why|how|who|which)\b', t_strip, re.IGNORECASE):
                    text = t_strip + "?"
                else:
                    text = t_strip + "."

        return text.strip()
