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
        "canonical_term": "Srinivas Awasthi",
        "aliases": ["Sriniwas Awasthi", "Sriniwas Awasti", "Srinivas Awasti", "Srinivas Avasthi", "Sriniwas"],
        "category": "Personal",
        "enabled": True,
        "notes": "Full user name"
    },
    {
        "canonical_term": "Wispr",
        "aliases": ["Wisper", "Whisper flow", "Wispr Flow"],
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
        canonical_term: str,
        aliases: Optional[List[str]] = None,
        category: str = "Custom",
        enabled: bool = True,
        case_sensitive: bool = False,
        notes: str = ""
    ) -> Optional[VocabularyEntry]:
        cleaned_term = canonical_term.strip()
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

    def delete_entry(self, entry_id: str) -> bool:
        initial = len(self.entries)
        self.entries = [e for e in self.entries if e.id != entry_id]
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
        Compiles active vocabulary terms and alias rules into a structured
        instruction for Gemini speech-to-text priming.
        """
        active = [e for e in self.entries if e.enabled]
        if not active:
            return ""

        # Group by category
        canonical_terms = [e.canonical_term for e in active]
        alias_rules = []
        for e in active:
            if e.aliases:
                aliases_str = ", ".join([f"'{a}'" for a in e.aliases])
                alias_rules.append(f"Aliases [{aliases_str}] -> Canonical '{e.canonical_term}'")

        injection = (
            "\n\nPersonal AI Vocabulary & Spelling Directives (Strict Enforcement):\n"
            f"- Prioritized terms & names: {', '.join(canonical_terms)}.\n"
        )
        if alias_rules:
            injection += "- Canonical Alias Normalization Rules:\n  * " + "\n  * ".join(alias_rules) + "\n"

        return injection

    def normalize(self, text: str) -> str:
        """
        Post-processes recognized text. Replaces any spoken variants or aliases
        with their canonical terms cleanly.
        """
        if not text:
            return text

        result = text
        for e in self.entries:
            if not e.enabled:
                continue

            # Replace aliases with canonical
            for alias in e.aliases:
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

    def normalize_text(self, text: str) -> str:
        """Instance method alias for normalize."""
        return self.normalize(text)

    @classmethod
    def normalize_string(cls, text: str) -> str:
        """Classmethod helper to quickly normalize text with default vocabulary."""
        engine = cls()
        return engine.normalize(text)


VocabEngine = VocabularyEngine
