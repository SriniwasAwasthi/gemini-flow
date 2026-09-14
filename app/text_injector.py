"""
Text Injector Module for Gemini Flow
Handles active window focus preservation, clipboard management, and simulated pasting/typing into target application.
"""
import time
import logging
import ctypes
from typing import Optional

logger = logging.getLogger("GeminiFlow.TextInjector")

try:
    import pyperclip
except ImportError:
    pyperclip = None

# Windows API constants and functions
user32 = ctypes.windll.user32
VK_CONTROL = 0x11
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002


class TextInjector:
    def __init__(self):
        self.last_target_hwnd: Optional[int] = None

    def capture_active_window(self):
        """Captures the currently focused window handle before HUD or background takes focus."""
        try:
            self.last_target_hwnd = user32.GetForegroundWindow()
            logger.debug(f"Captured active window handle: {self.last_target_hwnd}")
        except Exception as e:
            logger.warning(f"Could not capture foreground window: {e}")

    def get_target_app_name(self) -> str:
        """Resolves a human-friendly application name for the currently captured target window."""
        hwnd = self.last_target_hwnd or user32.GetForegroundWindow()
        if not hwnd:
            return "General"
        try:
            kernel32 = ctypes.windll.kernel32
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                hproc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
                if hproc:
                    buf = ctypes.create_unicode_buffer(1024)
                    size = ctypes.c_ulong(1024)
                    if kernel32.QueryFullProcessImageNameW(hproc, 0, buf, ctypes.byref(size)):
                        kernel32.CloseHandle(hproc)
                        exe_name = buf.value.split('\\')[-1].lower()
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

            # Fallback to window title
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
        """Restores focus to the window that was active when speech started."""
        if self.last_target_hwnd:
            try:
                user32.SetForegroundWindow(self.last_target_hwnd)
                time.sleep(0.05)
            except Exception as e:
                logger.warning(f"Could not restore foreground window: {e}")

    @staticmethod
    def _safe_set_clipboard(text: str, max_retries: int = 5) -> bool:
        """Sets clipboard text with exponential backoff for transient Windows clipboard locks."""
        for attempt in range(max_retries):
            try:
                pyperclip.copy(text)
                return True
            except Exception:
                time.sleep(0.03 * (attempt + 1))

        # Native Win32 ctypes fallback
        try:
            kernel32 = ctypes.windll.kernel32
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
                time.sleep(0.03)
        except Exception as e:
            logger.debug(f"Direct Win32 clipboard note: {e}")
        return False

    def paste_text(self, text: str, restore_clipboard: bool = False, leave_in_clipboard: Optional[str] = None) -> bool:
        """
        Injects the text into the active cursor position by copying to clipboard
        and simulating Ctrl + V.
        If leave_in_clipboard is provided, sets the clipboard to leave_in_clipboard immediately after
        the Ctrl+V paste action completes (e.g. leaving normal spoken text as safeguard/backup).
        """
        if not text:
            return False

        if pyperclip is None:
            logger.error("pyperclip is not available.")
            return False

        old_clipboard = None
        if restore_clipboard:
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                old_clipboard = None

        try:
            # 1. Bring target window back to foreground
            self.focus_target_window()

            # 2. Set clipboard to the primary text to paste (with retry)
            if not self._safe_set_clipboard(text):
                logger.warning("Could not set primary clipboard text.")
            time.sleep(0.04)

            # 3. Simulate Ctrl + V using Win32 keybd_event
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_V, 0, 0, 0)
            time.sleep(0.03)
            user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

            logger.info("Text pasted successfully via Ctrl+V.")

            # 4. Handle post-paste clipboard state
            if leave_in_clipboard is not None:
                # Allow target window time to process the Ctrl+V paste message
                time.sleep(0.08)
                self._safe_set_clipboard(leave_in_clipboard)
                logger.info("Clipboard updated with safeguard text (normal speech backup).")
            elif restore_clipboard and old_clipboard is not None:
                time.sleep(0.5)
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
        # Use SendInput or pynput to type unicode characters
        try:
            from pynput.keyboard import Controller
            keyboard = Controller()
            keyboard.type(text)
        except Exception as e:
            logger.error(f"Error during manual typing: {e}")

    def get_selected_text(self) -> str:
        """Captures currently highlighted text in foreground window via Ctrl + C simulation."""
        old_clip = ""
        try:
            old_clip = pyperclip.paste() if pyperclip else ""
        except Exception:
            old_clip = ""

        # Clear clipboard temporarily to detect if new text was copied
        try:
            if pyperclip:
                pyperclip.copy("")
        except Exception:
            pass

        # 1. Temporarily release modifier keys that might still be held down by user (e.g. Shift from Ctrl+Shift+T, Alt)
        VK_SHIFT = 0x10
        VK_MENU = 0x12
        VK_T = 0x54
        VK_C = 0x43
        try:
            user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_T, 0, KEYEVENTF_KEYUP, 0)
        except Exception:
            pass
        time.sleep(0.04)

        self.focus_target_window()
        time.sleep(0.04)

        # 2. Simulate clean Ctrl + C
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_C, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.08)

        new_text = ""
        try:
            new_text = pyperclip.paste().strip() if pyperclip else ""
        except Exception:
            new_text = ""

        # 3. If nothing new was copied, fallback to old clipboard content if non-empty
        if not new_text:
            if old_clip and pyperclip:
                try:
                    pyperclip.copy(old_clip)
                except Exception:
                    pass
            return old_clip.strip() if old_clip else ""

        return new_text
