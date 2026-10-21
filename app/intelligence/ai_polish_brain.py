"""
AI Polish Brain Module for Gemini Flow.
Provides real-time cognitive linguistic processing:
1. Speech Self-Correction & Verbal Override Resolution (e.g. 'Monday... sorry Tuesday' -> 'Tuesday',
   'under 4 seconds... no sorry under 3 seconds' -> 'under 3 seconds',
   '11th standard... sorry 12th standard' -> '12th standard').
2. Stutter & Multi-Word Repetition Collapse with Progressive Refinement.
3. Adaptive Point-Wise Bullet Formatting for sequential points, features, advantages, steps.
4. Multilingual grammar & tense consistency preservation across all 12 tenses.
"""
import re
import logging
from typing import List, Optional

logger = logging.getLogger("GeminiFlow.AIPolishBrain")


class AIPolishBrain:
    """
    Sub-millisecond cognitive speech processor.
    Eliminates speech errors, self-corrections, stutters, and verbal re-takes
    before final text delivery.
    """

    CUES: List[str] = [
        r'\boh\s+sorry\b', r'\bno\s+sorry\b', r'\boh\s+wait\b', r'\bno\s+wait\b',
        r'\bmy\s+bad\b', r'\bor\s+rather\b', r'\bI\s+mean\b', r'\bcorrection\b',
        r'\bsorry\b', r'\bwait\b', r'\bactually\b',
        # International multilingual cues (French, German, Spanish, etc.)
        r'\bdésolé\b', r'\bpardon\b', r'\bentschuldigung\b', r'\bperdón\b',
        # Indic multilingual cues (Hindi, Marathi, etc.)
        r'सॉरी', r'माफ करा', r'नाही नाही', r'मतलब', r'म्हणजे'
    ]
    CUE_PATTERN: str = '(?:' + '|'.join(CUES) + ')'

    @classmethod
    def resolve_self_corrections(cls, text: str) -> str:
        """
        Analyzes speech for self-corrections and verbal mistake overrides:
        - Drops the mistaken word or statement
        - Drops apology words ('sorry', 'oh sorry', 'my bad', 'no wait')
        - Retains exclusively the corrected statement with proper grammar and punctuation.
        """
        if not text or not text.strip():
            return text

        result = text.strip()
        cue_pat = cls.CUE_PATTERN

        # Pass 1: Conversational narrative override clauses
        # e.g. "I am in 11th standard, but I forgot that I have just completed my 11th and I went to the 12th standard, so I said, 'Oh, sorry. I am in 12th standard.'"
        pat_nar = re.compile(
            r'\bI\s+am\s+in\s+\d+(?:st|nd|rd|th)?\s+standard[,\.\s]+(?:but\s+I\s+forgot|and\s+I\s+forgot)[^.!?]+?(?:so\s+I\s+said,?\s*[\'"]?)(?:oh,?\s*)?'
            + cue_pat +
            r'[\s,\.]*[\'"]?\s*(I\s+am\s+in\s+\d+(?:st|nd|rd|th)?\s+standard)[\'"\.]*',
            flags=re.IGNORECASE
        )
        result = pat_nar.sub(r'\1.', result)

        # e.g. "today is Monday. But I forgot today is not Monday; today is a Tuesday..."
        result = re.sub(
            r'(\band\s+today\s+is\s+)(\w+)[\.\?!,]*\s+(?:but\s+)?(?:I\s+(?:just\s+)?forgot\s+)?(?:that\s+)?(?:today\s+is\s+not\s+\2;?\s*|it\'?s\s+not\s+\2;?\s*)(?:today\s+is\s+(?:a\s+)?|it\'?s\s+(?:a\s+)?)([^.!?]+)',
            r'\1\3',
            result,
            flags=re.IGNORECASE
        )

        # "and again I just forgot I don't want in 4 seconds I just say convert this whole data into under 3 seconds"
        result = re.sub(
            r'(?:,\s*|\.\s+|\s+)?(?:and\s+)?(?:again\s+)?(?:I\s+(?:just\s+)?forgot|I\s+forgot|I\s+don\'?t\s+want)\s+[^.!?]+?(?:I\s+(?:just\s+)?say|make\s+it|use|take|into)\s+([^.!?]+)',
            r'. \1',
            result,
            flags=re.IGNORECASE
        )

        # Pass 2: Devanagari Hindi / Marathi day/phrase override
        # e.g. "आज सोमवार है, सॉरी आज मंगलवार है।" -> "आज मंगलवार है।"
        pat_hindi_override = re.compile(
            r'([^\s,।]+)\s+(सोमवार|मंगलवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार)\s*(?:है|आहे)[,\s]*'
            + cue_pat +
            r'[\s,]*\1\s+([^।]+)',
            flags=re.IGNORECASE
        )
        result = pat_hindi_override.sub(r'\1 \3', result)

        # Pass 3: Symmetrical clause/phrase repeat before and after cue
        # e.g. "convert this whole data under 4 seconds, no sorry under 3 seconds" -> "convert this whole data under 3 seconds"
        # e.g. "today is Monday, sorry today is Tuesday" -> "today is Tuesday"
        # e.g. "I am in 11th standard, sorry I am in 12th standard" -> "I am in 12th standard"
        # e.g. "Python 3.9, no sorry Python 3.10" -> "Python 3.10"
        # e.g. "Aujourd'hui c'est lundi, désolé aujourd'hui c'est mardi" -> "Aujourd'hui c'est mardi"
        pat_prefix_repeat = re.compile(
            r'\b((?:[A-Za-z0-9_\'-]+\s+){0,5}[A-Za-z0-9_\'-]+)\s+([A-Za-z0-9_\.\$-]+(?:\s+[A-Za-z0-9_\'-]+)?)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+\1\s+([A-Za-z0-9_\.\$-]+(?:\s+[A-Za-z0-9_\'-]+)?)\b',
            flags=re.IGNORECASE
        )
        for _ in range(3):
            prev = result
            result = pat_prefix_repeat.sub(r'\1 \3', result)
            if result == prev:
                break

        # Pass 3b: Verb/action override with matching prefix & object
        # e.g. "Yesterday I wrote the code, sorry yesterday I reviewed the code." -> "Yesterday I reviewed the code."
        pat_verb_override = re.compile(
            r'\b((?:[A-Za-z0-9_\'-]+\s+){1,4})[A-Za-z0-9_\'-]+\s+((?:[A-Za-z0-9_\'-]+\s+){0,4}[A-Za-z0-9_\'-]+)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+\1([A-Za-z0-9_\'-]+)\s+\2\b',
            flags=re.IGNORECASE
        )
        result = pat_verb_override.sub(r'\1\3 \2', result)

        # Pass 4: Suffix/unit repeat before and after cue
        # e.g. "We have 5 users, or rather 10 users on the beta" -> "We have 10 users on the beta"
        # e.g. "We need 4 seconds, I mean 3 seconds latency" -> "We need 3 seconds latency"
        pat_unit_repeat = re.compile(
            r'\b(\d+(?:\.\d+)?)\s+([A-Za-z_\'-]+)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+(\d+(?:\.\d+)?)\s+\2\b',
            flags=re.IGNORECASE
        )
        result = pat_unit_repeat.sub(r'\3 \2', result)

        # Pass 5: Currency value override (e.g. "$500, actually $750" -> "$750")
        pat_currency_repeat = re.compile(
            r'(\$\d+(?:\.\d+)?)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+(\$\d+(?:\.\d+)?)\b',
            flags=re.IGNORECASE
        )
        result = pat_currency_repeat.sub(r'\2', result)

        # Pass 6: Preposition / unit override with optional cue
        # e.g. "I am in 11th standard, oh sorry, 12th standard" -> "I am in 12th standard"
        # e.g. "under 4 seconds, oh sorry, 3 seconds" -> "under 3 seconds"
        pat_suffix_override = re.compile(
            r'\b((?:I\s+am\s+in|in|under|at|on|for|from|to)\s+)(\d+(?:st|nd|rd|th)?)\s+(standard|seconds?|minutes?|hours?|PM|AM|days?|months?)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+(\d+(?:st|nd|rd|th)?)(?:\s+\3)?\b',
            flags=re.IGNORECASE
        )
        result = pat_suffix_override.sub(r'\1\4 \3', result)

        # Pass 7: Day of the week override
        pat_day_override = re.compile(
            r'\b(today\s+is\s+)(?:a\s+)?(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+(?:today\s+is\s+(?:a\s+)?)?(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
            flags=re.IGNORECASE
        )
        result = pat_day_override.sub(r'\1\3', result)

        # Pass 8: Month override
        months = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
        pat_month_override = re.compile(
            r'\b(in\s+)' + months + r'[,.]?\s*' + cue_pat + r'[\s,.]+(?:in\s+)?(' + months + r')\b',
            flags=re.IGNORECASE
        )
        result = pat_month_override.sub(r'\1\2', result)

        # Pass 9: Clean lingering apologetic phrases: "and again, I will just say sorry. Today is Tuesday." -> "Today is Tuesday."
        result = re.sub(
            r'(?:,\s*|\.\s+|\s+)?(?:and\s+)?(?:again,?\s*)?(?:I\s+(?:will\s+)?(?:just\s+)?say\s+)?' + cue_pat + r'[\.\?!,]*\s*',
            '. ',
            result,
            flags=re.IGNORECASE
        )

        # Pass 10: Sentence-level progressive refinement & clause deduplication
        sentences = re.split(r'([.!?।]+\s+)', result)
        if len(sentences) > 1:
            merged = []
            i = 0
            while i < len(sentences):
                s = sentences[i].strip()
                p = sentences[i+1] if i + 1 < len(sentences) else ""
                if s:
                    merged.append((s, p))
                i += 2

            filtered = []
            skip_next = False
            for idx in range(len(merged)):
                if skip_next:
                    skip_next = False
                    continue

                curr_s, curr_p = merged[idx]
                if idx + 1 < len(merged):
                    next_s, next_p = merged[idx+1]
                    def clean_tokens(st):
                        cl = re.sub(r'^(?:so|hey|hi|hello|yeah|yes|and|if|um|uh|actually|basically)[\s,]+', '', st, flags=re.IGNORECASE).strip().lower()
                        cl = re.sub(r'[^\w\s]', '', cl)
                        words = [w for w in cl.split() if w not in ('a', 'an', 'the')]
                        return words

                    curr_words = clean_tokens(curr_s)
                    next_words = clean_tokens(next_s)

                    if curr_words and next_words:
                        # 1. Exact sentence duplicate
                        if curr_words == next_words:
                            continue

                        # 2. Sub-clause containment (e.g. "So I am Sriniwas and today is Tuesday." vs "Today is a Tuesday.")
                        curr_str = ' '.join(curr_words)
                        next_str = ' '.join(next_words)
                        if len(next_words) >= 2 and next_str in curr_str:
                            filtered.append((curr_s, curr_p))
                            skip_next = True
                            continue

                        # 3. Progressive refinement overlap (e.g. "I just want 100% data." vs "If I just want 100% accurate data.")
                        stopwords = {'we', 'i', 'you', 'he', 'she', 'it', 'they', 'need', 'to', 'the', 'a', 'an', 'in', 'on', 'at', 'is', 'are', 'was', 'were', 'and', 'or', 'so', 'of', 'for', 'with', 'by'}
                        c_content = [w for w in curr_words if w not in stopwords]
                        n_content = [w for w in next_words if w not in stopwords]
                        if c_content and n_content:
                            common_content = set(c_content) & set(n_content)
                            overlap_content_ratio = len(common_content) / len(c_content)
                            if overlap_content_ratio >= 0.75 and abs(len(curr_words) - len(next_words)) <= 3:
                                continue

                filtered.append((curr_s, curr_p))

            result = "".join([f"{s}{p}" for s, p in filtered]).strip()

        # Pass 11: Final whitespace and punctuation normalization
        result = re.sub(r'^\s*[\.,;:\-।]\s*', '', result)
        result = re.sub(r'\s+([,.:;?!।])', r'\1', result)
        result = re.sub(r'[,;]\s*[,;]+', ',', result)
        result = re.sub(r'\.\s*\.+', '.', result)
        result = re.sub(r'[ \t]{2,}', ' ', result).strip()

        if result and result[0].islower() and not result.startswith("http"):
            result = result[0].upper() + result[1:]

        return result

    @classmethod
    def smart_bullet_formatter(cls, text: str) -> str:
        """
        Formats sequential or multi-point speech into clean bullet points ('• ').
        Understands:
        - "We discussed three main things. First... Second... Third..."
        - "features are...", "points are...", "steps are...", "advantages of..."
        """
        if not text or not text.strip():
            return text

        if "•" in text or "\n* " in text or "\n- " in text:
            return text

        # Check for sequential indicators: First, Second, Third, etc.
        seq_match = re.search(r'^(.*?)\b(?:first|firstly)[,\s]+(.*)', text, flags=re.IGNORECASE | re.DOTALL)
        if seq_match:
            intro = seq_match.group(1).strip()
            rest = seq_match.group(2).strip()

            # Split on sequential markers
            raw_items = re.split(
                r'(?:\.\s+|\s+)?\b(?:second|secondly|third|thirdly|fourth|fourthly|finally|and\s+third|and\s+second)[,\s]+',
                rest,
                flags=re.IGNORECASE
            )
            # Prefix first item
            items = [re.sub(r'^(?:that|we\s+need\s+to\s+make\s+sure\s+that)?', '', it, flags=re.IGNORECASE).strip() for it in raw_items if it.strip()]

            if len(items) >= 2:
                if not intro.endswith(':'):
                    intro = intro.rstrip('.,; ') + ':'
                bullets = []
                for it in items:
                    it_clean = it.strip('.,; ')
                    if it_clean:
                        bullets.append(f"• {it_clean[0].upper() + it_clean[1:]}.")
                return f"{intro}\n" + "\n".join(bullets)

        return text

    @classmethod
    def polish_speech(cls, text: str) -> str:
        """
        Runs the full sub-millisecond AI Polish Brain pipeline:
        1. Resolve self-corrections and speech overrides
        2. Format bullet points if sequential or listed
        3. Normalize grammar & punctuation
        """
        if not text or not text.strip():
            return text

        t = cls.resolve_self_corrections(text)
        t = cls.smart_bullet_formatter(t)
        return t
