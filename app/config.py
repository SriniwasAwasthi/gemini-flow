"""
Config Manager for Gemini Flow (Wispr Flow AI Alternative)
Handles settings persistence, JSON storage, dictionary mappings, snippets, and history logging.
"""
import os
import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("GeminiFlow.Config")

try:
    APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "GeminiFlow"
    APP_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    APP_DIR = Path(__file__).parent.parent / "recordings"
    APP_DIR.mkdir(parents=True, exist_ok=True)

RECORDINGS_DIR = APP_DIR / "recordings"
try:
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    RECORDINGS_DIR = Path(__file__).parent.parent / "recordings"
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

WORKSPACE_RECORDINGS_DIR = Path(__file__).parent.parent / "recordings"
try:
    WORKSPACE_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

CONFIG_FILE = APP_DIR / "config.json"
HISTORY_FILE = APP_DIR / "history.json"

# Load environment variables (.env) from project root if available
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path, override=True)
    else:
        load_dotenv(override=True)
except Exception:
    pass


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
        "You are Gemini Flow, an elite, ultra-fast speech-to-text transcriber and intelligent real-time voice dictation assistant. "
        "Your mission is to transcribe the user's spoken audio into accurate, natural, and beautifully structured text in the authentic language spoken.\n\n"
        "Strict Conversion Rules:\n"
        "1. Active Language & Selection Enforcement: Strictly adhere to the Active Spoken Language Constraints specified at the end of this prompt. Output exclusively in the user's authorized language(s) and script. If the speaker speaks an unselected foreign or regional language that is NOT in the active authorized list, do NOT output in that unselected language's script; instead, translate the speech into the primary authorized language.\n"
        "2. Intelligent Dictation, Speech Override & Self-Correction Resolution (Wispr Flow AI Brain): Completely REMOVE all verbal fillers, hesitation sounds, stutters, and verbal re-takes ('uh', 'um', 'ah', 'er', 'eh', 'like', 'you know', 'basically', 'actually', 'mean', 'means', 'so like', 'etcetera etcetera', 'and and', 'if if', 'na', 'ya', 'मतलब', 'म्हणजे', false starts). "
        "CRITICAL SELF-CORRECTION & OVERRIDE RULE: When the speaker changes their mind, makes a mistake, slips of the tongue, or corrects a word, date, number, time, name, or statement, you MUST ALWAYS OVERRIDE the mistake with the correction. NEVER output the mistaken phrase, and NEVER output apology words ('sorry', 'oh sorry', 'my bad', 'no wait', 'actually'). Examples: "
        "- Saying 'today is Monday... sorry today is Tuesday' -> Output strictly: 'today is Tuesday.' "
        "- Saying 'convert this whole data under 4 seconds... no sorry under 3 seconds' -> Output strictly: 'convert this whole data under 3 seconds.' "
        "- Saying 'I am in 11th standard... sorry I am in 12th standard' -> Output strictly: 'I am in 12th standard.' "
        "- Saying 'the budget is $500... actually $750' -> Output strictly: 'the budget is $750.' "
        "- Saying 'total budget was around ₹550. Oh wait, the total budget was ₹750.' -> Output strictly: 'the total budget was ₹750.' "
        "- Saying 'the budget is $500... actually $750' -> Output strictly: 'the budget is $750.' "
        "- Saying 'the meeting is at 2 p.m. Sorry, the meeting is at 3 p.m.' -> Output strictly: 'the meeting is at 3 p.m.' "
        "- Saying 'convert this whole data under 4 seconds or no, sorry, under 3 seconds' -> Output strictly: 'convert this whole data under 3 seconds.' "
        "If a sentence or thought is repeated with additions or refinements (e.g. saying 'I just want 100% data. If I just want 100% accurate data.'), collapse the repetition into the single finalized refined thought ('I want 100% accurate data.'). Eliminate stray mic-check greetings ('hello', 'mic check') spoken during pauses.\n"
        "3. Adaptive AI Brain Structuring & Smart Point-Wise Bullet Formatting (Wispr Flow Intelligence): Intelligently detect whether the speaker is conveying continuous narrative or structured point-wise content:\n"
        "   - Structured & Multi-Point Content: When the speaker dictates sequential points, advantages/disadvantages, pros/cons, numbered items ('firstly, secondly', 'one, two, three', 'points are', 'features are'), action items, steps, or multi-point comparisons, DO NOT merge them into one dense wall of text. Automatically identify natural section headers where appropriate (e.g., 'Advantages:', 'Key Points:', 'Next Steps:'), insert clean line breaks, and format each distinct point on its own new line using a clean bullet point ('• ').\n"
        "   - CRITICAL BULLET POINT NUMBERING RULE: When formatting bullet points ('• '), you MUST OMIT the spoken numbering or ordinal words ('First is', 'Second is', 'And third is', 'First point is', 'Point 1:', '1.') from the beginning of each bullet item, because the bullet marker '• ' itself denotes the numbering. Example: Spoken 'first is Antigravity, second is I made changes in Wispr, and third is I used an API key' -> formatted into bullet items '• Antigravity.', '• I made changes in Wispr.', '• I used an API key.'\n"
        "   - Continuous Narrative: When the speaker is conveying ordinary conversational sentences, explanations, or continuous narrative, format as clean, flowing paragraphs with natural double-newline paragraph breaks.\n"
        "   - Spoken Formatting Commands: If the speaker explicitly says formatting or punctuation commands ('bullet point', 'new line', 'next line', 'colon', 'semicolon', 'comma', 'period', 'question mark'), immediately apply that exact formatting and symbol.\n"
        "4. Strict Vocabulary & Verb Integrity (NEVER Substitute Words): You MUST transcribe the EXACT verbs, nouns, and terminology spoken by the user. NEVER substitute verbs with synonyms: when the user says 'analyze', you MUST transcribe 'analyze' (NEVER substitute with 'list' or 'enumerate'). When the user says 'localhost', transcribe 'localhost' (NEVER substitute with 'token' or 'server'). When the user says 'in my Chrome', transcribe 'in my Chrome' (NEVER rephrase into an action command like 'Opening Chrome' or split with an unintended period).\n"
        "5. Proper Name Integrity & Zero Unsolicited Injection: Transcribe proper nouns and names accurately ONLY as explicitly spoken in the audio. Never substitute spoken names with other names. Under NO circumstances should you inject, assume, alter, or append personal names, greetings, or signatures that were not uttered in the audio.\n"
        "6. Universal Accent, Tense & Grammar Intelligence: The speaker or general public may speak with varied international accents, regional cadence, non-native phrasing, or mixed tenses (mixing past, present, and future). Decipher the intended meaning and seamlessly polish spoken grammar, irregular verb agreements, and tense consistency natively across past, present, and future tenses in the spoken language, while preserving 100% of the user's intended thoughts, vocabulary, verbs, numbers, specifics, and technical terms. Automatically insert proper commas (,), periods (.), question marks (?), exclamation marks (!), quotation marks (\"...\"), semicolons (;), colons (:), and capitalization naturally based on speech pauses and clause boundaries.\n"
        "7. No Code Fences or Code Formatting for Normal Speech: Do NOT wrap sentences in Markdown code blocks (```) or treat normal speech as code generation. Only format code if the speaker explicitly dictates programming syntax or commands 'code block'.\n"
        "8. 100% Transcription Completeness & Zero Omissions: You MUST transcribe 100% of all spoken concepts, syllabus items, textbook definitions, technical lists, and ideas from the audio. Never summarize, condense, truncate, or omit any spoken topic, no matter how long the speech is.\n"
        "9. Strict Anti-Repetition Rule: Under NO circumstances should you repeat a word or phrase in an infinite loop. Even if there are pauses or repeated terms in the audio, transcribe each concept once and continue immediately to the next spoken thought.\n"
        "10. Output Format: Output ONLY the finalized transcribed and grammatically perfected text directly. Do NOT add any preamble, conversational filler, markdown block formatting wrapping plain sentences, or prompt wrapping."
    ),
    "smart_polish": (
        "You are an elite Executive AI Writing Assistant and Communications Director running on Gemini 2.5 Flash. "
        "Transform the user's raw spoken thoughts, rambling ideas, or meeting notes into impeccably polished, structured, executive-grade business writing.\n\n"
        "Mandatory Rules:\n"
        "1. Complete Filler & Repetition Elimination: Remove all verbal fillers ('uh', 'ah', 'um', 'like', 'you know', 'basically', 'means') and stutters ('12 12' -> '12').\n"
        "2. Structural Organization & Bullet Points: When the user lists items, steps, priorities, or multi-point thoughts, you MUST format them as clear bullet points ('• ') on separate new lines. Never collapse lists into a single continuous sentence.\n"
        "3. Paragraph Breaks: Use clean paragraph breaks (double newlines) between introductory context, bulleted items, and concluding thoughts.\n"
        "4. Syntax & Executive Grammar Polish: Fix all grammar, insert precise punctuation including semicolons (;), colons (:), elevate Indian English/Hinglish to articulate standard executive English, and refine cadence.\n"
        "5. 100% Content Completeness: Preserve every single topic, discussion point, and idea spoken without omitting or summarizing anything.\n"
        "6. Strict Anti-Repetition: Never repeat any phrase or word in an infinite loop.\n"
        "7. Spoken Formatting Commands: If the speaker says 'bullet point', 'new line', 'next line', 'colon', 'semicolon', insert the exact formatting and line breaks.\n"
        "8. Output ONLY the polished final text directly without conversational remarks or markdown code fences wrapping plain prose."
    ),
    "code_assistant": (
        "You are an elite Developer Dictation Assistant and Technical Writing Expert running on Gemini 2.5 Flash. The user is dictating code, technical instructions, PR descriptions, architectural decisions, or documentation.\n\n"
        "Mandatory Rules:\n"
        "1. Complete Filler & Hesitation Elimination: Strip ALL verbal hesitation sounds ('uh', 'ah', 'um', 'er', 'like', 'you know', 'basically', 'actually', 'mean', 'means', 'matlab', 'yaani', 'etcetera') and repetitions/stutters.\n"
        "2. Technical & Code Formatting: Programmatically format programming terms, frameworks, API endpoints (e.g. FastAPI, Docker, PyTorch), variable/function declarations in camelCase or snake_case (e.g. 'userId', 'auth_token', 'fetchData'), semicolons (;), colons (:), syntax, and terminal commands cleanly. Wrap code blocks in markdown fences (```).\n"
        "3. Superior Grammar & Technical Polish: Refine spoken grammar and elevate conversational phrasing into articulate, concise, professional technical communication.\n"
        "4. 100% Technical Completeness: Capture 100% of all technical terms, code snippets, algorithms, syllabus topics, and architectures spoken without omitting or summarizing anything.\n"
        "5. Strict Anti-Repetition: Never repeat any phrase, identifier, or word in an infinite loop.\n"
        "6. Spoken Formatting Commands: If the speaker says 'bullet point', 'new line', 'next line', 'colon', 'semicolon', insert the exact formatting and line breaks.\n"
        "7. Output ONLY the finalized polished technical text or code directly without preamble, quotes, unnecessary outer wrappers, or conversational remarks."
    ),
    "prompt_enhancer": (
        "You are an expert AI Prompt Engineer running on Gemini 2.5 Flash. The user has provided text or instructions to be transformed into a high-impact AI Prompt.\n"
        "Transform the user's input into an exceptionally clear, comprehensive, and high-impact AI Prompt.\n"
        "Structure the prompt logically with:\n"
        "- Role & Objective: Define the specific persona and primary goal\n"
        "- Context & Requirements: Clear constraints, guidelines, and specifications\n"
        "- Step-by-Step Instructions: Logical numbered steps to follow\n"
        "- Expected Output Format: Concrete structure (e.g., code, explanations, formats)\n"
        "Output ONLY the finalized optimized prompt directly without conversational filler or extra commentary."
    ),
    "verbatim": (
        "Transcribe the spoken audio with 100% high fidelity and completeness running on Gemini 2.5 Flash. "
        "Transcribe every single word and concept spoken without omitting or summarizing anything. "
        "Remove stuttering and verbal hesitation sounds ('uh', 'ah', 'um') and accidental repetitions ('12 12' -> '12'). "
        "Never repeat any word or phrase in an infinite loop. Add proper punctuation, semicolons, colons, and capitalization. "
        "Spoken commands ('new line', 'bullet point', 'colon', 'semicolon') must be formatted into respective symbols and line breaks. "
        "Output ONLY the transcribed text without quotes or commentary."
    )
}
GOLDEN_ANCHOR_EXAMPLES = """--- 22 FEW-SHOT GOLDEN ANCHOR DEMONSTRATIONS ---
[Input]: "yesterday i go to office and seen him"
[Output]: "Yesterday I went to the office and saw him."

[Input]: "there is many problem with the servers"
[Output]: "There are many problems with the servers."

[Input]: "she don\'t know nothing about it"
[Output]: "She doesn\'t know anything about it."

[Input]: "he buyed three apple and runned away"
[Output]: "He bought three apples and ran away."

[Input]: "um like so basically i think we should meet on friday"
[Output]: "I think we should meet on Friday."

[Input]: "the thing is you know actually the api is failing with 500 error"
[Output]: "The API is failing with a 500 error."

[Input]: "buy milk bread eggs butter and apples from store"
[Output]: "Buy from the store:
• Milk
• Bread
• Eggs
• Butter
• Apples"

[Input]: "first install python second setup venv third run the app"
[Output]: "Here are the steps:
1. Install Python
2. Set up venv
3. Run the app"

[Input]: "agenda today is review sales discuss budget and plan sprint"
[Output]: "Today\'s agenda:
• Review sales
• Discuss budget
• Plan sprint"

[Input]: "bugs are crash on login missing icon and slow loading"
[Output]: "Bug report:
• Crash on login
• Missing icon
• Slow loading"

[Input]: "hi sarah thanks for the proposal i reviewed slide four"
[Output]: "Hi Sarah, thanks for the proposal. I reviewed slide 4."

[Input]: "hey alex can you pull the git branch and test payments"
[Output]: "Hey Alex, can you pull the Git branch and test payments?"

[Input]: "are you free for a thirty minute zoom call tomorrow at two pm"
[Output]: "Are you free for a 30-minute Zoom call tomorrow at 2:00 PM?"

[Input]: "total is fifteen hundred dollars with eighteen percent gst"
[Output]: "The total is $1,500 with 18% GST."

[Input]: "the event is scheduled on november twenty fifth at ten thirty am"
[Output]: "The event is scheduled on November 25th at 10:30 AM."

[Input]: "run git commit dash m initial commit and push to main"
[Output]: "Run `git commit -m \"initial commit\"` and push to `main`."

[Input]: "we need sixteen gigabytes ram and an rtx twenty fifty gpu"
[Output]: "We need 16 GB RAM and an RTX 2050 GPU."

[Input]: "if i was you i would have did the same thing"
[Output]: "If I were you, I would have done the same thing."

[Input]: "the decision was took by the management yesterday"
[Output]: "The decision was made by the management yesterday."

[Input]: "let me know once you reach home safe"
[Output]: "Let me know once you reach home safely."

[Input]: "why you are not answering my messages since morning"
[Output]: "Why haven\'t you been answering my messages since morning?"

[Input]: "we tested faster whisper and ollama gemma on cuda"
[Output]: "We tested Faster-Whisper and Ollama Gemma on CUDA."
"""


DEFAULT_DICTIONARY = [
    {"spoken": "Javascript", "replacement": "JavaScript"},
    {"spoken": "Typescript", "replacement": "TypeScript"},
    {"spoken": "Github", "replacement": "GitHub"},
    {"spoken": "local host", "replacement": "localhost"},
    {"spoken": "fast whisper", "replacement": "Faster-Whisper"},
    {"spoken": "faster whisper", "replacement": "Faster-Whisper"},
    {"spoken": "olama", "replacement": "Ollama"},
    {"spoken": "gemini flow", "replacement": "Gemini Flow"},
    {"spoken": "antigravity", "replacement": "Antigravity"},
    {"spoken": "pytorch", "replacement": "PyTorch"},
    {"spoken": "leetcode", "replacement": "LeetCode"},
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
        "prompt": DEFAULT_PROMPTS["clean_dictation"],
        "is_active": True
    },
    {
        "id": "smart_polish_custom",
        "title": "Smart Executive Polish",
        "prompt": DEFAULT_PROMPTS["smart_polish"],
        "is_active": False
    },
    {
        "id": "code_dev_custom",
        "title": "Developer Code & Technical Assistant",
        "prompt": DEFAULT_PROMPTS["code_assistant"],
        "is_active": False
    },
    {
        "id": "prompt_enhancer",
        "title": "AI Prompt Architecture & Meta-Prompt",
        "prompt": DEFAULT_PROMPTS["prompt_enhancer"],
        "is_active": False
    }
]


DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "",
    "model_name": "auto",
    "model_mode": "auto",
    "active_profile": "casual",
    "hotkey": "<ctrl>+<space>",
    "hotkey_display": "Ctrl + Space",
    "hotkey_mode": "toggle",  # "toggle" (press to start/stop) or "push_to_talk" (hold while speaking)
    "prompt_hotkey": "<alt>+p",
    "prompt_hotkey_display": "Alt + P",
    "transform_hotkey": "<alt>+t",
    "transform_hotkey_display": "Alt + T",
    "voice_hotkey_history": [
        {"display": "Ctrl + Space", "internal": "<ctrl>+<space>"},
        {"display": "Ctrl + Win", "internal": "<ctrl>+<cmd>"},
        {"display": "Alt + Space", "internal": "<alt>+<space>"}
    ],
    "prompt_hotkey_history": [
        {"display": "Alt + P", "internal": "<alt>+p"},
        {"display": "Ctrl + Shift + P", "internal": "<ctrl>+<shift>+p"},
        {"display": "Ctrl + Shift + L", "internal": "<ctrl>+<shift>+l"},
        {"display": "Ctrl + Alt + P", "internal": "<ctrl>+<alt>+p"}
    ],
    "transform_hotkey_history": [
        {"display": "Alt + T", "internal": "<alt>+t"},
        {"display": "Ctrl + Shift + T", "internal": "<ctrl>+<shift>+t"},
        {"display": "Ctrl + Alt + T", "internal": "<ctrl>+<alt>+t"}
    ],
    "mode_preset": "clean_dictation",
    "custom_prompt": "",
    "saved_prompts": DEFAULT_SAVED_PROMPTS,
    "custom_vocabulary": ["Gemini Flow", "Faster-Whisper", "Ollama", "Wispr Flow", "localhost", "PyTorch", "LeetCode", "TypeScript"],
    "dictionary": DEFAULT_DICTIONARY,
    "snippets": DEFAULT_SNIPPETS,
    "input_device_index": None,
    "input_device_name": "Default System Microphone",
    "auto_paste": True,
    "play_sounds": True,
    "hud_position": "bottom_center",  # "bottom_center", "custom"
    "hud_custom_x": None,
    "hud_custom_y": None,
    "hud_opacity": 0.20,  # 80% transparency
    "hud_theme": "dark_glass",
    "start_with_windows": True,
    "history_limit": 5000,
    "max_recording_seconds": 14400,  # 4 hours continuous speech support
    "settings_window_state": {
        "x": None,
        "y": None,
        "width": 820,
        "height": 720,
        "is_maximized": False
    },
    "auto_cost_mode": True,
    "auto_prompt_conversion": False,  # If False, voice dictation outputs clean verbatim text everywhere
    "dsp_fan_filter_enabled": False,  # 80 Hz Butterworth High-Pass Filter (OFF by default)
    "dsp_noise_gate_enabled": False,  # Dynamic noise gate (OFF by default to avoid degrading Whisper WER)
    "dsp_noise_gate_threshold_db": -52.0,  # Noise gate cutoff threshold in dB
    "offline_fallback_enabled": True,  # Offline speech recognition fallback when network drops
    "selected_languages": ["English"],  # Selected spoken languages (defaults to English only, or custom subset of 200+)
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
                    # Enforce valid Gemini API Key (retain config key or load from Windows Registry / DPAPI)
                    curr_key = self.config.get("api_key", "").strip()
                    if not curr_key or any(bad in curr_key for bad in ["KLd4Prd", "ISb0Ozd", "mock_working_key", "KKjYK0n"]):
                        try:
                            from app.security.security_manager import SecurityManager
                            sec_key = SecurityManager(APP_DIR).load_api_key("")
                            if sec_key:
                                self.config["api_key"] = sec_key
                                needs_save = True
                        except Exception:
                            pass
                    # Default high-speed model configuration (Gemini 3.5 Flash Lite)
                    if not self.config.get("model_name") or self.config.get("model_name") in ("gemini-2.5-flash", "gemini-3.5-transcribe"):
                        self.config["model_name"] = "gemini-3.5-flash-lite"
                        needs_save = True
                    if not self.config.get("model_mode") or self.config.get("model_mode") in ("gemini-2.5-flash", "gemini-3.5-transcribe"):
                        self.config["model_mode"] = "gemini-3.5-flash-lite"
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
                    if "selected_languages" not in self.config or not isinstance(self.config.get("selected_languages"), list):
                        self.config["selected_languages"] = ["English"]
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
        """Retrieves active Gemini API key from environment (.env), DPAPI encrypted storage, or config."""
        env_k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if env_k:
            cleaned_env = sanitize_api_key(env_k)
            if cleaned_env:
                return cleaned_env
        try:
            from app.security.security_manager import SecurityManager
            sec = SecurityManager(APP_DIR)
            raw = sec.load_api_key(self.config.get("api_key") or self.config.get("gemini_api_key", ""))
            if raw:
                return sanitize_api_key(raw)
        except Exception as e:
            logger.error(f"Error retrieving secure API key: {e}")
        return sanitize_api_key(self.config.get("api_key") or self.config.get("gemini_api_key", ""))

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
        self.config["gemini_api_key"] = cleaned
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
        return bool(self.config.get("dsp_fan_filter_enabled", False))

    def set_dsp_fan_filter_enabled(self, enabled: bool) -> None:
        self.config["dsp_fan_filter_enabled"] = bool(enabled)
        self.save_config()

    def get_dsp_noise_gate_enabled(self) -> bool:
        return bool(self.config.get("dsp_noise_gate_enabled", False))

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

    def get_selected_languages(self) -> List[str]:
        langs = self.config.get("selected_languages", ["English"])
        if not langs or not isinstance(langs, list):
            return ["English"]
        return langs

    def set_selected_languages(self, languages: List[str]) -> None:
        if not languages:
            languages = ["English"]
        self.config["selected_languages"] = languages
        self.save_config()

    def get_primary_language_code(self) -> Optional[str]:
        langs = self.get_selected_languages()
        if not langs or "All" in langs or ("English" in langs and len(langs) == 1):
            return "en"
        from app.languages import get_language_by_name
        non_en = [l for l in langs if str(l).lower() != "english"]
        if len(non_en) == 1:
            item = get_language_by_name(non_en[0])
            if item:
                return item.code
        return None

    def get_saved_prompts(self) -> List[Dict[str, Any]]:
        prompts = self.config.get("saved_prompts")
        if not prompts:
            prompts = [p.copy() for p in DEFAULT_SAVED_PROMPTS]
            self.config["saved_prompts"] = prompts
            self.save_config()
        else:
            existing_ids = {p.get("id") for p in prompts}
            updated = False
            for dp in DEFAULT_SAVED_PROMPTS:
                if dp["id"] not in existing_ids:
                    prompts.append(dp.copy())
                    updated = True
            if updated:
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

    def get_system_prompt(self, preset_override: str = None, app_context: Any = None, profile_id_override: str = None) -> str:
        active_saved = self.get_active_saved_prompt()
        custom_prompt = (active_saved.get("prompt") if active_saved else "") or self.config.get("custom_prompt", "").strip()

        # SAFEGUARD: Voice dictation should never be hijacked by a prompt_enhancer instruction
        if custom_prompt and ("AI Prompt Engineer" in custom_prompt or "Role & Objective" in custom_prompt or "Expected Output Format" in custom_prompt):
            logger.warning("Detected prompt_enhancer instruction in custom_prompt during speech dictation. Falling back to clean_dictation.")
            custom_prompt = ""

        # SAFEGUARD: Prevent legacy hardcoded multilingual override from conflicting with active language selection
        if custom_prompt and "Universal Multilingual Fidelity (200+ Languages):" in custom_prompt:
            legacy_phrase = "Universal Multilingual Fidelity (200+ Languages): Accurately detect and transcribe speech in whatever language or dialect is spoken (including English, Marathi, Hindi, Sanskrit, Tamil, Telugu, Kannada, Bengali, Gujarati, Spanish, French, German, Japanese, Chinese, Arabic, and all 200+ global and regional languages). Faithfully preserve the authentic native script (e.g. Devanagari script for Marathi and Hindi, Latin script for English/European languages, etc.) with 100% fidelity. NEVER force-translate non-English speech into English, and never transliterate regional languages into phonetic Latin script unless explicitly commanded to translate. For code-switching (e.g. Marathi/Hindi mixed with English technical terms like 'database', 'LinkedIn', 'dataset', 'API', 'localhost'), seamlessly preserve both in their natural script."
            enforced_phrase = "Active Language & Selection Enforcement: Strictly adhere to the Active Spoken Language Constraints specified at the end of this prompt. Output exclusively in the user's authorized language(s) and script. If the speaker speaks an unselected foreign or regional language that is NOT in the active authorized list, do NOT output in that unselected language's script; instead, translate the speech into the primary authorized language."
            custom_prompt = custom_prompt.replace(legacy_phrase, enforced_phrase)

        preset = preset_override or self.config.get("mode_preset", "clean_dictation")
        if preset == "prompt_enhancer":
            preset = "clean_dictation"

        if preset_override and preset_override not in ("clean_dictation", self.config.get("mode_preset")):
            base_prompt = DEFAULT_PROMPTS.get(preset_override, DEFAULT_PROMPTS["clean_dictation"])
        elif custom_prompt:
            base_prompt = custom_prompt
        else:
            base_prompt = DEFAULT_PROMPTS.get(preset, DEFAULT_PROMPTS["clean_dictation"])

        # 1. Inject Active Profile Directives (Dynamically adapted from active app or override)
        try:
            from app.profiles.profile_manager import ProfileManager
            pm = ProfileManager()
            active_prof_id = profile_id_override or self.config.get("active_profile") or getattr(app_context, "profile_id", None) or "casual"
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

        # 5. Inject Active Multilingual Constraints (200+ Languages Catalog)
        try:
            from app.languages import format_language_prompt_instruction
            selected_langs = self.get_selected_languages()
            lang_prompt = format_language_prompt_instruction(selected_langs)
            if lang_prompt:
                base_prompt += f"\n{lang_prompt}"
        except Exception as e:
            logger.debug(f"Language prompt injection note: {e}")

        # 6. Inject 22 Few-Shot Golden Anchor Demonstrations
        if "FEW-SHOT GOLDEN ANCHOR DEMONSTRATIONS" not in base_prompt:
            base_prompt += f"\n\n{GOLDEN_ANCHOR_EXAMPLES}"

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
                    entry["model"] = self.get("model_name", "gemini-2.5-flash")
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

    @staticmethod
    def save_recorded_audio(wav_bytes: bytes, prefix: str = "rec") -> str:
        """
        Saves full, complete, playable 16-bit PCM WAV audio to disk.
        Saves to workspace recordings directory and AppData recordings directory.
        Guarantees that saved audio has a valid WAV RIFF header, is playable, and returns the absolute path.
        """
        if not wav_bytes or len(wav_bytes) < 44:
            return ""

        final_wav = wav_bytes
        if not (wav_bytes.startswith(b"RIFF") and b"WAVE" in wav_bytes[:16]):
            try:
                import io
                import wave
                out_io = io.BytesIO()
                with wave.open(out_io, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(wav_bytes)
                final_wav = out_io.getvalue()
            except Exception as whe:
                logger.debug(f"WAV header fixup note: {whe}")

        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{ts}_{int(time.time() * 1000) % 10000:04d}.wav"
        saved_path = ""

        # 1. Prioritize Workspace recordings directory (always writable and accessible)
        try:
            WORKSPACE_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
            ws_file = WORKSPACE_RECORDINGS_DIR / filename
            with open(ws_file, "wb") as f_ws:
                f_ws.write(final_wav)
            ws_last = WORKSPACE_RECORDINGS_DIR / "last_recording.wav"
            with open(ws_last, "wb") as f_wl:
                f_wl.write(final_wav)
            if ws_file.exists() and ws_file.stat().st_size > 0:
                saved_path = str(ws_file.resolve())
        except Exception as we:
            logger.debug(f"Workspace recording save error: {we}")

        # 2. Also save to AppData recordings directory if accessible
        try:
            RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
            file_path = RECORDINGS_DIR / filename
            with open(file_path, "wb") as f:
                f.write(final_wav)
            last_path = RECORDINGS_DIR / "last_recording.wav"
            with open(last_path, "wb") as f_last:
                f_last.write(final_wav)
            if not saved_path and file_path.exists() and file_path.stat().st_size > 0:
                saved_path = str(file_path.resolve())
        except Exception as ae:
            logger.debug(f"AppData recording save error: {ae}")

        return saved_path

    def add_history_entry(self, text: str, duration_sec: float, mode: str,
                          app_name: str = "General", model: str = "",
                          title: str = "", is_pinned: bool = False, is_favorite: bool = False,
                          raw_text: str = "", prompt: str = "", audio_path: str = "") -> str:
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
            "model": model or self.get("model_name", "gemini-2.5-flash"),
            "app_name": app_name or "General",
            "title": title or "",
            "api_key_tag": (self.get_api_key() or "")[-8:] if len(self.get_api_key() or "") >= 8 else "default",
            "is_pinned": bool(is_pinned),
            "is_favorite": bool(is_favorite),
            "audio_path": str(audio_path or "")
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
