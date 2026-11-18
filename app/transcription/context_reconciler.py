"""
Cumulative Context-Aware Transcription Reconciler for Gemini Flow.
Maintains rolling and persistent context across dynamic audio chunks,
resolving sentence continuity, boundary overlaps, tenses, quotations,
bullet-point enumerations, and pronoun/demonstrative references.
"""
import re
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("GeminiFlow.ContextReconciler")


@dataclass
class ChunkRecord:
    chunk_id: int
    start_sec: float
    end_sec: float
    raw_text: str
    reconciled_text: str
    is_sentence_complete: bool = False
    open_conjunction: str = ""
    timestamp: float = field(default_factory=time.time)


class SentenceContinuityTracker:
    """
    Analyzes sentence boundaries and structural continuity between consecutive speech chunks.
    Identifies whether the present chunk continues an open clause, completes an incomplete sentence,
    or introduces a new independent sentence.
    """
    OPEN_CONJUNCTIONS = {
        "and", "that", "because", "which", "with", "to", "so", "but", "if", "or",
        "as", "while", "although", "since", "until", "unless", "where", "when",
        "working on", "trying to", "looking for", "focused on", "talking about",
        "explained that", "noticed that", "stated that", "said that"
    }

    OPEN_PREPOSITIONS = {
        "in", "at", "on", "for", "of", "from", "by", "under", "over", "into", "onto", "about"
    }

    COPULA_AUXILIARY = {
        "is", "was", "are", "were", "am", "be", "been", "being",
        "have", "has", "had", "will", "would", "shall", "should", "can", "could", "may", "might", "must"
    }

    @classmethod
    def is_clause_open(cls, text: str) -> Tuple[bool, str]:
        """
        Returns (is_open, open_marker).
        Checks if the text ends without final terminal punctuation or ends with a conjunction/preposition.
        """
        if not text or not text.strip():
            return False, ""
        clean = text.strip()

        # If it ends with explicit open punctuation
        if clean.endswith((",", ";", ":", "-", "–", "—", "...", "…")):
            return True, clean[-1]

        # If it ends with terminal punctuation (. ? !), check if the last word is an abbreviation (e.g. vs., etc.)
        if clean.endswith((".", "!", "?")):
            # Check for quotation mark closure
            if clean.endswith(('."', '!"', '?"', ".'", "!'", "?'")):
                return False, ""
            # Abbreviations check (e.g., e.g., i.e., vs., p.m., a.m.)
            if re.search(r'\b(?:e\.g|i\.e|vs|etc|p\.m|a\.m)\.$', clean, re.IGNORECASE):
                return True, "abbrev"
            return False, ""

        words = clean.split()
        if not words:
            return False, ""

        last_word = re.sub(r'[^\w]', '', words[-1]).lower()
        last_two = " ".join([re.sub(r'[^\w]', '', w).lower() for w in words[-2:]]) if len(words) >= 2 else ""

        if last_two in cls.OPEN_CONJUNCTIONS:
            return True, last_two

        if last_word in cls.OPEN_CONJUNCTIONS or last_word in cls.OPEN_PREPOSITIONS or last_word in cls.COPULA_AUXILIARY:
            return True, last_word

        # If no terminal punctuation at all, clause is open by default
        return True, "unterminated"


class CumulativeContextReconciler:
    """
    Universal Cumulative Transcription Engine:
    Maintains chronological chunk history, rolling contextual window,
    and reconciles every newly transcribed chunk against all previously processed content.
    """
    def __init__(self):
        self.chunk_history: List[ChunkRecord] = []
        self.cumulative_text: str = ""
        self.active_quotation_open: bool = False
        self.active_list_mode: bool = False
        self._lock_id = 0

    def reset(self):
        """Resets all state for a new recording session."""
        self.chunk_history.clear()
        self.cumulative_text = ""
        self.active_quotation_open = False
        self.active_list_mode = False
        self._lock_id = 0

    def get_context_prompt_for_model(self, max_words: int = 40) -> str:
        """
        Returns the compact trailing context of previous chunks to prime models
        (e.g., Whisper initial_prompt or Gemini context) for boundary consistency.
        Supports up to max_words trailing words (typically 40 words or last 2 sentences).
        """
        if not self.cumulative_text:
            return ""
        words = self.cumulative_text.split()
        trailing = words[-max_words:] if len(words) > max_words else words
        return " ".join(trailing).strip()

    def add_chunk(
        self,
        chunk_id: int,
        raw_text: str,
        start_sec: float = 0.0,
        end_sec: float = 0.0,
        language: str = "en",
        duration: Optional[float] = None
    ) -> str:
        """
        Core Reconciler Step:
        Receives new raw chunk transcription, performs contextual reconciliation
        against previous chunks, updates cumulative transcript, and returns current coherent text.
        """
        if duration is not None and duration > 0.0 and end_sec <= start_sec:
            end_sec = start_sec + duration
        clean_raw = (raw_text or "").strip()
        if not clean_raw:
            return self.cumulative_text

        # First chunk initialization
        if not self.chunk_history or not self.cumulative_text:
            reconciled = self._clean_standalone_chunk(clean_raw)
            is_open, open_marker = SentenceContinuityTracker.is_clause_open(reconciled)
            record = ChunkRecord(
                chunk_id=chunk_id,
                start_sec=start_sec,
                end_sec=end_sec,
                raw_text=clean_raw,
                reconciled_text=reconciled,
                is_sentence_complete=not is_open,
                open_conjunction=open_marker
            )
            self.chunk_history.append(record)
            self.cumulative_text = reconciled
            return self.cumulative_text

        prev_record = self.chunk_history[-1]
        prev_text = self.cumulative_text

        # 0. Sequential Context-Chaining: align tenses, verbs, and plurals to Chunks 1..(k-1)
        aligned_raw = self._align_context_tense_and_plurals(prev_text, clean_raw)

        # 1. Boundary Overlap & Duplicate Word Resolution
        stitched_text = self._reconcile_chunk_boundary(prev_text, aligned_raw)

        # 2. Contextual Reference & Pronoun Repair
        stitched_text = self._reconcile_contextual_references(stitched_text)

        # 3. Sentence Structure & Quotation Preservation
        stitched_text = self._reconcile_quotations_and_tenses(stitched_text)

        # 4. Enumerated Lists & Numbered Points Detection
        stitched_text = self._reconcile_enumerated_structures(stitched_text)

        # Update State
        is_open, open_marker = SentenceContinuityTracker.is_clause_open(stitched_text)
        record = ChunkRecord(
            chunk_id=chunk_id,
            start_sec=start_sec,
            end_sec=end_sec,
            raw_text=clean_raw,
            reconciled_text=stitched_text,
            is_sentence_complete=not is_open,
            open_conjunction=open_marker
        )
        self.chunk_history.append(record)
        self.cumulative_text = stitched_text

        return self.cumulative_text

    _PAST_CONTEXT_RE = re.compile(
        r'\b(?:yesterday|last\s+(?:night|week|month|year)|earlier|ago|started|migrated|deployed|wrote|built|created|updated|tested|worked|went|was|were|had|fixed|pushed|merged|ran|sent)\b',
        re.IGNORECASE
    )
    _COORD_PAST_MAP = {
        "write": "wrote", "run": "ran", "build": "built", "send": "sent",
        "make": "made", "take": "took", "get": "got", "give": "gave", "find": "found",
        "deploy": "deployed", "test": "tested", "fix": "fixed", "update": "updated",
        "create": "created", "check": "checked", "push": "pushed", "merge": "merged",
        "start": "started", "migrate": "migrated", "commit": "committed", "review": "reviewed",
    }
    _PLURAL_NOUNS = (
        "endpoint", "test", "issue", "bug", "error", "service", "file",
        "chunk", "model", "user", "feature", "problem", "point", "api", "route"
    )

    def _align_context_tense_and_plurals(self, prev_text: str, curr_text: str) -> str:
        """
        Aligns incoming chunk k against cumulative Chunks 1..(k-1) for:
        - Coordinated past-tense verb agreement when continuing a past-tense clause
        - Plural noun agreement after plural quantifiers ('all the', 'many', 'several', etc.)
        """
        if not curr_text or not prev_text:
            return curr_text

        aligned = curr_text

        # 1. Past-tense coordination alignment across chunk boundaries
        # Check trailing ~30 words of prev_text for active past-tense context
        prev_tail = " ".join(prev_text.split()[-30:])
        is_past_ctx = bool(self._PAST_CONTEXT_RE.search(prev_tail))
        # Ensure prev_tail didn't already switch to explicit future/present-only markers
        has_future_switch = bool(re.search(r'\b(?:tomorrow|will|going\s+to|next\s+week)\b', prev_tail, re.IGNORECASE))
        if is_past_ctx and not has_future_switch:
            verbs_pat = "|".join(self._COORD_PAST_MAP.keys())
            # Match ", and <verb>" or "^and <verb>" or "then <verb>" (never after "to", "will", "would", "can", "did")
            coord_re = re.compile(
                rf'(?:(?<=^)|(?<=\s))(and|then)\s+({verbs_pat})\b(?!\s+(?:to|ing))',
                re.IGNORECASE
            )
            def _replace_verb(m: re.Match) -> str:
                conj = m.group(1)
                v = m.group(2)
                past = self._COORD_PAST_MAP.get(v.lower(), v)
                if v[0].isupper():
                    past = past[0].upper() + past[1:]
                return f"{conj} {past}"
            aligned = coord_re.sub(_replace_verb, aligned)

        # 2. Plural noun alignment after plural quantifiers
        nouns_pat = "|".join(self._PLURAL_NOUNS)
        plural_re = re.compile(
            rf'\b(all\s+the|all|many|several|multiple|both|these|those|various)\s+(?:(new|old|active|failed|remaining)\s+)?({nouns_pat})\b',
            re.IGNORECASE
        )
        def _pluralize(m: re.Match) -> str:
            quant = m.group(1)
            adj = m.group(2)
            noun = m.group(3)
            plural = noun + "s"
            return f"{quant} {adj} {plural}" if adj else f"{quant} {plural}"
        aligned = plural_re.sub(_pluralize, aligned)

        # Also handle "the new test" when preceded by "wrote" / "ran" / "all" in a plural/past context
        if re.search(r'\b(?:wrote|ran|all|many|several|new)\b', aligned, re.IGNORECASE):
            aligned = re.sub(r'\b(the\s+new)\s+(test|endpoint|feature|service)\b', r'\1 \2s', aligned, flags=re.IGNORECASE)

        return aligned

    def _clean_standalone_chunk(self, text: str) -> str:
        """Cleans and standardizes an individual chunk transcription."""
        t = text.strip()
        # Remove accidental outer quotes
        if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
            t = t[1:-1].strip()
        # Standardize capitalization of first character if not URL
        if t and t[0].islower() and not t.startswith(("http", "www", "git")):
            t = t[0].upper() + t[1:]
        return t

    def _reconcile_chunk_boundary(self, prev_text: str, curr_raw: str) -> str:
        """
        Reconciles the boundary between the cumulative previous transcript and incoming chunk.
        - Removes overlap duplicate words (suffix-prefix).
        - Connects continuing clauses smoothly without artificial periods.
        - Resolves boundary stutters (e.g., 'just, just installed, installed').
        """
        curr_text = curr_raw.strip()
        if not curr_text:
            return prev_text

        # 0. Check for whole chunk duplication or whole incoming text already present at tail
        norm_prev = re.sub(r'[^\w\s]', '', prev_text).lower()
        norm_curr = re.sub(r'[^\w\s]', '', curr_text).lower()
        if norm_prev == norm_curr or (norm_curr and norm_prev.endswith(norm_curr)):
            return prev_text

        prev_words = prev_text.split()
        curr_words = curr_text.split()

        # 1. Overlap Duplicate Word Detection (up to 12 words)
        max_overlap = min(12, len(prev_words), len(curr_words))
        best_overlap = 0

        for k in range(max_overlap, 0, -1):
            p_slice = [re.sub(r'[^\w]', '', w).lower() for w in prev_words[-k:]]
            c_slice = [re.sub(r'[^\w]', '', w).lower() for w in curr_words[:k]]
            if p_slice == c_slice and all(len(w) > 0 for w in p_slice):
                best_overlap = k
                break

        if best_overlap > 0:
            remaining_words = curr_words[best_overlap:]
            if not remaining_words:
                return prev_text
            curr_text = " ".join(remaining_words).strip()

        # 2. Accidental Stutter / Repeated Words Boundary Collapse
        # e.g., prev ends with "installed" and curr starts with "installed"
        if prev_words and curr_text.split():
            last_p = re.sub(r'[^\w]', '', prev_words[-1]).lower()
            first_c = re.sub(r'[^\w]', '', curr_text.split()[0]).lower()
            if last_p == first_c and len(last_p) >= 2:
                curr_text = " ".join(curr_text.split()[1:]).strip()
                if not curr_text:
                    return prev_text

        # 3. Check Sentence Continuity
        is_open, open_marker = SentenceContinuityTracker.is_clause_open(prev_text)

        first_curr_word = curr_text.split()[0] if curr_text.split() else ""
        first_clean = re.sub(r'[^\w]', '', first_curr_word).lower()

        # Words that indicate a continuation of the previous clause
        continuing_conjunctions = {
            "that", "and", "or", "which", "because", "to", "with", "for", "in", "on", "at",
            "from", "so", "as", "is", "are", "was", "were", "be", "being", "been"
        }

        # If curr starts with a lowercase letter or continuing conjunction, strip trailing period from prev
        if is_open or first_clean in continuing_conjunctions or (first_curr_word and first_curr_word[0].islower()):
            clean_prev = prev_text.rstrip('.?!,;:-–— ')
            # Lowercase the first word of current text if it was falsely capitalized by chunk-level model
            if curr_text and curr_text[0].isupper() and first_clean not in ("i", "i'm", "i'll", "i've", "i'd", "god", "gemini", "antigravity", "whisper", "ollama"):
                curr_text = curr_text[0].lower() + curr_text[1:]
            return f"{clean_prev} {curr_text}".strip()

        # If previous was legitimately completed and current introduces a new sentence
        if not prev_text.endswith((".", "!", "?", ":", ";", "\n")):
            clean_prev = prev_text.rstrip(' ,;:-–—') + "."
        else:
            clean_prev = prev_text

        # Ensure first word of new sentence is capitalized
        if curr_text and curr_text[0].islower():
            curr_text = curr_text[0].upper() + curr_text[1:]

        return f"{clean_prev} {curr_text}".strip()

    def _reconcile_contextual_references(self, text: str) -> str:
        """
        Maintains consistency for references such as 'this approach', 'these problems',
        'it', and application names across chunk seams.
        """
        if not text:
            return ""
        t = text

        # Prevent splitting before reference demonstratives
        t = re.sub(r'\.\s+(This approach|This mechanism|These improvements|These priorities|This problem)\b', r', \1', t)
        # Reconcile project and feature references
        t = re.sub(r'\bgemini\s+flow\b', 'Gemini Flow', t, flags=re.IGNORECASE)
        t = re.sub(r'\banti[\s-]gravity\b', 'Antigravity', t, flags=re.IGNORECASE)
        t = re.sub(r'\bfaster[\s-]whisper\b', 'Faster-Whisper', t, flags=re.IGNORECASE)
        t = re.sub(r'\bvocabulary\s+engine\b', 'Vocabulary Engine', t, flags=re.IGNORECASE)
        t = re.sub(r'\bcustom\s+dictionary\b', 'Custom Dictionary', t, flags=re.IGNORECASE)
        t = re.sub(r'\bquick\s+text\b', 'Quick Text', t, flags=re.IGNORECASE)

        return t

    def _reconcile_quotations_and_tenses(self, text: str) -> str:
        """
        Preserves spoken quotations across multiple chunk intervals:
        e.g. As our mentor explained, "A good project is not just about adding features; it is about solving a real problem reliably."
        """
        if not text:
            return ""
        t = text

        # Match quotation introductions across chunks
        quote_intro_pat = re.compile(
            r'\b(as\s+(?:our\s+)?(?:mentor|teacher|professor|friend|manager|boss)\s+(?:explained|said|stated|told\s+us|reminded\s+us)[,:\s]+)(["“]?[^"”]+?)([.?!]?)$',
            re.IGNORECASE
        )
        m = quote_intro_pat.search(t)
        if m:
            intro = m.group(1).rstrip(",: \t") + ", "
            content = m.group(2).strip(' "“')
            if content:
                # Capitalize first word of direct quote
                content = content[0].upper() + content[1:]
                # Check if it was ended with a concluding thought
                if "that should guide" in t.lower() or "this should guide" in t.lower():
                    # Close quotation before conclusion
                    t = re.sub(
                        r'([^\"]+?)\s+([Tt]hat\s+should\s+guide|[Tt]his\s+should\s+guide)',
                        r'"\1" \2',
                        t
                    )

        # Standardize past, present, and future clause markers
        # "Yesterday I was working... Today I am trying... Tomorrow I will..."
        t = re.sub(r'^(Yesterday|Today|Tomorrow|Recently|Last night)\s+([iI]\b|we\b|they\b|you\b)', r'\1, \2', t)
        t = re.sub(r'\.\s+(Yesterday|Today|Tomorrow|Recently|Last night)\s+([iI]\b|we\b|they\b|you\b)', r'. \1, \2', t)

        return t

    def _reconcile_enumerated_structures(self, text: str) -> str:
        """
        Detects spoken multi-point enumeration ('First...', 'Second...', 'Third...' or
        'Three priorities... First... Second... Third...') and maintains clean structure.
        """
        if not text:
            return ""
        t = text

        # Check for forward list introductions (e.g. "three main priorities:" BEFORE "First...")
        # Strictly ignore demonstrative backward summaries like "These three priorities will make..."
        intro_match = re.search(
            r'\b(?<!these\s)(three\s+(?:main\s+)?(?:priorities|problems|improvements|features|requirements|points|steps))\b(?:\s+that\s+we\s+need\s+to\s+focus\s+on)?(?!\s+(?:will|are|have|should|must|were|can))[:\.]?',
            t,
            re.IGNORECASE
        )
        if intro_match:
            first_item = re.search(r'\b(first|1st|firstly)\b', t, re.IGNORECASE)
            if first_item and intro_match.start() < first_item.start():
                intro_str = intro_match.group(0).rstrip(':.') + ":"
                t = t[:intro_match.start()] + intro_str + t[intro_match.end():]

        return t

    def finalize(self, language: str = "en") -> str:
        """
        Final pass executed when the user drops the recording hotkey.
        Ensures the final chunk is never omitted, performs full-recording coherence review,
        resolves trailing and terminal punctuation, normalizes spacing around quotes/parentheses,
        enforces sentence capitalization, and validates technical vocabulary consistency.
        """
        if not self.cumulative_text:
            return ""

        final_text = self.cumulative_text.strip()

        # 1. Clean accidental double spaces and orphaned punctuation
        final_text = re.sub(r'[ \t]{2,}', ' ', final_text)
        final_text = re.sub(r'\s+([,.:;?!])', r'\1', final_text)
        final_text = re.sub(r'\.{2,}', '...', final_text)

        # 2. Spacing and punctuation normalization around quotes, parentheses, and brackets
        final_text = re.sub(r'\(\s+', '(', final_text)
        final_text = re.sub(r'\s+\)', ')', final_text)
        final_text = re.sub(r'\[\s+', '[', final_text)
        final_text = re.sub(r'\s+\]', ']', final_text)
        final_text = re.sub(r'"\s+([^"\n]+?)\s+"', r'"\1"', final_text)
        # Ensure punctuation is followed by space unless digit, closing quote, or end of string
        final_text = re.sub(r'([,;:])([^\s\d"\'])', r'\1 \2', final_text)
        final_text = re.sub(r'(?<=[.?!])(?=[A-Z])', ' ', final_text)

        # 3. Technical vocabulary and acronym consistency
        final_text = self._reconcile_contextual_references(final_text)

        # 4. Reconcile terminal punctuation
        if final_text and not final_text.endswith((".", "!", "?", "...", "…", "\"", "'")):
            # If it's an incomplete thought, leave clean or with natural period if standard sentence
            if final_text.endswith((",", ";", ":", "-", "–", "—")):
                final_text = final_text.rstrip(' ,;:-–—') + "."
            else:
                final_text += "."

        # 5. Capitalization enforcement on sentence boundaries
        def _cap_starter(m):
            return m.group(0).upper()

        final_text = re.sub(
            r'(?:^|(?<=[.!?]\s)|(?<=[.!?]"\s)|(?<=[.!?]\'\s))[a-z]',
            _cap_starter,
            final_text
        )

        # 6. Multilingual safety: only apply English structuring rules to English speech
        if language.lower() in ("en", "eng", "english"):
            from app.intelligence.ai_polish_brain import AIPolishBrain
            # Format bullet points if user dictated multi-point priorities
            final_text = AIPolishBrain.smart_bullet_formatter(final_text)

        logger.info(f"Cumulative reconciliation finalized: {len(self.chunk_history)} chunks processed.")
        return final_text.strip()
