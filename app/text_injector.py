"""
Text Injector Module for Gemini Flow.
Handles active window focus preservation, clipboard management, Win32 SendInput atomic injection,
terminal-aware paste chord routing (Ctrl+Shift+V vs Ctrl+V), modifier key release handling,
and active foreground window tracking for contextual text formatting.
Inspired by OpenWhispr native windows-fast-paste architecture.
"""
import os
import time
import logging
import ctypes
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger("GeminiFlow.TextInjector")

try:
    import pyperclip
except ImportError:
    pyperclip = None

# Windows API constants and functions
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt key
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_C = 0x43
VK_V = 0x56
VK_P = 0x50
VK_T = 0x54
VK_LWIN = 0x5B
VK_RWIN = 0x5C

KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1

TERMINAL_CLASSES = {
    "consolewindowclass",
    "cascadia_hosting_window_class",
    "mintty",
    "virtualconsoleclass",
    "putty",
    "alacritty",
    "org.wezfurlong.wezterm",
    "hyper",
    "tmobaxterm",
    "kitty"
}

TERMINAL_EXES = {
    "termius.exe",
    "tabby.exe",
    "wave.exe",
    "rio.exe",
    "windowsterminal.exe",
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",
    "bash.exe",
    "wsl.exe"
}

MODIFIER_VKS = [
    VK_LCONTROL, VK_RCONTROL,
    VK_LSHIFT, VK_RSHIFT,
    VK_LMENU, VK_RMENU,
    VK_LWIN, VK_RWIN
]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p)
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort)
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p)
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT)
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", _INPUT_UNION)
    ]


def release_held_modifiers() -> List[int]:
    """Releases any modifier keys that are physically held down to prevent chord collision."""
    released = []
    for vk in MODIFIER_VKS:
        if user32.GetAsyncKeyState(vk) & 0x8000:
            released.append(vk)
    if released:
        inputs = (INPUT * len(released))()
        for idx, vk in enumerate(released):
            inputs[idx].type = INPUT_KEYBOARD
            inputs[idx].union.ki.wVk = vk
            inputs[idx].union.ki.dwFlags = KEYEVENTF_KEYUP
        user32.SendInput(len(released), ctypes.byref(inputs), ctypes.sizeof(INPUT))
    return released


def restore_modifiers(released: List[int]):
    """Restores any modifier keys that were temporarily released."""
    if not released:
        return
    inputs = (INPUT * len(released))()
    for idx, vk in enumerate(released):
        inputs[idx].type = INPUT_KEYBOARD
        inputs[idx].union.ki.wVk = vk
        inputs[idx].union.ki.dwFlags = 0
    user32.SendInput(len(released), ctypes.byref(inputs), ctypes.sizeof(INPUT))


def send_atomic_paste(is_terminal: bool = False):
    """
    Sends atomic paste keystroke via Win32 SendInput API:
    - Normal applications: Ctrl + V
    - Terminal emulators: Ctrl + Shift + V
    """
    if is_terminal:
        # 6 inputs: Ctrl Down, Shift Down, V Down, V Up, Shift Up, Ctrl Up
        inputs = (INPUT * 6)()
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].union.ki.wVk = VK_CONTROL
        inputs[0].union.ki.dwFlags = 0

        inputs[1].type = INPUT_KEYBOARD
        inputs[1].union.ki.wVk = VK_SHIFT
        inputs[1].union.ki.dwFlags = 0

        inputs[2].type = INPUT_KEYBOARD
        inputs[2].union.ki.wVk = VK_V
        inputs[2].union.ki.dwFlags = 0

        inputs[3].type = INPUT_KEYBOARD
        inputs[3].union.ki.wVk = VK_V
        inputs[3].union.ki.dwFlags = KEYEVENTF_KEYUP

        inputs[4].type = INPUT_KEYBOARD
        inputs[4].union.ki.wVk = VK_SHIFT
        inputs[4].union.ki.dwFlags = KEYEVENTF_KEYUP

        inputs[5].type = INPUT_KEYBOARD
        inputs[5].union.ki.wVk = VK_CONTROL
        inputs[5].union.ki.dwFlags = KEYEVENTF_KEYUP
        user32.SendInput(6, ctypes.byref(inputs), ctypes.sizeof(INPUT))
    else:
        # 4 inputs: Ctrl Down, V Down, V Up, Ctrl Up
        inputs = (INPUT * 4)()
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].union.ki.wVk = VK_CONTROL
        inputs[0].union.ki.dwFlags = 0

        inputs[1].type = INPUT_KEYBOARD
        inputs[1].union.ki.wVk = VK_V
        inputs[1].union.ki.dwFlags = 0

        inputs[2].type = INPUT_KEYBOARD
        inputs[2].union.ki.wVk = VK_V
        inputs[2].union.ki.dwFlags = KEYEVENTF_KEYUP

        inputs[3].type = INPUT_KEYBOARD
        inputs[3].union.ki.wVk = VK_CONTROL
        inputs[3].union.ki.dwFlags = KEYEVENTF_KEYUP
        user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def send_atomic_copy():
    """Sends atomic Ctrl+C key combination via Win32 SendInput API."""
    inputs = (INPUT * 4)()
    inputs[0].type = INPUT_KEYBOARD
    inputs[0].union.ki.wVk = VK_CONTROL
    inputs[0].union.ki.dwFlags = 0
    inputs[1].type = INPUT_KEYBOARD
    inputs[1].union.ki.wVk = VK_C
    inputs[1].union.ki.dwFlags = 0
    inputs[2].type = INPUT_KEYBOARD
    inputs[2].union.ki.wVk = VK_C
    inputs[2].union.ki.dwFlags = KEYEVENTF_KEYUP
    inputs[3].type = INPUT_KEYBOARD
    inputs[3].union.ki.wVk = VK_CONTROL
    inputs[3].union.ki.dwFlags = KEYEVENTF_KEYUP
    user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))


class TextInjector:
    def __init__(self):
        self.last_target_hwnd: Optional[int] = None
        self._last_clipboard_backup: Optional[str] = None
        self._fast_paste_bin = Path(__file__).parent / "resources" / "bin" / "windows-fast-paste.exe"

    def capture_active_window(self):
        """Captures the currently focused window handle before HUD or background takes focus."""
        try:
            self.last_target_hwnd = user32.GetForegroundWindow()
            logger.debug(f"Captured active window handle: {self.last_target_hwnd}")
        except Exception as e:
            logger.warning(f"Could not capture foreground window: {e}")

    def is_terminal_target(self, hwnd: Optional[int] = None) -> bool:
        """Detects whether the target window is a terminal or console host."""
        target = hwnd or self.last_target_hwnd or user32.GetForegroundWindow()
        if not target:
            return False
        try:
            # 1. Check window class name
            buf = ctypes.create_unicode_buffer(256)
            if user32.GetClassNameW(target, buf, 256):
                cname = buf.value.lower()
                if cname in TERMINAL_CLASSES or any(term in cname for term in ("terminal", "console", "cascadia")):
                    return True

            # 2. Check process executable name
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(target, ctypes.byref(pid))
            if pid.value:
                hproc = kernel32.OpenProcess(0x1000, False, pid.value)
                if hproc:
                    pbuf = ctypes.create_unicode_buffer(1024)
                    size = ctypes.c_ulong(1024)
                    if kernel32.QueryFullProcessImageNameW(hproc, 0, pbuf, ctypes.byref(size)):
                        exe_name = os.path.basename(pbuf.value).lower()
                        if exe_name in TERMINAL_EXES:
                            kernel32.CloseHandle(hproc)
                            return True
                    kernel32.CloseHandle(hproc)
        except Exception as ex:
            logger.debug(f"Terminal detection error: {ex}")
        return False

    def get_target_window_title(self) -> str:
        """Retrieves the full active window title for context injection (e.g. 'main.py - Wisper - Visual Studio Code')."""
        hwnd = self.last_target_hwnd or user32.GetForegroundWindow()
        if not hwnd:
            return ""
        try:
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                return buf.value.strip()
        except Exception as e:
            logger.debug(f"Error fetching window title: {e}")
        return ""

    def get_foreground_context(self) -> Dict[str, str]:
        """Tracks GetForegroundWindow to detect active application context, title, and category."""
        hwnd = self.last_target_hwnd or user32.GetForegroundWindow()
        app_name = self.get_target_app_name()
        window_title = self.get_target_window_title()
        lower_app = app_name.lower()
        lower_title = window_title.lower()

        category = "general"
        if self.is_terminal_target(hwnd):
            category = "terminal"
        elif any(k in lower_app or k in lower_title for k in ("code", "pycharm", "intellij", "studio", "sublime", "vim", "cursor", ".py", ".ts", ".js", ".java", ".cpp")):
            category = "coding"
        elif any(k in lower_app or k in lower_title for k in ("terminal", "cmd", "powershell", "bash", "wt", "git")):
            category = "terminal"
        elif any(k in lower_app or k in lower_title for k in ("slack", "discord", "teams", "whatsapp", "telegram", "chat")):
            category = "chat"
        elif any(k in lower_app or k in lower_title for k in ("word", "docs", "notepad", "writer", "obsidian", "notion", "notes")):
            category = "document"
        elif any(k in lower_app or k in lower_title for k in ("outlook", "thunderbird", "mail", "gmail")):
            category = "email"

        return {
            "hwnd": str(hwnd),
            "app_name": app_name,
            "window_title": window_title,
            "category": category
        }

    def apply_contextual_formatting(self, text: str, context: Optional[Dict[str, str]] = None) -> str:
        """Applies application-specific formatting based on active window context."""
        ctx = context or self.get_foreground_context()
        cat = ctx.get("category", "general")
        if cat == "terminal":
            # Avoid smart quotes in terminal
            return text.replace("“", """).replace("”", """).replace("‘", "'").replace("’", "'")
        return text

    def get_target_app_name(self) -> str:
        """Resolves a human-friendly application name for the currently captured target window."""
        hwnd = self.last_target_hwnd or user32.GetForegroundWindow()
        if not hwnd:
            return "General"
        try:
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                hproc = kernel32.OpenProcess(0x1000, False, pid.value)
                if hproc:
                    buf = ctypes.create_unicode_buffer(1024)
                    size = ctypes.c_ulong(1024)
                    if kernel32.QueryFullProcessImageNameW(hproc, 0, buf, ctypes.byref(size)):
                        kernel32.CloseHandle(hproc)
                        exe_name = os.path.basename(buf.value).lower()
                        if 'code' in exe_name: return 'VS Code'
                        if 'chrome' in exe_name: return 'Google Chrome'
                        if 'msedge' in exe_name: return 'Microsoft Edge'
                        if 'firefox' in exe_name: return 'Firefox'
                        if 'whatsapp' in exe_name: return 'WhatsApp'
                        if 'notepad' in exe_name: return 'Notepad'
                        if 'word' in exe_name or 'winword' in exe_name: return 'Microsoft Word'
                        if 'excel' in exe_name: return 'Microsoft Excel'
                        if 'slack' in exe_name: return 'Slack'
                        if 'discord' in exe_name: return 'Discord'
                        if 'terminal' in exe_name or 'cmd' in exe_name or 'powershell' in exe_name: return 'Terminal'
                        return exe_name.replace('.exe', '').capitalize()
                    kernel32.CloseHandle(hproc)

            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.strip()
                if title:
                    for suffix in [" - Visual Studio Code", " - Google Chrome", " - Personal - Microsoft​ Edge"]:
                        if suffix in title:
                            title = title.replace(suffix, "").strip()
                    return title[:30]
        except Exception as e:
            logger.debug(f"Error resolving app name: {e}")
        return "General"

    def focus_target_window(self):
        """Restores focus to the window that was active when speech started with zero lag."""
        if self.last_target_hwnd:
            try:
                fore_hwnd = user32.GetForegroundWindow()
                if fore_hwnd != self.last_target_hwnd:
                    cur_thread = kernel32.GetCurrentThreadId()
                    target_thread = user32.GetWindowThreadProcessId(self.last_target_hwnd, None)
                    if target_thread != 0 and target_thread != cur_thread:
                        user32.AttachThreadInput(cur_thread, target_thread, True)
                        user32.BringWindowToTop(self.last_target_hwnd)
                        user32.SetForegroundWindow(self.last_target_hwnd)
                        user32.AttachThreadInput(cur_thread, target_thread, False)
                    else:
                        user32.BringWindowToTop(self.last_target_hwnd)
                        user32.SetForegroundWindow(self.last_target_hwnd)
            except Exception as e:
                logger.warning(f"Could not restore foreground window: {e}")

    @staticmethod
    def _safe_set_clipboard(text: str, max_retries: int = 5) -> bool:
        """Sets clipboard text with exponential backoff for transient Windows clipboard locks."""
        for attempt in range(max_retries):
            try:
                if pyperclip:
                    pyperclip.copy(text)
                    return True
            except Exception:
                time.sleep(0.01 * (attempt + 1))

        try:
            GMEM_MOVEABLE = 0x0002
            CF_UNICODETEXT = 13
            for attempt in range(max_retries):
                if user32.OpenClipboard(None):
                    try:
                        user32.EmptyClipboard()
                        encoded = text.encode('utf-16-le') + b'\x00\x00'
                        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
                        if h_mem:
                            p_mem = kernel32.GlobalLock(h_mem)
                            if p_mem:
                                ctypes.memmove(p_mem, encoded, len(encoded))
                                kernel32.GlobalUnlock(h_mem)
                                user32.SetClipboardData(CF_UNICODETEXT, h_mem)
                        return True
                    finally:
                        user32.CloseClipboard()
                time.sleep(0.01)
        except Exception as e:
            logger.debug(f"Direct Win32 clipboard note: {e}")
        return False

    def paste_text(self, text: str, restore_clipboard: bool = False, leave_in_clipboard: Optional[str] = None) -> bool:
        """
        High-Speed OpenWhispr-Grade Atomic Injection:
        1. Identifies if destination is a terminal (switches to Ctrl+Shift+V).
        2. Restores original foreground window focus.
        3. Releases physical modifier keys held down by hotkey (Ctrl/Alt/Shift/Win).
        4. Copies text directly to clipboard with zero-wait Win32 API.
        5. Fires atomic SendInput paste.
        6. Restores clipboard asynchronously.
        """
        if not text:
            return False

        old_clipboard = None
        if restore_clipboard:
            try:
                old_clipboard = pyperclip.paste() if pyperclip else None
            except Exception:
                old_clipboard = None

        try:
            # 1. Bring target window back to foreground
            self.focus_target_window()

            # 2. Check if target is a terminal emulator
            is_terminal = self.is_terminal_target()

            # 3. Contextual formatting
            formatted_text = self.apply_contextual_formatting(text)

            # 4. Set clipboard with finalized text
            if not self._safe_set_clipboard(formatted_text):
                logger.warning("Could not set primary clipboard text.")

            # 5. Release any physically held modifier keys
            released = release_held_modifiers()

            # 6. Send atomic paste (Ctrl+Shift+V for terminals, Ctrl+V for normal apps)
            send_atomic_paste(is_terminal=is_terminal)

            # 7. Restore previously held modifiers if any
            if released:
                restore_modifiers(released)

            logger.info(f"Text injected instantly via {'Terminal (Ctrl+Shift+V)' if is_terminal else 'Standard (Ctrl+V)'} Win32 SendInput.")

            # 8. Post-paste clipboard restoration
            if leave_in_clipboard is not None:
                time.sleep(0.04)
                self._safe_set_clipboard(leave_in_clipboard)
            elif restore_clipboard and old_clipboard is not None:
                time.sleep(0.04)
                self._safe_set_clipboard(old_clipboard)

            return True
        except Exception as e:
            logger.error(f"Error pasting text: {e}")
            return False

    def type_text_manually(self, text: str):
        """Types text character by character (fallback if clipboard paste is disabled)."""
        if not text:
            return
        self.focus_target_window()
        try:
            from pynput.keyboard import Controller
            keyboard = Controller()
            keyboard.type(text)
        except Exception as e:
            logger.error(f"Error during manual typing: {e}")

    def get_selected_text_with_backup(self, require_selection: bool = True) -> Tuple[Optional[str], Optional[str]]:
        """
        Captures currently highlighted / selected text in the foreground window while backing up clipboard:
        - Waits for physical Alt / modifier key release so Windows doesn't intercept as Ctrl+Alt+C.
        - Backs up existing clipboard content.
        - Uses atomic Win32 SendInput for Ctrl+C.
        - If no text was selected, restores original clipboard and returns (None, backup).
        - If text was selected, returns (selected_text, backup).
        """
        old_clip: Optional[str] = None
        try:
            old_clip = pyperclip.paste() if pyperclip else None
        except Exception:
            old_clip = None

        self._last_clipboard_backup = old_clip

        # 1. Release held modifiers
        release_held_modifiers()

        # 2. Focus target window
        self.focus_target_window()

        # 3. Set clipboard to empty sentinel before copy
        sentinel = f"__GEMINI_FLOW_CAPTURE_{int(time.time()*1000)}__"
        try:
            if pyperclip:
                pyperclip.copy(sentinel)
        except Exception:
            pass

        # 4. Send atomic Ctrl + C via SendInput
        try:
            send_atomic_copy()
        except Exception:
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_C, 0, 0, 0)
            time.sleep(0.01)
            user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

        # 5. Poll clipboard for copied selection
        new_text = ""
        poll_start = time.time()
        while time.time() - poll_start < 0.25:
            try:
                t = pyperclip.paste() if pyperclip else ""
                if t and t != sentinel:
                    new_text = t.strip()
                    break
            except Exception:
                pass
            time.sleep(0.015)

        if new_text:
            return (new_text, old_clip)

        # 6. Restore original clipboard if no selection was captured
        if require_selection:
            if old_clip is not None:
                self.restore_clipboard_backup(old_clip)
            return (None, old_clip)

        fallback = old_clip.strip() if old_clip else None
        return (fallback, old_clip)

    def restore_clipboard_backup(self, backup: Optional[str] = None) -> bool:
        """
        Restores clipboard to the pre-hotkey backup content safely and atomically.
        """
        target = backup if backup is not None else self._last_clipboard_backup
        if target is None:
            return True
        return self._safe_set_clipboard(target)

    def get_selected_text(self, require_selection: bool = True) -> str:
        """
        Captures currently highlighted / selected text in the foreground window:
        - Waits for physical Alt / modifier key release so Windows doesn't intercept as Ctrl+Alt+C.
        - Dismisses any active application Menu Bar loop triggered by pressing Alt.
        - Uses atomic Win32 SendInput for Ctrl+C.
        - Preserves original clipboard content if capture fails or text is unchanged.
        """
        text, _ = self.get_selected_text_with_backup(require_selection=require_selection)
        return text or ""

    def get_clipboard_text(self) -> str:
        """Safely reads current clipboard text without modifying it."""
        try:
            return (pyperclip.paste() or "").strip() if pyperclip else ""
        except Exception:
            return ""
