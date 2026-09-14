"""
Hotkey Manager for Gemini Flow
Supports Global Keyboard Shortcuts for Dictation (Toggle & Push-to-Talk), Prompt Transformation,
and Escape Cancellation.
"""
import logging
import threading
from typing import Callable, Optional, Set, Any
from pynput import keyboard

logger = logging.getLogger("GeminiFlow.HotkeyManager")


def _is_win32_key_down(vk_code: int) -> bool:
    """Queries Windows OS kernel directly for physical hardware key state."""
    try:
        import ctypes
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)
    except Exception:
        return False

def _is_any_vk_down(vk_codes: list) -> bool:
    return any(_is_win32_key_down(vk) for vk in vk_codes)


class HotkeyManager:
    def __init__(
        self,
        hotkey_str: str = "<ctrl>+<space>",
        mode: str = "toggle",  # "toggle" or "push_to_talk"
        prompt_hotkey_str: str = "<ctrl>+<shift>+p",
        transform_hotkey_str: str = "<ctrl>+<shift>+t",
        on_start: Optional[Callable[[], None]] = None,
        on_stop: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        on_prompt: Optional[Callable[[], None]] = None,
        on_transform: Optional[Callable[[], None]] = None
    ):
        self.hotkey_str = hotkey_str
        self.mode = mode
        self.prompt_hotkey_str = prompt_hotkey_str
        self.transform_hotkey_str = transform_hotkey_str
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_cancel = on_cancel
        self.on_prompt = on_prompt
        self.on_transform = on_transform

        self.is_active = False
        self.is_recording = False
        self.is_processing = False
        self._listener: Optional[keyboard.Listener] = None
        self._current_keys: Set[Any] = set()
        self._lock = threading.Lock()

        # State tracking to prevent Windows OS keyboard repeat from double-triggering or cutting off speech
        self._main_hotkey_active = False
        self._prompt_hotkey_active = False
        self._transform_hotkey_active = False
        self._last_toggle_time = 0.0

    def update_config(
        self,
        hotkey_str: str,
        mode: str,
        prompt_hotkey_str: str = "<ctrl>+<shift>+p",
        transform_hotkey_str: str = "<ctrl>+<shift>+t"
    ):
        with self._lock:
            self.hotkey_str = hotkey_str
            self.mode = mode
            self.prompt_hotkey_str = prompt_hotkey_str
            self.transform_hotkey_str = transform_hotkey_str
            self._main_hotkey_active = False
            self._prompt_hotkey_active = False
            self._transform_hotkey_active = False
            logger.info(f"Hotkey updated: Main={hotkey_str} ({mode}), Prompt={prompt_hotkey_str}, Transform={transform_hotkey_str}")

    def set_processing_state(self, processing: bool):
        with self._lock:
            self.is_processing = processing

    def set_recording_state(self, recording: bool):
        with self._lock:
            self.is_recording = recording

    def _check_match(self, hotkey_str: str) -> bool:
        """Checks if current pressed keys satisfy target hotkey combination string with Win32 physical state backup."""
        if not hotkey_str:
            return False
        parts = [p.strip().lower() for p in hotkey_str.split("+") if p.strip()]
        if not parts:
            return False

        for part in parts:
            if part in ("<ctrl>", "ctrl", "control"):
                is_pynput_down = (keyboard.Key.ctrl_l in self._current_keys or keyboard.Key.ctrl_r in self._current_keys or keyboard.Key.ctrl in self._current_keys)
                is_win32_down = _is_any_vk_down([0x11, 0xA2, 0xA3])
                if not (is_pynput_down or is_win32_down):
                    return False
            elif part in ("<alt>", "alt"):
                is_pynput_down = (keyboard.Key.alt_l in self._current_keys or keyboard.Key.alt_r in self._current_keys or keyboard.Key.alt in self._current_keys or keyboard.Key.alt_gr in self._current_keys)
                is_win32_down = _is_any_vk_down([0x12, 0xA4, 0xA5])
                if not (is_pynput_down or is_win32_down):
                    return False
            elif part in ("<shift>", "shift"):
                is_pynput_down = (keyboard.Key.shift_l in self._current_keys or keyboard.Key.shift_r in self._current_keys or keyboard.Key.shift in self._current_keys)
                is_win32_down = _is_any_vk_down([0x10, 0xA0, 0xA1])
                if not (is_pynput_down or is_win32_down):
                    return False
            elif part in ("<cmd>", "<win>", "win", "cmd", "windows"):
                is_pynput_down = (keyboard.Key.cmd in self._current_keys or keyboard.Key.cmd_l in self._current_keys or keyboard.Key.cmd_r in self._current_keys)
                is_win32_down = _is_any_vk_down([0x5B, 0x5C])
                if not (is_pynput_down or is_win32_down):
                    return False
            elif part in ("<space>", "space"):
                is_pynput_down = keyboard.Key.space in self._current_keys
                is_win32_down = _is_win32_key_down(0x20)
                if not (is_pynput_down or is_win32_down):
                    return False
            elif part in ("<esc>", "esc", "escape"):
                is_pynput_down = keyboard.Key.esc in self._current_keys
                is_win32_down = _is_win32_key_down(0x1B)
                if not (is_pynput_down or is_win32_down):
                    return False
            elif part.startswith("f") and part[1:].isdigit():
                f_idx = int(part[1:])
                f_key = getattr(keyboard.Key, part, None)
                is_pynput_down = f_key in self._current_keys if f_key else False
                is_win32_down = _is_win32_key_down(0x70 + (f_idx - 1)) if (1 <= f_idx <= 12) else False
                if not (is_pynput_down or is_win32_down):
                    return False
            elif len(part) == 1:
                is_pynput_down = any(
                    (isinstance(k, keyboard.KeyCode) and k.char and k.char.lower() == part)
                    for k in self._current_keys
                )
                vk = ord(part.upper())
                is_win32_down = _is_win32_key_down(vk)
                if not (is_pynput_down or is_win32_down):
                    return False
        return True

    def _on_key_press(self, key):
        import time as _time
        with self._lock:
            self._current_keys.add(key)

            # 1. Escape key cancellation check
            if key == keyboard.Key.esc:
                if self.is_recording or self.is_processing:
                    logger.info("Escape pressed: Cancelling active speech session!")
                    self.is_recording = False
                    self.is_processing = False
                    self._main_hotkey_active = False
                    if self.on_cancel:
                        threading.Thread(target=self.on_cancel, daemon=True).start()
                    return

            # 2. Prompt enhancement hotkey check (e.g. Ctrl + Shift + P)
            if self.prompt_hotkey_str and self._check_match(self.prompt_hotkey_str):
                if not self._prompt_hotkey_active:
                    self._prompt_hotkey_active = True
                    logger.info(f"Prompt transformation hotkey matched: {self.prompt_hotkey_str}")
                    if self.on_prompt:
                        threading.Thread(target=self.on_prompt, daemon=True).start()
                return

            # 3. Universal text transformation hotkey check (e.g. Ctrl + Shift + T)
            if self.transform_hotkey_str and self._check_match(self.transform_hotkey_str):
                if not self._transform_hotkey_active:
                    self._transform_hotkey_active = True
                    logger.info(f"Universal transform hotkey matched: {self.transform_hotkey_str}")
                    if self.on_transform:
                        threading.Thread(target=self.on_transform, daemon=True).start()
                return

            # 4. Main Dictation hotkey check (with debounce and autorepeat immunity)
            if self._check_match(self.hotkey_str):
                if not self._main_hotkey_active:
                    self._main_hotkey_active = True
                    now = _time.time()
                    if now - self._last_toggle_time < 0.35:
                        # Ignore bounce within 350ms
                        return
                    self._last_toggle_time = now

                    if self.mode == "toggle":
                        if not self.is_recording:
                            self.is_recording = True
                            if self.on_start:
                                threading.Thread(target=self.on_start, daemon=True).start()
                        else:
                            self.is_recording = False
                            if self.on_stop:
                                threading.Thread(target=self.on_stop, daemon=True).start()
                    elif self.mode == "push_to_talk":
                        if not self.is_recording:
                            self.is_recording = True
                            if self.on_start:
                                threading.Thread(target=self.on_start, daemon=True).start()

    def _on_key_release(self, key):
        with self._lock:
            if key in self._current_keys:
                self._current_keys.discard(key)

            # Check if main hotkey combo is no longer held down
            if self._main_hotkey_active and not self._check_match(self.hotkey_str):
                self._main_hotkey_active = False
                if self.mode == "push_to_talk" and self.is_recording:
                    self.is_recording = False
                    if self.on_stop:
                        threading.Thread(target=self.on_stop, daemon=True).start()

            # Check if prompt / transform hotkeys were released
            if self._prompt_hotkey_active and not self._check_match(self.prompt_hotkey_str):
                self._prompt_hotkey_active = False

            if self._transform_hotkey_active and not self._check_match(self.transform_hotkey_str):
                self._transform_hotkey_active = False

            # Auto-reset any phantom modifiers
            try:
                import ctypes
                user32 = ctypes.windll.user32
                any_modifier_down = any(
                    bool(user32.GetAsyncKeyState(vk) & 0x8000)
                    for vk in (0x11, 0x10, 0x12, 0x5B, 0x5C)
                )
                if not any_modifier_down and not self.is_recording:
                    self._current_keys.clear()
            except Exception:
                pass

    def reset_keys(self):
        """Clears stuck phantom keys in _current_keys using Win32 physical key checks."""
        with self._lock:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                # VK codes: Ctrl=0x11, Shift=0x10, Alt=0x12, LWin=0x5B, RWin=0x5C
                any_modifier_down = any(
                    bool(user32.GetAsyncKeyState(vk) & 0x8000)
                    for vk in (0x11, 0x10, 0x12, 0x5B, 0x5C)
                )
                if not any_modifier_down and self._current_keys:
                    self._current_keys.clear()
            except Exception:
                if not self.is_recording and not self.is_processing:
                    self._current_keys.clear()

    def check_health(self) -> bool:
        """
        Health-check watchdog called periodically.
        Restarts keyboard listener if Windows unhooked or dropped it during sleep/standby.
        """
        self.reset_keys()
        if not self.is_active:
            return True

        if self._listener is None or not self._listener.is_alive():
            logger.warning("Keyboard listener thread was dead or unhooked by Windows. Restarting...")
            self.restart()
            return False
        return True

    def restart(self):
        """Cleanly restarts the listener."""
        self.stop()
        self.start()

    def start(self):
        """Starts the global keyboard listener in the background."""
        if self._listener is not None:
            return
        self.is_active = True
        self._current_keys.clear()
        self._listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._listener.daemon = True
        self._listener.start()
        logger.info(f"Global Hotkey Listener started. Main={self.hotkey_str} ({self.mode}), Prompt={self.prompt_hotkey_str}")

    def stop(self):
        """Stops the global keyboard listener."""
        self.is_active = False
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self._current_keys.clear()
        logger.info("Global Hotkey Listener stopped.")

