"""
Application-Aware Intelligence for Gemini Flow.
Detects the active foreground workspace and provides contextual formatting directives,
tone guidelines, vocabulary priorities, and model routing biases.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger("GeminiFlow.AppIntelligence")


@dataclass
class AppContext:
    app_name: str
    category: str           # "dev", "communication", "email", "writing", "browser", "general", "ai_chat"
    preferred_model: str    # Model routing recommendation
    tone_directive: str     # Context prompt instruction
    formatting_directive: str
    vocabulary_priorities: List[str] = field(default_factory=list)
    icon: str = "🖥️"
    is_prompt_interface: bool = False

    @property
    def system_prompt_addition(self) -> str:
        return f"Tone: {self.tone_directive}\nFormatting: {self.formatting_directive}"


APP_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Developer Environments / IDEs & AI Prompt Interfaces
    "antigravity": {
        "canonical_name": "Antigravity",
        "category": "dev",
        "preferred_model": "gemini-3.5-flash-lite",
        "tone_directive": "Technical, precise, and direct developer style.",
        "formatting_directive": "Accurate verbatim speech transcription with proper punctuation, sentence casing, and clean programming terms.",
        "vocabulary_priorities": ["Programming", "Technical"],
        "icon": "🚀",
        "is_prompt_interface": True
    },
    "chatgpt": {
        "canonical_name": "ChatGPT",
        "category": "ai_chat",
        "preferred_model": "gemini-3.5-flash",
        "tone_directive": "Clear, precise conversational and instruction style.",
        "formatting_directive": "Accurate verbatim speech transcription with clean sentence structure and proper punctuation.",
        "vocabulary_priorities": ["Technical", "Prompting"],
        "icon": "🤖",
        "is_prompt_interface": True
    },
    "claude": {
        "canonical_name": "Claude AI",
        "category": "ai_chat",
        "preferred_model": "gemini-3.5-flash",
        "tone_directive": "Structured, articulate instruction style.",
        "formatting_directive": "Accurate verbatim speech transcription with clean sentence structure and proper punctuation.",
        "vocabulary_priorities": ["Technical", "Prompting"],
        "icon": "🧠",
        "is_prompt_interface": True
    },
    "perplexity": {
        "canonical_name": "Perplexity",
        "category": "ai_chat",
        "preferred_model": "gemini-3.5-flash-lite",
        "tone_directive": "Sharp, concise search and query style.",
        "formatting_directive": "Accurate speech transcription with proper punctuation.",
        "vocabulary_priorities": ["General"],
        "icon": "🔍",
        "is_prompt_interface": True
    },
    "vs code": {
        "canonical_name": "VS Code",
        "category": "dev",
        "preferred_model": "gemini-3.7-flash",
        "tone_directive": "Technical, precise, and developer-oriented.",
        "formatting_directive": "Accurate verbatim speech transcription with proper punctuation, clean programming terms, and syntax.",
        "vocabulary_priorities": ["Programming", "Technical"],
        "icon": "💻",
        "is_prompt_interface": True
    },
    "code": {
        "canonical_name": "VS Code",
        "category": "dev",
        "preferred_model": "gemini-3.7-flash",
        "tone_directive": "Technical, precise, and developer-oriented.",
        "formatting_directive": "Accurate verbatim speech transcription with proper punctuation, clean programming terms, and syntax.",
        "vocabulary_priorities": ["Programming", "Technical"],
        "icon": "💻",
        "is_prompt_interface": True
    },
    "cursor": {
        "canonical_name": "Cursor",
        "category": "dev",
        "preferred_model": "gemini-3.7-flash",
        "tone_directive": "Technical, precise coding instruction style.",
        "formatting_directive": "Accurate verbatim speech transcription with proper punctuation and clean code terminology.",
        "vocabulary_priorities": ["Programming", "Technical"],
        "icon": "⚡",
        "is_prompt_interface": True
    },
    "windsurf": {
        "canonical_name": "Windsurf",
        "category": "dev",
        "preferred_model": "gemini-3.7-flash",
        "tone_directive": "Technical, precise coding instruction style.",
        "formatting_directive": "Accurate verbatim speech transcription with proper punctuation and clean code terminology.",
        "vocabulary_priorities": ["Programming", "Technical"],
        "icon": "🏄",
        "is_prompt_interface": True
    },
    "cline": {
        "canonical_name": "Cline AI",
        "category": "dev",
        "preferred_model": "gemini-3.7-flash",
        "tone_directive": "Technical, autonomous AI coding instruction style.",
        "formatting_directive": "Accurate verbatim speech transcription with proper punctuation and clean code terminology.",
        "vocabulary_priorities": ["Programming", "Technical"],
        "icon": "🤖",
        "is_prompt_interface": True
    },
    "continue": {
        "canonical_name": "Continue AI",
        "category": "dev",
        "preferred_model": "gemini-3.7-flash",
        "tone_directive": "Clear, precise developer instructions.",
        "formatting_directive": "Accurate verbatim speech transcription with proper punctuation.",
        "vocabulary_priorities": ["Programming", "Technical"],
        "icon": "⏩",
        "is_prompt_interface": True
    },
    "zed": {
        "canonical_name": "Zed Editor",
        "category": "dev",
        "preferred_model": "gemini-3.7-flash",
        "tone_directive": "Technical, precise developer style.",
        "formatting_directive": "Accurate verbatim speech transcription with proper punctuation.",
        "vocabulary_priorities": ["Programming", "Technical"],
        "icon": "⚡",
        "is_prompt_interface": True
    },
    "visual studio": {
        "canonical_name": "Visual Studio",
        "category": "dev",
        "preferred_model": "gemini-3.7-flash",
        "tone_directive": "Technical, precise C#/C++ and .NET software engineering style.",
        "formatting_directive": "Clean developer casing and indentation. Wrap syntax in code blocks.",
        "vocabulary_priorities": ["Programming", "Technical"],
        "icon": "💻"
    },
    "pycharm": {
        "canonical_name": "PyCharm",
        "category": "dev",
        "preferred_model": "gemini-3.7-flash",
        "tone_directive": "Pythonic, concise, developer style. Respect PEP8 naming conventions.",
        "formatting_directive": "Format Python functions and variables in snake_case. Clean docstring formatting.",
        "vocabulary_priorities": ["Programming", "Technical"],
        "icon": "🐍"
    },
    "terminal": {
        "canonical_name": "Terminal",
        "category": "dev",
        "preferred_model": "gemini-3.7-flash",
        "tone_directive": "Direct CLI command and shell script style. No conversational fluff.",
        "formatting_directive": "Format flags (e.g. --flag), paths, and Unix/PowerShell commands cleanly on one line.",
        "vocabulary_priorities": ["Technical", "Programming"],
        "icon": "⚡"
    },

    # 2. Email Clients
    "gmail": {
        "canonical_name": "Gmail",
        "category": "email",
        "preferred_model": "gemini-3.5-flash",
        "tone_directive": "Professional, courteous, and clear email correspondence.",
        "formatting_directive": "Organize into natural email paragraphs with polite opening salutation and professional sign-off if dictated.",
        "vocabulary_priorities": ["Personal", "Custom"],
        "icon": "✉️"
    },
    "microsoft outlook": {
        "canonical_name": "Microsoft Outlook",
        "category": "email",
        "preferred_model": "gemini-3.5-flash",
        "tone_directive": "Corporate executive email style. Crisp, polished, and courteous.",
        "formatting_directive": "Clean business paragraphs, bullet points for action items, polite closing.",
        "vocabulary_priorities": ["Personal", "Project"],
        "icon": "✉️"
    },

    # 3. Real-Time Chat & Collaboration
    "whatsapp": {
        "canonical_name": "WhatsApp",
        "category": "communication",
        "preferred_model": "gemini-3.5-flash-lite",
        "tone_directive": "Natural, direct, conversational chat messaging.",
        "formatting_directive": "Concise sentences without overly stiff corporate boilerplate.",
        "vocabulary_priorities": ["Personal"],
        "icon": "💬"
    },
    "slack": {
        "canonical_name": "Slack",
        "category": "communication",
        "preferred_model": "gemini-3.5-flash-lite",
        "tone_directive": "Collaborative, crisp workplace chat. Friendly yet productive.",
        "formatting_directive": "Use bullet points or bold keys if listing items. Keep messages compact.",
        "vocabulary_priorities": ["Project", "Technical"],
        "icon": "💬"
    },
    "discord": {
        "canonical_name": "Discord",
        "category": "communication",
        "preferred_model": "gemini-3.5-flash-lite",
        "tone_directive": "Casual, friendly, community conversation.",
        "formatting_directive": "Natural phrasing and direct style.",
        "vocabulary_priorities": ["Custom"],
        "icon": "💬"
    },

    # 4. Code Repository / Review (GitHub / GitLab)
    "github": {
        "canonical_name": "GitHub",
        "category": "dev",
        "preferred_model": "gemini-3.7-flash",
        "tone_directive": "Clear open-source software engineering style. Structured and constructive.",
        "formatting_directive": "Markdown-compatible formatting with headers (###), checklists (- [ ]), and code backticks for commit IDs and file paths.",
        "vocabulary_priorities": ["Technical", "Programming", "Project"],
        "icon": "🐙"
    },

    # 5. Documents & Note-Taking
    "microsoft word": {
        "canonical_name": "Microsoft Word",
        "category": "writing",
        "preferred_model": "gemini-2.5-pro",
        "tone_directive": "Formal, articulate, and grammatically impeccable prose.",
        "formatting_directive": "Full paragraphs, rich punctuation balance, and structured sections.",
        "vocabulary_priorities": ["Academic", "Personal"],
        "icon": "📄"
    },
    "notion": {
        "canonical_name": "Notion",
        "category": "writing",
        "preferred_model": "gemini-3.5-flash",
        "tone_directive": "Structured knowledge base and product management style.",
        "formatting_directive": "Markdown headers, checklists, and bulleted takeaways.",
        "vocabulary_priorities": ["Project", "Technical"],
        "icon": "📝"
    },
    "notepad": {
        "canonical_name": "Notepad",
        "category": "writing",
        "preferred_model": "gemini-3.5-flash-lite",
        "tone_directive": "Clean, unpretentious plain text notes.",
        "formatting_directive": "Direct transcription with essential punctuation.",
        "vocabulary_priorities": ["Custom"],
        "icon": "📝"
    }
}


class AppIntelligenceManager:
    """Resolves active application context and generates tailored prompting directives."""
    def __init__(self):
        self.registry = APP_REGISTRY

    def resolve_context(self, raw_app_name: str, window_title: str = "") -> AppContext:
        """Maps detected application name and window title to structured AppContext."""
        app_clean = (raw_app_name or "General").strip().lower()
        title_clean = (window_title or "").strip().lower()

        # 1. Antigravity IDE / Desktop Detection
        if "antigravity" in app_clean or "antigravity" in title_clean or "integrator" in app_clean or "integrator" in title_clean:
            cfg = self.registry["antigravity"]
            return AppContext(
                app_name="Antigravity",
                category=cfg["category"],
                preferred_model=cfg["preferred_model"],
                tone_directive=cfg["tone_directive"],
                formatting_directive=cfg["formatting_directive"],
                vocabulary_priorities=cfg["vocabulary_priorities"],
                icon=cfg["icon"],
                is_prompt_interface=True
            )

        # 2. VS Code & Modern Code Editors (Direct AI Prompt Conversion)
        if (
            "vs code" in app_clean
            or "vs code" in title_clean
            or "bs code" in app_clean
            or "bs code" in title_clean
            or "visual studio code" in app_clean
            or "visual studio code" in title_clean
            or app_clean == "code.exe"
            or app_clean == "code"
            or app_clean.startswith("code")
        ):
            cfg = self.registry.get("vs code", self.registry["antigravity"])
            return AppContext(
                app_name="VS Code",
                category="dev",
                preferred_model="gemini-3.7-flash",
                tone_directive=cfg["tone_directive"],
                formatting_directive=cfg["formatting_directive"],
                vocabulary_priorities=cfg.get("vocabulary_priorities", ["Programming", "Technical"]),
                icon="💻",
                is_prompt_interface=True
            )

        # 3. Cursor, Windsurf & AI Agent Coding Environments
        if "cursor" in app_clean or "cursor" in title_clean:
            cfg = self.registry.get("cursor", self.registry["antigravity"])
            return AppContext(
                app_name="Cursor",
                category="dev",
                preferred_model="gemini-3.7-flash",
                tone_directive=cfg["tone_directive"],
                formatting_directive=cfg["formatting_directive"],
                vocabulary_priorities=cfg.get("vocabulary_priorities", ["Programming", "Technical"]),
                icon="⚡",
                is_prompt_interface=True
            )

        if "windsurf" in app_clean or "windsurf" in title_clean:
            cfg = self.registry.get("windsurf", self.registry["antigravity"])
            return AppContext(
                app_name="Windsurf",
                category="dev",
                preferred_model="gemini-3.7-flash",
                tone_directive=cfg["tone_directive"],
                formatting_directive=cfg["formatting_directive"],
                vocabulary_priorities=cfg.get("vocabulary_priorities", ["Programming", "Technical"]),
                icon="🏄",
                is_prompt_interface=True
            )

        if "cline" in app_clean or "cline" in title_clean:
            cfg = self.registry.get("cline", self.registry["antigravity"])
            return AppContext(
                app_name="Cline AI",
                category="dev",
                preferred_model="gemini-3.7-flash",
                tone_directive=cfg["tone_directive"],
                formatting_directive=cfg["formatting_directive"],
                vocabulary_priorities=cfg.get("vocabulary_priorities", ["Programming", "Technical"]),
                icon="🤖",
                is_prompt_interface=True
            )

        if "continue" in app_clean or "continue" in title_clean:
            cfg = self.registry.get("continue", self.registry["antigravity"])
            return AppContext(
                app_name="Continue AI",
                category="dev",
                preferred_model="gemini-3.7-flash",
                tone_directive=cfg["tone_directive"],
                formatting_directive=cfg["formatting_directive"],
                vocabulary_priorities=cfg.get("vocabulary_priorities", ["Programming", "Technical"]),
                icon="⏩",
                is_prompt_interface=True
            )

        if "zed" in app_clean or "zed" in title_clean:
            cfg = self.registry.get("zed", self.registry["antigravity"])
            return AppContext(
                app_name="Zed",
                category="dev",
                preferred_model="gemini-3.7-flash",
                tone_directive=cfg["tone_directive"],
                formatting_directive=cfg["formatting_directive"],
                vocabulary_priorities=cfg.get("vocabulary_priorities", ["Programming", "Technical"]),
                icon="⚡",
                is_prompt_interface=True
            )

        # 4. AI Chat & Prompt-Generation Interfaces
        for ai_key in ("chatgpt", "claude", "gemini", "perplexity", "copilot", "poe.com", "mistral", "deepseek", "aistudio", "roo-code", "roo code", "aider"):
            if ai_key in title_clean or ai_key in app_clean:
                cfg = self.registry.get(ai_key, self.registry["chatgpt"])
                return AppContext(
                    app_name=cfg.get("canonical_name", ai_key.capitalize()),
                    category="ai_chat",
                    preferred_model=cfg.get("preferred_model", "gemini-3.5-flash"),
                    tone_directive="Clear, high-impact prompt engineering style.",
                    formatting_directive="Structure spoken thoughts directly into high-impact AI prompts.",
                    vocabulary_priorities=cfg.get("vocabulary_priorities", ["Technical", "Prompting"]),
                    icon=cfg.get("icon", "🤖"),
                    is_prompt_interface=True
                )

        # 3. Check GitHub in browser
        if "github" in title_clean or "github" in app_clean:
            cfg = self.registry["github"]
            return AppContext(
                app_name="GitHub",
                category=cfg["category"],
                preferred_model=cfg["preferred_model"],
                tone_directive=cfg["tone_directive"],
                formatting_directive=cfg["formatting_directive"],
                vocabulary_priorities=cfg["vocabulary_priorities"],
                icon=cfg["icon"],
                is_prompt_interface=False
            )

        # 4. Check Gmail in browser
        if "gmail" in title_clean or "mail" in title_clean:
            cfg = self.registry["gmail"]
            return AppContext(
                app_name="Gmail",
                category=cfg["category"],
                preferred_model=cfg["preferred_model"],
                tone_directive=cfg["tone_directive"],
                formatting_directive=cfg["formatting_directive"],
                vocabulary_priorities=cfg["vocabulary_priorities"],
                icon=cfg["icon"],
                is_prompt_interface=False
            )

        # 5. Check registry match
        for key, cfg in self.registry.items():
            if key in app_clean or app_clean in key:
                return AppContext(
                    app_name=cfg["canonical_name"],
                    category=cfg["category"],
                    preferred_model=cfg["preferred_model"],
                    tone_directive=cfg["tone_directive"],
                    formatting_directive=cfg["formatting_directive"],
                    vocabulary_priorities=cfg["vocabulary_priorities"],
                    icon=cfg["icon"],
                    is_prompt_interface=cfg.get("is_prompt_interface", False)
                )

        # Fallback General Context
        return AppContext(
            app_name=raw_app_name or "General",
            category="general",
            preferred_model="gemini-3.5-flash",
            tone_directive="Clear, natural, and helpful.",
            formatting_directive="Standard punctuation and sentence structure.",
            vocabulary_priorities=["Personal", "Custom"],
            icon="🖥️"
        )

    def get_prompt_directives(self, context: AppContext) -> str:
        """Returns the system prompt block representing application context."""
        return (
            f"\n\nActive Application Context ({context.icon} {context.app_name} - {context.category.upper()}):\n"
            f"- Tone: {context.tone_directive}\n"
            f"- Formatting: {context.formatting_directive}\n"
        )

    @classmethod
    def get_active_app_context(cls) -> AppContext:
        """Helper to get context for the currently active foreground window in Windows."""
        raw_app_name = "General"
        window_title = ""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                # Window title
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    window_title = buf.value

                # Process executable name
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value:
                    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                    kernel32 = ctypes.windll.kernel32
                    hproc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
                    if hproc:
                        pbuf = ctypes.create_unicode_buffer(1024)
                        size = ctypes.c_ulong(1024)
                        if kernel32.QueryFullProcessImageNameW(hproc, 0, pbuf, ctypes.byref(size)):
                            raw_app_name = pbuf.value.split('\\')[-1].lower()
                        kernel32.CloseHandle(hproc)
        except Exception:
            pass

        mgr = cls()
        return mgr.resolve_context(raw_app_name, window_title)


AppIntelligenceEngine = AppIntelligenceManager
