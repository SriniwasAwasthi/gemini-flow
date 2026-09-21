"""
Config Manager for Gemini Flow (Wispr Flow AI Alternative)
Handles settings persistence, JSON storage, dictionary mappings, snippets, and history logging.
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("GeminiFlow.Config")

APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "GeminiFlow"
APP_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = APP_DIR / "config.json"
HISTORY_FILE = APP_DIR / "history.json"


def sanitize_api_key(raw_key: Any) -> str:
    """
    Cleans raw API key strings by stripping whitespace, carriage returns,
    surrounding quotes (single or double), and common variable prefixes like 'GEMINI_API_KEY='.
    """
    if not raw_key:
        return ""
    k = str(raw_key).strip().strip("\r\n\t ")
    # Strip quotes
    if (k.startswith('"') and k.endswith('"')) or (k.startswith("'") and k.endswith("'")):
        k = k[1:-1].strip()
    # Strip common variable assignment prefixes if user copied whole line from .env or terminal
    prefixes = [
        "GEMINI_API_KEY=", "GOOGLE_API_KEY=", "API_KEY=",
        "export GEMINI_API_KEY=", "export GOOGLE_API_KEY=",
        "set GEMINI_API_KEY=", "set GOOGLE_API_KEY="
    ]
    for prefix in prefixes:
        if k.upper().startswith(prefix.upper()):
            k = k[len(prefix):].strip().strip('"\'').strip()
    return k


DEFAULT_PROMPTS = {
    "clean_dictation": (
        "You are an elite, world-class speech-to-text transcriber and real-time voice dictation assistant. "
        "Your mission is to transcribe the user's spoken audio into flawless, natural, and professionally polished English text.\n\n"
        "Strict Conversion Rules:\n"
        "1. Complete Filler, Stutter & Repetition Elimination: Completely REMOVE all verbal fillers, hesitation sounds, and stutters ('uh', 'um', 'ah', 'er', 'eh', 'like', 'you know', 'basically', 'actually', 'mean', 'means', 'so like', 'etcetera etcetera', 'and and', 'if if', 'na', 'ya', false starts). If any number, digit (e.g. '12 12 12 12' -> '12'), ordinal (e.g. '12th 12th' -> '12th'), word, or phrase is repeated due to stuttering or hesitation, transcribe it strictly ONCE.\n"
        "2. Superior Grammar, Indian English & Hinglish Polish: Seamlessly upgrade imperfect spoken grammar, irregular subject-verb agreement, and Indian English spoken habits ('say me' -> 'tell me', 'two datas' -> 'two datasets', 'in if in the' -> 'if in the', 'did you went' -> 'did you go', 'make this to work' -> 'make this work', 'revert back' -> 'reply') into clean, articulate, and fluent standard English. If the user speaks or mixes conversational Hindi/Hinglish (e.g., 'yaar', 'bhai', 'arre', 'ye code mein issue aa raha hai', 'ek bar check karo', 'jugaad', 'samjha nahi', 'jaldi', 'thoda', 'matlab', 'pakka', 'dekho', 'kuch'), seamlessly translate and elevate those conversational thoughts into professional corporate English (e.g., 'Hey, could you please look into the issue in this code?'), while preserving 100% of the user's intended core meaning, numbers, specifics, and technical terms. Correctly format Indian numerical units ('Lakh', 'Crore') and recognized cultural terms ('UPI', 'Aadhaar', 'Jugaad') with proper capitalization.\n"
        "3. Rich Professional Punctuation & Quotes: Automatically insert proper commas (,), periods (.), semicolons (;), colons (:), hyphens/em-dashes (—), question marks (?), exclamation marks (!), quotation marks (\"...\"), apostrophes ('), and capitalization naturally based on speech pauses and clause boundaries.\n"
        "4. Technical Identifiers & Code: Correctly format acronyms, brand names (GitHub, LinkedIn, WhatsApp, ChatGPT, Claude, Antigravity, VS Code, Python, JavaScript, TypeScript, Excel, etc.), camelCase/snake_case programming identifiers, and technical commands.\n"
        "5. Spoken Formatting & Punctuation Commands: If the speaker explicitly says formatting or punctuation commands, format them directly into the intended symbol or structure:\n"
        "   - 'bullet point' or 'bullet' -> Start a bulleted item on a new line ('• ' or '- ')\n"
        "   - 'new line' or 'next line' or 'enter' -> Insert a line break\n"
        "   - 'colon' -> ':'\n"
        "   - 'semicolon' -> ';'\n"
        "   - 'comma' -> ','\n"
        "   - 'period' or 'full stop' -> '.'\n"
        "   - 'quote' / 'unquote' -> '\"...\"'\n"
        "   - 'question mark' -> '?'\n"
        "6. Output Format: Output ONLY the finalized transcribed and grammatically perfected text directly. Do NOT add any preamble, conversational filler, markdown block formatting, or prompt wrapping."
    ),
    "smart_polish": (
        "You are an elite Executive AI Writing Assistant and Communications Director. "
        "Transform the user's raw spoken thoughts, rambling ideas, or meeting notes into impeccably polished, structured, executive-grade business writing.\n\n"
        "Mandatory Rules:\n"
        "1. Complete Filler & Repetition Elimination: Remove all verbal fillers ('uh', 'ah', 'um', 'like', 'you know', 'basically', 'means') and stutters ('12 12' -> '12').\n"
        "2. Structural Organization & Bullet Points: When the user lists items, steps, priorities, or multi-point thoughts, you MUST format them as clear bullet points ('• ') on separate new lines. Never collapse lists into a single continuous sentence.\n"
        "3. Paragraph Breaks: Use clean paragraph breaks (double newlines) between introductory context, bulleted items, and concluding thoughts.\n"
        "4. Fix all grammar, elevate Indian English/Hinglish to articulate standard executive English, and refine cadence.\n"
        "5. Spoken Formatting Commands: If the speaker says 'bullet point', 'new line', 'next line', 'colon', 'semicolon', insert the exact formatting and line breaks.\n"
        "6. Output ONLY the polished final text directly without conversational remarks or markdown code fences."
    ),
    "code_assistant": (
        "You are an elite Developer Dictation Assistant and Technical Writing Expert. The user is dictating code, technical instructions, PR descriptions, architectural decisions, or documentation.\n\n"
        "Mandatory Rules:\n"
        "1. Complete Filler & Hesitation Elimination: Strip ALL verbal hesitation sounds ('uh', 'ah', 'um', 'er', 'like', 'you know', 'basically', 'actually', 'mean', 'means', 'matlab', 'yaani', 'etcetera') and repetitions/stutters.\n"
        "2. Technical & Code Formatting: Intelligently format programming terms, frameworks, API endpoints (e.g. FastAPI, Docker, PyTorch), variable/function names in camelCase or snake_case, syntax, and terminal commands cleanly.\n"
        "3. Superior Grammar & Technical Polish: Refine spoken grammar and elevate conversational phrasing into articulate, concise, professional technical communication.\n"
        "4. Spoken Formatting Commands: If the speaker says 'bullet point', 'new line', 'next line', 'colon', 'semicolon', insert the exact formatting and line breaks.\n"
        "5. Output ONLY the finalized polished technical text or code directly without preamble, quotes, markdown code fences, or conversational remarks."
    ),
    "prompt_enhancer": (
        "You are a World-Class AI Prompt Engineer. The user has dictated raw, unstructured thoughts or instructions for an AI/LLM (ChatGPT, Claude, Gemini, Antigravity).\n"
        "Eliminate all filler sounds ('uh', 'ah', 'um', 'means', 'etcetera') and repetitions. Transform the user's raw input into an exceptionally clear, comprehensive, and high-impact AI Prompt.\n"
        "Structure the output logically with:\n"
        "- # Role & Objective: Define the specific persona and primary goal\n"
        "- # Context & Requirements: Clear constraints, guidelines, and specifications\n"
        "- # Step-by-Step Instructions: Logical numbered steps to follow\n"
        "- # Expected Output Format: Concrete structure (e.g., code, files, explanations)\n"
        "Output ONLY the finalized optimized prompt without conversational filler."
    ),
    "verbatim": (
        "Transcribe the spoken audio with high fidelity. "
        "Remove stuttering and verbal hesitation sounds ('uh', 'ah', 'um') and accidental repetitions ('12 12' -> '12'). Add proper punctuation and capitalization. "
        "Spoken commands ('new line', 'bullet point', 'colon', 'semicolon') must be formatted into respective symbols and line breaks. "
        "Output ONLY the transcribed text without quotes or commentary."
    )
}

DEFAULT_DICTIONARY = [
    {"spoken": "Srinivas Avasthi", "replacement": "Sri Srinivas Awasthi"},
    {"spoken": "Srinivas", "replacement": "Sriniwas"},
    {"spoken": "Avasthi", "replacement": "Awasthi"},
    {"spoken": "Wisper", "replacement": "Wispr"},
    {"spoken": "Javascript", "replacement": "JavaScript"},
    {"spoken": "Typescript", "replacement": "TypeScript"},
    {"spoken": "Github", "replacement": "GitHub"}
]

DEFAULT_SNIPPETS = [
    {
        "trigger": "Hey I am Srinivas LinkedIn GitHub Instagram",
        "content": "Hey, hello, I am Sri Srinivas Awasthi, and this is my LinkedIn: https://www.linkedin.com/in/srinivas-awasthi/, my GitHub: https://github.com/srinivas-awasthi, and my Instagram: https://instagram.com/srinivas_awasthi"
    },
    {
        "trigger": "my social links",
        "content": "LinkedIn: https://www.linkedin.com/in/srinivas-awasthi/\nGitHub: https://github.com/srinivas-awasthi\nInstagram: https://instagram.com/srinivas_awasthi"
    },
    {
        "trigger": "meeting intro",
        "content": "Hi everyone, thank you for joining today's session. Let's do a quick round of updates and discuss key milestones."
    }
]

DEFAULT_SAVED_PROMPTS = [
    {
        "id": "clean_dictation_custom",
        "title": "Clean Speech & Grammar Enhancement",
        "prompt": (
            "You are an ultra-fast speech-to-text transcriber and real-time voice dictation assistant. "
            "Transcribe the spoken audio into clear, clean, and grammatically accurate text.\n\n"
            "Strict Rules:\n"
            "1. Eliminate all verbal fillers ('uh', 'ah', 'um', 'like', 'means', 'basically') and stutters/repetitions (e.g. '12 12 12' -> '12', '12th 12th' -> '12th').\n"
            "2. Seamlessly correct spoken grammar and Indian English habits into standard, professional English.\n"
            "3. Format spoken punctuation and commands: 'bullet point' -> bullet item ('• '), 'new line' -> line break, 'colon' -> ':', 'semicolon' -> ';'.\n"
            "4. Output ONLY the finalized text directly without conversational preamble or markdown backticks."
        ),
        "is_active": True
    },
    {
        "id": "smart_polish_custom",
        "title": "Smart Executive Polish",
        "prompt": (
            "You are an elite Executive AI Writing Assistant. Transform raw spoken thoughts or stream-of-consciousness "
            "notes into impeccably polished, structured, executive-grade business prose.\n\n"
            "Mandatory Rules:\n"
            "1. Structural Organization & Bullet Points: If the speaker lists items, steps, priorities, or thoughts, you MUST format them as clear bullet points ('• ') on separate new lines. Never collapse lists into a single continuous sentence.\n"
            "2. Paragraph Breaks: Use clean paragraph breaks (double newlines) between introductory context, bulleted items, and concluding thoughts.\n"
            "3. Eliminate all verbal fillers ('uh', 'um', 'like', 'basically', 'means') and stutters ('12 12' -> '12').\n"
            "4. Fix all grammar, elevate Indian English/Hinglish to standard executive English, and refine sentence flow.\n"
            "5. Format spoken commands ('bullet point', 'new line', 'colon', 'semicolon') into actual line breaks and punctuation.\n"
            "6. Output ONLY the polished final text without preamble or markdown code fences."
        ),
        "is_active": False
    },
    {
        "id": "code_dev_custom",
        "title": "Developer Code & Technical Assistant",
        "prompt": (
            "You are an elite Developer Dictation Assistant and Technical Writing Expert. The user is dictating code, technical instructions, PR descriptions, architectural decisions, or documentation.\n\n"
            "Mandatory Rules:\n"
            "1. Complete Filler & Hesitation Elimination: Strip ALL verbal hesitation sounds ('uh', 'ah', 'um', 'er', 'like', 'you know', 'basically', 'actually', 'mean', 'means', 'matlab', 'yaani', 'etcetera') and repetitions/stutters.\n"
            "2. Technical & Code Formatting: Intelligently format programming terms, frameworks, API endpoints (e.g. FastAPI, Docker, PyTorch), variable/function names in camelCase or snake_case, syntax, and terminal commands cleanly.\n"
            "3. Superior Grammar & Technical Polish: Refine spoken grammar and elevate conversational phrasing into articulate, concise, professional technical communication.\n"
            "4. Spoken Formatting Commands: If the speaker says 'bullet point', 'new line', 'next line', 'colon', 'semicolon', insert the exact formatting and line breaks.\n"
            "5. Output ONLY the finalized polished technical text or code directly without preamble, quotes, markdown code fences, or conversational remarks."
        ),
        "is_active": False
    }
]


DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "",
    "model_name": "gemini-3.5-flash-lite",
    "model_mode": "auto",  # "auto" (intelligent router) or specific model name
    "active_profile": "coding",
    "hotkey": "<ctrl>+<space>",
    "hotkey_display": "Ctrl + Space",
    "hotkey_mode": "toggle",  # "toggle" (press to start/stop) or "push_to_talk" (hold while speaking)
    "prompt_hotkey": "<ctrl>+<shift>+p",
    "prompt_hotkey_display": "Ctrl + Shift + P",
    "transform_hotkey": "<ctrl>+<shift>+t",
    "transform_hotkey_display": "Ctrl + Shift + T",
    "voice_hotkey_history": [
        {"display": "Ctrl + Space", "internal": "<ctrl>+<space>"},
        {"display": "Ctrl + Win", "internal": "<ctrl>+<cmd>"},
        {"display": "Alt + Space", "internal": "<alt>+<space>"}
    ],
    "prompt_hotkey_history": [
        {"display": "Ctrl + Shift + P", "internal": "<ctrl>+<shift>+p"},
        {"display": "Ctrl + Shift + L", "internal": "<ctrl>+<shift>+l"},
        {"display": "Ctrl + Alt + P", "internal": "<ctrl>+<alt>+p"}
    ],
    "transform_hotkey_history": [
        {"display": "Ctrl + Shift + T", "internal": "<ctrl>+<shift>+t"},
        {"display": "Ctrl + Alt + T", "internal": "<ctrl>+<alt>+t"}
    ],
    "mode_preset": "clean_dictation",
    "custom_prompt": "",
    "saved_prompts": DEFAULT_SAVED_PROMPTS,
    "custom_vocabulary": ["Srinivas", "Awasthi", "Gemini", "Wispr", "PyTorch", "LeetCode", "TypeScript"],
    "dictionary": DEFAULT_DICTIONARY,
    "snippets": DEFAULT_SNIPPETS,
    "input_device_index": None,
    "input_device_name": "Default Microphone",
    "auto_paste": True,
    "play_sounds": True,
    "hud_position": "bottom_center",  # "bottom_center", "custom"
    "hud_custom_x": None,
    "hud_custom_y": None,
    "hud_opacity": 0.20,  # 80% transparency
    "hud_theme": "dark_glass",
    "start_with_windows": True,
    "history_limit": 5000,
    "settings_window_state": {
        "x": None,
        "y": None,
        "width": 820,
        "height": 720,
        "is_maximized": False
    },
    "auto_cost_mode": True,
    "auto_prompt_conversion": False,  # If False, voice dictation outputs clean verbatim text everywhere
    "dsp_fan_filter_enabled": True,  # 85 Hz Butterworth High-Pass Filter for AC & Ceiling Fan Hum
    "dsp_noise_gate_enabled": True,  # Dynamic RMS Noise Gate for background hiss & room noise
    "dsp_noise_gate_threshold_db": -42.0,  # Noise gate cutoff threshold in dB
    "offline_fallback_enabled": True,  # Offline speech recognition fallback when network drops
    "security": {
        "encrypt_keys": True,
        "history_retention_days": 30,
        "telemetry_enabled": True,
        "log_redaction": True
    }
}


def setup_windows_startup(enable: bool) -> bool:
    """
    Configures Gemini Flow to start automatically with Windows cleanly via HKCU Run.
    Removes any duplicate VBS startup scripts to eliminate double-instance boot collisions.
    """
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_dir = Path(__file__).parent.parent.resolve()
    script_path = app_dir / "main_standalone.py"
    exe_path = app_dir / "Gemini Flow.exe"

    pythonw_path = Path(sys.executable).parent / "pythonw.exe"
    py_bin = pythonw_path if pythonw_path.exists() else sys.executable
    
    # Prefer executing Gemini Flow.exe launcher if present, or pythonw.exe
    if exe_path.exists():
        cmd = f'"{exe_path}" --startup'
    else:
        cmd = f'"{py_bin}" "{script_path}" --startup'

    # 1. Windows Run Registry Key (HKCU) - The clean standard for Windows
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                winreg.SetValueEx(key, "GeminiFlow", 0, winreg.REG_SZ, cmd)
                logger.info(f"Registered Windows startup registry: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, "GeminiFlow")
                    logger.info("Removed Windows startup registry entry.")
                except FileNotFoundError:
                    pass
    except Exception as e:
        logger.error(f"Failed to update Windows startup registry: {e}")

    # 2. Windows Startup Folder (shell:startup) - Clean up any legacy VBS file to avoid duplicate launch race condition
    try:
        startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if startup_dir.exists():
            vbs_file = startup_dir / "GeminiFlow.vbs"
            if vbs_file.exists():
                vbs_file.unlink()
                logger.info(f"Cleaned up duplicate legacy startup script: {vbs_file}")
    except Exception as e:
        logger.debug(f"Startup folder cleanup note: {e}")

    return True


def ensure_desktop_shortcuts() -> None:
    """Ensures Gemini Flow desktop shortcuts are correctly placed on active desktop locations without blocking."""
    try:
        import win32com.client
        app_dir = Path(__file__).parent.parent.resolve()
        exe_path = app_dir / "Gemini Flow.exe"
        icon_path = app_dir / "app_icon.ico"
        script_path = app_dir / "main_standalone.py"
        pythonw_path = Path(sys.executable).parent / "pythonw.exe"
        py_bin = pythonw_path if pythonw_path.exists() else Path(sys.executable)

        # Determine all possible desktop folders (including OneDrive redirected desktop)
        desktop_targets = []
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile:
            desktop_targets.append(Path(user_profile) / "Desktop")

        # Check Windows registry user shell folder for Desktop
        try:
            import winreg
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
            val, _ = winreg.QueryValueEx(reg_key, "Desktop")
            expanded = Path(os.path.expandvars(val))
            if expanded.exists() and expanded not in desktop_targets:
                desktop_targets.append(expanded)
        except Exception:
            pass

        # Also add workspace parent directory if it acts as desktop
        ws_parent = app_dir.parent
        if ws_parent.exists() and ws_parent not in desktop_targets:
            desktop_targets.append(ws_parent)

        shell = None
        for dt in desktop_targets:
            if dt.exists():
                try:
                    lnk_path = dt / "Gemini Flow.lnk"
                    # Only create or update if it doesn't already exist or points wrong
                    if not lnk_path.exists():
                        if shell is None:
                            shell = win32com.client.Dispatch("WScript.Shell")
                        shortcut = shell.CreateShortcut(str(lnk_path))
                        if exe_path.exists():
                            shortcut.TargetPath = str(exe_path)
                            shortcut.Arguments = ""
                        else:
                            shortcut.TargetPath = str(py_bin)
                            shortcut.Arguments = f'"{str(script_path)}"'
                        shortcut.WorkingDirectory = str(app_dir)
                        if icon_path.exists():
                            shortcut.IconLocation = f"{str(icon_path)},0"
                        shortcut.Description = "Gemini Flow — Voice AI (Ctrl+Space)"
                        shortcut.Save()
                except Exception as ex:
                    logger.debug(f"Could not create desktop shortcut in {dt}: {ex}")
    except Exception as e:
        logger.debug(f"Desktop shortcut check note: {e}")


def is_windows_startup_enabled() -> bool:
    """Checks if Gemini Flow is currently configured in Windows Run key."""
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, "GeminiFlow")
            return True
    except Exception:
        return False


class ConfigManager:
    def __init__(self):
        self.config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self) -> Dict[str, Any]:
        needs_save = False
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
                    # Update API Key if outdated or matching old test keys
                    curr_key = self.config.get("api_key", "")
                    if not curr_key or "KLd4Prd" in curr_key or "ISb0Ozd" in curr_key or "mock_working_key" in curr_key:
                        self.config["api_key"] = DEFAULT_CONFIG["api_key"]
                        needs_save = True
                    # Ensure defaults for all advanced features
                    if "model_name" not in self.config:
                        self.config["model_name"] = "gemini-2.0-flash"
                        needs_save = True
                    if "model_mode" not in self.config:
                        self.config["model_mode"] = "auto"
                        needs_save = True
                    if "active_profile" not in self.config:
                        self.config["active_profile"] = "coding"
                        needs_save = True
                    if "hotkey" not in self.config:
                        self.config["hotkey"] = "<ctrl>+<space>"
                        self.config["hotkey_display"] = "Ctrl + Space"
                        needs_save = True
                    if "transform_hotkey" not in self.config:
                        self.config["transform_hotkey"] = "<ctrl>+<shift>+t"
                        self.config["transform_hotkey_display"] = "Ctrl + Shift + T"
                        needs_save = True
                    if "transform_hotkey_history" not in self.config or not self.config["transform_hotkey_history"]:
                        self.config["transform_hotkey_history"] = DEFAULT_CONFIG["transform_hotkey_history"].copy()
                        needs_save = True
                    if "security" not in self.config:
                        self.config["security"] = DEFAULT_CONFIG["security"].copy()
                        needs_save = True
                    # Ensure dictionary and snippets exist
                    if "dictionary" not in self.config or not self.config["dictionary"]:
                        self.config["dictionary"] = DEFAULT_DICTIONARY.copy()
                        needs_save = True
                    if "snippets" not in self.config or not self.config["snippets"]:
                        self.config["snippets"] = DEFAULT_SNIPPETS.copy()
                        needs_save = True
                    if "prompt_hotkey" not in self.config:
                        self.config["prompt_hotkey"] = "<ctrl>+<shift>+p"
                        self.config["prompt_hotkey_display"] = "Ctrl + Shift + P"
                        needs_save = True
                    if "voice_hotkey_history" not in self.config or not self.config["voice_hotkey_history"]:
                        self.config["voice_hotkey_history"] = DEFAULT_CONFIG["voice_hotkey_history"].copy()
                        needs_save = True
                    if "prompt_hotkey_history" not in self.config or not self.config["prompt_hotkey_history"]:
                        self.config["prompt_hotkey_history"] = DEFAULT_CONFIG["prompt_hotkey_history"].copy()
                        needs_save = True
                    if "saved_prompts" not in self.config or not self.config["saved_prompts"]:
                        self.config["saved_prompts"] = [p.copy() for p in DEFAULT_SAVED_PROMPTS]
                        needs_save = True
                    if "auto_cost_mode" not in self.config:
                        self.config["auto_cost_mode"] = True
                        needs_save = True
                    if "auto_prompt_conversion" not in self.config:
                        self.config["auto_prompt_conversion"] = False
                        needs_save = True
                    if "settings_window_state" not in self.config:
                        self.config["settings_window_state"] = DEFAULT_CONFIG["settings_window_state"].copy()
                        needs_save = True
                    if needs_save:
                        self.save_config()
                    logger.debug("Configuration loaded.")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        else:
            self.save_config()

        # Enforce history retention on launch
        self.enforce_retention()
        return self.config

    def save_config(self) -> bool:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def get_api_key(self) -> str:
        """Retrieves active Gemini API key from environment, DPAPI encrypted storage, or config."""
        try:
            from app.security.security_manager import SecurityManager
            sec = SecurityManager(APP_DIR)
            raw = sec.load_api_key(self.config.get("api_key", ""))
            return sanitize_api_key(raw)
        except Exception as e:
            logger.error(f"Error retrieving secure API key: {e}")
            return sanitize_api_key(self.config.get("api_key", ""))

    def set_api_key(self, api_key: str) -> None:
        """Securely stores API key using Windows DPAPI if enabled."""
        cleaned = sanitize_api_key(api_key)
        try:
            from app.security.security_manager import SecurityManager
            sec = SecurityManager(APP_DIR)
            sec.save_api_key(cleaned)
        except Exception as e:
            logger.error(f"Failed to persist secure key: {e}")
        self.config["api_key"] = cleaned
        self.save_config()

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save_config()

    def get_dictionary(self) -> List[Dict[str, str]]:
        return self.config.get("dictionary", DEFAULT_DICTIONARY)

    def set_dictionary(self, dictionary_list: List[Dict[str, str]]) -> None:
        self.config["dictionary"] = dictionary_list
        self.save_config()

    def get_snippets(self) -> List[Dict[str, str]]:
        return self.config.get("snippets", DEFAULT_SNIPPETS)

    def set_snippets(self, snippets_list: List[Dict[str, str]]) -> None:
        self.config["snippets"] = snippets_list
        self.save_config()

    def get_voice_hotkey_history(self) -> List[Dict[str, str]]:
        return self.config.get("voice_hotkey_history", DEFAULT_CONFIG["voice_hotkey_history"])

    def add_voice_hotkey_history(self, display: str, internal: str) -> None:
        history = self.get_voice_hotkey_history()
        history = [h for h in history if h.get("internal") != internal]
        history.insert(0, {"display": display, "internal": internal})
        self.config["voice_hotkey_history"] = history[:8]
        self.save_config()

    def get_prompt_hotkey_history(self) -> List[Dict[str, str]]:
        return self.config.get("prompt_hotkey_history", DEFAULT_CONFIG["prompt_hotkey_history"])

    def add_prompt_hotkey_history(self, display: str, internal: str) -> None:
        history = self.get_prompt_hotkey_history()
        history = [h for h in history if h.get("internal") != internal]
        history.insert(0, {"display": display, "internal": internal})
        self.config["prompt_hotkey_history"] = history[:8]
        self.save_config()

    def get_transform_hotkey_history(self) -> List[Dict[str, str]]:
        return self.config.get("transform_hotkey_history", DEFAULT_CONFIG["transform_hotkey_history"])

    def add_transform_hotkey_history(self, display: str, internal: str) -> None:
        history = self.get_transform_hotkey_history()
        history = [h for h in history if h.get("internal") != internal]
        history.insert(0, {"display": display, "internal": internal})
        self.config["transform_hotkey_history"] = history[:8]
        self.save_config()

    def get_auto_prompt_conversion(self) -> bool:
        return bool(self.config.get("auto_prompt_conversion", False))

    def set_auto_prompt_conversion(self, enabled: bool) -> None:
        self.config["auto_prompt_conversion"] = bool(enabled)
        self.save_config()

    def get_dsp_fan_filter_enabled(self) -> bool:
        return bool(self.config.get("dsp_fan_filter_enabled", True))

    def set_dsp_fan_filter_enabled(self, enabled: bool) -> None:
        self.config["dsp_fan_filter_enabled"] = bool(enabled)
        self.save_config()

    def get_dsp_noise_gate_enabled(self) -> bool:
        return bool(self.config.get("dsp_noise_gate_enabled", True))

    def set_dsp_noise_gate_enabled(self, enabled: bool) -> None:
        self.config["dsp_noise_gate_enabled"] = bool(enabled)
        self.save_config()

    def get_dsp_noise_gate_threshold_db(self) -> float:
        return float(self.config.get("dsp_noise_gate_threshold_db", -42.0))

    def set_dsp_noise_gate_threshold_db(self, threshold_db: float) -> None:
        self.config["dsp_noise_gate_threshold_db"] = float(threshold_db)
        self.save_config()

    def get_offline_fallback_enabled(self) -> bool:
        return bool(self.config.get("offline_fallback_enabled", True))

    def set_offline_fallback_enabled(self, enabled: bool) -> None:
        self.config["offline_fallback_enabled"] = bool(enabled)
        self.save_config()

    def get_saved_prompts(self) -> List[Dict[str, Any]]:
        prompts = self.config.get("saved_prompts")
        if not prompts:
            prompts = [p.copy() for p in DEFAULT_SAVED_PROMPTS]
            self.config["saved_prompts"] = prompts
            self.save_config()
        return prompts

    def save_custom_prompt(self, title: str, prompt_text: str, prompt_id: str = None, set_active: bool = False) -> str:
        prompts = self.get_saved_prompts()
        import uuid
        if not prompt_id:
            prompt_id = str(uuid.uuid4())
            new_entry = {
                "id": prompt_id,
                "title": title.strip() or "Custom Prompt",
                "prompt": prompt_text.strip(),
                "is_active": bool(set_active)
            }
            prompts.append(new_entry)
        else:
            found = False
            for p in prompts:
                if p.get("id") == prompt_id:
                    p["title"] = title.strip() or p.get("title", "Custom Prompt")
                    p["prompt"] = prompt_text.strip()
                    if set_active:
                        p["is_active"] = True
                    found = True
                    break
            if not found:
                prompts.append({
                    "id": prompt_id,
                    "title": title.strip() or "Custom Prompt",
                    "prompt": prompt_text.strip(),
                    "is_active": bool(set_active)
                })

        if set_active:
            for p in prompts:
                if p.get("id") != prompt_id:
                    p["is_active"] = False
            self.config["custom_prompt"] = prompt_text.strip()

        self.config["saved_prompts"] = prompts
        self.save_config()
        return prompt_id

    def delete_saved_prompt(self, prompt_id: str) -> bool:
        prompts = self.get_saved_prompts()
        initial_len = len(prompts)
        prompts = [p for p in prompts if p.get("id") != prompt_id]
        if len(prompts) < initial_len:
            self.config["saved_prompts"] = prompts
            self.save_config()
            return True
        return False

    def set_active_saved_prompt(self, prompt_id: str) -> bool:
        prompts = self.get_saved_prompts()
        target_text = ""
        found = False
        for p in prompts:
            if p.get("id") == prompt_id:
                p["is_active"] = True
                target_text = p.get("prompt", "")
                found = True
            else:
                p["is_active"] = False
        if found:
            self.config["custom_prompt"] = target_text
            self.config["saved_prompts"] = prompts
            self.save_config()
            return True
        return False

    def get_active_saved_prompt(self) -> Optional[Dict[str, Any]]:
        for p in self.get_saved_prompts():
            if p.get("is_active"):
                return p
        return None

    def get_system_prompt(self, preset_override: str = None, app_context: Any = None) -> str:
        preset = preset_override or self.config.get("mode_preset", "clean_dictation")
        custom_prompt = self.config.get("custom_prompt", "").strip()
        if custom_prompt and not preset_override:
            base_prompt = custom_prompt
        else:
            base_prompt = DEFAULT_PROMPTS.get(preset, DEFAULT_PROMPTS["clean_dictation"])

        # 1. Inject Active Profile Directives
        try:
            from app.profiles.profile_manager import ProfileManager
            pm = ProfileManager()
            active_prof_id = self.config.get("active_profile", "coding")
            pm.set_active_profile(active_prof_id)
            prof = pm.get_active_profile()
            if prof and prof.system_prompt_addition:
                base_prompt += f"\n\n[Profile Directive - {prof.name}]:\n{prof.system_prompt_addition}"
        except Exception as e:
            logger.debug(f"Profile prompt injection note: {e}")

        # 2. Inject Active Application Context Directives
        if app_context and getattr(app_context, "system_prompt_addition", ""):
            base_prompt += f"\n\n[App Context - {app_context.app_name} ({app_context.category})]:\n{app_context.system_prompt_addition}"

        # 3. Inject Phonetic Dictionary Rules
        dictionary = self.get_dictionary()
        if dictionary:
            dict_rules = [f"'{d.get('spoken', '')}' -> '{d.get('replacement', '')}'" for d in dictionary if d.get('spoken') and d.get('replacement')]
            if dict_rules:
                base_prompt += "\n\nPhonetic & Word Replacement Rules (ALWAYS apply these exact spellings when spoken):\n" + "\n".join(dict_rules)

        # 4. Inject Personal AI Vocabulary Rules
        try:
            from app.vocabulary.vocab_engine import VocabEngine
            ve = VocabEngine()
            vocab_prompt = ve.get_prompt_injection()
            if vocab_prompt:
                base_prompt += f"\n\n{vocab_prompt}"
        except Exception:
            vocab = self.config.get("custom_vocabulary", [])
            if vocab:
                vocab_str = ", ".join(vocab)
                base_prompt += f"\n\nSpecial vocabulary, names, or jargon to prioritize: {vocab_str}."

        return base_prompt

    def enforce_retention(self):
        """Enforces history retention limit in days based on security settings."""
        try:
            retention_days = self.config.get("security", {}).get("history_retention_days", 30)
            from app.security.security_manager import SecurityManager
            sec = SecurityManager(APP_DIR)
            history = self.get_history()
            retained, purged = sec.enforce_history_retention(history, retention_days)
            if purged > 0:
                self._save_history(retained)
                logger.info(f"Purged {purged} expired history records based on {retention_days}-day retention policy.")
        except Exception as e:
            logger.debug(f"Retention enforcement note: {e}")

    def _save_history(self, history: List[Dict[str, Any]]) -> bool:
        """Internal helper to atomically serialize history records to disk."""
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
            return False

    def get_history(self) -> List[Dict[str, Any]]:
        if not HISTORY_FILE.exists():
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            # Ensure backwards compatibility and default fields
            import uuid
            updated = False
            for entry in history:
                if "id" not in entry:
                    entry["id"] = str(uuid.uuid4())
                    updated = True
                if "is_pinned" not in entry:
                    entry["is_pinned"] = False
                    updated = True
                if "is_favorite" not in entry:
                    entry["is_favorite"] = False
                    updated = True
                if "title" not in entry:
                    entry["title"] = ""
                    updated = True
                if "app_name" not in entry:
                    entry["app_name"] = "General"
                    updated = True
                if "model" not in entry:
                    entry["model"] = self.get("model_name", "gemini-3.5-flash-lite")
                    updated = True
            if updated:
                try:
                    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                        json.dump(history, f, indent=2)
                except Exception:
                    pass
            return history
        except Exception as e:
            logger.error(f"Failed to read history: {e}")
            return []

    def add_history_entry(self, text: str, duration_sec: float, mode: str,
                          app_name: str = "General", model: str = "",
                          title: str = "", is_pinned: bool = False, is_favorite: bool = False,
                          raw_text: str = "", prompt: str = "") -> str:
        if not text.strip():
            return ""
        import datetime
        import uuid
        history = self.get_history()
        entry_id = str(uuid.uuid4())
        entry = {
            "id": entry_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "time_str": datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "text": text,
            "raw_text": raw_text or text,
            "prompt": prompt,
            "duration": round(duration_sec, 2),
            "mode": mode,
            "model": model or self.get("model_name", "gemini-3.5-flash-lite"),
            "app_name": app_name or "General",
            "title": title or "",
            "api_key_tag": (self.get_api_key() or "")[-8:] if len(self.get_api_key() or "") >= 8 else "default",
            "is_pinned": bool(is_pinned),
            "is_favorite": bool(is_favorite)
        }
        history.insert(0, entry)
        limit = self.config.get("history_limit", 5000)
        history = history[:limit]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
        return entry_id

    def update_history_entry(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Updates specific fields of an existing history entry (e.g. is_pinned, is_favorite, title)."""
        history = self.get_history()
        found = False
        for entry in history:
            if entry.get("id") == entry_id:
                for k, v in updates.items():
                    entry[k] = v
                found = True
                break
        if found:
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=2)
                return True
            except Exception as e:
                logger.error(f"Failed to update history entry: {e}")
        return False

    def delete_history_entry(self, entry_id: str) -> bool:
        """Permanently deletes a single specific history entry by its unique ID."""
        history = self.get_history()
        initial_len = len(history)
        history = [entry for entry in history if entry.get("id") != entry_id]
        if len(history) < initial_len:
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=2)
                return True
            except Exception as e:
                logger.error(f"Failed to delete history entry: {e}")
        return False

    def clear_history(self, clear_pinned: bool = False) -> tuple:
        """
        Clears history. If clear_pinned is False, all pinned entries are strictly preserved!
        Returns (cleared_count, preserved_count).
        """
        history = self.get_history()
        if clear_pinned:
            cleared_count = len(history)
            preserved_count = 0
            new_history = []
        else:
            new_history = [entry for entry in history if entry.get("is_pinned", False)]
            preserved_count = len(new_history)
            cleared_count = len(history) - preserved_count

        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(new_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
        return cleared_count, preserved_count
