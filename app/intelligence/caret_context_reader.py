"""
Windows Caret Context Reader & Password Field Guard for Gemini Flow.
Provides real-time inspection of active cursor context:
1. Password Field Guard: Detects whether the focused control is a password input.
   If True, dictation is automatically blocked for credential security.
2. Caret Context: Inspects text around the caret to determine:
   - Whether to prepend a space (if preceding character is alphanumeric)
   - Whether to capitalize the first word (if preceding character is terminal punctuation)
   - Whether the caret is inside an unclosed quote or parenthesis
"""
import ctypes
from ctypes import wintypes, byref, Structure, sizeof
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("GeminiFlow.CaretContextReader")

user32 = ctypes.windll.user32

GWL_STYLE = -16
ES_PASSWORD = 0x0020
EM_GETPASSWORDCHAR = 0x00D2
EM_GETSEL = 0x00B0
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E


class GUITHREADINFO(Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


@dataclass
class CaretContext:
    is_password: bool = False
    preceding_text: str = ""
    following_text: str = ""
    needs_leading_space: bool = False
    should_capitalize: bool = True
    is_within_quotes: bool = False
    focused_hwnd: Optional[int] = None
    focused_class: str = ""


class CaretContextReader:
    @staticmethod
    def get_focused_control() -> Tuple[Optional[int], str]:
        """Returns the currently focused HWND and its window class name."""
        try:
            fg_hwnd = user32.GetForegroundWindow()
            if not fg_hwnd:
                return None, ""

            tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
            g = GUITHREADINFO()
            g.cbSize = sizeof(GUITHREADINFO)

            if user32.GetGUIThreadInfo(tid, byref(g)) and g.hwndFocus:
                target_hwnd = g.hwndFocus
            else:
                target_hwnd = fg_hwnd

            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(target_hwnd, buf, 256)
            class_name = buf.value

            return target_hwnd, class_name
        except Exception as e:
            logger.debug(f"Error querying focused control: {e}")
            return None, ""

    @classmethod
    def is_password_field(cls, hwnd: Optional[int] = None) -> bool:
        """
        Rock-solid Windows credential protection:
        Returns True if the control has ES_PASSWORD style, returns a password char,
        or has a password-associated window class.
        """
        try:
            if not hwnd:
                hwnd, class_name = cls.get_focused_control()
            else:
                buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, buf, 256)
                class_name = buf.value

            if not hwnd:
                return False

            low_class = class_name.lower()
            if any(p in low_class for p in ("password", "passbox", "secureedit")):
                return True

            # 1. Check Win32 ES_PASSWORD window style
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            if style and (style & ES_PASSWORD):
                return True

            # 2. Check EM_GETPASSWORDCHAR message
            pwd_char = user32.SendMessageW(hwnd, EM_GETPASSWORDCHAR, 0, 0)
            if pwd_char != 0:
                return True

            return False
        except Exception as e:
            logger.debug(f"is_password_field check error: {e}")
            return False

    @classmethod
    def get_context(cls, max_chars: int = 100) -> CaretContext:
        """
        Inspects the active caret context and returns a CaretContext object.
        Gracefully degrades if control text cannot be read directly.
        """
        target_hwnd, class_name = cls.get_focused_control()
        if not target_hwnd:
            return CaretContext()

        is_pwd = cls.is_password_field(target_hwnd)
        if is_pwd:
            return CaretContext(is_password=True, focused_hwnd=target_hwnd, focused_class=class_name)

        preceding = ""
        following = ""

        try:
            # Query standard Win32 edit control caret position
            start = wintypes.DWORD()
            end = wintypes.DWORD()
            res = user32.SendMessageW(target_hwnd, EM_GETSEL, byref(start), byref(end))
            caret_pos = start.value

            text_len = user32.SendMessageW(target_hwnd, WM_GETTEXTLENGTH, 0, 0)
            if text_len > 0:
                buf = ctypes.create_unicode_buffer(text_len + 1)
                user32.SendMessageW(target_hwnd, WM_GETTEXT, text_len + 1, buf)
                full_text = buf.value
                if 0 <= caret_pos <= len(full_text):
                    preceding = full_text[max(0, caret_pos - max_chars):caret_pos]
                    following = full_text[caret_pos:min(len(full_text), caret_pos + max_chars)]
        except Exception as e:
            logger.debug(f"Direct edit buffer inspection note: {e}")

        # Linguistic context inference
        needs_leading_space = False
        should_capitalize = True
        is_within_quotes = False

        if preceding:
            clean_preceding = preceding.rstrip()
            if clean_preceding:
                last_char = clean_preceding[-1]
                # If preceding text ends with a letter, number, or comma/semicolon without trailing space
                if preceding[-1] not in (" ", "\t", "\n"):
                    needs_leading_space = True

                # If preceding character is inside an unclosed quote or open paren
                if last_char in ('"', "'", "(", "[", "{"):
                    should_capitalize = False
                    is_within_quotes = True
                elif last_char not in (".", "!", "?", "\n"):
                    should_capitalize = False
            else:
                should_capitalize = True

        return CaretContext(
            is_password=False,
            preceding_text=preceding,
            following_text=following,
            needs_leading_space=needs_leading_space,
            should_capitalize=should_capitalize,
            is_within_quotes=is_within_quotes,
            focused_hwnd=target_hwnd,
            focused_class=class_name
        )
