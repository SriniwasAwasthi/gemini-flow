"""
Developer Productivity Profiles Manager for Gemini Flow.
Provides domain-specific tuning, prompt augmentation, vocabulary prioritisation,
and preferred model routing for Engineering, Coding, Professional, Academic, and Casual workflows.
"""
import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

from app.config import APP_DIR

logger = logging.getLogger("GeminiFlow.Profiles")

PROFILES_FILE = os.path.join(str(APP_DIR), "profiles.json")


@dataclass
class Profile:
    id: str
    name: str
    description: str
    preferred_model: str
    system_prompt_addition: str
    vocabulary_categories: List[str] = field(default_factory=list)
    temperature: float = 0.2
    is_builtin: bool = False
    icon: str = "⚡"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profile":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            preferred_model=data.get("preferred_model", "gemini-3.5-flash"),
            system_prompt_addition=data.get("system_prompt_addition", ""),
            vocabulary_categories=data.get("vocabulary_categories", []),
            temperature=float(data.get("temperature", 0.2)),
            is_builtin=bool(data.get("is_builtin", False)),
            icon=data.get("icon", "⚡")
        )


BUILTIN_PROFILES: Dict[str, Profile] = {
    "engineering": Profile(
        id="engineering",
        name="Engineering & Architecture",
        description="Optimized for system design, cloud infrastructure, schemas, and trade-off analysis.",
        preferred_model="gemini-2.5-pro",
        system_prompt_addition=(
            "You are an expert Principal Systems Architect. Use rigorous technical terminology, "
            "clear architectural trade-offs, and structured formats. Emphasize scalability, reliability, "
            "and security best practices."
        ),
        vocabulary_categories=["Architecture", "Cloud", "Programming", "Database"],
        temperature=0.2,
        is_builtin=True,
        icon="🏗️"
    ),
    "coding": Profile(
        id="coding",
        name="Coding & Development",
        description="Fine-tuned for code generation, PR descriptions, commit messages, and debugging.",
        preferred_model="gemini-3.7-flash",
        system_prompt_addition=(
            "You are a Senior Staff Software Engineer. Write idiomatic, clean, and bug-free code. "
            "Format identifiers correctly (camelCase, snake_case, PascalCase). Keep explanatory prose "
            "concise and focused on engineering rationale."
        ),
        vocabulary_categories=["Programming", "Git", "Frameworks", "DevOps"],
        temperature=0.1,
        is_builtin=True,
        icon="💻"
    ),
    "professional": Profile(
        id="professional",
        name="Professional & Executive",
        description="Tailored for executive memos, business emails, project updates, and proposals.",
        preferred_model="gemini-2.5-flash",
        system_prompt_addition=(
            "Adopt an articulate, executive, and diplomatic tone. Structure communications with clear "
            "action items, concise executive summaries, and eliminate all colloquialisms."
        ),
        vocabulary_categories=["Business", "Executive", "Management"],
        temperature=0.3,
        is_builtin=True,
        icon="👔"
    ),
    "academic": Profile(
        id="academic",
        name="Academic & Research",
        description="Structured for formal research papers, mathematical reasoning, and scientific prose.",
        preferred_model="gemini-2.5-pro",
        system_prompt_addition=(
            "Write in formal academic style with precise definitions, methodological rigor, "
            "and scholarly vocabulary. Clearly distinguish hypotheses, evidence, and conclusions."
        ),
        vocabulary_categories=["Science", "Research", "Mathematics"],
        temperature=0.2,
        is_builtin=True,
        icon="🎓"
    ),
    "casual": Profile(
        id="casual",
        name="Casual & Everyday Dictation",
        description="Fast, natural dictation for quick messages, Slack/WhatsApp, and stream-of-consciousness notes.",
        preferred_model="gemini-3.5-flash-lite",
        system_prompt_addition=(
            "Transcribe and polish conversationally. Keep the tone natural, warm, and authentic "
            "without over-formalizing everyday speech."
        ),
        vocabulary_categories=["General", "Conversational"],
        temperature=0.4,
        is_builtin=True,
        icon="☕"
    )
}


class BuiltinProfiles:
    ENGINEERING = "engineering"
    CODING = "coding"
    PROFESSIONAL = "professional"
    ACADEMIC = "academic"
    CASUAL = "casual"


class ProfileManager:
    """Manages profile loading, switching, and custom profile persistence."""

    def __init__(self, profiles_file: str = PROFILES_FILE):
        self.profiles_file = profiles_file
        self.profiles: Dict[str, Profile] = {}
        self.active_profile_id = BuiltinProfiles.CODING
        self.load_profiles()

    def load_profiles(self):
        """Loads built-ins plus user-defined custom profiles."""
        self.profiles = dict(BUILTIN_PROFILES)

        if os.path.exists(self.profiles_file):
            try:
                with open(self.profiles_file, "r", encoding="utf-8") as f:
                    custom_data = json.load(f)
                    for item in custom_data:
                        profile = Profile.from_dict(item)
                        profile.is_builtin = False
                        self.profiles[profile.id] = profile
                logger.info(f"Loaded {len(self.profiles)} profiles (including custom).")
            except Exception as e:
                logger.error(f"Error loading custom profiles: {e}")

    def save_custom_profiles(self):
        """Saves only custom (non-builtin) profiles to disk."""
        custom_list = [p.to_dict() for p in self.profiles.values() if not p.is_builtin]
        try:
            os.makedirs(os.path.dirname(self.profiles_file), exist_ok=True)
            with open(self.profiles_file, "w", encoding="utf-8") as f:
                json.dump(custom_list, f, indent=2)
            logger.info("Custom profiles saved successfully.")
        except Exception as e:
            logger.error(f"Error saving custom profiles: {e}")

    def get_all_profiles(self) -> List[Profile]:
        return list(self.profiles.values())

    def get_profile(self, profile_id: str) -> Optional[Profile]:
        return self.profiles.get(profile_id)

    def get_active_profile(self) -> Profile:
        return self.profiles.get(self.active_profile_id, BUILTIN_PROFILES[BuiltinProfiles.CODING])

    def set_active_profile(self, profile_id: str) -> bool:
        if profile_id in self.profiles:
            self.active_profile_id = profile_id
            logger.info(f"Active profile switched to: {self.profiles[profile_id].name}")
            return True
        logger.warning(f"Profile {profile_id} not found.")
        return False

    def create_custom_profile(self, profile: Profile) -> bool:
        if not profile.id or profile.id in BUILTIN_PROFILES:
            return False
        profile.is_builtin = False
        self.profiles[profile.id] = profile
        self.save_custom_profiles()
        return True

    def delete_profile(self, profile_id: str) -> bool:
        if profile_id in BUILTIN_PROFILES or profile_id not in self.profiles:
            return False
        del self.profiles[profile_id]
        if self.active_profile_id == profile_id:
            self.active_profile_id = BuiltinProfiles.CODING
        self.save_custom_profiles()
        return True
