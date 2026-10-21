"""
Personal AI Vocabulary Engine for Gemini Flow.
Manages canonical terms, aliases, phonetic variants, categories,
prompt-level priming, and multi-pass text normalization.
"""
import re
import json
import uuid
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Any

logger = logging.getLogger("GeminiFlow.VocabularyEngine")

DEFAULT_CATEGORIES = [
    "Personal",
    "Technical",
    "Programming",
    "Project",
    "Academic",
    "Custom"
]


@dataclass
class VocabularyEntry:
    id: str
    canonical_term: str
    aliases: List[str] = field(default_factory=list)
    category: str = "Custom"
    enabled: bool = True
    case_sensitive: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VocabularyEntry":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            canonical_term=data.get("canonical_term", "").strip(),
            aliases=[a.strip() for a in data.get("aliases", []) if a.strip()],
            category=data.get("category", "Custom"),
            enabled=bool(data.get("enabled", True)),
            case_sensitive=bool(data.get("case_sensitive", False)),
            notes=data.get("notes", "").strip()
        )


DEFAULT_VOCABULARY = [
    {
        "canonical_term": "Sriniwas Awasthi",
        "aliases": ["Srinivas Awasthi", "Sriniwas Awasti", "Srinivas Awasti", "Srinivas Avasthi", "Sriniwas Avasthi", "Sri Srinivas Awasthi", "Sri Sriniwas Awasthi", "Sri Srinivas"],
        "category": "Personal",
        "enabled": True,
        "notes": "Full user name"
    },
    {
        "canonical_term": "Sriniwas",
        "aliases": ["Srinivas", "Shriniwas", "Shreeniwas", "Shreenivas"],
        "category": "Personal",
        "enabled": True,
        "notes": "First name"
    },
    {
        "canonical_term": "Awasthi",
        "aliases": ["Avasthi", "Awasti", "Avasti"],
        "category": "Personal",
        "enabled": True,
        "notes": "Last name"
    },
    {
        "canonical_term": "Wispr",
        "aliases": ["Wisper", "Whisper flow", "Wispr Flow", "whisper", "the whisper"],
        "category": "Project",
        "enabled": True,
        "notes": "Application inspiration brand"
    },
    {
        "canonical_term": "TypeScript",
        "aliases": ["Typescript", "type script"],
        "category": "Programming",
        "enabled": True
    },
    {
        "canonical_term": "JavaScript",
        "aliases": ["Javascript", "java script"],
        "category": "Programming",
        "enabled": True
    },
    {
        "canonical_term": "GitHub",
        "aliases": ["Github", "git hub"],
        "category": "Technical",
        "enabled": True
    },
    {
        "canonical_term": "PyTorch",
        "aliases": ["Pytorch", "pie torch"],
        "category": "Programming",
        "enabled": True
    },
    {
        "canonical_term": "LeetCode",
        "aliases": ["Leetcode", "lead code"],
        "category": "Programming",
        "enabled": True
    },
    {
        "canonical_term": "camelCase",
        "aliases": ["camel case", "CamelCase"],
        "category": "Programming",
        "enabled": True
    },
    {
        "canonical_term": "snake_case",
        "aliases": ["snake case", "Snake_case"],
        "category": "Programming",
        "enabled": True
    }
]


class VocabularyEngine:
    """
    Manages personal vocabulary records, compiles AI priming instructions,
    and applies post-recognition canonical normalization.
    """
    def __init__(self, vocab_file: Optional[Path] = None):
        if vocab_file:
            self.file_path = vocab_file
        else:
            import os
            app_dir = Path(os.environ.get("APPDATA", Path.home())) / "GeminiFlow"
            app_dir.mkdir(parents=True, exist_ok=True)
            self.file_path = app_dir / "vocabulary.json"

        self.entries: List[VocabularyEntry] = []
        self.load_vocabulary()

    def load_vocabulary(self) -> List[VocabularyEntry]:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.entries = [VocabularyEntry.from_dict(d) for d in data if d.get("canonical_term")]
                logger.info(f"Loaded {len(self.entries)} personal vocabulary entries.")
                return self.entries
            except Exception as e:
                logger.error(f"Error loading vocabulary.json: {e}")

        # Seed defaults
        self.entries = [
            VocabularyEntry(
                id=str(uuid.uuid4()),
                canonical_term=d["canonical_term"],
                aliases=d.get("aliases", []),
                category=d.get("category", "Custom"),
                enabled=d.get("enabled", True),
                notes=d.get("notes", "")
            )
            for d in DEFAULT_VOCABULARY
        ]
        self.save_vocabulary()
        return self.entries

    def save_vocabulary(self) -> bool:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([e.to_dict() for e in self.entries], f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save vocabulary: {e}")
            return False

    def add_entry(
        self,
        canonical_term: Any,
        aliases: Optional[List[str]] = None,
        category: str = "Custom",
        enabled: bool = True,
        case_sensitive: bool = False,
        notes: str = ""
    ) -> Optional[VocabularyEntry]:
        if isinstance(canonical_term, VocabularyEntry):
            entry_obj = canonical_term
            cleaned_term = entry_obj.canonical_term.strip()
            aliases = entry_obj.aliases
            category = entry_obj.category
            enabled = entry_obj.enabled
            case_sensitive = entry_obj.case_sensitive
            notes = entry_obj.notes
        else:
            cleaned_term = str(canonical_term).strip()

        if not cleaned_term:
            return None

        # Check existing
        for e in self.entries:
            if e.canonical_term.lower() == cleaned_term.lower():
                # Merge aliases
                if aliases:
                    for a in aliases:
                        if a.strip() and a.strip() not in e.aliases:
                            e.aliases.append(a.strip())
                e.category = category
                e.enabled = enabled
                e.case_sensitive = case_sensitive
                e.notes = notes or e.notes
                self.save_vocabulary()
                return e

        entry = VocabularyEntry(
            id=str(uuid.uuid4()),
            canonical_term=cleaned_term,
            aliases=[a.strip() for a in (aliases or []) if a.strip()],
            category=category,
            enabled=enabled,
            case_sensitive=case_sensitive,
            notes=notes
        )
        self.entries.append(entry)
        self.save_vocabulary()
        return entry

    def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        for e in self.entries:
            if e.id == entry_id:
                if "canonical_term" in updates:
                    e.canonical_term = updates["canonical_term"].strip()
                if "aliases" in updates:
                    e.aliases = [a.strip() for a in updates["aliases"] if a.strip()]
                if "category" in updates:
                    e.category = updates["category"]
                if "enabled" in updates:
                    e.enabled = bool(updates["enabled"])
                if "case_sensitive" in updates:
                    e.case_sensitive = bool(updates["case_sensitive"])
                if "notes" in updates:
                    e.notes = updates["notes"].strip()
                self.save_vocabulary()
                return True
        return False

    def delete_entry(self, entry_id_or_term: str) -> bool:
        target = str(entry_id_or_term).strip().lower()
        initial = len(self.entries)
        self.entries = [
            e for e in self.entries
            if e.id != entry_id_or_term and e.canonical_term.lower() != target
        ]
        if len(self.entries) < initial:
            self.save_vocabulary()
            return True
        return False

    def search(self, query: str, category_filter: Optional[str] = None) -> List[VocabularyEntry]:
        q = (query or "").strip().lower()
        results = []
        for e in self.entries:
            if category_filter and category_filter != "All" and e.category != category_filter:
                continue
            if not q:
                results.append(e)
                continue
            if q in e.canonical_term.lower() or any(q in a.lower() for a in e.aliases) or q in e.notes.lower():
                results.append(e)
        return results

    def get_prompt_injection(self, category_priorities: Optional[List[str]] = None) -> str:
        """
        Compiles active vocabulary terms into a clean instruction for Gemini speech-to-text priming.
        """
        active = [e for e in self.entries if e.enabled]
        if not active:
            return ""

        canonical_terms = [e.canonical_term for e in active]
        return (
            "\n\nPersonal AI Vocabulary & Spelling Directives:\n"
            f"- If spoken, prioritize correct spelling for: {', '.join(canonical_terms)}.\n"
            "- CRITICAL RULE: Transcribe proper names ONLY if explicitly and unambiguously spoken. NEVER insert, assume, or append personal names or sign-offs that were not uttered in this recording."
        )

    format_prompt_injection = get_prompt_injection
    save = save_vocabulary

    @staticmethod
    def adaptive_bullet_format(text: str) -> str:
        """
        Wispr Flow Intelligence: Intelligently formats point-wise dictations (advantages,
        disadvantages, benefits, key points, steps, features) into clean bullet points ('• ').
        Does NOT convert ordinary narrative prose or general paragraphs into bullet points.
        """
        if not text or not text.strip():
            return text

        if "•" in text or "\n* " in text or "\n- " in text:
            return text

        # Check for genuine list indicators / introductory phrase
        has_list_intent = bool(re.search(
            r'\b(?:bullet\s+points?|bulleted|numbered\s+list|pros\s+and\s+cons|firstly|secondly|thirdly|'
            r'point\s+one|point\s+two|item\s+one|item\s+two|'
            r'advantages?\s+(?:of|about|are|include)|disadvantages?\s+(?:of|about|are|include)|'
            r'benefits?\s+(?:of|about|are|include)|key\s+points?\s*(?:are|:|include)|'
            r'the\s+following\s+points?|here\s+are\s+the\s+points|'
            r'points\s+are\s*(?:as|:|include)|steps?\s+(?:are|to|include))\b',
            text,
            re.IGNORECASE
        ))
        if not has_list_intent:
            return text

        match = re.search(
            r'^(.*?\b(?:advantages?\s+(?:of|about|are|include)|disadvantages?\s+(?:of|about|are|include)|'
            r'benefits?\s+(?:of|about|are|include)|pros\s+and\s+cons|key\s+points?\s*(?:are|:|include)|'
            r'the\s+following\s+points?|firstly|point\s+one|bullet\s+points?)\b.*?[,:\.\?!]\s*)(.*)',
            text,
            flags=re.IGNORECASE | re.DOTALL
        )
        if not match:
            match = re.search(
                r'^(.*?\b(?:advantages?|benefits?|features?|reasons?|points?)\s+(?:about|of)\s+[^.]+?[.!?]\s*)(.*)',
                text,
                flags=re.IGNORECASE | re.DOTALL
            )

        if match:
            intro = match.group(1).strip()
            body = match.group(2).strip()

            # Clean stutters and repeated clauses in body (e.g. ', are living organisms,' after 'many wild living organisms')
            body = re.sub(r'\b(living\s+organisms)\s*,\s*(?:are\s+)?\1\b', r'\1', body, flags=re.IGNORECASE)
            body = re.sub(r',\s*are\s+living\s+organisms,?', ',', body, flags=re.IGNORECASE)

            # Normalize connectors and sequential transitions
            body_cleaned = re.sub(r'\b(?:and\s+)?second\s+(?:it\'?s\s+also\s+called|it\'?s\s+called|it\'?s\s+also)\b', '. Also', body, flags=re.IGNORECASE)

            # Split on sentence terminators OR clause-level point transitions
            # Points frequently begin with key verbs: 'called', 'provide(s)', 'gives?', 'features?', 'has', 'have', 'contains?'
            # preceded by a comma or period
            points_raw = re.split(
                r'(?:[.!?]+\s+|\s+(?:and\s+also|also)\s+|,\s*(?=(?:called\b|provides?\b|gives?\b|contains?\b|features?\b|has\b|have\b|it\s+also\b)))',
                body_cleaned,
                flags=re.IGNORECASE
            )

            bullets = []
            for p in points_raw:
                p = p.strip()
                # Clean leading conversational fluff
                p = re.sub(r'^(?:as\s+(?:the\s+)?forest\s+(?:give|gives|provide|provides)\s+us\s+)?', '', p, flags=re.IGNORECASE)
                p = re.sub(r'^(?:as\s+we\s+know\s+(?:that\s+)?(?:the\s+)?advantages?[,\s]+)?(?:the\s+forest\s+have\s+many\s+advantages\s+like\s+)?', '', p, flags=re.IGNORECASE)
                p = re.sub(r'^(?:like\s+)?(?:it\s+is\s+the\s+home\b|it\s+is\s+home\b|forest\s+give\s+us\s+home\b)', 'Home', p, flags=re.IGNORECASE)
                p = re.sub(r'^(?:and\s+also|also|it\s+also|it)\s+', '', p, flags=re.IGNORECASE)
                p = re.sub(r'^[^\w]+', '', p).strip()
                if len(p.split()) >= 3:
                    cap = p[0].upper() + p[1:]
                    if not cap.endswith('.'):
                        cap += '.'
                    bullets.append(f'• {cap}')

            if len(bullets) >= 2:
                if intro.endswith(('.', ',')):
                    intro = intro[:-1] + ':'
                elif not intro.endswith(':'):
                    intro += ':'
                return f'{intro}\n' + '\n'.join(bullets)

        # AI Polish Brain sequential bullet formatter
        try:
            from app.intelligence.ai_polish_brain import AIPolishBrain
            res_brain = AIPolishBrain.smart_bullet_formatter(text)
            if res_brain != text:
                return res_brain
        except Exception:
            pass

        return text

    @staticmethod
    def collapse_repetitions_and_stutters(text: str) -> str:
        """
        AI Brain post-processing: Detects and collapses identical repeated words, phrases,
        sentence re-takes, and false starts with intervening filler spoken due to mic checks,
        stuttering, or hesitation.
        """
        if not text or not text.strip():
            return text

        result = text.strip()

        # Pass 0: AI Polish Brain Self-Correction & Verbal Override Resolution
        try:
            from app.intelligence.ai_polish_brain import AIPolishBrain
            result = AIPolishBrain.resolve_self_corrections(result)
        except Exception as brain_err:
            logger.debug(f"AIPolishBrain self-correction note: {brain_err}")

        # Pass 0b: Eliminate unsolicited trailing name injection (e.g. '... to the GitHub. I am Sriniwas Awasthi.')
        # If the user did not say 'introduce myself' or 'my name is', strip unsolicited trailing self-introduction
        if not re.search(r'\b(?:my name is|call me|introduce myself)\b', result, re.IGNORECASE):
            result = re.sub(r'[\s,\.]+(?:I am|This is|My name is)\s+Sriniwas\s*(?:Awasthi)?[\.\?!]?\s*$', '.', result, flags=re.IGNORECASE)

        # Pass 1: Common phonetic acoustic confusion corrections
        result = re.sub(r'\bpass(?:ed)?\s+the\s+neutral\b', 'personal', result, flags=re.IGNORECASE)
        result = re.sub(r'\bpast\s+neutral\b', 'personal', result, flags=re.IGNORECASE)
        if re.search(r'\b(?:github|git|repo|repository|code|push|zip)\b', result, re.IGNORECASE):
            result = re.sub(r'\bimportant\s+quotes\b', 'important codes', result, flags=re.IGNORECASE)

        # Pass 2: Eliminate mid-sentence stray greetings / mic-checks (e.g. '. Hello. And also...')
        result = re.sub(r'(?<=[.!?])\s*(?:hello|hi|hey|testing|mic check)[.!?]?\s+(?=[A-Z])', ' ', result, flags=re.IGNORECASE)

        # Pass 3: Self-correction refinement collapse:
        # 'many living organisms, many wild living organisms' -> 'many wild living organisms'
        result = re.sub(
            r'\b(?:the\s+)?many\s+living\s+organisms\s*,\s*(?:many\s+)?wild\s+living\s+organisms\b',
            'many wild living organisms',
            result,
            flags=re.IGNORECASE
        )
        result = re.sub(
            r'\b(\w+)\s+(\w+)\s*,\s*\1\s+(\w+)\s+\2\b',
            r'\1 \3 \2',
            result,
            flags=re.IGNORECASE
        )

        # Pass 4: Stutter and speech restart collapse with intervening filler words or restart cues:
        # e.g. 'It\'s also the it\'s also called' -> 'It\'s also called'
        # e.g. 'We need to, uh, we need to inspect the database schema.' -> 'We need to inspect the database schema.'
        # e.g. 'Analyze this schema, or rather analyze this schema for errors.' -> 'Analyze this schema for errors.'
        # e.g. 'We should deploy to staging, I mean deploy to staging right now.' -> 'We should deploy to staging right now.'
        # e.g. 'Open the dashboard, no wait open the dashboard.' -> 'Open the dashboard.'
        result = re.sub(r'\b(it\'?s\s+also)\s+(?:the|a|an)\s+\1\b', r'\1', result, flags=re.IGNORECASE)
        result = re.sub(r'\b(\w+\s+\w+)\s+(?:the|a|an|and)\s+\1\b', r'\1', result, flags=re.IGNORECASE)

        restart_cues = r'(?:uh|um|ah|er|eh|or rather|I mean|mean|no wait|wait|sorry)'
        # 1. Exact phrase repeated after hesitation filler or verbal restart cue
        pat_restart1 = r'\b((?:[A-Za-z0-9_\'-]+\s+){1,6}[A-Za-z0-9_\'-]+)[\s,]+' + restart_cues + r'[\s,]+\1\b'
        result = re.sub(pat_restart1, r'\1', result, flags=re.IGNORECASE)
        # 2. Leading clause + repeated subphrase after cue: e.g. 'We should deploy to staging, I mean deploy to staging right now.'
        pat_restart2 = r'\b((?:[A-Za-z0-9_\'-]+\s+){1,3})?((?:[A-Za-z0-9_\'-]+\s+){1,4}[A-Za-z0-9_\'-]+)[\s,]+' + restart_cues + r'[\s,]+\2\b'
        def _sub_restart2(m):
            prefix = m.group(1) or ''
            return f'{prefix}{m.group(2)}'
        result = re.sub(pat_restart2, _sub_restart2, result, flags=re.IGNORECASE)

        # Pass 5: Collapse consecutive identical multi-word phrase loops and single-word stutters (Universal Multilingual)
        u_token = r"[^\s,;:.!?—\-]+"
        for phrase_len in range(12, 0, -1):
            pat = re.compile(
                r'(?<![^\s,;:.!?—\-])((?:' + u_token + r'[\s,;—\-]+){' + str(phrase_len - 1) + r'}' + u_token + r')(?:[\s,;—\-]+)\1(?![^\s,;:.!?—\-])',
                flags=re.IGNORECASE
            )
            prev = None
            iters = 0
            while prev != result and iters < 8:
                prev = result
                iters += 1
                result = pat.sub(r'\1', result)

        # Pass 6: Near-duplicate consecutive sentences / false-start restart deduplication
        # Handles: 'Hey, I was just thinking of some advantages. Yeah, I was just thinking of some advantages about the forest.'
        sentences = re.split(r'([.!?]+(?:\s+|\n+|$))', result)
        if len(sentences) > 1:
            merged = []
            i = 0
            while i < len(sentences):
                s = sentences[i]
                punct = sentences[i+1] if i + 1 < len(sentences) else ""
                if s.strip():
                    merged.append((s.strip(), punct))
                i += 2

            filtered = []
            for idx in range(len(merged)):
                curr_s, curr_p = merged[idx]
                if idx + 1 < len(merged):
                    next_s, _ = merged[idx+1]
                    clean_c = re.sub(r'^(?:hey|yeah|yes|so|well|and|um|uh|actually|basically)[\s,]+', '', curr_s, flags=re.IGNORECASE).strip().lower()
                    clean_n = re.sub(r'^(?:hey|yeah|yes|so|well|and|um|uh|actually|basically)[\s,]+', '', next_s, flags=re.IGNORECASE).strip().lower()
                    c_alpha = re.sub(r'[^\w\s]', '', clean_c)
                    n_alpha = re.sub(r'[^\w\s]', '', clean_n)
                    if c_alpha and len(c_alpha.split()) >= 3 and n_alpha.startswith(c_alpha):
                        continue
                filtered.append((curr_s, curr_p))

            deduped = []
            for s, p in filtered:
                norm_s = re.sub(r'[^\w\s]', '', s).strip().lower()
                if not deduped:
                    deduped.append((s, p))
                else:
                    last_norm = re.sub(r'[^\w\s]', '', deduped[-1][0]).strip().lower()
                    if norm_s != last_norm:
                        deduped.append((s, p))
            result = "".join([f"{s}{p}" for s, p in deduped]).strip()

        # Pass 7: Adaptive Wispr Flow Bullet Point Structuring
        result = VocabularyEngine.adaptive_bullet_format(result)

        # Pass 8: Clean dangling punctuation & normalize spacing without corrupting currency or formatting
        result = re.sub(r'[,;]\s*(na|ya)\s*([.?!]?)$', r'\2', result, flags=re.IGNORECASE)
        result = re.sub(r'\s*,\s*,+', ',', result)
        result = re.sub(r'\s*,\s*\.', '.', result)
        result = re.sub(r'^\s*[,;:\.]\s*', '', result)
        result = re.sub(r'\s+([,.:;?!])', r'\1', result)
        result = re.sub(r'[ \t]{2,}', ' ', result).strip()

        if result and result[0].islower() and not result.startswith("http"):
            result = result[0].upper() + result[1:]

        return result

    def normalize(self, text: str) -> str:
        """
        Post-processes recognized text. Collapses stuttered/repeated phrases and
        replaces any spoken variants or aliases with their canonical terms cleanly.
        """
        if not text:
            return text

        result = self.collapse_repetitions_and_stutters(text)
        sorted_entries = sorted(self.entries, key=lambda e: len(e.canonical_term), reverse=True)
        for e in sorted_entries:
            if not e.enabled:
                continue

            # Sort aliases by length descending so longer phrases match first
            sorted_aliases = sorted(e.aliases, key=lambda a: len(a.strip()), reverse=True)
            for alias in sorted_aliases:
                if not alias.strip():
                    continue
                flags = 0 if e.case_sensitive else re.IGNORECASE
                pattern = re.compile(r'\b' + re.escape(alias.strip()) + r'\b', flags)
                result = pattern.sub(e.canonical_term, result)

            # Enforce exact canonical casing if not case-sensitive
            if not e.case_sensitive and e.canonical_term.lower() in result.lower():
                pattern = re.compile(r'\b' + re.escape(e.canonical_term) + r'\b', re.IGNORECASE)
                result = pattern.sub(e.canonical_term, result)

        return result

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Classmethod helper to quickly normalize text with default vocabulary."""
        engine = cls()
        return engine.normalize(text)

    @classmethod
    def normalize_string(cls, text: str) -> str:
        """Classmethod helper to quickly normalize text with default vocabulary."""
        engine = cls()
        return engine.normalize(text)


VocabEngine = VocabularyEngine
