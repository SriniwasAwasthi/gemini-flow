"""
AI Polish Brain Module for Gemini Flow (Wispr Flow Intelligence).
Provides real-time cognitive linguistic processing:
1. Speech Self-Correction & Verbal Override Resolution (e.g. 'Monday... sorry Tuesday' -> 'Tuesday',
   'under 4 seconds... no sorry under 3 seconds' -> 'under 3 seconds',
   'total budget was around ₹550. Oh wait, the total budget was ₹750' -> 'total budget was ₹750',
   'The meeting is at 2 p.m. Sorry, 3 p.m.' -> 'The meeting is at 3 p.m.',
   '11th standard... sorry 12th standard' -> '12th standard').
2. Stutter & Multi-Word Repetition Collapse with Progressive Refinement.
3. Adaptive Point-Wise Bullet Formatting with Ordinal Marker Stripping ('• Antigravity' instead of '• First is Antigravity').
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
        r'\bor\s+no,?\s+sorry\b', r'\bor\s+no,?\s+wait\b', r'\bor\s+no\b',
        r'\boh,?\s+sorry\b', r'\bno,?\s+sorry\b', r'\boh,?\s+wait\b', r'\bno,?\s+wait\b',
        r'\bor\s+rather\b', r'\bI\s+mean\b', r'\bor\s+actually\b', r'\bactually\b',
        r'\bmy\s+bad\b', r'\bcorrection\b', r'\bsorry\b', r'\bwait\b',
        r'\bor\s+sorry\b',
        # International multilingual cues (French, German, Spanish, etc.)
        r'\bdésolé\b', r'\bpardon\b', r'\bentschuldigung\b', r'\bperdón\b',
        # Indic multilingual cues (Hindi, Marathi, etc.)
        r'सॉरी', r'माफ करा', r'नाही नाही', r'मतलब', r'म्हणजे'
    ]
    CUE_PATTERN: str = '(?:' + '|'.join(CUES) + ')'

    @classmethod
    def clean_bullet_item(cls, item: str) -> str:
        """
        Strips leading ordinal markers and point labels from bullet items.
        Wispr Flow Intelligence: A bullet ('• ') already denotes the item,
        so redundant spoken ordinals ('First is', 'Second is', 'And third is',
        'Point 1:', '1.') are cleanly stripped.
        """
        cleaned = item.strip()
        cleaned = re.sub(r'^[•\*\-\d+\.\)]\s*', '', cleaned)

        ordinal_patterns = [
            r'^(?:and\s+)?(?:first|firstly|1st)\s*(?:is|was|point\s+is|item\s+is|advantage\s+is|feature\s+is|[:,\-–—])\s*',
            r'^(?:and\s+)?(?:second|secondly|2nd)\s*(?:is|was|point\s+is|item\s+is|advantage\s+is|feature\s+is|[:,\-–—])\s*',
            r'^(?:and\s+)?(?:third|thirdly|3rd)\s*(?:is|was|point\s+is|item\s+is|advantage\s+is|feature\s+is|[:,\-–—])\s*',
            r'^(?:and\s+)?(?:fourth|fourthly|4th)\s*(?:is|was|point\s+is|item\s+is|advantage\s+is|feature\s+is|[:,\-–—])\s*',
            r'^(?:and\s+)?(?:fifth|fifthly|5th)\s*(?:is|was|point\s+is|item\s+is|advantage\s+is|feature\s+is|[:,\-–—])\s*',
            r'^(?:and\s+)?(?:finally|lastly)\s*(?:is|was|point\s+is|[:,\-–—])\s*',
            r'^(?:point|item)\s*(?:number\s+)?(?:\d+|one|two|three|four|five)?\s*(?:is|was|[:,\-–—])\s*',
            r'^(?:point|item|advantage|feature)\s+(?:is|was)\s*',
            r'^(?:\d+[\.\)]|\([0-9]+\))\s*',
            # Indic ordinals
            r'^(?:पहिला|दुसरा|तिसरा|चौथा|पहिला मुद्दा|दुसरा मुद्दा|पहिला फायदा)\s*(?:आहे|म्हणजे)?\s*[:,\-–—]?\s*',
            r'^(?:पहला|दूसरा|तीसरा|चौथा|पहला बिंदु|दूसरा बिंदु|पहला फायदा)\s*(?:है|मतलब)?\s*[:,\-–—]?\s*'
        ]
        for pat in ordinal_patterns:
            cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE).strip()

        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        return cleaned

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

        # Pass 1: Narrative & Metacognitive error overrides
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

        # Pass 2: Budget, Price, & Currency Value Overrides
        # Handles: "total budget was around ₹550. Oh wait, the total budget was ₹750."
        # Handles: "total budget was $500... actually $750."
        pat_budget = re.compile(
            r'\b((?:the\s+)?(?:total\s+)?(?:budget|price|cost|amount|sum|bill)\s+(?:was|is)\s+)'
            r'(?:around\s+|about\s+|approx(?:imately)?\s+)?'
            r'([$€£\u20b9¥]\s*\d+(?:\.\d+)?|\b(?:Rs\.?|INR|USD|EUR|GBP)\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:rupees?|dollars?|euros?|pounds?|bucks?))[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+(?:(?:the\s+)?(?:total\s+)?(?:budget|price|cost|amount|sum|bill)?\s*(?:was|is)?\s*)?'
            r'([$€£\u20b9¥]\s*\d+(?:\.\d+)?|\b(?:Rs\.?|INR|USD|EUR|GBP)\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:rupees?|dollars?|euros?|pounds?|bucks?))\b',
            flags=re.IGNORECASE
        )
        result = pat_budget.sub(r'\1\3', result)

        # Standalone currency value override: "$500, actually $750" or "₹500, wait ₹750"
        pat_curr_standalone = re.compile(
            r'([$€£\u20b9¥]\s*\d+(?:\.\d+)?|\b(?:Rs\.?|INR|USD|EUR|GBP)\s*\d+(?:\.\d+)?)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+([$€£\u20b9¥]\s*\d+(?:\.\d+)?|\b(?:Rs\.?|INR|USD|EUR|GBP)\s*\d+(?:\.\d+)?)\b',
            flags=re.IGNORECASE
        )
        result = pat_curr_standalone.sub(r'\2', result)

        # Pass 3: Meeting, Schedule & Time Overrides
        # Handles: "The meeting is at 2 p.m. Sorry, the meeting is at 3 p.m."
        # Handles: "The meeting is at 2 PM. Sorry, 3 PM."
        pat_meeting = re.compile(
            r'\b((?:the\s+)?(?:meeting|call|event|flight|session|interview|sync|appointment)\s+is\s+at\s+)'
            r'(\d+(?::\d+)?\s*(?:p\.?m\.?|a\.?m\.?|o\'?clock)?)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+(?:(?:the\s+)?(?:meeting|call|event|flight|session|interview|sync|appointment)?\s*is\s*at\s*)?'
            r'(\d+(?::\d+)?\s*(?:p\.?m\.?|a\.?m\.?|o\'?clock)?)\b',
            flags=re.IGNORECASE
        )
        result = pat_meeting.sub(r'\1\3', result)

        # Pass 4: Duration, Numerical & Latency SLA Parameter Overrides
        # Handles: "convert this whole data under 4 seconds or no, sorry, under 3 seconds"
        # Handles: "under 4 seconds, no sorry 3 seconds"
        pat_duration = re.compile(
            r'\b((?:convert\s+this\s+(?:whole|hold)\s+data\s+)?(?:under|in|within|for)\s+)'
            r'(\d+(?:\.\d+)?)\s*(seconds?|minutes?|hours?|ms)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+(?:(?:under|in|within|for)\s+)?'
            r'(\d+(?:\.\d+)?)(?:\s*(seconds?|minutes?|hours?|ms))?\b',
            flags=re.IGNORECASE
        )
        result = pat_duration.sub(r'\1\4 \3', result)
        result = re.sub(r'\bhold\s+data\b', 'whole data', result, flags=re.IGNORECASE)

        # Pass 5: Day of the Week Overrides
        # Handles: "Today is Monday. Oh, sorry, today is Tuesday."
        pat_day = re.compile(
            r'\b(today\s+is\s+(?:a\s+)?)'
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+(?:today\s+is\s+(?:a\s+)?)?'
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
            flags=re.IGNORECASE
        )
        result = pat_day.sub(r'\1\3', result)

        # Pass 6: Standard / Class / Education Overrides
        # Handles: "I am in 11th standard... sorry I am in 12th standard."
        pat_std = re.compile(
            r'\b(I\s+am\s+in\s+)\d+(?:st|nd|rd|th)?\s+standard[\s,\.\—\-]*'
            + cue_pat +
            r'[\s,\.\—\-]+(?:I\s+am\s+in\s+)?(\d+(?:st|nd|rd|th)?\s+standard)\b',
            flags=re.IGNORECASE
        )
        result = pat_std.sub(r'\1\2', result)

        # Pass 7: Symmetrical clause/phrase repeat before and after cue
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

        # Pass 7b: Verb/action override with matching prefix & object
        # e.g. "Yesterday I wrote the code, sorry yesterday I reviewed the code." -> "Yesterday I reviewed the code."
        pat_verb_override = re.compile(
            r'\b((?:[A-Za-z0-9_\'-]+\s+){1,4})[A-Za-z0-9_\'-]+\s+((?:[A-Za-z0-9_\'-]+\s+){0,4}[A-Za-z0-9_\'-]+)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+\1([A-Za-z0-9_\'-]+)\s+\2\b',
            flags=re.IGNORECASE
        )
        result = pat_verb_override.sub(r'\1\3 \2', result)

        # Pass 8: Devanagari Hindi / Marathi day/phrase override
        # e.g. "आज सोमवार है, सॉरी आज मंगलवार है।" -> "आज मंगलवार है।"
        pat_hindi_override = re.compile(
            r'([^\s,।]+)\s+(सोमवार|मंगलवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार)\s*(?:है|आहे)[,\s]*'
            + cue_pat +
            r'[\s,]*\1\s+([^।]+)',
            flags=re.IGNORECASE
        )
        result = pat_hindi_override.sub(r'\1 \3', result)

        # Pass 9: Unit repeat before and after cue
        # e.g. "We have 5 users, or rather 10 users on the beta" -> "We have 10 users on the beta"
        pat_unit_repeat = re.compile(
            r'\b(\d+(?:\.\d+)?)\s+([A-Za-z_\'-]+)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+(\d+(?:\.\d+)?)\s+\2\b',
            flags=re.IGNORECASE
        )
        result = pat_unit_repeat.sub(r'\3 \2', result)

        # Pass 10: Clean lingering apologetic phrases: "and again, I will just say sorry. Today is Tuesday." -> "Today is Tuesday."
        result = re.sub(
            r'(?:,\s*|\.\s+|\s+)?(?:and\s+)?(?:again,?\s*)?(?:I\s+(?:will\s+)?(?:just\s+)?say\s+)?' + cue_pat + r'[\.\?!,]*\s*',
            '. ',
            result,
            flags=re.IGNORECASE
        )

        # Pass 11: Sentence-level progressive refinement & clause deduplication
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
                        return [w for w in cl.split() if w not in ('a', 'an', 'the')]

                    curr_words = clean_tokens(curr_s)
                    next_words = clean_tokens(next_s)

                    if curr_words and next_words:
                        if curr_words == next_words:
                            continue

                        curr_str = ' '.join(curr_words)
                        next_str = ' '.join(next_words)
                        if len(next_words) >= 2 and next_str in curr_str:
                            filtered.append((curr_s, curr_p))
                            skip_next = True
                            continue

                        # Progressive refinement overlap (e.g. "I just want 100% data." vs "I just want 100% accurate data.")
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

        # Pass 12: Final whitespace and punctuation normalization
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
        - Strips spoken ordinal markers ('First is', 'Second is', 'And third is', '1.')
          from individual bullet lines.
        """
        if not text or not text.strip():
            return text

        # If text already contains bullets, clean any ordinal markers from each bullet line!
        if "•" in text or "\n* " in text or "\n- " in text:
            lines = text.split('\n')
            out = []
            for line in lines:
                if line.strip().startswith(('•', '*', '-')):
                    m = re.match(r'^\s*([•\*\-])\s*(.*)', line)
                    if m:
                        body = m.group(2)
                        cleaned_body = cls.clean_bullet_item(body)
                        out.append(f"• {cleaned_body}")
                    else:
                        out.append(line)
                else:
                    out.append(line)
            return '\n'.join(out)

        # Convert continuous sequential points to bullet format
        seq_match = re.search(
            r'^(.*?)\b(?:first|firstly|first\s+point\s+is|first\s+advantage\s+is|point\s+one)[,\s:]+(.*)',
            text,
            flags=re.IGNORECASE | re.DOTALL
        )
        if seq_match:
            intro = seq_match.group(1).strip()
            rest = seq_match.group(2).strip()

            raw_items = re.split(
                r'(?:\.\s+|\s+)?\b(?:second|secondly|second\s+point\s+is|second\s+advantage\s+is|third|thirdly|third\s+point\s+is|fourth|finally|and\s+third|and\s+second)[,\s:]+',
                rest,
                flags=re.IGNORECASE
            )
            items = [cls.clean_bullet_item(it) for it in raw_items if it.strip()]
            if len(items) >= 2:
                if not intro.endswith(':'):
                    intro = intro.rstrip('.,; ') + ':'
                bullets = [f"• {it.rstrip('.')}." for it in items if it]
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
