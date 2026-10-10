"""
Hotkey Manager for Gemini Flow
Supports Dual-Engine Global Keyboard Shortcuts for Dictation (Toggle & Push-to-Talk),
Prompt Transformation, Universal Rewrite, and Escape Cancellation.

Engine 1: Windows Kernel-Level RegisterHotKey (WM_HOTKEY thread loop with MOD_NOREPEAT)
         - 100% immune to hook timeouts, sleep/standby wakeups, CPU spikes, or Windows unhooking.
Engine 2: pynput.keyboard.Listener (Low-Level Windows Hook WH_KEYBOARD_LL)
         - Real-time key release detection for push-to-talk mode and chord matching.
"""
import ctypes
import logging
import threading
import time
from ctypes import wintypes
from typing import Callable, Optional, Set, Any, Tuple
from pynput import keyboard

logger = logging.getLogger("GeminiFlow.HotkeyManager")

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

HOTKEY_ID_MAIN = 101
HOTKEY_ID_PROMPT = 102
HOTKEY_ID_TRANSFORM = 103


def _is_win32_key_down(vk_code: int) -> bool:
    """Queries Windows OS kernel directly for physical hardware key state."""
    try:
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)
    except Exception:
        return False


def _is_any_vk_down(vk_codes: list) -> bool:
    return any(_is_win32_key_down(vk) for vk in vk_codes)


def _parse_hotkey_to_win32(hotkey_str: str) -> Optional[Tuple[int, int]]:
    """Parses hotkey string (e.g. '<ctrl>+<space>') into (fsModifiers, vkCode) for Win32 RegisterHotKey."""
    if not hotkey_str:
        return None
    parts = [p.strip().lower() for p in hotkey_str.split("+") if p.strip()]
    if not parts:
        return None

    mod = MOD_NOREPEAT
    vk = 0

    for part in parts:
        if part in ("<ctrl>", "ctrl", "control"):
            mod |= MOD_CONTROL
        elif part in ("<alt>", "alt"):
            mod |= MOD_ALT
        elif part in ("<shift>", "shift"):
            mod |= MOD_SHIFT
        elif part in ("<cmd>", "<win>", "win", "cmd", "windows"):
            mod |= MOD_WIN
        elif part in ("<space>", "space"):
            vk = 0x20
        elif part in ("<esc>", "esc", "escape"):
            vk = 0x1B
        elif part.startswith("f") and part[1:].isdigit():
            f_num = int(part[1:])
            if 1 <= f_num <= 12:
                vk = 0x70 + (f_num - 1)
        elif len(part) == 1:
            vk = ord(part.upper())

    if vk == 0:
        return None
    return (mod, vk)


class MSG(ctypes.Structure):
    _fields_ = [
        ('hwnd', wintypes.HWND),
        ('message', wintypes.UINT),
        ('wParam', wintypes.WPARAM),
        ('lParam', wintypes.LPARAM),
        ('time', wintypes.DWORD),
        ('pt', wintypes.POINT)
    ]


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
        self._lock = threading.RLock()

        # Engine 1: Win32 RegisterHotKey Thread State
        self._win32_thread: Optional[threading.Thread] = None
        self._win32_tid: int = 0
        self._win32_ready = threading.Event()

        # State tracking to prevent double-triggering or debouncing across both engines
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

        # Re-register Win32 kernel hotkeys with fresh configuration
        if self.is_active:
            self._restart_win32_thread()

    def set_processing_state(self, processing: bool):
        with self._lock:
            self.is_processing = processing

    def set_recording_state(self, recording: bool):
        with self._lock:
            self.is_recording = recording
            if not recording:
                self._main_hotkey_active = False

    def _handle_main_trigger(self, source: str = "unknown"):
        """Central, synchronized entry point for main dictation hotkey across both engines."""
        with self._lock:
            now = time.time()
            if now - self._last_toggle_time < 0.32:
                # Debounce: suppress duplicate trigger within 320ms across both engines
                return
            self._last_toggle_time = now
            self._main_hotkey_active = True

            if self.mode == "toggle":
                if not self.is_recording:
                    self.is_recording = True
                    logger.info(f"Dictation Hotkey triggered START [Engine: {source}]")
                    if self.on_start:
                        threading.Thread(target=self.on_start, daemon=True, name="HotkeyStartThread").start()
                else:
                    self.is_recording = False
                    logger.info(f"Dictation Hotkey triggered STOP [Engine: {source}]")
                    if self.on_stop:
                        threading.Thread(target=self.on_stop, daemon=True, name="HotkeyStopThread").start()
            elif self.mode == "push_to_talk":
                if not self.is_recording:
                    self.is_recording = True
                    logger.info(f"Push-to-Talk triggered START [Engine: {source}]")
                    if self.on_start:
                        threading.Thread(target=self.on_start, daemon=True, name="HotkeyPushStartThread").start()

    def _handle_prompt_trigger(self, source: str = "unknown"):
        with self._lock:
            now = time.time()
            if self._prompt_hotkey_active and (now - self._last_toggle_time < 0.4):
                return
            self._last_toggle_time = now
            self._prompt_hotkey_active = True
            logger.info(f"Prompt transformation hotkey triggered [Engine: {source}]: {self.prompt_hotkey_str}")
            if self.on_prompt:
                threading.Thread(target=self.on_prompt, daemon=True, name="HotkeyPromptThread").start()

    def _handle_transform_trigger(self, source: str = "unknown"):
        with self._lock:
            now = time.time()
            if self._transform_hotkey_active and (now - self._last_toggle_time < 0.4):
                return
            self._last_toggle_time = now
            self._transform_hotkey_active = True
            logger.info(f"Universal transform hotkey triggered [Engine: {source}]: {self.transform_hotkey_str}")
            if self.on_transform:
                threading.Thread(target=self.on_transform, daemon=True, name="HotkeyTransformThread").start()

    # -------------------------------------------------------------------------
    # ENGINE 1: Windows Kernel-Level RegisterHotKey Thread Loop
    # -------------------------------------------------------------------------
    def _win32_hotkey_loop(self):
        """Dedicated message-pump thread executing Win32 RegisterHotKey with zero CPU consumption."""
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        self._win32_tid = kernel32.GetCurrentThreadId()
        self._win32_ready.set()

        registered_ids = []

        # 1. Register Main Dictation Hotkey
        main_spec = _parse_hotkey_to_win32(self.hotkey_str)
        if main_spec:
            mod, vk = main_spec
            res = user32.RegisterHotKey(0, HOTKEY_ID_MAIN, mod, vk)
            if res:
                registered_ids.append(HOTKEY_ID_MAIN)
                logger.info(f"Win32 RegisterHotKey: Successfully registered Main ({self.hotkey_str})")
            else:
                logger.debug(f"Win32 RegisterHotKey: Could not register Main ({self.hotkey_str}), relying on pynput hook companion.")

        # 2. Register Prompt Enhancement Hotkey
        prompt_spec = _parse_hotkey_to_win32(self.prompt_hotkey_str)
        if prompt_spec:
            mod, vk = prompt_spec
            res = user32.RegisterHotKey(0, HOTKEY_ID_PROMPT, mod, vk)
            if res:
                registered_ids.append(HOTKEY_ID_PROMPT)
                logger.info(f"Win32 RegisterHotKey: Successfully registered Prompt ({self.prompt_hotkey_str})")

        # 3. Register Transform Hotkey
        trans_spec = _parse_hotkey_to_win32(self.transform_hotkey_str)
        if trans_spec:
            mod, vk = trans_spec
            res = user32.RegisterHotKey(0, HOTKEY_ID_TRANSFORM, mod, vk)
            if res:
                registered_ids.append(HOTKEY_ID_TRANSFORM)
                logger.info(f"Win32 RegisterHotKey: Successfully registered Transform ({self.transform_hotkey_str})")

        msg = MSG()
        try:
            while self.is_active:
                # GetMessageW blocks efficiently until a message arrives, using 0% CPU
                ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
                if ret <= 0:
                    break

                if msg.message == WM_HOTKEY:
                    hotkey_id = msg.wParam
                    if hotkey_id == HOTKEY_ID_MAIN:
                        self._handle_main_trigger(source="win32_register_hotkey")
                    elif hotkey_id == HOTKEY_ID_PROMPT:
                        self._handle_prompt_trigger(source="win32_register_hotkey")
                    elif hotkey_id == HOTKEY_ID_TRANSFORM:
                        self._handle_transform_trigger(source="win32_register_hotkey")
                elif msg.message == WM_QUIT:
                    break
        except Exception as e:
            logger.debug(f"Win32 hotkey loop note: {e}")
        finally:
            for hid in registered_ids:
                try:
                    user32.UnregisterHotKey(0, hid)
                except Exception:
                    pass
            logger.debug("Win32 hotkey thread exited cleanly.")

    def _start_win32_thread(self):
        if self._win32_thread and self._win32_thread.is_alive():
            return
        self._win32_ready.clear()
        self._win32_thread = threading.Thread(target=self._win32_hotkey_loop, daemon=True, name="Win32RegisterHotKeyThread")
        self._win32_thread.start()
        self._win32_ready.wait(timeout=2.0)

    def _stop_win32_thread(self):
        if self._win32_tid != 0:
            try:
                ctypes.windll.user32.PostThreadMessageW(self._win32_tid, WM_QUIT, 0, 0)
            except Exception:
                pass
            self._win32_tid = 0
        if self._win32_thread and self._win32_thread.is_alive():
            self._win32_thread.join(timeout=1.0)
        self._win32_thread = None

    def _restart_win32_thread(self):
        self._stop_win32_thread()
        if self.is_active:
            self._start_win32_thread()

    # -------------------------------------------------------------------------
    # ENGINE 2: pynput Low-Level Keyboard Hook
    # -------------------------------------------------------------------------
    def _check_match(self, hotkey_str: str) -> bool:
        """Checks if current pressed keys satisfy target hotkey combination string with Win32 physical state backup."""
        if not hotkey_str:
            return False
        parts = [p.strip().lower() for p in hotkey_str.split("+") if p.strip()]
        if not parts:
            return False

        for part in parts:
            if part in ("<ctrl>", "ctrl", "control"):
                is_pynput_down = any(k in self._current_keys for k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r))
                is_win32_down = _is_any_vk_down([0x11, 0xA2, 0xA3])
                if not (is_pynput_down or is_win32_down):
                    self._current_keys.discard(keyboard.Key.ctrl_l)
                    self._current_keys.discard(keyboard.Key.ctrl_r)
                    self._current_keys.discard(keyboard.Key.ctrl)
                    return False
            elif part in ("<alt>", "alt"):
                is_pynput_down = any(k in self._current_keys for k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr))
                is_win32_down = _is_any_vk_down([0x12, 0xA4, 0xA5])
                if not (is_pynput_down or is_win32_down):
                    self._current_keys.discard(keyboard.Key.alt_l)
                    self._current_keys.discard(keyboard.Key.alt_r)
                    self._current_keys.discard(keyboard.Key.alt)
                    self._current_keys.discard(keyboard.Key.alt_gr)
                    return False
            elif part in ("<shift>", "shift"):
                is_pynput_down = any(k in self._current_keys for k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r))
                is_win32_down = _is_any_vk_down([0x10, 0xA0, 0xA1])
                if not (is_pynput_down or is_win32_down):
                    self._current_keys.discard(keyboard.Key.shift_l)
                    self._current_keys.discard(keyboard.Key.shift_r)
                    self._current_keys.discard(keyboard.Key.shift)
                    return False
            elif part in ("<cmd>", "<win>", "win", "cmd", "windows"):
                is_pynput_down = any(k in self._current_keys for k in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r))
                is_win32_down = _is_any_vk_down([0x5B, 0x5C])
                if not (is_pynput_down or is_win32_down):
                    self._current_keys.discard(keyboard.Key.cmd)
                    self._current_keys.discard(keyboard.Key.cmd_l)
                    self._current_keys.discard(keyboard.Key.cmd_r)
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
                        threading.Thread(target=self.on_cancel, daemon=True, name="HotkeyCancelThread").start()
                    return

            # 2. Prompt enhancement hotkey check
            if self.prompt_hotkey_str and self._check_match(self.prompt_hotkey_str):
                self._handle_prompt_trigger(source="pynput_hook")
                return

            # 3. Universal text transformation hotkey check
            if self.transform_hotkey_str and self._check_match(self.transform_hotkey_str):
                self._handle_transform_trigger(source="pynput_hook")
                return

            # 4. Main Dictation hotkey check
            if self._check_match(self.hotkey_str):
                self._handle_main_trigger(source="pynput_hook")

    def _on_key_release(self, key):
        with self._lock:
            if key in self._current_keys:
                self._current_keys.discard(key)

            # Check if main hotkey combo is no longer held down
            if self._main_hotkey_active and not self._check_match(self.hotkey_str):
                self._main_hotkey_active = False
                if self.mode == "push_to_talk" and self.is_recording:
                    self.is_recording = False
                    logger.info("Push-to-Talk key released: stopping speech capture.")
                    if self.on_stop:
                        threading.Thread(target=self.on_stop, daemon=True, name="HotkeyPushStopThread").start()

            # Check if prompt / transform hotkeys were released
            if self._prompt_hotkey_active and not self._check_match(self.prompt_hotkey_str):
                self._prompt_hotkey_active = False

            if self._transform_hotkey_active and not self._check_match(self.transform_hotkey_str):
                self._transform_hotkey_active = False

            # Auto-reset any phantom modifiers only when a modifier key itself was released
            if key in (
                keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr,
                keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r,
                keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r
            ):
                try:
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
        """Clears stuck phantom keys in _current_keys using Win32 physical key checks without disrupting active recording."""
        with self._lock:
            if not self.is_recording and not self.is_processing:
                self._main_hotkey_active = False
                self._prompt_hotkey_active = False
                self._transform_hotkey_active = False
            try:
                user32 = ctypes.windll.user32
                any_modifier_down = any(
                    bool(user32.GetAsyncKeyState(vk) & 0x8000)
                    for vk in (0x11, 0x10, 0x12, 0x5B, 0x5C)
                )
                if not any_modifier_down and not self.is_recording and not self.is_processing:
                    self._current_keys.clear()
            except Exception:
                if not self.is_recording and not self.is_processing:
                    self._current_keys.clear()

    def check_health(self) -> bool:
        """
        Health-check watchdog called periodically.
        Verifies both Win32 RegisterHotKey thread and pynput listener.
        Restarts keyboard listener if Windows unhooked or dropped it during sleep/standby.
        """
        if not self.is_recording and not self.is_processing:
            self.reset_keys()
        if not self.is_active:
            return True

        listener_healthy = (self._listener is not None and self._listener.is_alive())
        win32_healthy = (self._win32_thread is not None and self._win32_thread.is_alive())

        if not listener_healthy or not win32_healthy:
            logger.warning(f"Dual-Engine health check: listener={listener_healthy}, win32={win32_healthy}. Restoring hotkeys...")
            self.restart()
            return False
        return True

    def restart(self):
        """Cleanly restarts both hotkey engines."""
        self.stop()
        self.start()

    def start(self):
        """Starts both hotkey engines in the background."""
        if self.is_active:
            return
        self.is_active = True
        self._current_keys.clear()

        # Start Engine 1: Windows Kernel-Level RegisterHotKey Thread
        self._start_win32_thread()

        # Start Engine 2: pynput Low-Level Keyboard Hook
        self._listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._listener.daemon = True
        self._listener.start()

        logger.info(f"Dual-Engine Global Hotkey System started: Main={self.hotkey_str} ({self.mode}), Prompt={self.prompt_hotkey_str}")

    def stop(self):
        """Stops both hotkey engines cleanly."""
        self.is_active = False

        # Stop Engine 1
        self._stop_win32_thread()

        # Stop Engine 2
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

        self._current_keys.clear()
        logger.info("Dual-Engine Global Hotkey System stopped.")
