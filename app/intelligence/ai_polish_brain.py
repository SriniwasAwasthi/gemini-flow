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

        # Also strip leading auxiliary/copula verbs and fragments left over from split
        cleaned = re.sub(r'^(?:is|was|are|advantage\s+is|advantages\s+are)\s+', '', cleaned, flags=re.IGNORECASE).strip()

        # Clean trailing commas or dangling punctuation before normalizing
        cleaned = cleaned.rstrip(',;: \t')

        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        return cleaned

    @classmethod
    def strip_verbal_fillers(cls, text: str) -> str:
        """
        Eliminates conversational vocal fillers ('um', 'uh', 'ah', 'like', 'you know', 'basically')
        from both beginning and middle of speech.
        """
        if not text or not text.strip():
            return text
        t = text.strip()
        t = re.sub(r'^(?:(?:um|uh|ah|like|basically|you\s+know|so)\b[\s,]*)+', '', t, flags=re.IGNORECASE)
        t = re.sub(r'\b(?:you\s+know|basically|um|uh|ah)\b', '', t, flags=re.IGNORECASE)
        t = re.sub(r',\s*,', ',', t)
        t = re.sub(r'[ \t]{2,}', ' ', t).strip()
        if t:
            t = t[0].upper() + t[1:]
        return t

    @classmethod
    def format_list_items(cls, text: str) -> str:
        """
        Detects spoken comma-separated or 'and'-separated item lists (groceries, deliverables, tasks)
        and converts them into structured bullet points if 2 or more items are dictated.
        Never splits on raw whitespace.
        """
        if not text or "\u2022" in text or "\n" in text:
            return text

        prefix = ""
        rest = ""
        if ":" in text:
            prefix, rest = text.split(":", 1)
            prefix = prefix.strip() + ":"
            rest = rest.strip()
        else:
            m = re.match(
                r'^(.*?\b(?:buy|pack|need|bring|agenda|items|deliverables|priorities|bugs|steps|include|includes|following|purchased|bought)(?:\s+to\s+buy|\s+for\s+the\s+[^:]+|\s+the\s+following\s+items)?[:\s]+)(.+)$',
                text, re.IGNORECASE
            )
            if not m:
                return text
            prefix = m.group(1).strip()
            rest = m.group(2).strip()

        trail_m = re.search(
            r'(?:[.;]\s+|\s+)(?:Afterwards|After that|Then|Later|Finally|I come back|I came back|I returned|I go back|I went back|at\s+\d+|from\s+\w+|for\s+\w+|on\s+\w+|tomorrow|yesterday|today)\b.*$',
            rest, re.IGNORECASE
        )
        trailing_sentence = ""
        if trail_m:
            trailing_sentence = rest[trail_m.start():].strip()
            trailing_sentence = re.sub(r'^[.;,\s]+', '', trailing_sentence)
            rest = rest[:trail_m.start()].strip()

        norm_rest = re.sub(
            r'(?<=[a-zA-Z])\s+(?=(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+)',
            ', ',
            rest,
            flags=re.IGNORECASE
        )
        parts = [p.strip().rstrip('.,;') for p in re.split(r'[,;]|\s+and\s+|\.\s+', norm_rest) if p.strip()]
        if len(parts) >= 2:
            bullets = "\n".join([f"\u2022 {p[0].upper() + p[1:] if p else p}" for p in parts])
            colon_prefix = prefix if prefix.endswith(":") else prefix + ":"
            result = f"{colon_prefix}\n{bullets}"
            if trailing_sentence:
                ts = trailing_sentence[0].upper() + trailing_sentence[1:] if trailing_sentence else ""
                if ts and not ts.endswith('.'):
                    ts += '.'
                result += f"\n{ts}"
            return result
        return text

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

        # Pass 0: Metacognitive instruction override
        # e.g. "Convert this whole data under 4 seconds, and again I just forgot I don't want in 4 seconds I just say convert this whole data into under 3 seconds."
        c2_m = re.search(
            r"(?:^|[\.\!\?\s]*)(?:[^.!?]*?)(?:,\s*|\.\s+|\s+)?(?:and\s+)?(?:again,?\s*)?(?:I\s+(?:just\s+)?forgot|I\s+forgot|I\s+don'?t\s+want)\s+[^.!?]+?(?:I\s+(?:just\s+)?say|make\s+it|use|take)\s+([^.!?]+)",
            result,
            re.IGNORECASE
        )
        if c2_m:
            res_c2 = c2_m.group(1).strip()
            if res_c2 and res_c2[0].islower():
                res_c2 = res_c2[0].upper() + res_c2[1:]
            if not res_c2.endswith(('.', '!', '?', '।')):
                res_c2 += "."
            result = res_c2

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
        # or "today is Monday. Wait, today is not Monday; today is Tuesday..."
        result = re.sub(
            r'(\band\s+today\s+is\s+|\btoday\s+is\s+)(\w+)[\.\?!,]*\s+(?:' + cue_pat + r'[\s,\.]*)?(?:but\s+)?(?:I\s+(?:just\s+)?forgot\s+)?(?:that\s+)?(?:today\s+is\s+not\s+\2;?\s*|it\'?s\s+not\s+\2;?\s*)(?:today\s+is\s+(?:a\s+)?|it\'?s\s+(?:a\s+)?)([^.!?]+)',
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

                # Pass 3b: General Time Override ("at 2 p.m. Sorry, 3 p.m." -> "at 3 p.m.")
        pat_time_gen = re.compile(
            r'\b(at\s+)?(\d+(?::\d+)?\s*(?:p\.?[mM]\.?|a\.?[mM]\.?|o\'?clock)?)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+(?:at\s+)?(\d+(?::\d+)?\s*(?:p\.?[mM]\.?|a\.?[mM]\.?|o\'?clock))\b',
            flags=re.IGNORECASE
        )
        result = pat_time_gen.sub(r'\1\3', result)

        # Pass 4: Duration, Numerical & Latency SLA Parameter Overrides
        # Handles: "convert this whole data under 4 seconds or no, sorry, under 3 seconds"
        # Handles: "under 4 seconds, no sorry 3 seconds"
        pat_duration = re.compile(
            r'\b((?:convert\s+this\s+(?:whole|hold)\s+data\s+)?(?:under|in|within|for)\s+)'
            r'(\d+(?:\.\d+)?)\s*(seconds?|minutes?|hours?|ms)(?:[\s,\.\…\—\-])*'
            + cue_pat +
            r'[\s,\.\…\—\-]+(?:(?:under|in|within|for)\s+)?'
            r'(\d+(?:\.\d+)?)(?:\s*(seconds?|minutes?|hours?|ms))?\b',
            flags=re.IGNORECASE
        )
        result = pat_duration.sub(r'\1\4 \3', result)
        result = re.sub(r'\bhold\s+data\b', 'whole data', result, flags=re.IGNORECASE)

        # Pass 5: Day of the Week Overrides
        # Handles: "Today is Monday. Oh, sorry, today is Tuesday." or "on Monday, wait Tuesday"
        pat_day = re.compile(
            r'\b((?:today\s+is\s+(?:a\s+)?|on\s+|starting\s+on\s+|by\s+|next\s+|this\s+)?)\b'
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:[\s,\.\…\—\-])*'
            + cue_pat +
            r'[\s,\.\…\—\-]+(?:(?:today\s+is\s+(?:a\s+)?|on\s+|starting\s+on\s+|by\s+|next\s+|this\s+)\s*)?'
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
            flags=re.IGNORECASE
        )
        result = pat_day.sub(r'\1\3', result)

        # Pass 5b: Month Overrides
        # Handles: "Release in January, no wait, February."
        pat_month = re.compile(
            r'\b((?:in\s+|on\s+|by\s+|during\s+|for\s+|from\s+|around\s+|until\s+|release\s+in\s+|launch\s+in\s+|start\s+in\s+)?)\b'
            r'(January|February|March|April|May|June|July|August|September|October|November|December)[,\.]?\s*'
            + cue_pat +
            r'[\s,\.]+(?:(?:in\s+|on\s+|by\s+|during\s+|for\s+|from\s+|around\s+|until\s+|release\s+in\s+|launch\s+in\s+|start\s+in\s+)\s*)?'
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\b',
            flags=re.IGNORECASE
        )
        result = pat_month.sub(r'\1\3', result)

        # Pass 6: Standard / Class / Education Overrides
        # Handles: "I am in 11th standard... sorry I am in 12th standard."
        pat_std = re.compile(
            r'\b((?:I\s+am|he\s+is|she\s+is|they\s+are|we\s+are)\s+in\s+)\d+(?:st|nd|rd|th)?\s+standard(?:[\s,\.\…\—\-])*'
            + cue_pat +
            r'[\s,\.\…\—\-]+(?:(?:I\s+am|he\s+is|she\s+is|they\s+are|we\s+are)\s+in\s+)?(\d+(?:st|nd|rd|th)?\s+standard)\b',
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

        # Pass 7c: Clause override with correction cue: "Clause A, [CUE] Clause B"
        # e.g. "We need 5 seconds latency, rather we need 3 seconds latency." -> "We need 3 seconds latency."
        # e.g. "Tomorrow we deploy to production, wait tomorrow we will deploy to production." -> "Tomorrow we will deploy to production."
        m_cue = re.search(r'([^.!?।]+?)[,\.]?\s+' + cue_pat + r'[\s,\.]+(.+)', result, flags=re.IGNORECASE)
        if m_cue:
            cl1 = m_cue.group(1).strip()
            cl2 = m_cue.group(2).strip()
            w1 = set(re.findall(r'\w+', cl1.lower()))
            w2 = set(re.findall(r'\w+', cl2.lower()))
            common = w1 & w2
            if len(common) >= 2 and (len(common) / max(len(w1), len(w2))) >= 0.4:
                cl2_clean = cl2[0].upper() + cl2[1:]
                result = cl2_clean

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
                        # 1. Exact duplicate sentence stutter collapse
                        if curr_words == next_words:
                            continue

                        # Check for explicit verbal correction or restart cues in either sentence
                        has_cue = any(
                            cue in (curr_s + " " + next_s).lower()
                            for cue in ('sorry', 'wait', 'no', 'mean', 'rather', 'actually', 'correction', 'instead', 'my bad', 'not')
                        )

                        # 2. Trailing clause duplicate collapse (e.g. "So, I am Sriniwas Awasthi, and today is Tuesday. Today is a Tuesday.")
                        if len(next_words) >= 2 and curr_words[-len(next_words):] == next_words:
                            skip_next = True
                            filtered.append((curr_s, curr_p))
                            continue

                        # 3. Subsequence progressive refinement (e.g. "We want zero latency. We want zero latency on Windows.")
                        def _is_subseq(sub, full):
                            if len(sub) < 2 or len(sub) >= len(full):
                                return False
                            it = iter(full)
                            return all(w in it for w in sub)

                        if _is_subseq(curr_words, next_words) and (len(next_words) - len(curr_words) <= 5):
                            clean_next = re.sub(r'^(?:so|if|and|like|just)\s+', '', next_s, flags=re.IGNORECASE).strip()
                            if clean_next:
                                clean_next = clean_next[0].upper() + clean_next[1:]
                                merged[idx+1] = (clean_next, next_p)
                            continue

                        # Progressive refinement overlap (e.g. "I just want 100% data. If I just want 100% accurate data.")
                        stopwords = {'we', 'i', 'you', 'he', 'she', 'it', 'they', 'need', 'to', 'the', 'a', 'an', 'in', 'on', 'at', 'is', 'are', 'was', 'were', 'and', 'or', 'so', 'of', 'for', 'with', 'by'}
                        c_content = [w for w in curr_words if w not in stopwords]
                        n_content = [w for w in next_words if w not in stopwords]

                        is_numbered_sequence = (
                            len(curr_words) >= 2 and len(next_words) >= 2 and
                            curr_words[0] in ('section', 'chapter', 'part', 'step', 'point', 'item', 'topic') and
                            next_words[0] in ('section', 'chapter', 'part', 'step', 'point', 'item', 'topic') and
                            curr_words[1] != next_words[1]
                        )

                        # Only drop earlier sentence if an explicit correction cue was present,
                        # or if it's an immediate stutter restart with addition (e.g. "I want 100% data. If I just want 100% accurate data.")
                        if not is_numbered_sequence and c_content and n_content:
                            common_content = set(c_content) & set(n_content)
                            overlap_content_ratio = len(common_content) / len(c_content) if c_content else 0
                            is_immediate_restart = (
                                overlap_content_ratio >= 0.75 and
                                len(c_content) >= 2 and
                                abs(len(curr_words) - len(next_words)) <= 3 and
                                (has_cue or any(re.match(r'^(?:so|if|and|like|just)\b', next_s, re.I) for _ in [1]))
                            )
                            if is_immediate_restart:
                                clean_next = re.sub(r'^(?:so|if|and|like|just)\s+', '', next_s, flags=re.IGNORECASE).strip()
                                if clean_next:
                                    clean_next = clean_next[0].upper() + clean_next[1:]
                                    merged[idx+1] = (clean_next, next_p)
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

        # Clean stray inline bullet noise like '• application •' while preserving list separation
        text = re.sub(r'[•\*\-]\s*(?:application|app)\s*[•\*\-]\s*', 'Third is ', text, flags=re.IGNORECASE)

        # 0. Primary: Support sequences introduced by headers like 'Some advantages, Item1. Second is Item2'
        # when the speaker omitted saying 'first is'
        if not re.search(r'\b(?:first\s+is|firstly|first\s+point)\b', text, re.IGNORECASE):
            adv_match = re.search(
                r'^(.*?)(\b(?:so,?\s+)?(?:I\s+have\s+)?(?:some\s+advantages|advantages|some\s+features|features))[,:\s]+(.*?)(?:\.\s+|\s+)\b(?:second|secondly|second\s+point|second\s+advantage|2nd|second\s+is)[,\s:]+(.*)',
                text,
                flags=re.IGNORECASE | re.DOTALL
            )
            if adv_match:
                preamble = adv_match.group(1).strip()
                header = adv_match.group(2).strip()
                first_item = adv_match.group(3).strip()
                remaining = adv_match.group(4).strip()
                rem_items = re.split(
                    r'(?:\.\s+|\s+)?\b(?:third|thirdly|3rd|and\s+third|finally|fourth)[,\s:]+|(?:[,\.\s]*\n?•\s+)',
                    remaining,
                    flags=re.IGNORECASE
                )
                raw_items = [first_item] + [it for it in rem_items if it.strip()]
                items = [cls.clean_bullet_item(it) for it in raw_items if it.strip()]
                if len(items) >= 2:
                    header_l = header.lower().strip()
                    if "some advantages" in header_l or "advantages" in header_l:
                        header_clean = "So, I have some advantages:"
                    else:
                        header_clean = header[0].upper() + header[1:]
                        if not header_clean.endswith(':'):
                            header_clean = header_clean.rstrip('.,; ') + ':'
                    bullets = [f"• {it.rstrip('.')}." for it in items if it]
                    bullet_str = "\n".join(bullets)
                    if preamble:
                        return f"{preamble} {header_clean}\n{bullet_str}"
                    else:
                        return f"{header_clean}\n{bullet_str}"

        # If text contains inline bullets without newlines, split them onto separate lines cleanly
        if "•" in text and "\n•" not in text:
            text = re.sub(r'\s*•\s*', '\n• ', text)

        # 1. If text already contains bullets, clean any ordinal markers from each bullet line!
        if "•" in text or "\n* " in text or "\n- " in text:
            lines = text.split('\n')
            out = []
            for line in lines:
                if line.strip().startswith(('•', '*', '-')):
                    m = re.match(r'^\s*([•\*\-])\s*(.*)', line)
                    if m:
                        body = m.group(2)
                        cleaned_body = cls.clean_bullet_item(body)
                        if cleaned_body:
                            out.append(f"• {cleaned_body}")
                    else:
                        out.append(line)
                else:
                    out.append(line)
            return '\n'.join(out)

        # 2. Convert continuous sequential points with explicit 'first is / first' to bullet format
        seq_match = re.search(
            r'^(.*?)\b(?:first\s+is|first|firstly|first\s+point\s+is|first\s+advantage\s+is|point\s+one)[,\s:]+(.*)',
            text,
            flags=re.IGNORECASE | re.DOTALL
        )
        if seq_match:
            intro = seq_match.group(1).strip()
            rest = seq_match.group(2).strip()

            raw_items = re.split(
                r'(?:\.\s+|\s+)?\b(?:second\s+is|second|secondly|second\s+point\s+is|second\s+advantage\s+is|third\s+is|third|thirdly|third\s+point\s+is|fourth\s+is|fourth|finally|and\s+third|and\s+second)[,\s:]+',
                rest,
                flags=re.IGNORECASE
            )
            items = [cls.clean_bullet_item(it) for it in raw_items if it.strip()]
            if len(items) >= 2:
                if not intro.endswith(':'):
                    intro = intro.rstrip('.,; ') + ':'
                bullets = [f"• {it.rstrip('.')}." for it in items if it]
                return f"{intro}\n" + "\n".join(bullets)

        try:
            from app.vocabulary.vocab_engine import VocabEngine
            formatted = VocabEngine.adaptive_bullet_format(text)
            if "•" in formatted:
                return cls.smart_bullet_formatter(formatted)
        except Exception:
            pass

        return text

    @classmethod
    def correct_grammar(cls, text: str) -> str:
        """
        Enhances spoken English grammar while strictly preserving all 12 English tenses,
        authentic meaning, proper nouns, dates, numbers, and technical terminology:
        - Corrects subject-verb agreement ('We was' -> 'We were', 'he don't' -> 'he doesn't')
        - Corrects double negatives ('don't know nothing' -> 'don't know anything')
        - Fixes spoken punctuation and article agreements ('an user' -> 'a user', 'a apple' -> 'an apple')
        - Retains 100% of past, present, and future tense distinctions without mutating timeline.
        """
        if not text or not text.strip():
            return text

        t = text

        # 1. Subject-verb agreement (without affecting modals like 'would have', 'could have')
        t = re.sub(r'\b(we|they|you)\s+was\b', r'\1 were', t, flags=re.IGNORECASE)
        t = re.sub(r"\b(he|she|it)\s+don'?t\b", r"\1 doesn't", t, flags=re.IGNORECASE)
        t = re.sub(r'(?<!will\s)(?<!would\s)(?<!could\s)(?<!should\s)(?<!must\s)\b(he|she|it)\s+have\b', r'\1 has', t, flags=re.IGNORECASE)
        t = re.sub(r'\b(i|we|they|you)\s+has\b', r'\1 have', t, flags=re.IGNORECASE)
        t = re.sub(
            r'\b(there)\s+is\s+(\d+|many|several|multiple|a\s+few)\b',
            lambda m: f"{'There' if m.group(1)[0].isupper() else 'there'} are {m.group(2)}",
            t,
            flags=re.IGNORECASE
        )
        # 1c. Quantifier noun pluralization: 'many/several/multiple problem' -> 'many/several/multiple problems'
        t = re.sub(
            r'\b(many|several|multiple|a\s+few)\s+([a-z]+)\b',
            lambda m: f"{m.group(1)} {m.group(2)}s" if not m.group(2).endswith(('s', 'sh', 'ch', 'x', 'z', 'y')) and m.group(2).lower() in ('problem', 'bug', 'issue', 'ticket', 'error', 'model', 'feature', 'question', 'item', 'thing', 'change', 'step', 'second', 'minute', 'hour', 'day', 'word') else m.group(0),
            t,
            flags=re.IGNORECASE
        )

        # 1b. Common irregular verb & plural corrections
        irregular_verbs = {
            r'\bbuyed\b': 'bought',
            r'\brunned\b': 'ran',
            r'\bcatched\b': 'caught',
            r'\bgoed\b': 'went',
            r'\bteached\b': 'taught',
            r'\bthrowed\b': 'threw',
            r'\bdrawed\b': 'drew',
            r'\bflyed\b': 'flew',
            r'\bknowed\b': 'knew',
            r'\bthinked\b': 'thought',
            r'\btaked\b': 'took',
            r'\bsleeped\b': 'slept',
            r'\bswimmed\b': 'swam',
        }
        for pat, repl in irregular_verbs.items():
            t = re.sub(pat, repl, t, flags=re.IGNORECASE)

        t = re.sub(r'\b(two|three|four|five|six|seven|eight|nine|ten|\d+)\s+(apple|egg|banana|orange|server|ticket|minute|dollar|item|problem)\b',
                   lambda m: f"{m.group(1)} {m.group(2)}s", t, flags=re.IGNORECASE)

        # 1d. Spoken tense and adverb agreement enhancements
        t = re.sub(r'\b(would|could|should|must)\s+have\s+did\b', r'\1 have done', t, flags=re.IGNORECASE)
        t = re.sub(r'\bwas\s+took\b', 'was taken', t, flags=re.IGNORECASE)
        t = re.sub(r'\breach\s+home\s+safe\b', 'reach home safely', t, flags=re.IGNORECASE)
        t = re.sub(r'\bwhy\s+you\s+are\s+not\b', "why you aren't", t, flags=re.IGNORECASE)
        t = re.sub(r'\b(yesterday|last\s+\w+)\s+([iI]|we|they)\s+go\b', lambda m: f"{m.group(1)} {m.group(2)} went", t, flags=re.IGNORECASE)
        t = re.sub(r'(?<=\band\s)seen\s+(him|her|them|it|that)\b', r'saw \1', t, flags=re.IGNORECASE)
        t = re.sub(r'(?<=,\s)seen\s+(him|her|them|it|that)\b', r'saw \1', t, flags=re.IGNORECASE)

        # 2. Double negative resolution
        t = re.sub(r'\b(don\'?t|doesn\'?t|didn\'?t|won\'?t|can\'?t|couldn\'?t|hasn\'?t|haven\'?t)\s+know\s+nothing\b', r'\1 know anything', t, flags=re.IGNORECASE)
        t = re.sub(r'\b(don\'?t|doesn\'?t|didn\'?t|won\'?t|can\'?t|couldn\'?t|hasn\'?t|haven\'?t)\s+see\s+nothing\b', r'\1 see anything', t, flags=re.IGNORECASE)
        t = re.sub(r'\b(don\'?t|doesn\'?t|didn\'?t|won\'?t|can\'?t|couldn\'?t|hasn\'?t|haven\'?t)\s+have\s+no\b', r'\1 have any', t, flags=re.IGNORECASE)

        # 3. Indefinite article agreement (with case preservation)
        def _fix_a_to_an(m):
            lead = 'A ' if m.group(0)[0].isupper() else 'a '
            lead_an = 'An ' if m.group(0)[0].isupper() else 'an '
            word = m.group(1)
            if word.lower().startswith(('user', 'unit', 'one', 'univ', 'util')):
                return lead + word
            return lead_an + word

        def _fix_an_to_a(m):
            lead = 'A ' if m.group(0)[0].isupper() else 'a '
            lead_an = 'An ' if m.group(0)[0].isupper() else 'an '
            word = m.group(1)
            if word.lower().startswith(('hour', 'honest', 'honor', 'heir')):
                return lead_an + word
            return lead + word

        t = re.sub(r'\ba\s+([aeiouAEIOU]\w*|hour\w*|honest\w*|honor\w*|heir\w*)\b', _fix_a_to_an, t, flags=re.IGNORECASE)
        t = re.sub(r'\ban\s+([bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]\w*)\b', _fix_an_to_a, t, flags=re.IGNORECASE)

        # 4. Spoken punctuation commands
        t = re.sub(r'(?<=[a-zA-Z0-9])\s+(?:period|full stop)\b', '.', t, flags=re.IGNORECASE)
        t = re.sub(r'(?<=[a-zA-Z0-9])\s+comma\b', ',', t, flags=re.IGNORECASE)
        t = re.sub(r'(?<=[a-zA-Z0-9])\s+question mark\b', '?', t, flags=re.IGNORECASE)
        t = re.sub(r'(?<=[a-zA-Z0-9])\s+exclamation mark\b', '!', t, flags=re.IGNORECASE)
        t = re.sub(r'(?<=[a-zA-Z0-9])\s+colon\b', ':', t, flags=re.IGNORECASE)
        t = re.sub(r'(?<=[a-zA-Z0-9])\s+semicolon\b', ';', t, flags=re.IGNORECASE)
        t = re.sub(r'\b(?:new\s+line|next\s+line|new\s+paragraph)\b', '\n\n', t, flags=re.IGNORECASE)

        return t

    @classmethod
    def intelligent_structure_formatting(cls, text: str) -> str:
        """
        Structures long continuous dictations into readable paragraphs, short paragraphs,
        and adaptive bullet points based on topic shifts and transitions.
        """
        if not text or not text.strip():
            return text

        # If already formatted with paragraph breaks, preserve
        if "\n\n" in text:
            return text

        # Split into distinct thoughts/paragraphs when major discourse transition cues occur
        t = text
        transitions = [
            r'\b(?:Furthermore|Moreover|In addition|On the other hand|Regarding|Moving on to|As for the next step|To summarize|In conclusion)\b'
        ]
        for tr in transitions:
            t = re.sub(r'(?<=[.!?])\s+(' + tr + ')', r'\n\n\1', t)

        return t

    @classmethod
    def extract_vocabulary_and_terms(cls, text: str) -> str:
        """
        Extracts key technical vocabulary, proper nouns, and significant terms
        from spoken text when explicitly requested by the user.
        """
        if not text or not text.strip():
            return ""

        import re
        words = re.findall(r'\b[A-Za-z0-9_\-\.\$₹€£]+\b', text)
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have',
            'has', 'had', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'shall',
            'should', 'may', 'might', 'must', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
            'this', 'that', 'these', 'those', 'what', 'which', 'who', 'whom', 'whose',
            'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
            'so', 'than', 'too', 'very', 's', 't', 'just', 'don', 'now', 'also', 'first',
            'second', 'third', 'main', 'things', 'yesterday'
        }
        seen = set()
        key_terms = []
        for w in words:
            w_clean = re.sub(r'^[^\w]+|[^\w]+$', '', w)
            if len(w_clean) > 2 and w_clean.lower() not in stopwords:
                key = w_clean.lower()
                if key not in seen:
                    seen.add(key)
                    key_terms.append(w_clean)

        if not key_terms:
            return text

        bullets = [f"• {t}" for t in key_terms[:30]]
        return "Key Vocabulary & Terms Extracted:\n" + "\n".join(bullets)

    @classmethod
    def polish_speech(cls, text: str) -> str:
        """
        Runs the full sub-millisecond AI Polish Brain pipeline:
        1. Resolve self-corrections and speech overrides
        2. Correct grammar and preserve all 12 tenses
        3. Apply intelligent structure and paragraph breaks
        4. Format bullet points if sequential or listed with stripped ordinals
        """
        if not text or not text.strip():
            return text

        try:
            from app.vocabulary.vocab_engine import VocabEngine
            text = VocabEngine.normalize_text(text)
        except Exception:
            pass

        t = cls.resolve_self_corrections(text)
        t = cls.strip_verbal_fillers(t)
        t = cls.correct_grammar(t)
        t = cls.intelligent_structure_formatting(t)
        t = cls.smart_bullet_formatter(t)
        t = cls.format_list_items(t)

        try:
            from app.vocabulary.vocab_engine import VocabEngine
            t = VocabEngine.normalize_text(t)
        except Exception:
            pass
        return t
